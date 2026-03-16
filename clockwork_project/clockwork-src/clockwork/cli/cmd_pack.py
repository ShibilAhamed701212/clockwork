"""clockwork pack"""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.packaging.packaging_engine import PackagingEngine
console = Console()
def run(output: str = typer.Option("project.clockwork", "--output", "-o")) -> None:
    """Package project intelligence."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]"); raise typer.Exit(1)
    out = PackagingEngine(repo).pack(output)
    console.print(f"[green]Package created: {out}[/green]")
