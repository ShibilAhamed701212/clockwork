"""clockwork scan � scan repo and auto-update knowledge graph."""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.scanner.repository_scanner import RepositoryScanner
from clockwork.graph.graph_engine import GraphEngine
console = Console()

def run(json_output: bool = typer.Option(False, "--json")) -> None:
    """Scan repository, update repo_map.json and knowledge graph."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]")
        raise typer.Exit(1)
    console.print("[cyan]Scanning repository...[/cyan]")
    result = RepositoryScanner(repo).scan()
    console.print("[cyan]Updating knowledge graph...[/cyan]")
    try:
        GraphEngine(repo).build()
        graph_status = "updated"
    except Exception as e:
        graph_status = f"skipped ({e})"
    if json_output:
        import json; console.print(json.dumps(result, indent=2))
    else:
        console.print("[green]Scan complete.[/green]")
        console.print(f"  Files          : {result['total_files']}")
        console.print(f"  Languages      : {', '.join(result['languages']) or 'none'}")
        console.print(f"  repo_map.json  : updated")
        console.print(f"  knowledge graph: {graph_status}")
