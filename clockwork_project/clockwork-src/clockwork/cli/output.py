"""
clockwork/cli/output.py
------------------------
Shared output helpers for consistent, human-readable CLI printing.

All commands must use these helpers rather than bare print() calls so
output style stays uniform and --json mode is easy to add later.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import typer


# ── ANSI colour codes (disabled on non-TTY automatically) ──────────────────

def _supports_color() -> bool:
    return sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _supports_color():
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:  return _c("32", text)
def yellow(text: str) -> str: return _c("33", text)
def red(text: str) -> str:    return _c("31", text)
def cyan(text: str) -> str:   return _c("36", text)
def bold(text: str) -> str:   return _c("1",  text)
def dim(text: str) -> str:    return _c("2",  text)


# ── Standard output helpers ────────────────────────────────────────────────

def header(title: str) -> None:
    """Print a section header line."""
    typer.echo(bold(f"\n{title}"))
    typer.echo(dim("─" * len(title)))


def success(message: str) -> None:
    typer.echo(green(f"  ✓ {message}"))


def info(message: str) -> None:
    typer.echo(f"  {message}")


def warn(message: str) -> None:
    typer.echo(yellow(f"  ⚠  {message}"))


def error(message: str) -> None:
    typer.echo(red(f"\nError: {message}"), err=True)


def step(label: str, detail: str = "") -> None:
    """Print a pipeline step line."""
    line = f"  → {label}"
    if detail:
        line += f"  {dim(detail)}"
    typer.echo(line)


def json_output(data: Any) -> None:
    """Dump *data* as pretty-printed JSON to stdout."""
    typer.echo(json.dumps(data, indent=2, default=str))


def result_block(title: str, items: list[str]) -> None:
    """Print a labelled list of items."""
    typer.echo(bold(f"\n{title}:"))
    for item in items:
        typer.echo(f"    {item}")


def rule() -> None:
    typer.echo(dim("─" * 48))
