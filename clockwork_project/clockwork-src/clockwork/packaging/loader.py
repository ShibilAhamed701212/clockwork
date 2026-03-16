"""
clockwork/packaging/loader.py
------------------------------
PackageLoader — imports a .clockwork archive into the local repository.

Import Pipeline (spec §9):
    Package Load
    ↓
    Integrity Validation
    ↓
    Context Merge
    ↓
    Rule Validation
    ↓
    Context Activation
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

from clockwork.packaging.checksum import (
    compute_directory_checksum,
    verify_checksum_file,
)
from clockwork.packaging.models import PackageMetadata


class LoadError(Exception):
    """Raised when a package cannot be loaded."""


class PackageLoader:
    """
    Loads a .clockwork package into a target repository.

    Usage::

        loader = PackageLoader(repo_root=Path("/path/to/repo"))
        loader.load(package_path=Path("project.clockwork"))
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load(self, package_path: Path) -> None:
        """
        Execute the full import pipeline for *package_path*.

        Raises LoadError if validation fails at any stage.
        """
        start = time.perf_counter()

        print(f"Clockwork Load — importing {package_path.name}...")

        # 1. Package Load — extract to temp
        package_path = package_path.resolve()
        if not package_path.exists():
            raise LoadError(f"Package file not found: {package_path}")

        if not zipfile.is_zipfile(package_path):
            raise LoadError(
                f"'{package_path.name}' is not a valid .clockwork archive."
            )

        with tempfile.TemporaryDirectory(prefix="clockwork_load_") as tmp:
            staging = Path(tmp) / "extracted"
            staging.mkdir()

            self._extract(package_path, staging)

            # 2. Integrity Validation
            self._validate_integrity(staging)

            # 3. Compatibility Validation
            metadata = self._load_metadata(staging)
            self._validate_compatibility(metadata)

            # 4. Context Merge — copy files into .clockwork
            self._merge_context(staging)

        elapsed_ms = (time.perf_counter() - start) * 1000
        print("Package loaded successfully.")
        print(f"Project: {metadata.project_name}  |  Packed: {metadata.generated_at}")
        print(f"Completed in {elapsed_ms:.1f} ms")

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract(package_path: Path, staging: Path) -> None:
        """Unzip the archive into the staging directory."""
        with zipfile.ZipFile(package_path, "r") as zf:
            zf.extractall(staging)

    def _validate_integrity(self, staging: Path) -> None:
        """
        Verify the package checksum.

        Re-computes the directory checksum (excluding the checksum file itself)
        and compares it against the stored value.
        """
        checksum_file = staging / "package_checksum.txt"
        if not checksum_file.exists():
            raise LoadError(
                "Package integrity check failed: 'package_checksum.txt' not found.\n"
                "The archive may be corrupt or tampered with."
            )

        # Compute checksum over everything *except* the checksum file itself.
        # Move it outside the staging directory so rglob does not pick it up.
        stored = checksum_file.read_text(encoding="utf-8").strip()
        tmp_check = staging.parent / "_cw_checksum_verify.txt"
        checksum_file.rename(tmp_check)
        try:
            actual = compute_directory_checksum(staging)
        finally:
            tmp_check.rename(checksum_file)

        if stored != actual:
            raise LoadError(
                "Package integrity check FAILED.\n"
                f"  Expected: {stored}\n"
                f"  Actual:   {actual}\n"
                "The package may be corrupt or has been modified."
            )

        print("  ✓ Integrity check passed.")

    @staticmethod
    def _load_metadata(staging: Path) -> PackageMetadata:
        """Parse and return the package metadata."""
        meta_path = staging / "metadata.json"
        if not meta_path.exists():
            raise LoadError(
                "Package is missing 'metadata.json'. Cannot determine compatibility."
            )
        return PackageMetadata.from_json(meta_path.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_compatibility(metadata: PackageMetadata) -> None:
        """Refuse loading if version is incompatible."""
        if not metadata.is_compatible():
            raise LoadError(
                f"Incompatible package version.\n"
                f"  Package clockwork_version : {metadata.clockwork_version}\n"
                f"  Package schema_version    : {metadata.package_version}\n"
                f"  Running clockwork_version : {metadata.clockwork_version}\n"
                "Upgrade Clockwork or use a compatible package."
            )
        print(f"  ✓ Compatibility check passed (v{metadata.clockwork_version}).")

    def _merge_context(self, staging: Path) -> None:
        """
        Copy staged files into .clockwork/, creating directories as needed.

        Skips metadata and checksum files — those are package-internal.
        """
        skip = {"metadata.json", "package_checksum.txt"}
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for src in sorted(staging.rglob("*")):
            if not src.is_file():
                continue
            rel = str(src.relative_to(staging))
            if rel in skip:
                continue

            dest = self.clockwork_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(rel)

        print(f"  ✓ Context merged: {len(copied)} file(s) restored.")
        for name in copied:
            print(f"    → .clockwork/{name}")
