"""
Clockwork MCP Server
--------------------
Exposes repository intelligence as Model Context Protocol tools.

Usage:
  clockwork-mcp                 # stdio transport (Claude Code)
  clockwork-mcp --http 8080     # HTTP/SSE transport (Cursor, web)
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


def main() -> None:
    """Entry point — detect transport and launch."""
    import argparse
    parser = argparse.ArgumentParser(description="Clockwork MCP Server")
    parser.add_argument("--http", type=int, metavar="PORT",
                        help="Run HTTP/SSE server on this port")
    parser.add_argument("--repo", type=str, default=".",
                        help="Repository root (default: cwd)")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()

    if args.http:
        _run_http(repo_root, args.http)
    else:
        _run_stdio(repo_root)


def _run_stdio(repo_root: Path) -> None:
    """stdio transport — reads JSON-RPC from stdin, writes to stdout."""
    server = ClockworkMCPServer(repo_root)
    server.run_stdio()


def _run_http(repo_root: Path, port: int) -> None:
    """HTTP/SSE transport."""
    server = ClockworkMCPServer(repo_root)
    asyncio.run(server.run_http(port))


class ClockworkMCPServer:
    """
    Implements the MCP tool protocol for Clockwork.

    Tools exposed:
      get_project_context   — full context.yaml
      query_graph           — dependency queries
      check_file_safety     — safe to modify/delete?
      get_handoff_brief     — next_agent_brief.md content
      run_verify            — run rule engine on files
      search_codebase       — find relevant files by description
    """

    TOOL_DEFINITIONS = [
        {
            "name": "get_project_context",
            "description": (
                "Returns the full Clockwork project context: architecture, "
                "frameworks, current tasks, recent changes, and project summary. "
                "Call this at the start of any session to understand the codebase."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "query_graph",
            "description": (
                "Query the repository knowledge graph for dependency relationships. "
                "Find what depends on a file, what a file imports, which files "
                "belong to a layer, or whether it's safe to delete a file."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "enum": ["depends_on", "dependencies_of",
                                 "files_in_layer", "safe_to_delete",
                                 "files_importing"],
                        "description": "Query type.",
                    },
                    "target": {
                        "type": "string",
                        "description": "File path, module name, or layer name.",
                    },
                },
                "required": ["query", "target"],
            },
        },
        {
            "name": "check_file_safety",
            "description": (
                "Check if modifying, creating, or deleting a file would violate "
                "Clockwork governance rules or break dependent modules. "
                "Always call this before suggesting deletion or major refactoring."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": ["modify", "delete", "create"],
                    },
                },
                "required": ["file_path", "operation"],
            },
        },
        {
            "name": "get_handoff_brief",
            "description": (
                "Returns the current agent handoff brief — a markdown summary "
                "of project state, current tasks, and next steps. "
                "Useful when resuming work or coordinating between agents."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "run_verify",
            "description": (
                "Run the Clockwork rule engine against specified files. "
                "Returns validation results including any violations or warnings."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to verify.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["strict", "balanced", "relaxed"],
                        "default": "balanced",
                    },
                },
                "required": ["files"],
            },
        },
        {
            "name": "search_codebase",
            "description": (
                "Find files relevant to a natural language description. "
                "Uses the knowledge graph to locate authentication code, "
                "database models, API endpoints, etc."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you're looking for, e.g. 'authentication handling'.",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Max results.",
                    },
                },
                "required": ["query"],
            },
        },
    ]

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.cw_dir = repo_root / ".clockwork"

    def run_stdio(self) -> None:
        """JSON-RPC over stdio — used by Claude Code."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._handle(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": None,
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    def _handle(self, request: dict) -> dict:
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._ok(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "clockwork", "version": "0.1.0"},
            })

        if method == "tools/list":
            return self._ok(req_id, {"tools": self.TOOL_DEFINITIONS})

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_input = params.get("arguments", {})
            result = self._call_tool(tool_name, tool_input)
            return self._ok(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            })

        return self._ok(req_id, {})

    def _ok(self, req_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _call_tool(self, name: str, args: dict) -> Any:
        if name == "get_project_context":
            return self._tool_get_context()
        if name == "query_graph":
            return self._tool_query_graph(args)
        if name == "check_file_safety":
            return self._tool_check_safety(args)
        if name == "get_handoff_brief":
            return self._tool_get_handoff()
        if name == "run_verify":
            return self._tool_run_verify(args)
        if name == "search_codebase":
            return self._tool_search(args)
        raise ValueError(f"Unknown tool: {name}")

    def _tool_get_context(self) -> dict:
        try:
            from clockwork.context import ContextEngine
            engine = ContextEngine(self.cw_dir)
            ctx = engine.load_or_default()
            return ctx.to_dict()
        except Exception as e:
            return {"error": str(e), "note": "Run clockwork init && clockwork scan"}

    def _tool_query_graph(self, args: dict) -> Any:
        query = args.get("query", "")
        target = args.get("target", "")
        db_path = self.cw_dir / "knowledge_graph.db"
        if not db_path.exists():
            return {"error": "Graph not built. Run: clockwork graph"}
        try:
            from clockwork.graph import GraphEngine
            engine = GraphEngine(self.repo_root)
            q = engine.query()
            if query == "depends_on":
                nodes = q.who_depends_on(target)
                return [n.to_dict() for n in nodes]
            if query == "dependencies_of":
                nodes = q.dependencies_of(target)
                return [n.to_dict() for n in nodes]
            if query == "files_in_layer":
                nodes = q.files_in_layer(target)
                return [n.to_dict() for n in nodes]
            if query == "safe_to_delete":
                safe, reasons = q.is_safe_to_delete(target)
                return {"safe": safe, "reasons": reasons}
            if query == "files_importing":
                nodes = q.files_importing(target)
                return [n.to_dict() for n in nodes]
            engine.close()
        except Exception as e:
            return {"error": str(e)}

    def _tool_check_safety(self, args: dict) -> dict:
        file_path = args.get("file_path", "")
        operation = args.get("operation", "modify")
        result = {
            "file": file_path,
            "operation": operation,
            "safe": True,
            "reasons": [],
            "risk_level": "low",
        }
        # Rule check
        try:
            from clockwork.rules import RuleEngine
            engine = RuleEngine(self.repo_root)
            if operation == "delete":
                report = engine.evaluate([], deleted_files=[file_path])
            else:
                report = engine.evaluate([file_path])
            if not report.passed:
                result["safe"] = False
                result["risk_level"] = "high"
                result["reasons"].extend(
                    [str(v) for v in report.blocking_violations]
                )
        except Exception as e:
            result["reasons"].append(f"Rule check error: {e}")

        # Graph check — who depends on this?
        db_path = self.cw_dir / "knowledge_graph.db"
        if db_path.exists() and operation == "delete":
            try:
                from clockwork.graph import GraphEngine
                ge = GraphEngine(self.repo_root)
                safe, dep_reasons = ge.query().is_safe_to_delete(file_path)
                ge.close()
                if not safe:
                    result["safe"] = False
                    result["risk_level"] = "high"
                    result["reasons"].extend(dep_reasons)
            except Exception:
                pass

        if result["safe"]:
            result["risk_level"] = "low"
        return result

    def _tool_get_handoff(self) -> str:
        brief_path = self.cw_dir / "handoff" / "next_agent_brief.md"
        if brief_path.exists():
            return brief_path.read_text(encoding="utf-8")
        return ("No handoff brief found. "
                "Run: clockwork scan && clockwork update && clockwork handoff")

    def _tool_run_verify(self, args: dict) -> dict:
        files = args.get("files", [])
        try:
            from clockwork.rules import RuleEngine
            engine = RuleEngine(self.repo_root)
            report = engine.evaluate(files)
            return {
                "passed": report.passed,
                "files_checked": len(files),
                "violations": len(report.blocking_violations),
                "warnings": len(report.warnings),
                "details": [str(v) for v in report.violations],
            }
        except Exception as e:
            return {"error": str(e), "passed": False}

    def _tool_search(self, args: dict) -> list:
        query = args.get("query", "").lower()
        limit = args.get("limit", 10)
        results = []
        # Layer-based search
        layer_keywords = {
            "frontend": ["frontend", "ui", "view", "component", "page"],
            "backend": ["backend", "api", "server", "service", "handler"],
            "database": ["database", "db", "model", "migration", "schema"],
            "tests": ["test", "spec"],
        }
        target_layer = None
        for layer, keywords in layer_keywords.items():
            if any(kw in query for kw in keywords):
                target_layer = layer
                break
        db_path = self.cw_dir / "knowledge_graph.db"
        if db_path.exists():
            try:
                from clockwork.graph import GraphEngine
                ge = GraphEngine(self.repo_root)
                q = ge.query()
                if target_layer:
                    nodes = q.files_in_layer(target_layer)[:limit]
                else:
                    nodes = q.stats().get("nodes_by_kind", {})
                    # Fallback: return a layer summary
                    ge.close()
                    return [{"message": "Use specific layer query",
                            "available": list(q.layer_summary().keys())}]
                ge.close()
                return [{"path": n.file_path, "layer": n.layer,
                         "language": n.language} for n in nodes]
            except Exception as e:
                results.append({"error": str(e)})

        # Fallback: search index
        index_path = self.cw_dir / "index.db"
        if index_path.exists():
            try:
                from clockwork.index import LiveContextIndex
                idx = LiveContextIndex(self.repo_root)
                entries = idx.all_entries()
                matches = [
                    {"path": e.file_path, "language": e.language,
                     "layer": e.layer}
                    for e in entries
                    if query in e.file_path.lower()
                       or query in (e.language or "").lower()
                       or query in (e.layer or "").lower()
                ]
                return matches[:limit]
            except Exception:
                pass
        return results

    async def run_http(self, port: int) -> None:
        """HTTP/SSE transport for Cursor and web IDEs."""
        try:
            from aiohttp import web
        except ImportError:
            print("Install aiohttp for HTTP mode: pip install aiohttp",
                  file=sys.stderr)
            sys.exit(1)

        async def handle_sse(request):
            response = web.StreamResponse(headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            })
            await response.prepare(request)
            capabilities = {
                "tools": self.TOOL_DEFINITIONS,
                "serverInfo": {"name": "clockwork", "version": "0.1.0"},
            }
            await response.write(
                f"data: {json.dumps(capabilities)}\n\n".encode()
            )
            return response

        async def handle_call(request):
            body = await request.json()
            result = self._call_tool(body.get("tool", ""),
                                     body.get("arguments", {}))
            return web.json_response({"result": result})

        app = web.Application()
        app.router.add_get("/sse", handle_sse)
        app.router.add_post("/call", handle_call)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        print(f"Clockwork MCP server running on http://localhost:{port}/sse")
        await site.start()
        await asyncio.Event().wait()
