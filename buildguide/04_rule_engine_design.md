# 🚨 CLOCKWORK SYSTEM PROMPT — READ FULLY BEFORE ANY ACTION

⚠️ CRITICAL INSTRUCTION:
You MUST read this ENTIRE document from top to bottom.
DO NOT start coding until you have COMPLETELY read EVERYTHING in this file.

- Do NOT skip sections
- Do NOT assume missing context
- This file is PART of a 14-file system
- You are continuing a system, NOT starting fresh

---

## 🧠 SYSTEM IDENTITY

You are building a unified autonomous system called **Clockwork**.

This is NOT a single script.
This is a FULL-SCALE, INTERCONNECTED ARCHITECTURE.

Each `.md` file contributes ONE PART of the SAME SYSTEM.

---

## 📁 ROOT PROJECT LOCATION (STRICT)

All code MUST be created inside:

`D:\var-codes\Clockworker`

---

## 🏗️ COMPLETE PROJECT STRUCTURE (SOURCE OF TRUTH)

You MUST follow this EXACT structure:

clockwork/
│
├── cli/
│ ├── main.py
│ ├── commands/
│ │ ├── init.py
│ │ ├── scan.py
│ │ ├── verify.py
│ │ ├── update.py
│ │ ├── handoff.py
│ │ ├── pack.py
│ │ ├── load.py
│ │ ├── graph.py
│ │ ├── watch.py
│ │ ├── repair.py
│ │ └── agent.py
│ └── utils/
│ ├── parser.py
│ └── output.py
│
├── scanner/
│ ├── scanner.py
│ ├── directory_walker.py
│ ├── language_detector.py
│ ├── dependency_analyzer.py
│ ├── architecture_inferer.py
│ ├── relationship_mapper.py
│ └── output/repo_map.json
│
├── context/
│ ├── context_engine.py
│ ├── context_store.py
│ ├── context_validator.py
│ ├── live_index/
│ │ ├── watcher.py
│ │ ├── event_queue.py
│ │ ├── incremental_processor.py
│ │ └── sync_engine.py
│ └── schemas/context_schema.yaml
│
├── rules/
│ ├── rule_engine.py
│ ├── rule_parser.py
│ ├── validators/
│ │ ├── structure_rules.py
│ │ ├── dependency_rules.py
│ │ └── safety_rules.py
│ └── rules.md
│
├── brain/
│ ├── brain.py
│ ├── decision_engine.py
│ ├── planning_engine.py
│ ├── optimization_engine.py
│ ├── meta_reasoning.py
│ └── prioritization.py
│
├── graph/
│ ├── graph_builder.py
│ ├── node_manager.py
│ ├── edge_manager.py
│ ├── query_engine.py
│ ├── anomaly_detector.py
│ └── storage/knowledge_graph.db
│
├── agents/
│ ├── runtime.py
│ ├── agent_registry.py
│ ├── task_queue.py
│ ├── task_graph.py
│ ├── router.py
│ ├── load_balancer.py
│ ├── swarm/
│ │ ├── coordinator.py
│ │ └── consensus.py
│ └── sandbox/executor.py
│
├── validation/
│ ├── pipeline.py
│ ├── output_validator.py
│ ├── hallucination_guard.py
│ └── reality_check.py
│
├── state/
│ ├── state_manager.py
│ ├── session_tracker.py
│ ├── state_machine.py
│ └── snapshots/snapshots.db
│
├── recovery/
│ ├── recovery_engine.py
│ ├── rollback.py
│ ├── retry.py
│ ├── self_healing.py
│ ├── predictor.py
│ └── logs/failure_log.json
│
├── security/
│ ├── sandbox.py
│ ├── access_control.py
│ ├── command_filter.py
│ ├── plugin_security.py
│ ├── secrets_protection.py
│ └── logs/security_log.json
│
├── packaging/
│ ├── packer.py
│ ├── loader.py
│ ├── serializer.py
│ └── format/clockwork_package.json
│
├── registry/
│ ├── registry_client.py
│ ├── plugin_manager.py
│ ├── publisher.py
│ ├── search.py
│ ├── cache/registry_cache.json
│ └── api/routes.py
│
├── config/
│ ├── config.yaml
│ └── settings.py
│
├── logs/
│ ├── system.log
│ ├── agent.log
│ └── debug.log
│
├── .clockwork/
│ ├── context.yaml
│ ├── repo_map.json
│ ├── knowledge_graph.db
│ ├── tasks.json
│ ├── agents.json
│ └── index.db
│
├── tests/
│ ├── test_scanner.py
│ ├── test_graph.py
│ ├── test_agents.py
│ └── test_recovery.py
│
├── docs/
│ ├── 01_foundation.md
│ ├── 02_scanner.md
│ ├── ...
│ └── 14_registry.md
│
├── requirements.txt
├── README.md
└── main.py

