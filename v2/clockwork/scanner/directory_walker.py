import os
from pathlib import Path
from typing import List, Set

EXCLUDED_DIRS: Set[str] = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "build", "dist", ".clockwork", ".mypy_cache", ".pytest_cache"
}

class DirectoryWalker:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.ignore_patterns = self._load_ignore_patterns()

    def _load_ignore_patterns(self) -> List[str]:
        patterns = []
        for ignore_file in [".gitignore", ".clockworkignore"]:
            p = self.root / ignore_file
            if p.exists():
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
        return patterns

    def _is_ignored(self, path: Path) -> bool:
        name = path.name
        if name in EXCLUDED_DIRS:
            return True
        for pattern in self.ignore_patterns:
            if path.match(pattern):
                return True
        return False

    def walk(self) -> List[Path]:
        result = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            current = Path(dirpath)
            dirnames[:] = [
                d for d in dirnames
                if not self._is_ignored(current / d)
            ]
            for fname in filenames:
                fpath = current / fname
                if not self._is_ignored(fpath):
                    result.append(fpath)
        return result

    def get_tree(self) -> dict:
        tree = {}
        for fpath in self.walk():
            rel = fpath.relative_to(self.root)
            parts = rel.parts
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = str(fpath)
        return tree