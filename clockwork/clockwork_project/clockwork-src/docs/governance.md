# Governance & Rules Engine

Clockwork provides a governance layer that enforces project conventions
across AI coding agents and human developers.

## Rules Configuration

Rules are defined in `.clockwork/rules.md` using markdown format:

```markdown
# Project Rules

## Code Quality
- All new files must have docstrings
- Tests must mirror source structure in tests/
- Type hints required for all public functions

## Protected Files
- Do not modify .clockwork/ directory
- Do not delete core/engine.py without approval
- Must not change database migrations after deploy

## Architecture
- CLI commands must use typer.Option for all parameters
- All commands must support --json output
- Scanner pipeline: scanner → context → graph → brain
```

## Config Settings

`.clockwork/config.yaml` controls runtime behavior:

```yaml
mode: safe          # safe | autonomous
autonomy: restricted  # restricted | partial | full
validation: strict    # strict | relaxed

# IDE context auto-generation (Phase 3)
auto_generate_ide_files: true
ide_formats:
  - claude-md
  - cursorrules
  - copilot

# Scanner configuration
scanner:
  ignore_dirs:
    - vendor
    - coverage
```

## Verification Pipeline

The verification pipeline runs on every `clockwork verify`:

1. **Required files check** — context.yaml, rules.md, config.yaml
2. **Schema validation** — context.yaml structure
3. **Diff analysis** — changed files since last scan (git-aware)
4. **Rule evaluation** — check changed files against rules.md
5. **Deep validation** — predictive risk scoring (with `--deep`)

## Pre-Commit Integration

Install the pre-commit hook to enforce rules before every commit:

```bash
clockwork hooks install
```

This runs `clockwork verify --staged` before each commit, blocking
commits that violate project rules.

## IDE Integration

Generated context files carry rules into AI assistants:
- **CLAUDE.md** → Claude Code reads this automatically
- **.cursorrules** → Cursor reads this automatically
- **AGENTS.md** → Codex/OpenAI agents read this
- **.github/copilot-instructions.md** → GitHub Copilot reads this
