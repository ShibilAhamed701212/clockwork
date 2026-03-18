import argparse
import sys
from cli.utils import output as out
from cli.utils.parser import IntentParser
from config.settings import Settings
from state.state_manager import StateManager
from context.context_engine import ContextEngine

class ClockworkCLI:
    def __init__(self, settings, state, context):
        self.settings      = settings
        self.state         = state
        self.context       = context
        self.intent_parser = IntentParser()
        self.parser        = self._build_parser()

    def _build_parser(self):
        parser = argparse.ArgumentParser(prog="clockwork", description="Clockwork AI OS")
        parser.add_argument("--mode",    choices=["safe","balanced","aggressive"])
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--json",    action="store_true")
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("init")
        p_scan = sub.add_parser("scan")
        p_scan.add_argument("--focus",   default="")
        p_scan.add_argument("--json",    action="store_true")
        p_scan.add_argument("--verbose", action="store_true")
        p_verify = sub.add_parser("verify")
        p_verify.add_argument("--json",    action="store_true")
        p_verify.add_argument("--explain", action="store_true")
        sub.add_parser("update")
        p_handoff = sub.add_parser("handoff")
        p_handoff.add_argument("--to", default="next_agent")
        p_pack = sub.add_parser("pack")
        p_pack.add_argument("--label", default="")
        p_load = sub.add_parser("load")
        p_load.add_argument("path",      nargs="?", default="")
        p_load.add_argument("--merge",   action="store_true")
        p_load.add_argument("--inspect", action="store_true")
        p_graph = sub.add_parser("graph")
        p_graph.add_argument("--query", default="status",
                              choices=["status","build","anomalies","health","deps","tasks"])
        sub.add_parser("watch")
        sub.add_parser("repair")
        p_agent = sub.add_parser("agent")
        p_agent.add_argument("--goal",          default="analyze repository")
        p_agent.add_argument("--json",          action="store_true")
        p_agent.add_argument("--explain",       action="store_true")
        p_agent.add_argument("--auto-priority", action="store_true", dest="auto_priority")
        p_status = sub.add_parser("status")
        p_status.add_argument("--json", action="store_true")
        sub.add_parser("doctor")
        return parser

    def run(self, args):
        out.banner()
        if len(args) == 1 and not args[0].startswith("-"):
            intent = self.intent_parser.parse_intent(args[0])
            if intent and args[0] not in ["init","scan","verify","update","handoff",
                                           "pack","load","graph","watch","repair",
                                           "agent","status","doctor"]:
                out.info("Intent: " + intent + " from: " + args[0])
                args = [intent]
        parsed = self.parser.parse_args(args)
        if parsed.mode:
            self.settings.mode = parsed.mode
            out.info("Mode: " + parsed.mode)
        if getattr(parsed, "verbose", False):
            out.set_verbose(True)
        if getattr(parsed, "json", False):
            out.set_mode("json")
        if not parsed.command:
            self.parser.print_help()
            return
        self._dispatch(parsed)

    def _dispatch(self, args):
        cmd = args.command
        out.verbose("Command: " + cmd)
        self.state.emit_event("command_received", {"command": cmd})
        handlers = {
            "init":    self._cmd_init,    "scan":    self._cmd_scan,
            "verify":  self._cmd_verify,  "update":  self._cmd_update,
            "handoff": self._cmd_handoff, "pack":    self._cmd_pack,
            "load":    self._cmd_load,    "graph":   self._cmd_graph,
            "watch":   self._cmd_watch,   "repair":  self._cmd_repair,
            "agent":   self._cmd_agent,   "status":  self._cmd_status,
            "doctor":  self._cmd_doctor,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            out.error_with_hint("Unknown command: " + cmd, "Run: clockwork --help")

    def _cmd_init(self, args):
        from cli.commands.init import InitCommand
        InitCommand(self.settings, self.state, self.context).execute(json_mode=getattr(args,"json",False))

    def _cmd_scan(self, args):
        from cli.commands.scan import ScanCommand
        ScanCommand(self.settings, self.state, self.context).execute(
            focus=getattr(args,"focus",""), json_mode=getattr(args,"json",False),
            verbose=getattr(args,"verbose",False))

    def _cmd_verify(self, args):
        from cli.commands.verify import VerifyCommand
        VerifyCommand(self.settings, self.state, self.context).execute(
            json_mode=getattr(args,"json",False), explain=getattr(args,"explain",False))

    def _cmd_update(self, args):
        from cli.commands.update import UpdateCommand
        UpdateCommand(self.settings, self.state, self.context).execute()

    def _cmd_handoff(self, args):
        from cli.commands.handoff import HandoffCommand
        HandoffCommand(self.settings, self.state, self.context).execute(handoff_to=getattr(args,"to","next_agent"))

    def _cmd_pack(self, args):
        from cli.commands.pack import PackCommand
        PackCommand(self.settings, self.state, self.context).execute(label=getattr(args,"label",""))

    def _cmd_load(self, args):
        from cli.commands.load import LoadCommand
        path = getattr(args,"path","")
        if not path:
            from cli.commands.pack import PackCommand
            PackCommand(self.settings, self.state, self.context).list_packages()
            return
        cmd = LoadCommand(self.settings, self.state, self.context)
        if getattr(args,"inspect",False):
            cmd.inspect(path)
        else:
            cmd.execute(path, merge=getattr(args,"merge",False))

    def _cmd_graph(self, args):
        from cli.commands.graph import GraphCommand
        GraphCommand(self.settings, self.state, self.context).execute(query=getattr(args,"query","status"))

    def _cmd_watch(self, args):
        from cli.commands.watch import WatchCommand
        WatchCommand(self.settings, self.state, self.context).execute()

    def _cmd_repair(self, args):
        from cli.commands.repair import RepairCommand
        RepairCommand(self.settings, self.state, self.context).execute()

    def _cmd_agent(self, args):
        from cli.commands.agent import AgentCommand
        AgentCommand(self.settings, self.state, self.context).execute(
            goal=getattr(args,"goal","analyze repository"),
            json_mode=getattr(args,"json",False),
            auto_priority=getattr(args,"auto_priority",False),
            explain=getattr(args,"explain",False))

    def _cmd_status(self, args):
        json_mode = getattr(args,"json",False)
        snap = self.state.snapshot()
        data = {"session_id": snap.get("session_id",""), "mode": snap.get("mode",""),
                "healthy": snap.get("healthy",True), "tasks_done": snap.get("tasks_completed",0),
                "architecture": self.context.get_architecture(),
                "current_task": self.context.get_current_task(),
                "skills": self.context.get_skills()}
        if json_mode:
            out.json_output(data)
        else:
            out.header("System Status")
            for k, v in data.items():
                out.result(k, v)

    def _cmd_doctor(self, args):
        out.header("Clockwork Doctor")
        from cli.commands.verify import VerifyCommand
        ok = VerifyCommand(self.settings, self.state, self.context).execute()
        if ok:
            out.success("System is healthy.")
        else:
            out.warn("Issues found. Run: clockwork repair")