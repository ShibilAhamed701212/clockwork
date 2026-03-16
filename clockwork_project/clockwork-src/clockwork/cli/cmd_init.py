"""clockwork init"""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.context.initializer import initialize_clockwork_dir
console = Console()

def run(force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .clockwork")) -> None:
    """Initialize Clockwork in the current repository."""
    repo = Path.cwd()
    d = repo / ".clockwork"
    if d.exists() and not force:
        console.print("[yellow]Already initialized. Use --force to reinitialize.[/yellow]")
        raise typer.Exit(0)
    if d.exists() and force:
        if not typer.confirm("WARNING: This will overwrite existing .clockwork data. Continue?", default=False):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)
    try:
        initialize_clockwork_dir(repo, force=force)
        console.print("[green]Clockwork initialized successfully.[/green]")
        console.print("  Files: context.yaml, rules.yaml, rules.md, config.yaml, tasks.json")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