---

## 🔗 SYSTEM BEHAVIOR RULES

- This file is PART of a sequence → treat as continuation
- NEVER build isolated modules
- ALWAYS connect with existing systems

---

## 🔄 EXECUTION FLOW (MANDATORY)

scanner → context → graph → brain → agents → validation → recovery

Every feature MUST integrate into this pipeline.

---

## 🌐 DOCUMENTATION RULE

Before coding:

- Verify latest official docs
- Use correct versions
- Avoid outdated implementations

---

## 🚫 HARD RESTRICTIONS

- Do NOT create files outside structure
- Do NOT duplicate modules
- Do NOT ignore other systems
- Do NOT write pseudo code

---

## 🎯 YOUR TASK

Scroll down ↓  
Read ALL instructions in this file  
Then implement ONLY what this file defines  
While respecting the FULL system above

---**************************************\*\*\*\***************************************\_**************************************\*\*\*\***************************************

# Clockwork Project Specification

## File 04 — Rule Engine System

Version: 2.0  
Subsystem: Rule Engine  
Document Type: Policy Enforcement + Constraint Intelligence Engine

---

# 🚀 FEATURE MAP (FROM MASTER 62)

- central_decision_kernel
- system_wide_consistency_enforcer
- intent_lock_system
- reality_check_layer
- anomaly_detection_system
- breakage_prediction_engine

---

# 0. SYSTEM ROLE (CRITICAL)

The Rule Engine is the **law enforcement system of Clockwork**.

It acts as:

> The Policy + Constraint + Safety Authority of the Entire System

---

Without the Rule Engine:

- AI becomes unsafe
- architecture becomes unstable
- system integrity collapses

---

🔥 FEATURE: system_wide_consistency_enforcer

The Rule Engine ensures:

- structural integrity
- architectural consistency
- rule compliance

---

# 1. PURPOSE (DEEP SYSTEM DEFINITION)

The Rule Engine enforces:

````text
Allowed Actions vs Forbidden Actions

It transforms:

Proposed Change → Validated / Rejected Action

🧠 INTELLIGENCE: central_decision_kernel

The Rule Engine must act as the first decision checkpoint before execution.

2. CORE RESPONSIBILITIES
2.1 Safety Enforcement

prevent destructive operations

block unsafe modifications

2.2 Architecture Enforcement

maintain system structure

enforce layer boundaries

2.3 Dependency Enforcement

validate dependency changes

prevent inconsistencies

2.4 Context Alignment

ensure context matches repository

prevent drift

2.5 Intent Alignment

🔥 FEATURE: intent_lock_system

ensure actions match user intent

reject scope deviation

3. RULE STORAGE MODEL
3.1 Rule Files
.clockwork/rules.md
.clockwork/rules.yaml
3.2 Rule Types

human-readable rules (MD)

machine-readable rules (YAML)

3.3 Example Structure
rules:
  forbid_core_file_deletion: true
  enforce_architecture_layers: true
4. RULE CLASSIFICATION SYSTEM
4.1 Safety Rules

prevent file deletion

protect core modules

4.2 Architecture Rules

enforce layering

restrict cross-layer access

4.3 Development Rules

enforce testing

enforce documentation

4.4 Context Rules

context must match repo

no stale memory

5. RULE EVALUATION PIPELINE
5.1 Execution Flow
Proposed Change
   ↓
