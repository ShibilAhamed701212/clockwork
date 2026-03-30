"""
clockwork/packaging/checksum.py
--------------------------------
Checksum utilities for package integrity verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Return the hex digest of a single file."""
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_directory_checksum(directory: Path, algorithm: str = "sha256") -> str:
    """
    Compute a deterministic checksum over all files inside *directory*.

    Files are sorted by relative path so the result is stable across
    machines regardless of filesystem ordering.
    """
    h = hashlib.new(algorithm)
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue
        # Include relative path in the hash so renames are detected.
        relative = str(file_path.relative_to(directory))
        h.update(relative.encode())
        h.update(b"\n")
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65_536), b""):
                h.update(chunk)
    return h.hexdigest()


def write_checksum_file(checksum: str, destination: Path) -> None:
    """Write checksum string to *destination*."""
    destination.write_text(checksum, encoding="utf-8")


def verify_checksum_file(checksum: str, checksum_file: Path) -> bool:
    """Return True if the stored checksum matches *checksum*."""
    if not checksum_file.exists():
        return False
    stored = checksum_file.read_text(encoding="utf-8").strip()
    return stored == checksum


def build_manifest(directory: Path) -> dict[str, str]:
    """
    Build a {relative_path: sha256} manifest for all files in *directory*.
    Used for fine-grained integrity reporting.
    """
    manifest: dict[str, str] = {}
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel = str(file_path.relative_to(directory))
            manifest[rel] = compute_file_checksum(file_path)
    return manifest
