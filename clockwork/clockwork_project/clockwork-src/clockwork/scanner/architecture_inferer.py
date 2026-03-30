from __future__ import annotations


def infer_architecture(repo_map: dict) -> dict:
    files = repo_map.get("files", [])
    paths = [str(item.get("path", "")).lower() for item in files]
    score = {"cli": 0, "frontend": 0, "backend": 0}
    for path in paths:
        if "cli" in path:
            score["cli"] += 1
        if any(token in path for token in ["frontend", "ui", "pages", "components"]):
            score["frontend"] += 1
        if any(token in path for token in ["api", "server", "service", "backend"]):
            score["backend"] += 1
    inferred = max(score, key=score.get) if score else "unknown"
    confidence = "low"
    if score.get(inferred, 0) >= 10:
        confidence = "high"
    elif score.get(inferred, 0) >= 3:
        confidence = "medium"
    components: dict[str, list[str]] = {}
    for item in files:
        path = str(item.get("path", ""))
        if not path:
            continue
        key = path.split("/")[0] if "/" in path else path.split("\\")[0]
        components.setdefault(key, []).append(path)
    return {"type": inferred, "confidence": confidence, "scores": score, "components": components}


class ArchitectureInferer:
    """Compatibility inferer that accepts file paths and repository root."""

    def __init__(self, files: list[str], root) -> None:
        self.files = files
        self.root = root

    def infer(self) -> dict:
        repo_map = {"files": [{"path": str(path)} for path in self.files]}
        return infer_architecture(repo_map)

