from __future__ import annotations

from pathlib import Path


def parse_rules_markdown(rules_path: str | Path) -> list[str]:
    path = Path(rules_path)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [line[2:].strip() for line in lines if line.strip().startswith("- ")]