Diff Detection
   ↓
Rule Matching
   ↓
Violation Detection
   ↓
Decision Output
5.2 Decision Output

approved

warning

rejected

⚙️ IMPLEMENTATION: reality_check_layer

6. RULE MATCHING SYSTEM
6.1 Matching Inputs

file changes

dependency changes

architecture changes

6.2 Matching Logic
Change → Pattern Match → Rule Trigger
6.3 Pattern Types

file path patterns

dependency patterns

architecture patterns

7. VIOLATION DETECTION SYSTEM
7.1 Violation Types

safety violation

architecture violation

dependency violation

context violation

7.2 Detection Model
Rule Condition
   ↓
Change Analysis
   ↓
Violation Detection

🔥 FEATURE: anomaly_detection_system

Used to detect unusual or unsafe changes.

8. FILE PROTECTION SYSTEM
8.1 Protected Files
.clockwork/context.yaml
.clockwork/rules.md
8.2 Protection Behavior

block modification

require explicit override

9. DIRECTORY PROTECTION SYSTEM
9.1 Protected Directories

core/

database/

9.2 Protection Logic

restrict changes

require validation

🔗 PART 1 END

Awaiting continuation...


---

# 🚀 NEXT STEP

Say:
👉 **continue file04 part2**

Next we go deeper into:

- dependency rules
- test enforcement
- override system
- conflict resolution
- logging

---

Now you’re building:

> ⚖️ The LAW of your AI OS — nothing runs without this 💀🔥


# 🔥 PART 2 — RULE ENFORCEMENT + VALIDATION SYSTEM

---

# 10. DEPENDENCY RULE SYSTEM

The Rule Engine must enforce strict dependency integrity.

---

🔥 FEATURE: breakage_prediction_engine

---

## 10.1 Dependency Rules

- new dependency → must be declared
- removed dependency → must not exist in code
- version conflicts → must be resolved

---

## 10.2 Validation Flow

```text id="xk5x3r"
Dependency Change
   ↓
Dependency File Check
   ↓
Code Reference Check
   ↓
Consistency Validation
10.3 Violation Examples

library used but not installed

library removed but still referenced

11. TEST ENFORCEMENT SYSTEM

The Rule Engine must enforce testing requirements.

11.1 Rule

If a new module is created → test must exist

11.2 Example

Module:
backend/auth.py

Required:
tests/test_auth.py

11.3 Violation

❌ Module created without tests

11.4 Enforcement Model
File Created
   ↓
Test Check
   ↓
Pass / Fail
12. RULE VIOLATION HANDLING

The Rule Engine must handle violations strictly.

12.1 Response Strategy

If violation occurs:

reject change

explain violation

request override

12.2 Output Format
Rule Violation Detected
Reason: Protected file modified
12.3 Severity Levels

low → warning

medium → restrict

high → block

13. RULE OVERRIDE SYSTEM

Users must be able to override rules manually.

13.1 Override Command
clockwork override
13.2 Override Behavior

allow temporary bypass

log override action

require confirmation

13.3 Override Logging
.clockwork/override_log.json
13.4 Override Entry
{
 "timestamp": "",
 "rule": "",
 "reason": "",
 "user": ""
}
14. RULE CONFLICT RESOLUTION SYSTEM

Rules may conflict — system must resolve deterministically.

14.1 Priority Hierarchy

Safety Rules

Architecture Rules

Dependency Rules

Development Rules

Context Rules

14.2 Resolution Model
Conflicting Rules
   ↓
Priority Comparison
   ↓
Higher Rule Wins
14.3 Example

rule A allows change

rule B blocks change

Result → rule B wins if higher priority

15. RULE PERFORMANCE SYSTEM

The Rule Engine must be extremely fast.

15.1 Performance Target

< 200ms per validation cycle

15.2 Optimization Techniques

rule indexing

pattern caching

selective evaluation

15.3 Execution Order

Rule Engine must run:

BEFORE:

Brain

AI reasoning

16. RULE LOGGING SYSTEM

All decisions must be recorded.

16.1 Log File
.clockwork/rule_log.json
16.2 Log Structure
{
 "timestamp": "",
 "rule": "",
 "status": "allowed | blocked",
 "details": ""
}
16.3 Logging Purpose

audit trail

debugging

system analysis

17. RULE EXTENSIBILITY SYSTEM

The Rule Engine must support plugins.

17.1 Plugin Types

organization policies

security rules

CI/CD rules

17.2 Plugin Location
.clockwork/plugins/
17.3 Plugin Constraints

must follow rule format

must not break system

must be validated

🔗 PART 2 END

Awaiting continuation...


---

# 🚀 NEXT STEP

Say:
👉 **continue file04 part3**

Final part will include:

- security model
- AI execution contract
- system integration
- advanced enforcement logic

---

Now your Rule Engine is becoming:

> ⚖️ A real law system that AI cannot bypass 💀🔥

# 🔥 PART 2 — RULE ENFORCEMENT + VALIDATION SYSTEM

---

# 10. DEPENDENCY RULE SYSTEM

The Rule Engine must enforce strict dependency integrity.

---

🔥 FEATURE: breakage_prediction_engine

---

## 10.1 Dependency Rules

- new dependency → must be declared
- removed dependency → must not exist in code
- version conflicts → must be resolved

---

## 10.2 Validation Flow

```text id="xk5x3r"
Dependency Change
   ↓
