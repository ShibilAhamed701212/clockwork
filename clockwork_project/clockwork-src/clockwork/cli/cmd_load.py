"""clockwork load"""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.packaging.packaging_engine import PackagingEngine
console = Console()
def run(package: str = typer.Argument(..., help="Path to .clockwork file")) -> None:
    """Load a .clockwork package."""
    pkg = Path(package)
    if not pkg.exists():
        console.print(f"[red]File not found: {package}[/red]"); raise typer.Exit(1)
    PackagingEngine(Path.cwd()).load(pkg)
    console.print("[green]Package loaded successfully.[/green]")
