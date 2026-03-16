"""clockwork verify � Rule Engine then MiniBrain pipeline."""
from pathlib import Path
import typer
from rich.console import Console
from clockwork.rules.rule_engine import RuleEngine
from clockwork.brain.mini_brain import MiniBrain
console = Console()

def run() -> None:
    """Verify repository integrity: Rule Engine then Brain Analysis."""
    repo = Path.cwd()
    if not (repo / ".clockwork").exists():
        console.print("[red]Error: run clockwork init first.[/red]")
        raise typer.Exit(1)
    console.print("[cyan]Step 1 � Rule Engine...[/cyan]")
    passed, violations = RuleEngine(repo).verify()
    if not passed:
        console.print("[red]Verification failed � Rule Engine.[/red]")
        for v in violations: console.print(f"  [red]x[/red] {v}")
        raise typer.Exit(1)
    console.print("  [green]?[/green] Rule Engine passed.")
    console.print("[cyan]Step 2 � Brain Analysis...[/cyan]")
    assessment = MiniBrain(repo).analyze()
    recs = assessment.get("recommendations", [])
    if recs:
        console.print("  [yellow]Recommendations:[/yellow]")
        for r in recs: console.print(f"    � {r}")
    else:
        console.print("  [green]?[/green] Brain Analysis passed.")
    console.print("[green]Verification passed.[/green]")
