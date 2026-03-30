# Clockwork
Local-first repository intelligence and AI agent coordination system.

## Architecture Contract

### v1 Core — Canonical Implementation (`clockwork.agent.*`)
`clockwork/agent/` contains the **authoritative, spec-compliant implementation** for all agent
orchestration logic:

| Module | Role |
|---|---|
| `agent/models.py` | Canonical `Agent`, `Task`, `Capability`, `TaskStatus` data models |
| `agent/registry.py` | Authoritative JSON-backed persistence for agents and tasks |
| `agent/lock_manager.py` | File-level conflict prevention with TTL-based stale-lock cleanup |
| `agent/router.py` | Capability + priority dispatch (`TaskRouter`) and 3-stage `ValidationPipeline` |
| `agent/runtime.py` | Top-level `AgentRuntime` orchestrator composing all subsystems |

All spec references (§2 Agent Runtime, §7 Routing, §10 Validation, §13 Monitoring, §14 Recovery)
are implemented **once** in this namespace. Business logic lives here and nowhere else.

### v2 Compatibility Facade (`clockwork.agents.*`)
`clockwork/agents/` provides **import-path compatibility** for v2-style consumers. Each module is a
thin adapter — it carries no independent business logic and delegates all execution to the v1 core:

| v2 Module | Delegates to |
|---|---|
| `agents/runtime.py` | `agent/runtime.AgentRuntime` (subclass, adds v2 `submit`/`run_pipeline` surface) |
| `agents/agent_registry.py` | Standalone in-memory v2 registry with pre-loaded defaults; adapts the v2 `AgentRecord` interface (not delegated to v1 — intentionally avoids persistent storage for v2 callers) |
| `agents/router.py` | Action-type inference over v2 registry |
| `agents/task_queue.py` | Thread-safe queue with priority + dependency resolution |
| `agents/task_graph.py` | Topological dependency graph over `TaskItem` objects |
| `agents/load_balancer.py` | Round-robin / least-loaded distribution over v2 registry |

**Rule:** Never add business logic to `agents/`. If a capability needs to change, change it in `agent/`
and let the facade inherit the fix automatically.

### Other Compatibility Facades
| Module | Core delegate |
|---|---|
| `context/context_engine.py` | `context/engine.ContextEngine` |
| `brain/brain.py` | `brain/brain_manager.BrainManager` + `brain/decision_engine.DecisionEngine` |

### Test Gates
Both test suites must pass on every change:

- `tests/test_agent.py` — v1 core correctness (unit + integration for all subsystems)
- `tests/test_v2_path_compat.py` — v2 import-path compatibility smoke tests
- `tests/test_v2_remaining_suite.py` — full v2 compatibility integration tests

Run all gates with:
```
pytest tests/
```

---

## IDE Setup (JetBrains)
Use this folder as project root:
`clockwork/clockwork_project/clockwork-src`

Select interpreter:
`.venv/Scripts/python.exe` (or `.venv/bin/python` on Linux/macOS)

## Install
```
pip install -e .
```

## Commands
```
clockwork init          # Initialize .clockwork/ in current repo
clockwork scan          # Scan repository structure
clockwork verify        # Verify pending changes against rules + brain
clockwork verify --deep # Deep verification with full context validation
clockwork update        # Update live context index
clockwork handoff       # Transfer task to another agent
clockwork pack          # Package portable context snapshot
clockwork load          # Load a packaged context snapshot
clockwork graph         # Generate / update knowledge graph
clockwork status        # Show runtime metrics and task queue
clockwork recover       # Run failure-recovery and self-healing routines
```
