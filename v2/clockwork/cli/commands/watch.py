import time
from pathlib import Path
from context.live_index.sync_engine import SyncEngine
from cli.utils import output as out

class WatchCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, root: str = "."):
        out.check_initialized()
        out.header("Live Context Index")
        out.info("Starting real-time repository monitoring...")
        self.state.emit_event("watch_started", {"root": root})

        graph_builder = None
        try:
            from graph.graph_builder import GraphBuilder
            graph_builder = GraphBuilder()
        except Exception:
            out.warn("Graph builder unavailable — graph updates disabled.")

        rule_engine = None
        try:
            from rules.rule_engine import RuleEngine
            rule_engine = RuleEngine()
        except Exception:
            pass

        engine = SyncEngine(
            root=root,
            context_engine=self.context,
            graph_builder=graph_builder,
            rule_engine=rule_engine,
        )

        def on_modified(event):
            path = event.get("path","")
            out.info("Modified: " + path)
            if rule_engine:
                result = rule_engine.validate({"type": "modify", "target": path})
                if not result.approved:
                    out.warn("Rule violation on change: " + result.reason)

        def on_created(event):
            out.info("Created:  " + event.get("path",""))

        def on_deleted(event):
            out.warn("Deleted:  " + event.get("path",""))

        engine.processor.register("modified", on_modified)
        engine.processor.register("created",  on_created)
        engine.processor.register("deleted",  on_deleted)

        ok = engine.start()
        if not ok:
            out.error_with_hint(
                "watchdog not installed.",
                "Run: pip install watchdog"
            )
            return None

        out.success("Watching: " + root)
        out.info("Press Ctrl+C to stop.")

        try:
            interval = 10
            while True:
                time.sleep(interval)
                stats = engine.stats()
                out.info(
                    "Uptime: " + str(stats["uptime_s"]) + "s | "
                    "Events: " + str(stats["events_processed"]) + " | "
                    "Pending: " + str(stats["queue_pending"])
                )
        except KeyboardInterrupt:
            engine.stop()
            self.state.emit_event("watch_stopped", engine.stats())
            out.success("Watch stopped.")

        return engine.stats()