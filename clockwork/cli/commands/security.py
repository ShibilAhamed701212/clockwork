"""
clockwork/cli/commands/security.py
------------------------------------
CLI commands for the Security subsystem (spec §14).

Commands:
    clockwork security scan    — scan repo for security issues
    clockwork security audit   — full security audit report
    clockwork security log     — show recent security events
    clockwork security verify  — verify a plugin before installing
"""

from __future__ import annotations

import json
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

security_app = typer.Typer(
    name="security",
    help="Security scanning and auditing tools.",
    no_args_is_help=True,
)


def _engine(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.security import SecurityEngine
    from clockwork.security.secrets_protection import SecretsProtection
    from clockwork.security.sandbox import Sandbox

    return SecurityEngine(root)


# ── clockwork security scan ────────────────────────────────────────────────


@security_app.command("scan")
def security_scan(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Scan the repository for security issues."""
    eng = _engine(repo_root)

    if not as_json:
        header("Clockwork Security Scan")
        step("Scanning repository...")

    result = eng.scan()

    if as_json:
        json_output(result.to_dict())
        return

    rule()
    if result.passed:
        success(f"Scan passed — risk level: {result.risk_level.upper()}")
    else:
        error(f"Scan found issues — risk level: {result.risk_level.upper()}")

    info(f"  Elapsed : {result.elapsed_ms:.0f} ms")

    if result.sensitive_files_found:
        rule()
        warn(f"Sensitive files found ({len(result.sensitive_files_found)}):")
        for f in result.sensitive_files_found:
            warn(f"  ! {f}")

    if result.issues:
        rule()
        error(f"Issues ({len(result.issues)}):")
        for iss in result.issues:
            info(f"  ✗ {iss}")

    if result.warnings:
        rule()
        warn(f"Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            info(f"  ! {w}")

    if not result.protected_files_ok:
        rule()
        warn("Some protected files are missing or unreadable.")
        info("  Run:  clockwork repair")


# ── clockwork security audit ───────────────────────────────────────────────


@security_app.command("audit")
def security_audit(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run a full security audit (scan + plugins + agents + log review)."""
    eng = _engine(repo_root)

    if not as_json:
        header("Clockwork Security Audit")
        step("Running full audit...")

    report = eng.audit()

    if as_json:
        json_output(report)
        return

    rule()
    risk = report.get("risk_level", "unknown").upper()
    total = report.get("total_issues", 0)

    if total == 0:
        success(f"Audit passed — risk level: {risk}")
    else:
        error(f"Audit found {total} issue(s) — risk level: {risk}")

    scan = report.get("scan", {})
    info(f"  Scan issues   : {len(scan.get('issues', []))}")
    info(f"  Plugin issues : {len(report.get('plugin_issues', []))}")
    info(f"  Agent issues  : {len(report.get('agent_issues', []))}")
    info(f"  Log events    : {len(report.get('recent_events', []))}")

    for section, key in [
        ("Plugin issues", "plugin_issues"),
        ("Agent issues", "agent_issues"),
    ]:
        items = report.get(key, [])
        if items:
            rule()
            warn(f"{section}:")
            for item in items:
                info(f"  ! {item}")


# ── clockwork security log ─────────────────────────────────────────────────


@security_app.command("log")
def security_log(
    n: int = typer.Option(20, "--last", "-n", help="Number of recent events to show."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show recent security log events."""
    eng = _engine(repo_root)
    entries = eng.logger.recent(n)

    if as_json:
        json_output(entries)
        return

    header(f"Security Log (last {n})")
    if not entries:
        info("No security events recorded.")
        return

    for e in entries:
        risk = e.get("risk_level", "").upper()
        event = e.get("event", "")
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        fp = e.get("file", "")
        detail = e.get("detail", "")
        line = f"  [{ts}] [{risk:<8}] {event}"
        if fp:
            line += f"  {fp}"
        if detail and detail != f"Access to restricted path blocked: {fp}":
            line += f"\n    {detail}"
        info(line)


# ── clockwork security verify ──────────────────────────────────────────────


@security_app.command("verify")
def security_verify(
    plugin_path: Path = typer.Argument(
        ..., help="Path to the plugin directory to verify."
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Verify a plugin before installing it."""
    eng = _engine(repo_root)

    if not as_json:
        header(f"Plugin Verification: {plugin_path.name}")

    ok, issues = eng.verify_plugin(plugin_path)

    if as_json:
        json_output({"ok": ok, "issues": issues})
        return

    rule()
    if ok:
        success("Plugin verification passed.")
    else:
        error("Plugin verification failed.")
        for iss in issues:
            info(f"  ✗ {iss}")


# ── clockwork security secrets ───────────────────────────────────────────────


@security_app.command("secrets")
def security_secrets(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to scan"),
    redact: bool = typer.Option(False, "--redact", help="Redact found secrets"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Scan for exposed secrets (API keys, tokens, passwords)."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Secret Scanning")
        step(f"Scanning: {path}")

    scanner = SecretsProtection()
    findings = scanner.scan_directory(str(root / path))

    if as_json:
        if redact:
            for f in findings:
                f["redacted"] = scanner.redact(f.get("file", ""))
        json_output({"findings": findings, "count": len(findings)})
        return

    rule()
    if not findings:
        success("No secrets found.")
    else:
        error(f"Found {len(findings)} secret(s):")
        for f in findings:
            info(f"  ! {f['type']}: {f['file']}")


# ── clockwork security sandbox ───────────────────────────────────────────────


@security_app.command("sandbox")
def security_sandbox(
    command: str = typer.Option(..., "--exec", "-e", help="Command to test in sandbox"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Dry run mode"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Test a command in the sandbox before running for real."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Sandbox Execution")
        step(f"Command: {command}")

    sandbox = Sandbox(dry_run=dry_run, repo_root=root)
    ok, msg = sandbox.is_safe_command(command)

    if as_json:
        json_output({"safe": ok, "message": msg, "command": command})
        return

    rule()
    if ok:
        success("Command is safe.")
    else:
        error(f"Command blocked: {msg}")
