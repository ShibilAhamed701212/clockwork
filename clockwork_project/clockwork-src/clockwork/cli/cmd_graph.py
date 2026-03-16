"""clockwork graph"""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.graph.graph_engine import GraphEngine
console = Console()
def run() -> None:
    """Build knowledge graph database."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]"); raise typer.Exit(1)
    GraphEngine(repo).build()
    console.print("[green]Graph built: .clockwork/knowledge_graph.db[/green]")
