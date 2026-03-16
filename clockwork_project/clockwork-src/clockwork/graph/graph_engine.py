"""Graph Engine."""
import json, sqlite3
from pathlib import Path
from typing import Any

class GraphEngine:
    def __init__(self, repo_path: Path) -> None:
        self.d = repo_path / ".clockwork"
        self.db = self.d / "knowledge_graph.db"

    def build(self) -> None:
        rm_p = self.d/"repo_map.json"
        rm = json.loads(rm_p.read_text()) if rm_p.exists() else {}
        conn = sqlite3.connect(self.db)
        conn.execute("DROP TABLE IF EXISTS files")
        conn.execute("DROP TABLE IF EXISTS languages")
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, language TEXT, size_bytes INTEGER)")
        conn.execute("CREATE TABLE languages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_count INTEGER)")
        for f in rm.get("files",[]): conn.execute("INSERT INTO files VALUES (NULL,?,?,?)",(f.get("path",""),f.get("language",""),f.get("size_bytes",0)))
        for lang, cnt in rm.get("language_counts",{}).items(): conn.execute("INSERT INTO languages VALUES (NULL,?,?)",(lang,cnt))
        conn.commit(); conn.close()