Dependency File Check
   ↓
Code Reference Check
   ↓
Consistency Validation
10.3 Violation Examples

library used but not installed

library removed but still referenced

11. TEST ENFORCEMENT SYSTEM

The Rule Engine must enforce testing requirements.

11.1 Rule

If a new module is created → test must exist

11.2 Example

Module:
backend/auth.py

Required:
tests/test_auth.py

11.3 Violation

❌ Module created without tests

11.4 Enforcement Model
File Created
   ↓
Test Check
   ↓
Pass / Fail
12. RULE VIOLATION HANDLING

The Rule Engine must handle violations strictly.

12.1 Response Strategy

If violation occurs:

reject change

explain violation

request override

12.2 Output Format
Rule Violation Detected
Reason: Protected file modified
12.3 Severity Levels

low → warning

medium → restrict

high → block

13. RULE OVERRIDE SYSTEM

Users must be able to override rules manually.

13.1 Override Command
clockwork override
13.2 Override Behavior

allow temporary bypass

log override action

require confirmation

13.3 Override Logging
.clockwork/override_log.json
13.4 Override Entry
{
 "timestamp": "",
 "rule": "",
 "reason": "",
 "user": ""
}
14. RULE CONFLICT RESOLUTION SYSTEM

Rules may conflict — system must resolve deterministically.

14.1 Priority Hierarchy

Safety Rules

Architecture Rules

Dependency Rules

Development Rules

Context Rules

14.2 Resolution Model
Conflicting Rules
   ↓
Priority Comparison
   ↓
Higher Rule Wins
14.3 Example

rule A allows change

rule B blocks change

Result → rule B wins if higher priority

15. RULE PERFORMANCE SYSTEM

The Rule Engine must be extremely fast.

15.1 Performance Target

< 200ms per validation cycle

15.2 Optimization Techniques

rule indexing

pattern caching

selective evaluation

15.3 Execution Order

Rule Engine must run:

BEFORE:

Brain

AI reasoning

16. RULE LOGGING SYSTEM

All decisions must be recorded.

16.1 Log File
.clockwork/rule_log.json
16.2 Log Structure
{
 "timestamp": "",
 "rule": "",
 "status": "allowed | blocked",
 "details": ""
}
16.3 Logging Purpose

audit trail

debugging

system analysis

17. RULE EXTENSIBILITY SYSTEM

The Rule Engine must support plugins.

17.1 Plugin Types

organization policies

security rules

CI/CD rules

17.2 Plugin Location
.clockwork/plugins/
17.3 Plugin Constraints

must follow rule format

must not break system

must be validated

🔗 PART 2 END

Awaiting continuation...


---

# 🚀 NEXT STEP

Say:
👉 **continue file04 part3**

Final part will include:

- security model
- AI execution contract
- system integration
- advanced enforcement logic

