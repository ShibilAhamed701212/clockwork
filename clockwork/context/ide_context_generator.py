"""
Generates IDE-specific context files from Clockwork project intelligence.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


INTEGRATION_FILENAMES: dict[str, str] = {
    "claude-md": "agent-context.md",
    "cursorrules": "agent-rules.md",
    "agents-md": "agents.md",
    "copilot": "copilot-instructions.md",
}


def resolve_integration_output_map(
    repo_root: Path,
    *,
    include_legacy_root: bool = False,
) -> dict[str, list[Path]]:
    """
    Resolve output destinations for generated integration files.

    Primary destination is `.clockwork/integrations` unless overridden by
    `.clockwork/config.yaml` key `integration_output_dir`.
    """
    cw_dir = repo_root / ".clockwork"
    config_path = cw_dir / "config.yaml"

    configured_dir = ".clockwork/integrations"
    legacy_root = include_legacy_root

    if config_path.exists():
        try:
            import yaml
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            configured_dir = str(config.get("integration_output_dir", configured_dir))
            if not include_legacy_root:
                legacy_root = bool(config.get("legacy_root_integrations", False))
        except Exception:
            pass

    integration_dir = repo_root / configured_dir
    target_map = {
        "claude-md": [integration_dir / INTEGRATION_FILENAMES["claude-md"]],
        "cursorrules": [integration_dir / INTEGRATION_FILENAMES["cursorrules"]],
        "agents-md": [integration_dir / INTEGRATION_FILENAMES["agents-md"]],
        "copilot": [integration_dir / INTEGRATION_FILENAMES["copilot"]],
    }

    if legacy_root:
        target_map["claude-md"].append(repo_root / "CLAUDE.md")
        target_map["cursorrules"].append(repo_root / ".cursorrules")
        target_map["agents-md"].append(repo_root / "AGENTS.md")
        target_map["copilot"].append(repo_root / ".github" / "copilot-instructions.md")

    return target_map


class IDEContextGenerator:
    """
    Generates agent-context.md, agent-rules.md, agents.md, and copilot instructions
    from existing Clockwork context, rules, and graph data.
    """

    def __init__(self, repo_root: Path = None) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.cw_dir = self.repo_root / ".clockwork"

    def generate_all(self) -> dict[str, Path]:
        """Generate all formats and return {format: primary output_path}."""
        results = {}
        ctx = self._load_context()
        rules_text = self._load_rules()
        graph_summary = self._load_graph_summary()

        output_map = resolve_integration_output_map(self.repo_root)
        generators = {
            "claude-md": self.generate_claude_md,
            "cursorrules": self.generate_cursorrules,
            "agents-md": self.generate_agents_md,
            "copilot": self.generate_copilot_instructions,
        }

        for fmt, destinations in output_map.items():
            generator = generators.get(fmt)
            if not generator:
                continue
            try:
                content = generator(ctx, rules_text, graph_summary)
                for path in destinations:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                results[fmt] = destinations[0]
            except Exception:
                pass
        return results

    def generate_claude_md(
        self,
        ctx: dict,
        rules_text: str,
        graph: dict = None,
    ) -> str:
        graph = graph or {}
        project = ctx.get("project_name", "this project")
        summary = ctx.get("summary", "").strip()
        arch = ctx.get("architecture_overview", "").strip()
        primary_lang = ctx.get("primary_language", "")
        frameworks = ctx.get("frameworks", [])
        entry_points = ctx.get("entry_points", [])
        tasks = ctx.get("current_tasks", [])
        layers = graph.get("layers", {})

        fw_str = ", ".join(frameworks[:8]) if frameworks else "(auto-detect)"
        ep_str = "\n".join(f"- `{e}`" for e in entry_points[:6]) or "- (see repo root)"
        layer_str = "\n".join(
            f"- **{layer}**: {count} files"
            for layer, count in sorted(layers.items(), key=lambda x: -x[1])
        ) if layers else "- (run `clockwork graph` to build)"

        task_str = ""
        if tasks:
            pending = [t for t in tasks
                       if isinstance(t, dict) and t.get("status") != "done"][:5]
            if pending:
                task_str = "\n## Current tasks\n\n"
                for t in pending:
                    title = t.get("title", t.get("description", str(t)))
                    status = t.get("status", "pending")
                    task_str += f"- [{status}] {title}\n"

        protected = self._extract_protected_files(rules_text)
        protected_str = "\n".join(f"- `{f}`" for f in protected[:10])

        rules_summary = self._summarize_rules(rules_text)
        default_protected = "- `.clockwork/context.yaml`\n- `.clockwork/rules.md`"

        return f"""# {project}

{summary or f'Repository context for {project}.'}

> Generated by Clockwork on {datetime.now(timezone.utc).strftime("%Y-%m-%d")}.
> Run `clockwork update` to regenerate after changes.

## Architecture

{arch or f'{project} is a {primary_lang} project.'}

**Primary language**: {primary_lang or "mixed"}
**Frameworks**: {fw_str}

### Layer structure
{layer_str}

### Entry points
{ep_str}

## Development guidelines

{rules_summary}

## Protected files

Do not modify these files directly — they are managed by Clockwork:
{protected_str or default_protected}

## Clockwork commands
```bash
clockwork verify          # validate changes before committing
clockwork handoff         # generate session handoff brief
clockwork ask "..."       # query the codebase in natural language
clockwork graph query depends-on <file>  # find dependents
```
{task_str}
## Notes for AI agents

