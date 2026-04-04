# Clockwork Documentation

## Table of Contents

1. [What is Clockwork?](#what-is-clockwork)
2. [Purpose](#purpose)
3. [Use Cases](#use-cases)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Commands Reference](#commands-reference)
7. [Configuration](#configuration)
8. [AI Features](#ai-features)
9. [Examples](#examples)

---

## What is Clockwork?

Clockwork is a **local-first CI/CD tool with self-healing pipelines**. It automatically runs your build, test, and deploy stages, retries on failures, and optionally uses AI to analyze and suggest fixes when tests fail.

**Key Principles:**
- Works without AI (retries only)
- AI helps when you want it
- You always approve the fixes
- Runs locally on your machine

---

## Purpose

### The Problem

Traditional CI/CD systems have issues:
- **Long wait times** - Push code, wait 20+ minutes for CI to run
- **No auto-retry** - One failed test means failure
- **Complex configuration** - YAML files that take hours to understand
- **No local testing** - Can't test pipeline logic locally

### The Solution

Clockwork provides:
- **Local execution** - Run your entire pipeline on your machine
- **Auto-retries** - Automatically retry failed stages (up to 3x by default)
- **AI-assisted fixes** - Optional AI that analyzes errors and suggests fixes
- **Simple setup** - Configure in minutes, not hours
- **You stay in control** - Every fix requires your approval

---

## Use Cases

### 1. Solo Developers & Side Projects
- Quick feedback on code changes
- No waiting for cloud CI
- Test your pipeline locally before pushing

### 2. Local Development Workflow
- Run full CI/CD pipeline locally
- Catch issues before pushing to remote
- Iterate faster on fixes

### 3. CI/CD Pipeline Testing
- Test your CI configuration locally
- Debug pipeline issues without pushing
- Validate changes in isolation

### 4. Learning & Prototyping
- Learn CI/CD concepts without complexity
- Prototype pipeline ideas quickly
- Experiment with different configurations

### 5. AI-Assisted Bug Fixing (Optional)
- Get AI suggestions when tests fail
- Review AI-proposed fixes before applying
- Learn from AI's analysis

---

## Installation

### Requirements
- Python 3.10 or higher
- Git

### Install from PyPI (Coming Soon)
```bash
pip install clockwork
```

### Install from GitHub
```bash
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"
```

### Install for Development
```bash
git clone https://github.com/ShibilAhamed701212/clockwork.git
cd clockwork
pip install -e ".[dev]"
```

### Verify Installation
```bash
clockwork doctor
```

---

## Quick Start

### Step 1: Initialize a Project
```bash
cd your-project-directory
clockwork init
```

This creates:
- `.clockwork/` directory
- `context.yaml` - Project metadata
- `repo-map.json` - Code analysis results

### Step 2: Configure Your Pipeline
Edit `.clockwork/context.yaml` to define your stages:

```yaml
version: "2"
project:
  name: my-project
  language: python

pipeline:
  stages:
    - name: build
      command: pip install -e .
    - name: test
      command: pytest tests/ -v
    - name: deploy
      command: echo "Deploying..."
```

### Step 3: Run Your Pipeline
```bash
clockwork ci-run
```

### Step 4: (Optional) Enable AI
```bash
clockwork ai-config set
```

---

## Commands Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `clockwork init` | Initialize Clockwork in your project |
| `clockwork ci-run` | Run the CI/CD pipeline |
| `clockwork scan` | Analyze and map your codebase |
| `clockwork verify` | Verify project rules and configuration |
| `clockwork doctor` | Diagnose issues and check setup |

### Additional Commands

| Command | Description |
|---------|-------------|
| `clockwork update` | Update project metadata |
| `clockwork graph` | Build knowledge graph |
| `clockwork index` | Build search index |
| `clockwork handoff` | Generate project brief |
| `clockwork history` | View command history |
| `clockwork sync` | Sync with remote repository |

### MCP Server Commands

| Command | Description |
|---------|-------------|
| `clockwork mcp start` | Start MCP server |
| `clockwork mcp install` | Install MCP tools |

---

## Configuration

### context.yaml

The main configuration file:

```yaml
version: "2"
project:
  name: my-project
  language: python
  primary_branch: main

pipeline:
  stages:
    - name: build
      command: pip install -e .
      continue_on_error: false
    
    - name: test
      command: pytest tests/ -v
      max_retries: 3
      continue_on_error: false
    
    - name: deploy
      command: ./deploy.sh
      continue_on_error: false

rules:
  enabled: true
  path: .clockwork/rules.yaml

ai:
  enabled: false
  provider: ollama  # or openai, anthropic
```

### rules.yaml

Define project-specific rules:

```yaml
rules:
  - id: no-core-deletion
    type: safety
    description: Prevent deletion of core files
    pattern: "**/main.py"
    action: block

  - id: require-tests
    type: development
    description: New code must have tests
    action: warn
```

---

## AI Features

### Enabling AI

```bash
clockwork ai-config set
```

You'll be prompted to select a provider:
- **Ollama** - Local AI (free, runs on your machine)
- **OpenAI** - Cloud API (requires API key)
- **Anthropic** - Cloud API (requires API key)

### How AI Works

1. **On test failure** - After retries exhaust
2. **AI analyzes** - Error message, stack trace, code
3. **AI suggests** - A fix with explanation
4. **You approve** - Type `y` to apply, `n` to reject
5. **Fix applied** - If approved, changes are made
6. **Tests retry** - Pipeline continues

### AI Trust & Safety

- **Opt-in only** - AI is disabled by default
- **No auto-apply** - You must approve every fix
- **No external calls** - Unless you configure AI
- **Local AI option** - Use Ollama to keep everything local

---

## Examples

### Example 1: Python Project

```bash
# Initialize
clockwork init

# Configure pipeline in .clockwork/context.yaml
# Run pipeline
clockwork ci-run
```

### Example 2: With AI Fixes

```bash
# Enable AI
clockwork ai-config set

# Run pipeline - AI will help on failures
clockwork ci-run

# Output:
# ▶ Stage 1: build ✓
# ▶ Stage 2: test ✗ FAIL
# 
#    → Retry 1/3... ✗
#    → Retry 2/3... ✗
#    
#    → AI Analysis:
#    "Missing import for 'json' in utils.py line 42"
#    
#    ? Apply fix? (y/N): y
#    ✓ Fix applied
#    
#    → Retrying tests...
#    ✓ All tests passed
#
# ✓ Pipeline passed (1 fix applied)
```

### Example 3: Use as MCP Tool

```bash
# Install MCP integration
clockwork mcp install

# Use in Claude Code, Cursor, etc.
# Clockwork becomes available as an AI tool
```

### Example 4: Knowledge Graph

```bash
# Build knowledge graph of your codebase
clockwork graph build

# Query dependencies
clockwork graph depends-on src/utils.py

# Check if safe to delete
clockwork graph can-delete src/old_module/
```

### Example 5: Incremental Index

```bash
# Build file index for fast search
clockwork index

# Search code
clockwork index search "function_name"
```

---

## Troubleshooting

### Common Issues

**"No module named 'clockwork'"**
```bash
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"
```

**"context.yaml not found"**
```bash
clockwork init
```

**"Repository not a git repo"**
```bash
git init
```

### Check Health
```bash
clockwork doctor
```

This will:
- Check Python version
- Verify dependencies
- Check git repository
- Report any issues

---

## Philosophy

> **Simple, local, reliable.**

Clockwork is built for developers who want to:
- Ship faster without CI wait times
- Understand their tool in minutes
- Stay in control of their code
- Have AI help when they need it

---

## License

MIT - See [LICENSE](LICENSE)

---

## Support

- Report bugs: [GitHub Issues](https://github.com/ShibilAhamed701212/clockwork/issues)
- Discussions: [GitHub Discussions](https://github.com/ShibilAhamed701212/clockwork/discussions)
