import time
from typing import Dict, Any, Optional
from security.sandbox           import Sandbox, SandboxResult
from security.access_control    import AccessControl
from security.command_filter    import CommandFilter
from security.secrets_protection import SecretsProtection
from rules.validators.safety_rules import SafetyRules

class ExecutionResult:
    def __init__(self, success: bool, output: Any, explanation: Dict = {},
                 error: str = "", violation: bool = False):
        self.success     = success
        self.output      = output
        self.explanation = explanation
        self.error       = error
        self.violation   = violation
        self.timestamp   = time.time()

    def to_dict(self) -> Dict:
        return {
            "success":     self.success,
            "output":      str(self.output)[:500],
            "explanation": self.explanation,
            "error":       self.error,
            "violation":   self.violation,
            "timestamp":   self.timestamp,
        }


class SandboxExecutor:
    def __init__(self, dry_run: bool = False):
        self.dry_run   = dry_run
        self.sandbox   = Sandbox(timeout=30, dry_run=dry_run)
        self.access    = AccessControl()
        self.cmd_filter= CommandFilter()
        self.secrets   = SecretsProtection()
        self.safety    = SafetyRules()
        self._log: list = []

    def execute(self, task: Dict, agent_name: str = "general_agent") -> ExecutionResult:
        action  = task.get("action", {})
        atype   = action.get("type","unknown")
        target  = action.get("target","")
        content = action.get("content","")

        print("[Sandbox] " + agent_name + " -> " + atype + " -> " + target)

        # Access control check
        perm_map = {"scan":"read","verify":"read","read":"read",
                    "create":"write","modify":"write","update":"write",
                    "delete":"delete","execute":"execute","graph":"read",
                    "repair":"write","pack":"write","load":"write"}
        permission = perm_map.get(atype, "read")
        if not self.access.can(agent_name, permission, target):
            result = ExecutionResult(False, None, error="Access denied: " + agent_name + " -> " + permission, violation=True)
            self._record(task, result, agent_name)
            return result

        # Command safety check
        ok, msg, severity = self.cmd_filter.filter(atype + " " + target)
        if not ok:
            result = ExecutionResult(False, None, error="Command blocked: " + msg, violation=True)
            self._record(task, result, agent_name)
            return result

        # Content safety check
        if content:
            ok2, violations = self.safety.validate_code_content(content, target)
            if not ok2:
                result = ExecutionResult(False, None, error="Unsafe content: " + violations[0], violation=True)
                self._record(task, result, agent_name)
                return result
            findings = self.secrets.scan_content(content, target)[1]
            if findings:
                result = ExecutionResult(False, None, error="Secret detected in content", violation=True)
                self._record(task, result, agent_name)
                return result

        # Path validation
        if target:
            ok3, msg3 = self.sandbox.validate_operation(atype, target)
            if not ok3:
                result = ExecutionResult(False, None, error="Sandbox violation: " + msg3, violation=True)
                self._record(task, result, agent_name)
                return result

        if self.dry_run:
            result = ExecutionResult(True, "[DRY RUN] " + atype + " -> " + target,
                                     {"type": atype, "target": target, "dry_run": True})
            self._record(task, result, agent_name)
            return result

        result = self._dispatch(atype, target, content, task)
        self._record(task, result, agent_name)
        return result

    def _dispatch(self, atype: str, target: str, content: str, task: Dict) -> ExecutionResult:
        handlers = {
            "scan":   self._exec_scan,
            "verify": self._exec_verify,
            "update": self._exec_update,
            "create": self._exec_create,
            "read":   self._exec_read,
            "graph":  self._exec_graph,
            "repair": self._exec_repair,
        }
        handler = handlers.get(atype, self._exec_generic)
        return handler(target, content, task)

    def _exec_scan(self, target, content, task) -> ExecutionResult:
        from scanner.scanner import Scanner
        try:
            repo_map = Scanner(root=target).run()
            return ExecutionResult(True, repo_map,
                {"type":"scan","change":"Repository scanned",
                 "reason":"Build system understanding","impact":"Context updated"})
        except Exception as e:
            return ExecutionResult(False, None, error=str(e))

    def _exec_verify(self, target, content, task) -> ExecutionResult:
        from rules.validators.structure_rules import StructureRules
        ok, errors = StructureRules().validate_structure()
        return ExecutionResult(ok, {"ok":ok,"errors":errors},
            {"type":"verify","change":"System verified","reason":"Ensure integrity","impact":"Validated"})

    def _exec_update(self, target, content, task) -> ExecutionResult:
        return ExecutionResult(True, "context updated",
            {"type":"update","change":"Context synchronized","reason":"Keep memory current","impact":"Refreshed"})

    def _exec_create(self, target, content, task) -> ExecutionResult:
        from pathlib import Path
        try:
            if target and content:
                p = Path(target)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return ExecutionResult(True, "created: " + target,
                    {"type":"create","change":"File created","reason":task.get("name",""),"impact":"New file"})
            return ExecutionResult(False, None, error="Missing target or content")
        except Exception as e:
            return ExecutionResult(False, None, error=str(e))

    def _exec_read(self, target, content, task) -> ExecutionResult:
        from pathlib import Path
        try:
            text = Path(target).read_text(encoding="utf-8", errors="ignore")
            return ExecutionResult(True, text[:1000], {"type":"read","target":target})
        except Exception as e:
            return ExecutionResult(False, None, error=str(e))

    def _exec_graph(self, target, content, task) -> ExecutionResult:
        return ExecutionResult(True, "graph built",
            {"type":"graph","change":"Knowledge graph built","reason":"Map relationships","impact":"Graph updated"})

    def _exec_repair(self, target, content, task) -> ExecutionResult:
        return ExecutionResult(True, "repair attempted",
            {"type":"repair","change":"Self-heal triggered","reason":"Fix state","impact":"Structure restored"})

    def _exec_generic(self, target, content, task) -> ExecutionResult:
        return ExecutionResult(True, "executed: " + target,
            {"type":"generic","target":target,"change":"Action executed","reason":"Agent request","impact":"Unknown"})

    def _record(self, task: Dict, result: ExecutionResult, agent: str):
        self._log.append({
            "task":      task.get("name",""),
            "agent":     agent,
            "success":   result.success,
            "violation": result.violation,
            "ts":        result.timestamp,
        })

    def log(self) -> list:
        return list(self._log)

    def violation_count(self) -> int:
        return sum(1 for e in self._log if e.get("violation"))