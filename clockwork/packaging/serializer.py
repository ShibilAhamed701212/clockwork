from __future__ import annotations

import json
from pathlib import Path


def serialize_package(data: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def deserialize_package(input_path: str | Path) -> dict:
    path = Path(input_path)
    return json.loads(path.read_text(encoding="utf-8"))

