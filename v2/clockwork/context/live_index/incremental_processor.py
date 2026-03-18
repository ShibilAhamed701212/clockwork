import ast
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

INDEX_DB = Path(".clockwork/index.db")

class FileIndex:
    def __init__(self, db_path: Path = INDEX_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_index (
                    file_path     TEXT PRIMARY KEY,
                    hash          TEXT,
                    last_modified REAL,
                    module_type   TEXT,
                    dependencies  TEXT,
                    language      TEXT,
                    updated_at    REAL
                )
            """)
            conn.commit()

    def get(self, file_path: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM file_index WHERE file_path=?", (file_path,)
            ).fetchone()
        if not row:
            return None
        return {"file_path": row[0], "hash": row[1], "last_modified": row[2],
                "module_type": row[3], "dependencies": row[4],
                "language": row[5], "updated_at": row[6]}

    def upsert(self, file_path: str, file_hash: str, last_modified: float,
               module_type: str = "", dependencies: str = "", language: str = ""):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_index
                (file_path, hash, last_modified, module_type, dependencies, language, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_path, file_hash, last_modified, module_type, dependencies, language, time.time()))
            conn.commit()

    def delete(self, file_path: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM file_index WHERE file_path=?", (file_path,))
            conn.commit()

    def has_changed(self, file_path: str) -> bool:
        p = Path(file_path)
        if not p.exists():
            return True
        record = self.get(file_path)
        if not record:
            return True
        try:
            content  = p.read_bytes()
            new_hash = hashlib.md5(content).hexdigest()
            return new_hash != record["hash"]
        except Exception:
            return True

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM file_index").fetchone()[0]

    def clear(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM file_index")
            conn.commit()


class IncrementalProcessor:
    def __init__(self, context_engine=None, graph_builder=None, rule_engine=None):
        self.context      = context_engine
        self.graph        = graph_builder
        self.rule_engine  = rule_engine
        self.index        = FileIndex()
        self.handlers:    Dict[str, List[Callable]] = {}
        self.processed    = 0
        self.errors       = 0
        self._debounce:   Dict[str, float] = {}
        self.DEBOUNCE_MS  = 0.2

    def register(self, event_type: str, handler: Callable):
        self.handlers.setdefault(event_type, []).append(handler)

    def process_event(self, event: Dict) -> bool:
        etype = event.get("type","")
        path  = event.get("path","")

        if not self._should_process(path):
            return False

        t0 = time.time()
        try:
            if etype in ("modified","created"):
                self._process_change(path, etype)
            elif etype == "deleted":
                self._process_delete(path)
            elif etype == "moved":
                self._process_delete(event.get("src", path))
                self._process_change(path, "created")

            for handler in self.handlers.get(etype, []):
                try:
                    handler(event)
                except Exception as e:
                    print("[IncrementalProcessor] Handler error: " + str(e))

            self.processed += 1
            elapsed = round((time.time() - t0) * 1000, 1)
            print("[IncrementalProcessor] " + etype + " -> " + path + " (" + str(elapsed) + "ms)")
            return True
        except Exception as e:
            self.errors += 1
            print("[IncrementalProcessor] Error processing " + path + ": " + str(e))
            return False

    def process_all(self, events: List[Dict]) -> int:
        count = 0
        for event in events:
            if self.process_event(event):
                count += 1
        return count

    def _should_process(self, path: str) -> bool:
        now  = time.time()
        last = self._debounce.get(path, 0)
        if now - last < self.DEBOUNCE_MS:
            return False
        self._debounce[path] = now
        return True

    def _process_change(self, path: str, etype: str):
        p = Path(path)
        if not p.exists():
            return

        if not self.index.has_changed(path):
            return

        content = p.read_bytes()
        h       = hashlib.md5(content).hexdigest()
        mtime   = p.stat().st_mtime
        lang    = self._detect_lang(path)
        deps    = self._extract_deps(path, lang)
        mtype   = self._classify_module(path)

        self.index.upsert(path, h, mtime, mtype, ",".join(deps), lang)

        if self.graph:
            try:
                self.graph.nodes.clear_by_file(path)
                layer = self.graph._infer_layer(path)
                nid   = self.graph.nodes.upsert("file", p.name, path, lang, layer)
                for dep in deps:
                    tid = self.graph.nodes.upsert("module", dep, "", lang, "")
                    self.graph.edges.add(nid, tid, "imports", p.name, dep)
            except Exception as e:
                print("[IncrementalProcessor] Graph update error: " + str(e))

        if self.context:
            try:
                self.context.record_event("file_" + etype, {"path": path, "lang": lang})
            except Exception:
                pass

    def _process_delete(self, path: str):
        self.index.delete(path)
        if self.graph:
            try:
                self.graph.nodes.clear_by_file(path)
            except Exception:
                pass
        if self.context:
            try:
                self.context.record_event("file_deleted", {"path": path})
            except Exception:
                pass

    def _detect_lang(self, path: str) -> str:
        ext_map = {".py":"Python",".js":"JavaScript",".ts":"TypeScript",
                   ".go":"Go",".rs":"Rust",".java":"Java",".rb":"Ruby"}
        return ext_map.get(Path(path).suffix.lower(), "unknown")

    def _extract_deps(self, path: str, lang: str) -> List[str]:
        if lang != "Python":
            return []
        try:
            source = Path(path).read_text(encoding="utf-8", errors="ignore")
            tree   = ast.parse(source)
            deps   = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.append(node.module.split(".")[0])
            return list(set(deps))[:20]
        except Exception:
            return []

    def _classify_module(self, path: str) -> str:
        lower = path.replace("\\","/").lower()
        if "test" in lower:      return "test"
        if "config" in lower:    return "config"
        if "model" in lower:     return "model"
        if "route" in lower or "api" in lower: return "api"
        if "util" in lower:      return "utility"
        return "module"

    def stats(self) -> Dict:
        return {
            "processed":    self.processed,
            "errors":       self.errors,
            "indexed_files":self.index.count(),
        }

    def rebuild_index(self, root: str = "."):
        print("[IncrementalProcessor] Rebuilding index from scratch...")
        self.index.clear()
        walker_root = Path(root)
        count = 0
        for p in walker_root.rglob("*"):
            if p.is_file() and p.suffix in {".py",".js",".ts",".go",".rs"}:
                self._process_change(str(p), "created")
                count += 1
        print("[IncrementalProcessor] Index rebuilt: " + str(count) + " files")
        return count