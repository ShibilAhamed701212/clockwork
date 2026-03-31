"""
clockwork generate — generate IDE context files from project intelligence.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer
from clockwork.cli.output import header, success, info, warn, error, step, rule

FORMATS = ["claude-md", "cursorrules", "agents-md", "copilot", "all"]

def cmd_generate(
    fmt: str = typer.Argument(
        "all",
        help=f"Format to generate: {', '.join(FORMATS)}",
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    preview: bool = typer.Option(False, "--preview",
                                  help="Print to stdout instead of writing files."),
) -> None:
    """Generate IDE context files (CLAUDE.md, .cursorrules, AGENTS.md, etc.)."""
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Generate")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    try:
        from clockwork.context.ide_context_generator import IDEContextGenerator
        gen = IDEContextGenerator(root)
    except Exception as e:
        error(f"Generator error: {e}")
        raise typer.Exit(code=1)

    ctx = gen._load_context()
    rules = gen._load_rules()
    graph = gen._load_graph_summary()

    format_map = {
        "claude-md": ("CLAUDE.md", gen.generate_claude_md),
        "cursorrules": (".cursorrules", gen.generate_cursorrules),
        "agents-md": ("AGENTS.md", gen.generate_agents_md),
        "copilot": (".github/copilot-instructions.md",
                    gen.generate_copilot_instructions),
    }

    targets = list(format_map.items()) if fmt == "all" \
              else [(fmt, format_map[fmt])] if fmt in format_map else []

    if not targets:
        error(f"Unknown format '{fmt}'. Choose: {', '.join(FORMATS)}")
        raise typer.Exit(code=1)

    for name, (filename, generator) in targets:
        step(f"Generating {filename}...")
        try:
            content = generator(ctx, rules, graph)
            if preview:
                info(f"\n--- {filename} ---")
                typer.echo(content)
            else:
                out = root / filename
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(content, encoding="utf-8")
                success(f"Written: {filename}")
        except Exception as e:
            warn(f"Could not generate {filename}: {e}")

    rule()
    if not preview:
        info("Tip: re-run after `clockwork update` to keep files current.")
        info("Add `auto_generate_ide_files: true` to .clockwork/config.yaml "
             "to generate automatically on every update.")


FORMAT_OUTPUTS: dict[str, str] = {
    "claude-md": "CLAUDE.md",
    "cursorrules": ".cursorrules",
    "agents-md": "AGENTS.md",
    "copilot": ".github/copilot-instructions.md",
}


def generate_ide_files_auto(
    repo_root: Path,
    formats: Optional[list[str]] = None,
) -> list[str]:
    """
    Silently auto-generate IDE files.

    Called by `clockwork update` when auto_generate_ide_files is enabled.
    Returns list of generated file paths.
    """
    cw_dir = repo_root / ".clockwork"
    if not cw_dir.is_dir():
        return []

    try:
        from clockwork.context.ide_context_generator import IDEContextGenerator
        gen = IDEContextGenerator(repo_root)
    except Exception:
        return []

    ctx = gen._load_context()
    rules = gen._load_rules()
    graph = gen._load_graph_summary()

    generated: list[str] = []
    for fmt in (formats or list(FORMAT_OUTPUTS.keys())):
        if fmt not in FORMAT_OUTPUTS:
            continue
        format_map = {
            "claude-md": gen.generate_claude_md,
            "cursorrules": gen.generate_cursorrules,
            "agents-md": gen.generate_agents_md,
            "copilot": gen.generate_copilot_instructions,
        }
        generator = format_map.get(fmt)
        if not generator:
            continue
        try:
            content = generator(ctx, rules, graph)
            output_path = repo_root / FORMAT_OUTPUTS[fmt]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            generated.append(str(output_path))
        except Exception:
            pass

    return generated

