from __future__ import annotations


def map_relationships(files: list[dict]) -> dict:
    graph: dict[str, dict] = {}
    for file_entry in files:
        path = file_entry.get("path", "")
        imports = file_entry.get("imports", [])
        graph[path] = {"imports": imports}
    circular_imports: list[str] = []
    for source, payload in graph.items():
        for target in payload.get("imports", []):
            target_payload = graph.get(target, {})
            if source in target_payload.get("imports", []):
                cycle = f"{source} <-> {target}"
                if cycle not in circular_imports:
                    circular_imports.append(cycle)
    return {"graph": graph, "circular_imports": circular_imports}


class RelationshipMapper:
    """Compatibility mapper for v2 scanner tests."""

    def __init__(self, files: list[str], root) -> None:
        self.files = files
        self.root = root

    def map(self) -> dict:
        file_entries = [{"path": str(path), "imports": []} for path in self.files]
        return map_relationships(file_entries)