- Always run `clockwork verify` before suggesting commits
- Check `clockwork graph query safe-to-delete <file>` before deletions
- The `.clockwork/` directory is managed automatically — do not edit directly
- See `.clockwork/handoff/next_agent_brief.md` for current session state
"""

    def generate_cursorrules(
        self,
        ctx: dict,
        rules_text: str,
        graph: dict = None,
    ) -> str:
        graph = graph or {}
        project = ctx.get("project_name", "this project")
        primary_lang = ctx.get("primary_language", "")
        frameworks = ctx.get("frameworks", [])
        rules_summary = self._summarize_rules(rules_text)
        protected = self._extract_protected_files(rules_text)
        protected_str = ", ".join(f"`{f}`" for f in protected[:5])

        fw_note = ""
        if frameworks:
            fw_note = f"\nThis project uses: {', '.join(frameworks[:6])}.\n"

        return f"""# Cursor rules for {project}

## Project context

{project} is a {primary_lang} project.{fw_note}
Full context: read `agent-context.md` or run `clockwork handoff` for session state.

## Governance rules

{rules_summary}

## Protected files

Never modify: {protected_str or "`.clockwork/` directory contents"}.

## Before making changes

1. Check dependencies: run `clockwork graph query depends-on <file>`
2. Validate: run `clockwork verify`
3. For deletions: run `clockwork graph query safe-to-delete <file>`

## Code style

- Follow existing patterns in the codebase
- Match naming conventions of surrounding code
- Do not introduce new dependencies without checking `clockwork verify`

## Commit behavior

Run `clockwork verify --staged` before every commit.
The pre-commit hook does this automatically if installed.
"""

    def generate_agents_md(
        self,
        ctx: dict,
        rules_text: str,
        graph: dict = None,
    ) -> str:
        graph = graph or {}
        project = ctx.get("project_name", "this project")
        summary = ctx.get("summary", "").strip()
        frameworks = ctx.get("frameworks", [])
        tasks = ctx.get("current_tasks", [])
        rules_summary = self._summarize_rules(rules_text)

        pending = []
        if tasks:
            pending = [t for t in tasks
                       if isinstance(t, dict) and t.get("status") != "done"][:5]

        task_section = ""
        if pending:
            task_section = "\n## Open tasks\n\n"
            for t in pending:
                title = t.get("title", t.get("description", str(t)))
                task_section += f"- {title}\n"

        return f"""# Agents guide — {project}

{summary or f'AI agent context for {project}.'}

## Stack

{', '.join(frameworks) if frameworks else 'See requirements.txt / package.json'}

## Rules agents must follow

{rules_summary}

## Required workflow

1. Start: read `agent-context.md` for full context
2. Query dependencies before modifying files: `clockwork graph query depends-on <file>`  
3. Validate before finishing: `clockwork verify`
4. Handoff: run `clockwork handoff` before ending a session
{task_section}
## Clockwork integration

This repository uses Clockwork for AI governance. The MCP server
exposes `get_project_context`, `query_graph`, `check_file_safety`,
and `run_verify` tools — use them before making structural changes.
"""

    def generate_copilot_instructions(
        self,
        ctx: dict,
        rules_text: str,
        graph: dict = None,
    ) -> str:
        project = ctx.get("project_name", "this project")
        primary_lang = ctx.get("primary_language", "")
        rules_summary = self._summarize_rules(rules_text)

        return f"""# GitHub Copilot instructions — {project}

## Language and stack

Primary language: {primary_lang}. Follow existing code style and naming conventions.

## Rules

{rules_summary}

## Before suggesting deletions

Check dependents first using `clockwork graph query depends-on <file>`.

## Validation

All changes should pass `clockwork verify`. Do not suggest bypassing this.
"""

    # ── private helpers ──────────────────────────────────────────────────

    def _load_context(self) -> dict:
        import yaml
        ctx_path = self.cw_dir / "context.yaml"
        if not ctx_path.exists():
            return {}
        try:
            return yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def _load_rules(self) -> str:
        rules_path = self.cw_dir / "rules.md"
        if not rules_path.exists():
            return ""
        try:
            return rules_path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _load_graph_summary(self) -> dict:
        db_path = self.cw_dir / "knowledge_graph.db"
        if not db_path.exists():
            return {}
        try:
            from clockwork.graph import GraphEngine
            engine = GraphEngine(self.repo_root)
            q = engine.query()
            stats = q.stats()
            engine.close()
            return {"layers": stats.get("layers", {}),
                    "languages": stats.get("languages", {})}
        except Exception:
            return {}

    def _summarize_rules(self, rules_text: str) -> str:
        if not rules_text.strip():
            return "Follow existing patterns. Run `clockwork verify` before commits."
        lines = [l.strip() for l in rules_text.splitlines()
                 if l.strip().startswith("- ")]
        if not lines:
            return rules_text[:500]
        return "\n".join(lines[:15])

    def _extract_protected_files(self, rules_text: str) -> list[str]:
        protected = []
        capture = False
        for line in rules_text.splitlines():
            if "protect" in line.lower() or "do not" in line.lower():
                capture = True
            if capture and line.strip().startswith("- "):
                item = line.strip()[2:].strip()
                if item and len(item) < 80:
                    protected.append(item)
            elif capture and line.strip() == "":
                capture = False
        return protected or [".clockwork/context.yaml", ".clockwork/rules.md"]
