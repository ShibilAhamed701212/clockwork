import time
from pathlib import Path
from scanner.scanner import Scanner
from graph.graph_builder import GraphBuilder
from cli.utils import output as out

class ScanCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, root: str = ".", focus: str = "", json_mode: bool = False, verbose: bool = False):
        out.check_initialized()
        out.header("Repository Scanner")
        self.state.emit_event("scan_started", {"root": root})
        t0     = time.time()
        target = focus if focus else root
        out.info("Scanning: " + target)
        scanner  = Scanner(root=target)
        repo_map = scanner.run()
        try:
            builder       = GraphBuilder()
            graph_summary = builder.build_from_repo_map(repo_map)
            compressed    = builder.compress()
            self.context.set("graph_summary", compressed)
        except Exception as e:
            out.warn("Graph warning: " + str(e))
            graph_summary = {}
        self.context.sync_from_scanner(repo_map)
        elapsed = round(time.time() - t0, 3)
        meta    = repo_map.get("meta", {})
        langs   = repo_map.get("languages", {})
        arch    = repo_map.get("architecture", {})
        skills  = repo_map.get("skills", [])
        rels    = repo_map.get("relationships", {})
        self.state.emit_event("scan_completed", {
            "files": meta.get("total_files",0),
            "language": langs.get("primary",""),
            "arch": arch.get("type",""),
        })
        if json_mode:
            out.json_output({
                "files": meta.get("total_files",0),
                "language": langs.get("primary",""),
                "architecture": arch.get("type",""),
                "skills": skills, "duration_s": elapsed,
                "anomalies": len(rels.get("anomalies",[])),
            })
        else:
            out.result("Files",        meta.get("total_files",0))
            out.result("Language",     langs.get("primary","unknown"))
            out.result("Architecture", arch.get("type","unknown"))
            out.result("Skills",       ", ".join(skills))
            out.result("Duration",     str(elapsed) + "s")
            if rels.get("anomalies"):
                out.warn("Anomalies: " + str(len(rels["anomalies"])))
            if rels.get("circular_imports"):
                out.warn("Circular: " + str(len(rels["circular_imports"])))
            out.success("Scan complete.")
        return repo_map