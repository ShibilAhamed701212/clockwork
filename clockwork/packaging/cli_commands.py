"""
clockwork/packaging/cli_commands.py
-------------------------------------
Typer CLI command handlers for `clockwork pack` and `clockwork load`.

These functions are registered in the main CLI app (clockwork/cli/app.py).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from clockwork.packaging.packer import PackagingEngine, PackagingError
from clockwork.packaging.loader import PackageLoader, LoadError


def cmd_pack(
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory to write the .clockwork package (defaults to .clockwork/packages/).",
    ),
    project_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Override the project name used in the package filename.",
    ),
) -> None:
    """
    Package the full project intelligence into a portable .clockwork archive.

    Output is stored in .clockwork/packages/<project_name>.clockwork by default.
    """
    root = (repo_root or Path.cwd()).resolve()

    try:
        engine = PackagingEngine(
            repo_root=root,
            output_dir=output_dir,
            project_name=project_name,
        )
        output_path = engine.pack()
        typer.echo(f"\nPackage ready: {output_path}")
    except PackagingError as exc:
        typer.echo(f"\nError:\n{exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"\nUnexpected error: {exc}", err=True)
        raise typer.Exit(code=2)


def cmd_load(
    package_file: Path = typer.Argument(
        ...,
        help="Path to the .clockwork package file to load.",
        exists=True,
        readable=True,
    ),
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Root directory of the target repository (defaults to current directory).",
    ),
) -> None:
    """
    Load a .clockwork package into the local repository.

    Restores project intelligence from the portable archive into .clockwork/.
    """
    root = (repo_root or Path.cwd()).resolve()

    try:
        loader = PackageLoader(repo_root=root)
        loader.load(package_path=package_file)
        typer.echo("\nProject intelligence restored successfully.")
    except LoadError as exc:
        typer.echo(f"\nError:\n{exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"\nUnexpected error: {exc}", err=True)
        raise typer.Exit(code=2)
