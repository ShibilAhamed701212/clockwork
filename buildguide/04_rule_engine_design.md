
# Clockwork Project Specification
## File 04 — Rule Engine Design

Version: 0.1
Subsystem: Rule Engine
Document Type: Technical Architecture Specification

---

# 1. Purpose

The Rule Engine is responsible for enforcing **development standards, repository safety policies, and architectural constraints** inside Clockwork.

The rule engine acts as a **policy layer** that ensures every modification performed by humans or AI agents follows the defined project rules.

Without the Rule Engine, AI agents could:

• delete critical files  
• violate architecture boundaries  
• introduce incompatible changes  
• corrupt repository state  

The Rule Engine prevents these outcomes by validating every change before it is accepted.

---

# 2. Rule Engine Responsibilities

The Rule Engine must enforce:

• coding standards  
• architecture boundaries  
• repository safety rules  
• dependency constraints  
• testing requirements  

The engine must validate changes before the repository state is updated.

---

# 3. Rule Storage Location

Rules are stored in:

.clockwork/rules.md

Additional machine-readable rules may be stored in:

.clockwork/rules.yaml

Example structure:

rules:
  forbid_core_file_deletion: true
  require_tests_for_new_modules: true
  enforce_architecture_layers: true

---

# 4. Rule Categories

Rules fall into four major categories.

## Safety Rules

Prevent destructive operations.

Examples:

• prevent deletion of core files  
• prevent modification of protected directories  
• prevent context file tampering  

---

## Architecture Rules

Ensure repository structure remains valid.

Examples:

• frontend cannot directly access database  
• API layer must exist between frontend and backend  
• service modules cannot bypass repository layer  

---

## Development Rules

Ensure code quality.

Examples:

• tests required for new modules  
• documentation required for public APIs  
• dependency updates must be declared  

---

## Context Rules

Ensure project memory integrity.

Examples:

• context must match repository structure  
• architecture summary must be valid  
• framework declarations must match dependencies  

---

# 5. Rule Definition Format

Rules should support a structured definition format.

Example YAML:

rules:

  forbid_file_patterns:
    - "*.env"
    - ".clockwork/*"

  protected_directories:
    - "core/"
    - "database/"

  require_tests_for:
    - "backend/"
    - "services/"

---

# 6. Rule Evaluation Pipeline

The Rule Engine operates inside the Clockwork verification pipeline.

Pipeline:

Repository Change
        ↓
Repository Diff Detection
        ↓
Rule Engine Evaluation
        ↓
Brain Analysis
        ↓
Context Update

Rules must be evaluated before AI reasoning engines.

---

# 7. Rule Evaluation Steps

Evaluation steps:

1. Detect repository changes.
2. Identify modified files.
3. Match changes against rule patterns.
4. Detect violations.
5. Generate rule report.

Example report:

Rule violation detected:

Protected directory modified:
database/schema.sql

---

# 8. File Protection Rules

The engine must support protected files.

Example:

protected_files:

  - ".clockwork/context.yaml"
  - ".clockwork/rules.md"

These files cannot be modified without explicit confirmation.

---

# 9. Directory Protection Rules

Protected directories prevent modification of core infrastructure.

Example:

protected_directories:

  - "core/"
  - "database/"

Modifications require override approval.

---

# 10. Dependency Rules

Dependency rules enforce package consistency.

Example:

• dependency added → must appear in dependency file  
• dependency removed → must be removed from code  

Supported files:

requirements.txt  
package.json  
pyproject.toml  

---

# 11. Test Enforcement Rules

The rule engine should enforce test requirements.

Example:

If new module created:

backend/auth.py

Then test file must exist:

tests/test_auth.py

Violation example:

Rule violation:
Module created without tests.

---

# 12. Rule Violation Handling

If a rule violation occurs:

Clockwork must:

1. reject modification
2. display violation explanation
3. request override confirmation

Example output:

Rule Violation Detected

Protected file modification attempted:
.clockwork/context.yaml

---

# 13. Rule Override System

Users must be able to override rules manually.

Example command:

clockwork override

Overrides must be logged in:

.clockwork/override_log.json

---

# 14. Rule Conflict Resolution

Multiple rules may conflict.

Priority order:

1. Safety Rules
2. Architecture Rules
3. Development Rules
4. Context Rules

Higher priority rules override lower priority rules.

---

# 15. Rule Performance Requirements

Rule evaluation must remain fast.

Target evaluation time:

< 200 milliseconds per verification cycle.

The rule engine must operate before expensive reasoning engines.

---

# 16. Logging

All rule decisions must be logged.

Log file:

.clockwork/rule_log.json

Example entry:

{
 "timestamp": "2026-03-14",
 "rule": "protected_file_modification",
 "status": "blocked"
}

---

# 17. Rule Engine Extensibility

The rule engine must support custom rule plugins.

Examples:

• organization policies  
• CI/CD enforcement rules  
• security rules  

Plugins should be loaded from:

.clockwork/plugins/

---

# 18. Security Model

Rules must never execute code from the repository.

All analysis must be static.

Clockwork must treat rules as configuration only.

---

# 19. Future Enhancements

Future versions may include:

• automated rule suggestions  
• ML-based architecture detection  
• security vulnerability detection  
• automated refactoring recommendations
