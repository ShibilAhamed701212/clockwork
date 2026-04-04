"""
clockwork ask — natural language query against the repository.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
import typer
from clockwork.cli.output import header, info, warn, error, rule

def _parse_question(question: str) -> tuple[str, str]:
    """
    Parse a natural language question into a query type and target.

    Returns (query_type, target) where query_type is one of:
      depends_on, dependents_of, delete_impact, file_search, general
    """
    q = question.lower().strip()

    # "what depends on X" / "what imports X"
    dep_match = re.search(r"(?:depends on|imports?|uses?)\s+(.+?)[\?]?\s*$", q)
    if dep_match:
        return "dependents_of", dep_match.group(1).strip().strip('"\'')

    # "what does X depend on" / "dependencies of X"
    rev_dep_match = re.search(r"(?:dependencies of|what does)\s+(.+?)\s+(?:depend|import)", q)
    if rev_dep_match:
        return "depends_on", rev_dep_match.group(1).strip().strip('"\'')

    # "what would break if I delete X"
    delete_match = re.search(r"(?:break|impact|affected).*(?:delete|remove)\s+(.+?)[\?]?\s*$", q)
    if delete_match:
        return "delete_impact", delete_match.group(1).strip().strip('"\'')

    # "which files handle X" / "where is X"
    search_match = re.search(r"(?:which files?|where|find)\s+(?:handle|contain|implement|is|are|do|does)?\s*(.+?)[\?]?\s*$", q)
    if search_match:
        return "file_search", search_match.group(1).strip().strip('"\'')

    # Fallback: treat entire question as search
    return "file_search", q.strip("?").strip()

def cmd_ask(
    question: str = typer.Argument(..., help='Question about the codebase.'),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    limit: int = typer.Option(10, "--limit", "-n"),
) -> None:
    """Ask a natural language question about the codebase."""
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not cw_dir.is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    header("Clockwork Ask")
    info(f"  Query: {question}")
    rule()

    # Layer keyword detection
    layer_keywords = {
        "frontend": ["frontend", "ui", "view", "template", "component", "page",
                     "static", "style", "css"],
        "backend": ["backend", "api", "server", "endpoint", "route", "handler",
                    "service", "controller"],
        "database": ["database", "db", "model", "migration", "schema", "query",
                     "orm", "table", "sql"],
        "tests": ["test", "spec", "fixture", "mock"],
    }

    q_lower = question.lower()
    target_layer = None
    for layer, keywords in layer_keywords.items():
        if any(kw in q_lower for kw in keywords):
            target_layer = layer
            break

    # Graph query
    db_path = cw_dir / "knowledge_graph.db"
    if db_path.exists():
        try:
            from clockwork.graph import GraphEngine
            ge = GraphEngine(root)
            q = ge.query()

            # Dependency question: "what depends on X?" / "what breaks if X changes?"
            if "depends on" in q_lower or "break" in q_lower or "depend" in q_lower:
                words = question.split()
                for word in reversed(words):
                    word = word.strip("?.,")
                    if "/" in word or "." in word:
                        nodes = q.who_depends_on(word)
                        if nodes:
                            info(f"Files that depend on '{word}':")
                            for n in nodes[:limit]:
                                info(f"  - {n.file_path}")
                            ge.close()
                            return

            # Import question: "what does X import?"
            if "import" in q_lower or "use" in q_lower or "uses" in q_lower:
                words = question.split()
                for word in reversed(words):
                    word = word.strip("?.,")
                    if "/" in word or ".py" in word:
                        nodes = q.dependencies_of(word)
                        if nodes:
                            info(f"'{word}' depends on:")
                            for n in nodes[:limit]:
                                info(f"  - {n.label} ({n.kind})")
                            ge.close()
                            return

            # Layer question
            if target_layer:
                nodes = q.files_in_layer(target_layer)[:limit]
                info(f"Files in the '{target_layer}' layer:")
                for n in nodes:
                    info(f"  - {n.file_path}")
                ge.close()
                return

            # Safety question
            if "safe" in q_lower and ("delete" in q_lower or "remove" in q_lower):
                words = question.split()
                for word in reversed(words):
                    word = word.strip("?.,")
                    if "/" in word or "." in word:
                        safe, reasons = q.is_safe_to_delete(word)
                        if safe:
                            info(f"'{word}' appears safe to delete "
                                 f"(no known dependents).")
                        else:
                            warn(f"'{word}' is NOT safe to delete:")
                            for r in reasons[:5]:
                                info(f"  - {r}")
                        ge.close()
                        return

            ge.close()
        except Exception as e:
            warn(f"Graph query failed: {e}")

    # Fallback: index search
    index_path = cw_dir / "index.db"
    if index_path.exists():
        try:
            from clockwork.index import LiveContextIndex
            idx = LiveContextIndex(root)
            entries = idx.all_entries()
            keywords = [w.lower().strip("?.,")
                        for w in question.split() if len(w) > 3]
            matches = [
                e for e in entries
                if any(kw in e.file_path.lower() for kw in keywords)
            ][:limit]
            if matches:
                info(f"Possibly relevant files ({len(matches)}):")
                for e in matches:
                    info(f"  - {e.file_path} ({e.language})")
                return
        except Exception:
            pass

    warn("Could not find a specific answer. Try:")
    info("  clockwork graph query depends-on <file>")
    info("  clockwork graph query layer <backend|frontend|database|tests>")
