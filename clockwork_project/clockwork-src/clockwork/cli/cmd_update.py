"""clockwork update"""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.context.context_engine import ContextEngine
console = Console()
def run() -> None:
    """Update project context."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]"); raise typer.Exit(1)
    ContextEngine(repo).update()
    console.print("[green]Context updated. See .clockwork/context.yaml[/green]")
