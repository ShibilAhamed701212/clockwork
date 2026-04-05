# Clockwork

<div align="center">

### CI/CD that heals itself when tests fail

**Works without AI. AI helps when you want it. You always approve the fixes.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## TL;DR — Try it in 30 seconds

```bash
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"
clockwork init
clockwork ci-run
```

---

## The Problem

You're building something. You push code. Tests fail at 2am.

**What if the pipeline just... fixed itself?**

---

## What Clockwork Does

```
clockwork ci-run
```
→ runs your stages (build → test → deploy)
→ if tests fail → retries automatically (up to 3x)
→ if still failing → AI analyzes the error (optional)
→ AI suggests a fix → **you approve** → it applies → retry

---

## Quick Start

```bash
# Install
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"

# Initialize
clockwork init

# Run pipeline
clockwork ci-run
```

---

## Real Example

```bash
$ clockwork ci-run

▶ Stage 1: build ✓
▶ Stage 2: test ✗ FAIL

   → Retry 1/3... ✗ still failing
   
   → AI Analysis:
   "Add null check on line 42"
   
   ? Apply fix? (y/N): y
   ✓ Fix applied
   
   → Retrying tests...
   ✓ All 23 tests passed

✓ Pipeline passed (1 fix applied)
```

---

## Why Not GitHub Actions?

| | Clockwork | GitHub Actions |
|---|:---:|:---:|
| Runs locally | ✅ | ❌ |
| Auto-retries | ✅ | ⚠️ |
| AI-assisted fixes | ✅ | ❌ |
| Understand in 5 min | ✅ | ❌ |

---

## AI: Optional. Always.

- **No AI = works perfectly** — just retries
- **With AI = helper** — suggests fixes, you decide
- **Never auto-applies** — you approve every change

```bash
# Enable when ready (optional)
clockwork ai-config set
```

---

## Limitations (Honest)

- Single-user local machine
- Python 3.10+ required
- AI features need an API key

---

## Installation

```bash
# Install from GitHub
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"

# Or clone and install
git clone https://github.com/ShibilAhamed701212/clockwork.git
cd clockwork
pip install -e .
```

---

## Commands

| Command | What |
|---------|------|
| `clockwork init` | Setup project |
| `clockwork ci-run` | Run pipeline |
| `clockwork scan` | Analyze code |
| `clockwork verify` | Check rules |
| `clockwork doctor` | Diagnose issues |
| `clockwork security scan` | Security scan |
| `clockwork security secrets` | Scan for secrets |
| `clockwork security sandbox` | Test commands safely |
| `clockwork validate json` | Validate JSON |
| `clockwork validate yaml` | Validate YAML |
| `clockwork validate syntax` | Validate Python syntax |
| `clockwork validate guard` | Check for hallucinations |
| `clockwork session show` | Show session info |
| `clockwork agent swarm` | Run agent swarm |
| `clockwork agent consensus` | Consensus voting |

---

## The Philosophy

> **Simple, local, reliable.**

We're building the tool you reach for when you just want to ship.

---

MIT — [LICENSE](LICENSE)