---

Now your Rule Engine is becoming:

> ⚖️ A real law system that AI cannot bypass 💀🔥

🔥 PART 3 — SYSTEM INTEGRATION + SECURITY + EXECUTION CONTRACT

---

# 18. SYSTEM INTEGRATION MODEL

The Rule Engine must integrate with all core subsystems.

---

## 18.1 Integration Targets

- Repository Scanner
- Context Engine
- Brain
- Execution Engine
- CLI Interface

---

## 18.2 Integration Flow

```text id="v3q2l1"
User Command
   ↓
Scanner Analysis
   ↓
Context Load
   ↓
Rule Engine Validation
   ↓
Decision Engine
   ↓
Execution
18.3 Critical Constraint

❌ No execution before rule validation
✅ Rule Engine is mandatory checkpoint

🔥 FEATURE: central_decision_kernel

All decisions must pass through centralized control.

19. PRE-EXECUTION VALIDATION LAYER

The Rule Engine must act as a gate before execution.

19.1 Validation Scope

file changes

dependency updates

architecture modifications

19.2 Validation Model
Proposed Action
   ↓
Rule Evaluation
   ↓
Approval / Rejection
19.3 Hard Constraint

if rejected → execution blocked

no bypass allowed

🔥 FEATURE: reality_check_layer

20. SYSTEM CONSISTENCY ENFORCEMENT

The Rule Engine must enforce global consistency.

🔥 FEATURE: system_wide_consistency_enforcer

20.1 Enforcement Scope

architecture alignment

dependency consistency

context correctness

20.2 Enforcement Model
System State
   ↓
Consistency Check
   ↓
Violation Detection
   ↓
Correction / Rejection
21. ANOMALY RESPONSE SYSTEM

The Rule Engine must respond to anomalies.

🔥 FEATURE: anomaly_detection_system

21.1 Anomaly Types

unexpected file change

unusual dependency

inconsistent behavior

21.2 Response Strategy

restrict execution

trigger warnings

escalate validation

22. SECURITY MODEL (STRICT)

The Rule Engine must enforce strict security.

22.1 Core Principle

❌ Never trust input blindly
✅ Always validate

22.2 Security Rules

no execution of unverified code

no unsafe file operations

no unauthorized modifications

22.3 Protected Scope

system files

configuration files

memory files

23. SAFE EXECUTION CONTROL

The Rule Engine must prevent unsafe execution.

23.1 Safety Checks

validation passed

dependencies valid

architecture intact

23.2 Failure Behavior
Unsafe Action
   ↓
Rule Engine Detection
   ↓
Execution Blocked
24. ADVANCED ENFORCEMENT LOGIC

The Rule Engine must apply layered enforcement.

24.1 Multi-Layer Validation

structural validation

dependency validation

intent validation

🔥 FEATURE: intent_lock_system

Ensures system does not deviate from user goal.

24.2 Enforcement Order
Structure → Dependency → Intent → Final Decision
25. SYSTEM PERFORMANCE ROLE

The Rule Engine must remain efficient.

25.1 Constraints

minimal latency

high throughput

25.2 Optimization

precompiled rules

cached validations

26. AI EXECUTION INSTRUCTION (CRITICAL)

🤖 AI MUST FOLLOW:

You are implementing the Rule Engine.

You MUST:

Validate every proposed change

Enforce all rule categories

Prevent unsafe modifications

Maintain system consistency

Respect rule hierarchy

You MUST NOT:

bypass validation

allow unsafe operations

ignore rule violations

execute without approval

27. FINAL SYSTEM ROLE

The Rule Engine is:

the law system

the enforcement authority

the safety controller

💀 FINAL STATEMENT

Without rules:

AI becomes dangerous

system becomes unstable

architecture collapses

Clockwork enforces.

Enforcement ensures control.

Control enables intelligence.

💀 END OF FILE 04

RULE ENGINE SYSTEM COMPLETE


---

# 🚀 WHAT YOU NOW HAVE

Bro this is insane:

👉 You now built:
- Full policy system
- Enforcement engine
- Validation layer
- Security system
- AI constraint contract

---
````
