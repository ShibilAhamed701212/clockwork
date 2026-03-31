# Worktree Guide — Parallel Agent Sessions

Clockwork supports git worktrees for running multiple AI agent sessions
simultaneously on different tasks, without merge conflicts.

## Quick Start

```bash
# Create a worktree for a task
clockwork worktree create login-feature

# Work in the new worktree
cd ../myproject-login-feature

# List all active worktrees
clockwork worktree list

# Check for conflicts before merging
clockwork worktree merge login-feature

# Clean up after merging
clockwork worktree clean login-feature
```

## How It Works

1. **Create** — Makes a new git worktree at `../project-<task-name>/`
   with a new branch `feature/<task-name>`. Copies `.clockwork/` directory.
2. **Work** — Each worktree has its own Clockwork context, rules, and graph.
3. **Merge** — Predicts conflicts using the knowledge graph before merging.
4. **Clean** — Removes the worktree directory and the feature branch.

## Conflict Prediction

When running `clockwork worktree merge`, Clockwork analyzes:

- **File conflicts** — files modified in both branches
- **Dependency conflicts** — files modified in the feature branch whose
  dependents were modified in the base branch (via knowledge graph)
- **Risk assessment** — low/medium/high based on conflict count and
  dependency depth

## Multi-Agent Workflow

```
Agent A: clockwork worktree create auth
Agent B: clockwork worktree create ui-redesign
Agent C: clockwork worktree create api-v2

# Each agent works independently in their worktree
# When done:

clockwork worktree merge auth      # Check conflicts
git merge feature/auth             # Merge if safe
clockwork worktree clean auth      # Clean up
```

## Handoff Integration

Worktree metadata is automatically included in handoff data:
- `worktree_path` — where the agent is working
- `branch_name` — the feature branch
- `base_branch` — what to merge into
- `merge_conflicts_predicted` — predicted conflicts
