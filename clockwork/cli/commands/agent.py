"""
clockwork/cli/commands/agent.py
---------------------------------
CLI commands for the Agent Runtime subsystem.

Spec §12 commands:
    clockwork agent list
    clockwork agent register
    clockwork agent remove
    clockwork agent status

    clockwork task add <description>
    clockwork task list
    clockwork task run <task_id>
    clockwork task fail <task_id>
    clockwork task retry <task_id>
    clockwork task locks
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
from clockwork.agents.swarm import SwarmCoordinator, ConsensusEngine

# ── Typer sub-apps ─────────────────────────────────────────────────────────

agent_app = typer.Typer(
    name="agent",
    help="Manage registered AI agents.",
    no_args_is_help=True,
)

task_app = typer.Typer(
    name="task",
    help="Manage the agent task queue.",
    no_args_is_help=True,
)


# ── helpers ────────────────────────────────────────────────────────────────


def _runtime(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.agent import AgentRuntime

    rt = AgentRuntime(root)
    rt.initialise()
    return rt


# ══════════════════════════════════════════════════════════════════════════
# clockwork agent …
# ══════════════════════════════════════════════════════════════════════════


@agent_app.command("list")
def agent_list(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List all registered agents."""
    rt = _runtime(repo_root)
    agents = rt.list_agents()

    if as_json:
        json_output([a.to_dict() for a in agents])
        return

    header("Registered Agents")
    if not agents:
        warn("No agents registered. Run:  clockwork agent register <name>")
        return

    for a in sorted(agents, key=lambda x: x.priority):
        caps = ", ".join(a.capabilities) or "(none)"
        info(f"  {a.name:<20} priority={a.priority}  caps=[{caps}]")
        if a.description:
            info(f"    {a.description}")


