
# Clockwork Project Specification
## File 00 — Master Prompt for Claude Code

Version: 0.1
Purpose: AI Implementation Seed Prompt

---

# Purpose of This File

This document provides the master instruction prompt used to seed AI coding agents (such as Claude Code) to implement the Clockwork system.

The AI agent must read all specification files inside:

docs/spec/

and implement the system according to those specifications.

Clockwork is a **local-first repository intelligence and agent coordination system**.

The AI agent must treat the specification files as the **source of truth for system design**.

---

# Instructions for AI Coding Agent

You are tasked with implementing the Clockwork system according to the architecture specifications provided.

The specification files describe each subsystem in detail.

You must:

• read all files in docs/spec  
• understand subsystem relationships  
• implement the system incrementally  
• maintain modular architecture  

Do not invent architecture outside the specification unless necessary for implementation.

---

# Repository Layout to Generate

The AI agent must generate the following repository structure.

clockwork/

clockwork/
  cli/
  scanner/
  context/
  rules/
  brain/
  handoff/
  packaging/
  graph/

docs/
  spec/

tests/

pyproject.toml
README.md

---

# Development Principles

The generated code must follow these principles.

## Modular Design

Each subsystem must exist as its own module.

Examples:

clockwork/scanner/
clockwork/context/
clockwork/rules/
clockwork/brain/

Modules must interact through well-defined interfaces.

---

## Local First

Clockwork must run completely locally.

External APIs are optional integrations.

---

## Deterministic Core

Core system behavior must not depend on AI models.

MiniBrain must function without external models.

---

## Safety First

Clockwork must prevent destructive repository modifications.

Rule Engine and Brain must validate all changes.

---

# Implementation Order

The AI agent must implement subsystems in the following order.

1. CLI System
2. Repository Scanner
3. Context Engine
4. Rule Engine
5. Clockwork Brain
6. Knowledge Graph
7. Agent Handoff System
8. Packaging System

Each subsystem must include:

• unit tests
• type hints
• documentation

---

# Language Requirements

Implementation language:

Python 3.10+

Required libraries:

typer
pyyaml
gitpython
sqlite3

Optional libraries:

tree-sitter
networkx

---

# Code Quality Standards

The generated code must include:

• type hints
• docstrings
• modular structure
• readable variable names
• test coverage

Avoid monolithic files.

Prefer small focused modules.

---

# CLI Requirements

The CLI must expose commands:

clockwork init
clockwork scan
clockwork verify
clockwork update
clockwork handoff
clockwork pack
clockwork load
clockwork graph

Use the Typer framework.

---

# Testing Requirements

Tests must exist in:

tests/

Each subsystem must include tests.

Example:

tests/test_scanner.py
tests/test_context.py
tests/test_rules.py

---

# Logging

Clockwork must log operations inside:

.clockwork/

Example logs:

validation_log.json
rule_log.json
brain_log.json

---

# Error Handling

The system must fail safely.

Never crash due to malformed repository files.

Errors must produce readable CLI output.

---

# Security Requirements

The system must never execute repository code.

All analysis must be static.

Sensitive files must be ignored.

Examples:

.env
credentials.json
secrets files

---

# Extensibility

Clockwork must support plugin-based extensions.

Future plugins may include:

• additional reasoning engines
• security scanners
• CI/CD analyzers

Plugin loading should occur through:

.clockwork/plugins/

---

# Future Considerations

The architecture should support future features such as:

• multi-agent orchestration
• distributed context sharing
• architecture visualization
• autonomous development workflows

The system should be designed with extensibility in mind.

---

# Final Instruction

Read every specification file carefully.

Then begin implementing Clockwork incrementally while maintaining architecture consistency with the specifications.

Do not ignore subsystem boundaries.

Clockwork must be implemented as a **modular repository intelligence system**.
