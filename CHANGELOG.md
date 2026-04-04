# Changelog

All notable changes to Clockwork are documented in this file.

## [0.2.0] — 2026-03-30

### Added

#### Phase 1: Git Integration
- **GitDiffScanner** — diff-aware scanning via `gitpython` with SHA tracking
- **Diff-aware verify** — `clockwork verify` now only checks changed files by default
- `clockwork verify --staged` — pre-commit mode (only staged files)
- `clockwork verify --full` — bypass diff, check everything
- `clockwork hooks install/remove/status` — pre-commit hook management
- ScanResult extended with `git_branch`, `git_commit`, `git_is_dirty`, `git_untracked_count`
- `.clockwork/last_scan.json` — tracks last-scan SHA for incremental diffs

#### Phase 2: MCP Server
- **Clockwork MCP Server** — 6 tools for AI IDE integration:
  - `get_project_context`, `query_graph`, `check_file_safety`
  - `get_handoff_brief`, `run_verify`, `search_codebase`
- `clockwork mcp start` — stdio mode (Claude Code) and `--port` for HTTP/SSE (Cursor)
- `clockwork mcp install-claude` / `install-cursor` — auto-configure IDE MCP settings
- `clockwork-mcp` script entry point for direct MCP server usage

#### Phase 3: IDE Context File Generation
- **IDEContextGenerator** — generates CLAUDE.md, .cursorrules, AGENTS.md, copilot-instructions.md
- `clockwork generate --format all|claude-md|cursorrules|agents-md|copilot`
- `clockwork generate --preview` — print to stdout without writing
- Auto-generation on `clockwork update` when `auto_generate_ide_files: true` in config.yaml

#### Phase 4: AI Summarization
- **CodebaseSummarizer** — deterministic MiniBrain heuristics for project description
- Auto-fills empty `summary` and `architecture_overview` fields on `clockwork update`
- Convention detection from scan data

#### Phase 5: CLI Commands
- **Rich status dashboard** (`clockwork status`) — git info, context freshness, graph stats, active issues
- `clockwork diff` — changed files since last scan with impact analysis and risk assessment
- `clockwork ask "question"` — natural language codebase queries via graph + search
- `clockwork doctor` — diagnostic health checks (Python, deps, Ollama, project integrity)

#### Phase 6: Multi-Agent Worktree Support
- `clockwork worktree create/list/merge/clean` — git worktree management for parallel agents
- **ConflictPredictor** — pre-merge conflict analysis using knowledge graph
- HandoffData extended with `worktree_path`, `branch_name`, `base_branch`, `merge_conflicts_predicted`

#### Phase 7: Interactive Setup
- `clockwork init --interactive` — guided wizard with project type, AI tool selection
- `clockwork init --from-existing` — auto-scan + summarize + generate IDE files
- First-run detection in `clockwork scan` — offers to run `clockwork init` if not initialized

### Changed

#### Phase 8: Reliability Fixes
- **Windows watcher** — polling fallback when watchdog Observer fails
- **Error surfacing** — `clockwork update` now surfaces ContextEngine errors instead of silently swallowing
- **Field preservation** — merge_scan verified to never overwrite human-authored fields
- **Packaging** — optional files (handoff/handoff.json, etc.) no longer crash when missing

#### Phase 9: Documentation
- **README rewrite** — full professional README with installation, quick start, integration guides, and 5 workflow recipes
- Docs directory with MCP integration, worktree, governance, and troubleshooting guides
- CHANGELOG covering all phases

### Fixed
- **Version consistency** — `CLOCKWORK_VERSION` now reads `0.2.0` in all modules (context/models.py, packaging/models.py, init template) matching pyproject.toml
- **IDE file import** — `clockwork init --from-existing` now parses existing CLAUDE.md / .cursorrules and imports novel convention rules into rules.md
- **Formalized _preserve_fields** — ContextEngine.merge_scan() now documents its preservation contract via `_PRESERVE_FIELDS` and `_SCANNER_FIELDS` class constants

### Internal
- Version bumped to 0.2.0
- `mcp` optional dependency added (`pip install clockwork[mcp]`)
- 60+ new tests covering all new features

## [0.1.0] — 2026-03-15

### Added
- Initial release: scanner, context, graph, brain, agents, validation, recovery
- CLI commands: init, scan, update, verify, handoff, pack, load, index, repair, watch, status, recover, graph, agent
- 429 passing tests
