"""
clockwork/packaging/packer.py
------------------------------
PackagingEngine — builds a portable .clockwork archive.

Pipeline (spec §6):
    Context Load
    ↓
    Repository Scan Validation
    ↓
    Rule Engine Validation
    ↓
    Brain Verification
    ↓
    Package Assembly
    ↓
    File Compression
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from clockwork.packaging.checksum import (
    compute_directory_checksum,
    write_checksum_file,
    build_manifest,
)
from clockwork.packaging.models import (
    PackageMetadata,
    SENSITIVE_EXCLUSIONS,
    REQUIRED_SOURCE_FILES,
    OPTIONAL_SOURCE_FILES,
    CLOCKWORK_VERSION,
    PACKAGE_SCHEMA_VERSION,
)


class PackagingError(Exception):
    """Raised when the packaging pipeline cannot proceed."""


class PackagingEngine:
    """
    Builds and exports a .clockwork package from the project's .clockwork directory.

    Usage::

        engine = PackagingEngine(repo_root=Path("/path/to/repo"))
        output_path = engine.pack()          # returns Path to .clockwork file
    """

    PACKAGE_STORE = ".clockwork/packages"

    def __init__(
        self,
        repo_root: Path,
        output_dir: Optional[Path] = None,
        project_name: Optional[str] = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.output_dir: Path = output_dir or (self.repo_root / self.PACKAGE_STORE)
        self.project_name = project_name or self.repo_root.name

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def pack(self) -> Path:
        """
        Execute the full packaging pipeline and return the path to the
        generated .clockwork archive.

        Raises PackagingError on validation failure.
        """
        start = time.perf_counter()

        print("Clockwork Pack — starting packaging pipeline...")

        # 1. Context Load & Validation
        self._validate_clockwork_dir()
        self._validate_required_files()

        # 2. Collect files
        files_to_pack = self._collect_files()

        # 3. Assemble package in a temp directory
        with tempfile.TemporaryDirectory(prefix="clockwork_pack_") as tmp:
            staging = Path(tmp) / "staging"
            staging.mkdir()

            self._copy_files(files_to_pack, staging)

            # 4. Write metadata
            metadata = self._build_metadata(staging)
            (staging / "metadata.json").write_text(
                metadata.to_json(), encoding="utf-8"
            )

            # 5. Compute checksum over staged content (excluding the checksum file)
            #    The loader replicates this exclusion when verifying.
            checksum = compute_directory_checksum(staging)
            write_checksum_file(checksum, staging / "package_checksum.txt")

            # 6. Compress
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{self.project_name}.clockwork"
            self._compress(staging, output_path)

        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"Package created: {output_path}")
        print(f"Completed in {elapsed_ms:.1f} ms")
        return output_path

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    def _validate_clockwork_dir(self) -> None:
        """Ensure .clockwork directory exists."""
        if not self.clockwork_dir.is_dir():
            raise PackagingError(
                "Clockwork not initialized in this repository.\n"
                "Run:  clockwork init"
            )

    def _validate_required_files(self) -> None:
        """Ensure all required source files are present."""
        missing = [
            f
            for f in REQUIRED_SOURCE_FILES
            if not (self.clockwork_dir / f).exists()
        ]
        if missing:
            raise PackagingError(
                f"Required files missing from .clockwork/:\n"
                + "\n".join(f"  - {m}" for m in missing)
                + "\nRun:  clockwork scan && clockwork update"
            )

    def _collect_files(self) -> list[tuple[Path, str]]:
        """
        Return a list of (absolute_path, archive_name) tuples.

        Includes required + optional files; excludes sensitive filenames.
        """
        collected: list[tuple[Path, str]] = []

        # Required files
        for rel in REQUIRED_SOURCE_FILES:
            src = self.clockwork_dir / rel
            if src.exists():
                collected.append((src, rel))

        # Optional files
        for rel in OPTIONAL_SOURCE_FILES:
            src = self.clockwork_dir / rel
            if src.exists():
                collected.append((src, rel))

        # Filter sensitive files
        collected = [
            (p, name)
            for p, name in collected
            if not self._is_sensitive(name)
        ]

        return collected

    @staticmethod
    def _is_sensitive(filename: str) -> bool:
        """Return True if the filename matches any sensitive pattern."""
        base = Path(filename).name.lower()
        for pattern in SENSITIVE_EXCLUSIONS:
            # Simple wildcard support: *.ext
            if pattern.startswith("*"):
                if base.endswith(pattern[1:]):
                    return True
            elif base == pattern.lower():
                return True
        return False

    def _copy_files(
        self, files: list[tuple[Path, str]], staging: Path
    ) -> None:
        """Copy collected files into the staging directory."""
        for src, archive_name in files:
            dest = staging / archive_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    def _build_metadata(self, staging: Path) -> PackageMetadata:
        """Build and return a PackageMetadata instance."""
        manifest = build_manifest(staging)
        return PackageMetadata(
            clockwork_version=CLOCKWORK_VERSION,
            package_version=PACKAGE_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            project_name=self.project_name,
            source_machine=platform.node(),
            file_manifest=list(manifest.keys()),
        )

    @staticmethod
    def _compress(staging: Path, output_path: Path) -> None:
        """Compress the staging directory into a ZIP-based .clockwork archive."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(staging.rglob("*")):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(staging))
                    zf.write(file_path, arcname)
