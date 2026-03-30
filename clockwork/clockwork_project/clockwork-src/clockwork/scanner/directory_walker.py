from __future__ import annotations

import os
from pathlib import Path


def walk_files(root: str | Path, ignore_dirs: set[str] | None = None) -> list[str]:
    ignore_dirs = ignore_dirs or {".git", ".venv", "__pycache__", "node_modules"}
    root_path = Path(root).resolve()
    files: list[str] = []
    for dirpath, dirs, names in os.walk(root_path):
        dirs[:] = [name for name in dirs if name not in ignore_dirs]
        for name in names:
            files.append(str((Path(dirpath) / name).resolve()))
    return files


class DirectoryWalker:
    """Compatibility wrapper for v2 scanner tests."""

    def __init__(self, root: str | Path, ignore_dirs: set[str] | None = None) -> None:
        self.root = root
        self.ignore_dirs = ignore_dirs

    def walk(self) -> list[str]:
        return walk_files(self.root, self.ignore_dirs)