@agent_app.command("register")
def agent_register(
    name: str = typer.Argument(..., help="Unique agent name."),
    capabilities: Optional[str] = typer.Option(
        None,
        "--caps",
        "-c",
        help="Comma-separated capabilities (e.g. coding,testing).",
    ),
    priority: int = typer.Option(10, "--priority", "-p"),
    description: str = typer.Option("", "--desc", "-d"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Register a new agent."""
    from clockwork.agent.models import Agent

    caps = [c.strip() for c in (capabilities or "coding").split(",") if c.strip()]
    agent = Agent(
        name=name, capabilities=caps, priority=priority, description=description
    )

    rt = _runtime(repo_root)
    if rt.register_agent(agent):
        success(f"Agent '{name}' registered.")
        info(f"  Capabilities : {', '.join(caps)}")
        info(f"  Priority     : {priority}")
    else:
        warn(f"Agent '{name}' already exists.")


@agent_app.command("remove")
def agent_remove(
    name: str = typer.Argument(..., help="Agent name to remove."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Remove a registered agent."""
    rt = _runtime(repo_root)
    if rt.remove_agent(name):
        success(f"Agent '{name}' removed.")
    else:
        warn(f"Agent '{name}' not found.")


@agent_app.command("status")
def agent_status(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show agent runtime statistics."""
    rt = _runtime(repo_root)
    stats = rt.stats()

    if as_json:
        json_output(stats)
        return

    header("Agent Runtime Status")
    info(f"  Registered agents : {stats['agents']}")
    info(f"  Total tasks       : {stats['total_tasks']}")
    info(f"  Active locks      : {stats['active_locks']}")
    info(f"  Log entries       : {stats['log_entries']}")
    rule()
    info("Tasks by status:")
    for status, count in sorted(stats["tasks_by_status"].items()):
        info(f"  {status:<12} : {count}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork task …
# ══════════════════════════════════════════════════════════════════════════


@task_app.command("add")
def task_add(
    description: str = typer.Argument(..., help="Task description."),
    capability: str = typer.Option(
        "coding", "--cap", "-c", help="Required capability."
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Add a new task to the queue."""
    rt = _runtime(repo_root)
    task = rt.add_task(description, capability)

    if as_json:
        json_output(task.to_dict())
        return

    success(f"Task added: {task.task_id}")
    info(f"  Description  : {task.description}")
    info(f"  Capability   : {task.required_capability}")
    info(f"  Status       : {task.status}")
    if task.assigned_agent:
        info(f"  Assigned to  : {task.assigned_agent}")
    else:
        warn("  No agent available — register one with: clockwork agent register")


@task_app.command("list")
def task_list(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (pending/assigned/completed/failed).",
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List tasks in the queue."""
    rt = _runtime(repo_root)
    tasks = rt.list_tasks(status)

    if as_json:
        json_output([t.to_dict() for t in tasks])
        return

    header("Task Queue" + (f" [{status}]" if status else ""))
    if not tasks:
        info("No tasks found.")
        return

    for t in tasks:
        agent = f" → {t.assigned_agent}" if t.assigned_agent else ""
        info(f"  [{t.status:<10}] {t.task_id}  {t.description[:50]}{agent}")
        if t.validation_errors:
            for e in t.validation_errors:
                warn(f"    ! {e}")


@task_app.command("run")
def task_run(
    task_id: str = typer.Argument(..., help="Task ID to run."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run the validation pipeline for a task."""
    rt = _runtime(repo_root)
    step(f"Running validation pipeline for {task_id}...")
    result = rt.run_task(task_id)

    if as_json:
        json_output(result.to_dict())
        return

    rule()
    if result.passed:
        success("Validation passed — changes approved.")
    else:
        error("Validation failed — changes rejected.")
        for e in result.errors:
            info(f"  ✗ {e}")

    if result.warnings:
        for w in result.warnings:
            warn(f"  ! {w}")


@task_app.command("fail")
def task_fail(
    task_id: str = typer.Argument(..., help="Task ID to mark failed."),
    reason: str = typer.Option("", "--reason", help="Failure reason"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Mark a task as failed."""
    rt = _runtime(repo_root)
    if rt.fail_task(task_id, reason):
        warn(f"Task {task_id} marked as failed.")
    else:
        error(f"Task '{task_id}' not found.")


@task_app.command("retry")
def task_retry(
    task_id: str = typer.Argument(..., help="Task ID to retry."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Retry a failed task with a different agent."""
    rt = _runtime(repo_root)
    assigned = rt.retry_task(task_id)
    if assigned:
        success(f"Task {task_id} retried — assigned to '{assigned}'.")
    else:
        warn(f"Could not retry task '{task_id}' (not found or not in failed state).")


@task_app.command("locks")
def task_locks(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List all active file locks."""
    rt = _runtime(repo_root)
    locks = rt.lock_manager.list_locks()

    if as_json:
        json_output(locks)
        return

    header("Active File Locks")
    if not locks:
        info("No active locks.")
        return
    for lk in locks:
        info(f"  {lk.get('file_path'):<40} locked by {lk.get('agent')}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork agent swarm …
# ══════════════════════════════════════════════════════════════════════════


@agent_app.command("swarm")
def agent_swarm(
    tasks_json: Optional[str] = typer.Option(
        None, "--tasks", "-t", help="JSON array of task descriptions"
    ),
    mode: str = typer.Option(
        "safe", "--mode", "-m", help="Execution mode: safe|aggressive"
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run multiple agents in parallel swarm mode."""
    from clockwork.agents.task_queue import TaskItem

    root = (repo_root or Path.cwd()).resolve()
    from clockwork.agent import AgentRuntime

    rt = AgentRuntime(root)
    rt.initialise()

    if not tasks_json:
        tasks = rt.list_tasks("pending")
    else:
        import json

        task_list = json.loads(tasks_json)
        tasks = [
            TaskItem(name=d, action={"type": "coding", "description": d})
            for d in task_list
        ]

    if not tasks:
        info("No tasks to run.")
        return

    if not as_json:
        header("Agent Swarm Execution")
        step(f"Running {len(tasks)} tasks in {mode} mode...")

    coordinator = SwarmCoordinator(rt.registry, dry_run=dry_run)
    results = coordinator.run(tasks, mode=mode)

    if as_json:
        json_output({"results": results, "total": len(results)})
        return

    rule()
    success_count = sum(1 for r in results if r.get("success"))
    success(f"Completed {success_count}/{len(results)} tasks.")


@agent_app.command("consensus")
def agent_consensus(
    results_json: str = typer.Argument(..., help="JSON array of results to vote on"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run consensus voting on multiple agent results."""
    import json

    results = json.loads(results_json)
    engine = ConsensusEngine()

    best = engine.vote(results)
    confidence = engine.confidence(results)
    merged = engine.merge_explanations(results)

    if as_json:
        json_output({"best": best, "confidence": confidence, "merged": merged})
        return

    header("Consensus Results")
    info(f"  Confidence: {confidence:.1%}")
    if best:
        info(f"  Winning output: {str(best.get('output', ''))[:80]}")
    info(f"  Agents participated: {merged.get('agents', 0)}")
