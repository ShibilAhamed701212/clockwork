# MCP Integration Guide

Clockwork exposes repository intelligence as MCP (Model Context Protocol) tools,
enabling AI coding assistants to query your project context in real-time.

## Supported IDEs

| IDE | Transport | Command |
|-----|-----------|---------|
| Claude Code | stdio | `clockwork mcp install-claude` |
| Cursor | stdio | `clockwork mcp install-cursor` |
| GitHub Copilot | MCP config | Manual config |

## Quick Setup

### Claude Code

```bash
# Install MCP SDK
pip install clockwork[mcp]

# Auto-configure Claude Code
clockwork mcp install-claude

# Restart Claude Code
```

### Cursor

```bash
pip install clockwork[mcp]
clockwork mcp install-cursor
# Restart Cursor
```

### Manual Configuration

Add to your MCP config:

```json
{
  "mcpServers": {
    "clockwork": {
      "command": "clockwork-mcp",
      "args": [],
      "cwd": "/path/to/your/project"
    }
  }
}
```

## Available MCP Tools

### `get_project_context`
Returns the full project context (context.yaml) as structured data.
No parameters required.

### `query_graph`
Query dependency relationships in the codebase.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | One of: `depends_on`, `dependents_of`, `is_safe_to_delete`, `files_in_layer` |
| `target` | string | File path or layer name to query about |

### `check_file_safety`
Check if modifying or deleting a file would violate rules or break dependents.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Path to the file |
| `operation` | string | One of: `delete`, `modify`, `create` |

### `get_handoff_brief`
Returns the next agent handoff brief (next_agent_brief.md).
No parameters required.

### `run_verify`
Run Clockwork verification on the entire project.

### `search_codebase`
Search the codebase using the knowledge graph.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Search query |
| `limit` | integer | Max results (default: 10) |

## HTTP/SSE Mode

For web-based IDEs or remote access:

```bash
clockwork mcp start --port 8080
```

Requires additional dependencies: `pip install starlette uvicorn`
