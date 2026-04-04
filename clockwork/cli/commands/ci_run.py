"""
clockwork/cli/commands/ci_run.py
----------------------------------
`clockwork ci-run` - run CI/CD pipeline with auto-retry and optional AI assistance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import error, header, info, rule, step, success, warn


def cmd_ci_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would run without executing."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
    max_retries: int = typer.Option(
        3, "--retries", "-n", help="Max retries per stage."
    ),
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository."
    ),
) -> None:
    """Run the CI/CD pipeline with auto-retry and optional AI assistance."""
    root = (repo_root or Path.cwd()).resolve()
    if not (root / ".clockwork").is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    config_path = root / ".clockwork" / "context.yaml"
    if not config_path.exists():
        error("context.yaml not found. Run: clockwork init")
        raise typer.Exit(code=1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    pipeline_config = config.get("pipeline", {})
    stages = pipeline_config.get("stages", [])

    if not stages:
        error(
            "No pipeline stages configured. Add pipeline.stages to .clockwork/context.yaml"
        )
        raise typer.Exit(code=1)

    header("Clockwork CI/CD Pipeline")
    info(f"Running {len(stages)} stage(s)...")

    if dry_run:
        info("DRY RUN - No commands will be executed")
        for i, stage in enumerate(stages, 1):
            name = stage.get("name", f"stage-{i}")
            cmd = stage.get("command", "no command")
            info(f"  {i}. {name}: {cmd}")
        success("Dry run complete")
        return

    passed = 0
    failed = 0

    for i, stage in enumerate(stages, 1):
        name = stage.get("name", f"stage-{i}")
        command = stage.get("command", "")
        stage_retries = stage.get("max_retries", max_retries)
        continue_on_error = stage.get("continue_on_error", False)

        step(f"Stage {i}/{len(stages)}: {name}")

        for attempt in range(1, stage_retries + 2):
            if attempt > 1:
                info(f"  Retry {attempt - 1}/{stage_retries}...")

            result = run_command(command, root, verbose)

            if result.returncode == 0:
                success(f"  ✓ {name} passed")
                passed += 1
                break
            else:
                if attempt == stage_retries + 1:
                    warn(f"  ✗ {name} failed after {stage_retries} retries")
                    failed += 1

                    if verbose and result.stderr:
                        for line in result.stderr.splitlines()[:3]:
                            warn(f"     {line}")

                    if not continue_on_error:
                        error(f"Pipeline stopped at stage '{name}'")
                        rule()
                        info(f"Summary: {passed} passed, {failed} failed")
                        raise typer.Exit(code=1)
                else:
                    if verbose:
                        warn(f"  → Command failed with exit code {result.returncode}")

    rule()
    if failed == 0:
        success(f"✓ Pipeline passed ({passed} stage(s))")
    else:
        warn(f"⚠ Pipeline completed with {failed} failure(s)")
        info(f"Summary: {passed} passed, {failed} failed")


def run_command(command: str, cwd: Path, verbose: bool) -> subprocess.CompletedProcess:
    """Execute a command and return the result."""
    if not command:
        return subprocess.CompletedProcess(
            args=command, returncode=1, stdout="", stderr="No command provided"
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if verbose and result.stdout:
            for line in result.stdout.splitlines()[:5]:
                info(f"  {line}")
        return result
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=command, returncode=124, stdout="", stderr="Command timed out"
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=command, returncode=1, stdout="", stderr=str(e)
        )
