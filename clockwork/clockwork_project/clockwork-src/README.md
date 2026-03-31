# Clockwork

**Local-first repository intelligence and AI agent coordination.**

Clockwork is a CLI tool that understands your codebase and makes AI coding assistants smarter. It scans your repository, builds a knowledge graph of dependencies, enforces governance rules, and generates context files that AI tools (Claude Code, Cursor, GitHub Copilot) use to write better code.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why Clockwork?

- **Context persistence** — AI tools lose context between sessions. Clockwork stores project memory in `.clockwork/context.yaml` so every session starts informed.
- **Style contracts** — Auto-generates `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, and `copilot-instructions.md` from your actual codebase.
- **Pre-commit governance** — Block bad AI-generated code before it reaches `main` via git hooks.
- **MCP integration** — Claude Code and Cursor can query your knowledge graph in real-time via Model Context Protocol.
- **Parallel agent sessions** — Git worktree management for running multiple AI agents simultaneously.

---

## Installation

```bash
# Install directly from GitHub
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"

# With optional dependencies
pip install "clockwork[mcp] @ git+https://github.com/ShibilAhamed701212/clockwork.git"   # MCP server support
pip install "clockwork[graph] @ git+https://github.com/ShibilAhamed701212/clockwork.git" # Knowledge graph (networkx)

# Local development install
git clone https://github.com/ShibilAhamed701212/clockwork.git
cd clockwork
pip install -e .
pip install -e ".[dev]"       # Development tools (pytest)
```

---

## Quick Start

```bash
# 1. Initialize Clockwork in your project
clockwork init --from-existing

# 2. View project health
clockwork status

# 3. Verify integrity
clockwork verify

# 4. Generate IDE context files
clockwork generate --format all

# 5. Install pre-commit hook
clockwork hooks install
```

For a guided setup experience:

```bash
clockwork init --interactive
```

---

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `clockwork init` | Initialize Clockwork in a repository |
| `clockwork scan` | Analyze repository structure → `repo_map.json` |
| `clockwork update` | Merge scan results into `context.yaml` |
| `clockwork verify` | Verify repository against rules |
| `clockwork handoff` | Generate agent handoff data |
| `clockwork status` | Rich dashboard with git, context, graph info |

### Intelligence Commands

| Command | Description |
|---------|-------------|
| `clockwork diff` | Show changed files with impact analysis |
| `clockwork ask "question"` | Natural language codebase queries |
| `clockwork doctor` | Diagnose installation and project health |
| `clockwork generate` | Generate IDE context files |

### Git Integration

| Command | Description |
|---------|-------------|
| `clockwork hooks install` | Install pre-commit verification hook |
| `clockwork hooks remove` | Remove the pre-commit hook |
| `clockwork hooks status` | Check if hook is installed |
| `clockwork worktree create <name>` | Create parallel worktree + branch |
| `clockwork worktree list` | List active worktrees |
| `clockwork worktree merge <name>` | Check conflicts and merge |
| `clockwork worktree clean <name>` | Remove worktree after merge |

### Infrastructure

| Command | Description |
|---------|-------------|
| `clockwork graph build` | Build the knowledge graph |
| `clockwork graph stats` | Show graph statistics |
| `clockwork index` | Build/refresh the live context index |
| `clockwork pack` | Package project intelligence |
| `clockwork load <file>` | Restore from a `.clockwork` package |
| `clockwork mcp start` | Start the MCP server |
| `clockwork recover` | Trigger recovery for failures |
| `clockwork repair` | Wipe and rebuild index + graph |

### Flags Available on Most Commands

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable JSON output |
| `--repo <path>` | Override repository root |

---

## AI IDE Integration

### Claude Code

```bash
# Auto-configure MCP for Claude Code
pip install clockwork[mcp]
clockwork mcp install-claude

# Or generate a context file
clockwork generate --format claude-md
```

This creates a `CLAUDE.md` in your project root with architecture, conventions, protected files, and current tasks — all derived from your actual codebase.

### Cursor

```bash
# Auto-configure MCP for Cursor
clockwork mcp install-cursor

