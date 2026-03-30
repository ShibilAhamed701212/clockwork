from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from clockwork.index.index_engine import LiveContextIndex


class FileIndex:
    """Lightweight compatibility index used by v2 parity tests."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    file_path TEXT PRIMARY KEY,
                    hash TEXT,
                    mtime REAL,
                    module_type TEXT,
                    framework TEXT,
                    language TEXT
                )
                """
            )
            conn.commit()

    def upsert(self, file_path: str, file_hash: str, mtime: float, module_type: str, framework: str, language: str) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files (file_path, hash, mtime, module_type, framework, language)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_path, file_hash, mtime, module_type, framework, language),
            )
            conn.commit()

    def get(self, file_path: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT file_path, hash, mtime, module_type, framework, language FROM files WHERE file_path=?",
                (file_path,),
            ).fetchone()
        if not row:
            return None
        return {
            "file_path": row[0],
            "hash": row[1],
            "mtime": row[2],
            "module_type": row[3],
            "framework": row[4],
            "language": row[5],
        }

    def delete(self, file_path: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM files WHERE file_path=?", (file_path,))
            conn.commit()


class IncrementalProcessor:
    def __init__(self, context_engine: object | None = None, graph_builder: object | None = None, rule_engine: object | None = None, repo_root: Path | None = None) -> None:
        self.context_engine = context_engine
        self.graph_builder = graph_builder
        self.rule_engine = rule_engine
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.index = LiveContextIndex(self.repo_root)
        self._processed = 0
        self._errors = 0

    def process_event(self, event: dict) -> bool:
        path = str(event.get("path", ""))
        event_type = str(event.get("type", "modified"))
        if not path:
            self._errors += 1
            return False

        try:
            if isinstance(self.index, FileIndex):
                if event_type == "deleted":
                    self.index.delete(path)
                else:
                    file_path = Path(path)
                    if not file_path.exists() or not file_path.is_file():
                        self.index.delete(path)
                    else:
                        content = file_path.read_bytes()
                        file_hash = hashlib.sha256(content).hexdigest()
                        self.index.upsert(
                            path,
                            file_hash,
                            file_path.stat().st_mtime,
                            "module",
                            "",
                            "Python" if file_path.suffix.lower() == ".py" else "Other",
                        )
            else:
                if event_type == "deleted":
                    self.index.update_file(path)
                else:
                    self.index.update_file(path)
            self._processed += 1
            return True
        except Exception:
            self._errors += 1
            return False

    def process_all(self, events: list[dict]) -> int:
        count = 0
        for event in events:
            if self.process_event(event):
                count += 1
        return count

    def rebuild_index(self, root: str) -> None:
        self.index.repair()

    def stats(self) -> dict:
        return {"processed": self._processed, "errors": self._errors}

