# Troubleshooting

Common issues and fixes for Clockwork.

## Diagnostic Tool

Run `clockwork doctor` for automated health checks:

```bash
clockwork doctor
```

This checks Python version, dependencies, Ollama availability, project
integrity, and graph/index freshness.

## Activity History Quick Checks

If you need to inspect what agents/tools did recently, use `clockwork history`
(which reads `.clockwork/logs/activity_history.jsonl`).

```bash
# Show last 20 events (default)
clockwork history

# Show only entries from one actor (exact match)
clockwork history --actor mcp

# Show only one action (exact match)
clockwork history --action tool:git_pull

# Combine filters and limit output
clockwork history --actor mcp --action tool:git_pull --limit 10

# Machine-readable output for scripts
clockwork history --json
```

Tip: If output is empty, verify that `.clockwork/logs/activity_history.jsonl`
exists and that Clockwork commands have run in this repository.

## Common Issues

### `watchdog` crashes on Windows

**Symptom**: `clockwork watch` fails or hangs on Windows.

**Fix**: Clockwork v0.2+ includes a polling fallback. If watchdog crashes,
it automatically falls back to polling-based file monitoring (2s interval).

If you still have issues:
```bash
pip install watchdog --upgrade
```

### `clockwork update` silently fails

**Symptom**: Running `clockwork update` shows success but context.yaml
doesn't change.

**Fix (v0.2+)**: Update now surfaces ContextEngine errors. Check the
warning message for details. Common causes:
- Corrupted `repo_map.json` — re-run `clockwork scan`
- Invalid `context.yaml` — re-run `clockwork init --force`

### MCP server won't start

**Symptom**: `clockwork mcp start` fails with ImportError.

**Fix**: Install the MCP SDK:
```bash
pip install clockwork[mcp]
# or
pip install mcp
```

### Knowledge graph not building

**Symptom**: `clockwork graph build` fails or graph is empty.

**Fix**: Install networkx:
```bash
pip install clockwork[graph]
# or
pip install networkx
```

### Pre-commit hook blocking commits

**Symptom**: `git commit` fails with Clockwork verification errors.

**Fix options**:
1. Fix the issues reported by the hook
2. Bypass once: `git commit --no-verify`
3. Remove the hook: `clockwork hooks remove`

### Empty summary/architecture fields

**Symptom**: `context.yaml` has empty `summary` and `architecture_overview`.

**Fix (v0.2+)**: Run `clockwork update` — the CodebaseSummarizer now
auto-fills these fields using deterministic heuristics. No AI model needed.

### context.yaml overwrites manual edits

**Symptom**: Human-authored fields (summary, notes) get overwritten on update.

**Fix (v0.2+)**: The merge_scan method now only overwrites scanner-derived
fields (primary_language, languages, frameworks, entry_points, total_files).
Human-authored fields are preserved.

## Getting Help

1. Run `clockwork doctor` for automated diagnostics
2. Check the [CHANGELOG](../CHANGELOG.md) for recent changes
3. Open an issue on GitHub
