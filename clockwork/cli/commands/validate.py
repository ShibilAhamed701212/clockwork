"""
clockwork/cli/commands/validate.py
----------------------------------
CLI commands for validation utilities.

Commands:
    clockwork validate json   — validate JSON file
    clockwork validate yaml   — validate YAML file
    clockwork validate syntax — validate Python syntax
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header,
    success,
    info,
    warn,
    error,
    step,
    rule,
    json_output,
)
from clockwork.validation.output_validator import OutputValidator
from clockwork.validation.hallucination_guard import HallucinationGuard

validate_app = typer.Typer(
    name="validate",
    help="Validation utilities for JSON, YAML, and code.",
    no_args_is_help=True,
)


@validate_app.command("json")
def validate_json(
    file: Path = typer.Argument(..., help="JSON file to validate"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Validate a JSON file."""
    root = (repo_root or Path.cwd()).resolve()
    file_path = root / file if not file.is_absolute() else file

    if not as_json:
        header("JSON Validation")
        step(f"Checking: {file_path}")

    if not file_path.exists():
        error(f"File not found: {file_path}")
        raise typer.Exit(code=1)

    try:
        content = file_path.read_text(encoding="utf-8")
        import json

        json.loads(content)
    except json.JSONDecodeError as exc:
        error(f"Invalid JSON: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        error(f"Error: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output({"valid": True, "file": str(file_path)})
    else:
        success("Valid JSON")


@validate_app.command("yaml")
def validate_yaml(
    file: Path = typer.Argument(..., help="YAML file to validate"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Validate a YAML file."""
    root = (repo_root or Path.cwd()).resolve()
    file_path = root / file if not file.is_absolute() else file

    if not as_json:
        header("YAML Validation")
        step(f"Checking: {file_path}")

    if not file_path.exists():
        error(f"File not found: {file_path}")
        raise typer.Exit(code=1)

    try:
        content = file_path.read_text(encoding="utf-8")
        import yaml

        yaml.safe_load(content)
    except yaml.YAMLError as exc:
        error(f"Invalid YAML: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        error(f"Error: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output({"valid": True, "file": str(file_path)})
    else:
        success("Valid YAML")


@validate_app.command("syntax")
def validate_syntax(
    file: Path = typer.Argument(..., help="Python file to validate"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Validate Python syntax."""
    root = (repo_root or Path.cwd()).resolve()
    file_path = root / file if not file.is_absolute() else file

    if not as_json:
        header("Python Syntax Validation")
        step(f"Checking: {file_path}")

    if not file_path.exists():
        error(f"File not found: {file_path}")
        raise typer.Exit(code=1)

    ov = OutputValidator()
    try:
        content = file_path.read_text(encoding="utf-8")
        ok, msg = ov.validate_syntax(content, "python")
        if not ok:
            error(f"Syntax error: {msg}")
            raise typer.Exit(code=1)
    except Exception as exc:
        error(f"Error: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output({"valid": True, "file": str(file_path)})
    else:
        success("Valid Python syntax")


@validate_app.command("output")
def validate_output(
    json_data: str = typer.Option(..., "--data", "-d", help="JSON output to validate"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Validate agent output format."""
    import json

    if not as_json:
        header("Output Validation")

    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as exc:
        error(f"Invalid JSON: {exc}")
        raise typer.Exit(code=1)

    ov = OutputValidator()
    ok, errors = ov.validate(data)

    if as_json:
        json_output({"valid": ok, "errors": errors})
        return

    if ok:
        success("Valid output format")
    else:
        error("Invalid output format:")
        for e in errors:
            warn(f"  ! {e}")
        raise typer.Exit(code=1)


@validate_app.command("guard")
def validate_guard(
    output: str = typer.Option(
        ..., "--output", "-o", help="Output to check for hallucinations"
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Check output for potential hallucinations."""
    if not as_json:
        header("Hallucination Guard")

    guard = HallucinationGuard()
    issues = guard.check(output)

    if as_json:
        json_output({"issues": issues, "count": len(issues)})
        return

    if not issues:
        success("No hallucinations detected")
    else:
        warn(f"Potential issues ({len(issues)}):")
        for issue in issues:
            info(f"  ! {issue}")
