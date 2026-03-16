"""clockwork plugin � install and list plugins."""
from pathlib import Path
import typer
from rich.console import Console
console = Console()
plugin_app = typer.Typer(help="Manage Clockwork plugins.")

@plugin_app.command("install")
def install(name: str = typer.Argument(..., help="Plugin name")) -> None:
    """Install a plugin into .clockwork/plugins/."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]"); raise typer.Exit(1)
    p = repo / ".clockwork" / "plugins" / name
    if p.exists():
        console.print(f"[yellow]Already installed: {name}[/yellow]"); raise typer.Exit(0)
    p.mkdir(parents=True, exist_ok=True)
    (p / "plugin.yaml").write_text(f"name: {name}\nversion: 0.1\nstatus: placeholder\n")
    console.print(f"[green]Plugin installed: {name}[/green]")
    console.print(f"  Location: .clockwork/plugins/{name}/")

@plugin_app.command("list")
def list_plugins() -> None:
    """List installed plugins."""
    repo = Path.cwd()
    pd = repo / ".clockwork" / "plugins"
    if not pd.exists():
        console.print("[yellow]No plugins directory. Run clockwork init.[/yellow]"); raise typer.Exit(0)
    plugins = [p for p in pd.iterdir() if p.is_dir()]
    if not plugins:
        console.print("[yellow]No plugins installed.[/yellow]")
    else:
        console.print("[cyan]Installed plugins:[/cyan]")
        for p in plugins: console.print(f"  � {p.name}")