# Or generate a rules file
clockwork generate --format cursorrules
```

### GitHub Copilot

```bash
clockwork generate --format copilot
# Creates .github/copilot-instructions.md
```

### OpenAI Codex / Agents

```bash
clockwork generate --format agents-md
# Creates AGENTS.md
```

### MCP Server (Advanced)

Start the MCP server manually for custom integrations:

```bash
# stdio mode (Claude Code native)
clockwork-mcp

# HTTP/SSE mode (Cursor, web IDEs)
clockwork mcp start --port 8080
```

Available MCP tools: `get_project_context`, `query_graph`, `check_file_safety`, `get_handoff_brief`, `run_verify`, `search_codebase`.

See [docs/mcp-integration.md](docs/mcp-integration.md) for full details.

---

## Workflow Recipes

### 1. Solo Developer Session Handoff

When ending a coding session, create a handoff so your next AI session picks up where you left off:

```bash
# End of session
clockwork scan
clockwork update
clockwork handoff

# Next session — the AI reads .clockwork/handoff/next_agent_brief.md
clockwork status
```

### 2. Pre-Commit Validation with Teams

Enforce project rules on every commit:

```bash
# One-time setup (each developer)
clockwork init --from-existing
clockwork hooks install

# Now every `git commit` runs:
#   clockwork verify --staged --json
# Commits are blocked if rules are violated.
# Bypass with: git commit --no-verify
```

### 3. Parallel Feature Development with Worktrees

Run multiple AI agents on different features simultaneously:

```bash
# Create isolated worktrees
clockwork worktree create login-feature
clockwork worktree create api-refactor

# List active sessions
clockwork worktree list

# Before merging, check for conflicts
clockwork worktree merge login-feature

# Clean up after merge
clockwork worktree clean login-feature
```

### 4. Onboarding a New AI Agent to an Existing Project

```bash
# Generate everything the AI needs
clockwork init --from-existing
clockwork generate --format all

# The AI now has:
#   CLAUDE.md          — project context for Claude
#   .cursorrules       — conventions for Cursor
#   AGENTS.md          — setup instructions for Codex
#   .clockwork/        — full project memory
```

### 5. CI/CD Integration

Add Clockwork verification to your CI pipeline:

```yaml
# .github/workflows/clockwork.yml
name: Clockwork Verify
on: [pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install clockwork
      - run: clockwork verify --full --json
```

---

## Project Structure

```
.clockwork/                  # Project intelligence directory
├── context.yaml             # Project memory (auto-updated)
├── rules.md                 # Governance rules
├── config.yaml              # Runtime configuration
├── repo_map.json            # Repository scan results
├── last_scan.json           # Git SHA tracking for incremental diffs
├── knowledge_graph.db       # Dependency graph (SQLite)
├── live_index.db            # File index (SQLite)
├── handoff/                 # Agent handoff data
├── packages/                # Portable .clockwork archives
├── plugins/                 # Plugin registry
└── logs/                    # Operation logs
```

---

## Configuration

Edit `.clockwork/config.yaml` to customize behavior:

```yaml
brain:
  mode: minibrain              # minibrain | ollama

scanner:
  ignore_dirs:
    - .git
    - node_modules
    - .venv

# Auto-generate IDE files on `clockwork update`
auto_generate_ide_files: true
ide_formats:
  - claude-md
  - cursorrules

packaging:
  auto_snapshot: false

logging:
  level: info
```

---

## Troubleshooting

Run the diagnostic command:

```bash
clockwork doctor
```

This checks Python version, dependencies, Ollama availability, project integrity, and data freshness. See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues.

---

## Documentation

- [MCP Integration Guide](docs/mcp-integration.md) — Connect to Claude Code, Cursor, and other IDEs
- [Worktree Guide](docs/worktrees.md) — Parallel agent workflow
- [Governance Reference](docs/governance.md) — Rules engine configuration
- [Troubleshooting](docs/troubleshooting.md) — Common issues and fixes

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev,graph,mcp]"

# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=clockwork --cov-report=term-missing
```

---

## License

MIT
