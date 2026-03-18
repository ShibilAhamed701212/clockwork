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

---******************\*\*******************\*\*\*\*******************\*\*******************\_******************\*\*******************\*\*\*\*******************\*\*******************

# Clockwork Project Specification

## File 02 — Repository Scanner System

Version: 2.0  
Subsystem: Repository Scanner  
Document Type: System Intelligence + Structural Analysis Engine

---

# 🚀 FEATURE MAP (FROM MASTER 62)

- dependency_awareness_engine
- anomaly_detection_system
- semantic_layer
- unified_task_graph_engine
- knowledge_compression_engine
- breakage_prediction_engine

---

# 0. SYSTEM ROLE (CRITICAL)

The Repository Scanner is the **primary perception system of Clockwork**.

It acts as:

> The Eyes + Sensor Layer of the Entire System

---

Clockwork cannot:

- reason
- validate
- execute

without first understanding the repository.

---

🧠 INTELLIGENCE: semantic_layer

The scanner must not just "read files" —  
It must **understand structure, meaning, and relationships**.

---

# 1. PURPOSE (DEEP SYSTEM DEFINITION)

The Repository Scanner converts:

````text
Raw Codebase → Structured System Model

This transformation must produce:

structural understanding

dependency graph

architecture model

capability mapping

OUTPUT
.clockwork/repo_map.json
2. CORE RESPONSIBILITIES
2.1 Structural Analysis

directory tree traversal

file classification

module grouping

2.2 Language Intelligence

detect programming languages

calculate frequency distribution

2.3 Dependency Intelligence

⚙️ IMPLEMENTATION: dependency_awareness_engine

detect dependency systems

extract dependency lists

understand version constraints

2.4 Architectural Inference

detect system structure

identify layers

infer patterns

2.5 Relationship Mapping

file relationships

module dependencies

call graph

2.6 Skill Mapping

detect required developer skills

classify expertise areas

3. SCANNER EXECUTION MODEL

Triggered via:

clockwork scan
3.1 Execution Pipeline
Repository Root
   ↓
Directory Walker
   ↓
File Classifier
   ↓
Language Analyzer
   ↓
Dependency Analyzer
   ↓
Architecture Inference
   ↓
Graph Builder
   ↓
Repository Map Generator
4. DIRECTORY WALKER ENGINE
4.1 Exclusion Rules

.git

node_modules

pycache

.venv

build

dist

4.2 Ignore File Support

.gitignore

.clockworkignore

4.3 Traversal Strategy

recursive

memory-efficient

non-blocking

5. LANGUAGE ANALYSIS ENGINE
5.1 Language Mapping

.py → Python

.js → JavaScript

.ts → TypeScript

5.2 Frequency Model
{
 "python": 42,
 "javascript": 10
}
5.3 Advanced Detection

syntax patterns

keyword analysis

6. DEPENDENCY ANALYSIS ENGINE

⚙️ IMPLEMENTATION: dependency_awareness_engine

6.1 Detection Targets

requirements.txt

pyproject.toml

package.json

Cargo.toml

go.mod

6.2 Extraction Model
Dependency File
   ↓
Parse Structure
   ↓
Extract Packages
   ↓
Normalize Data
6.3 Dependency Graph

nodes → packages

edges → relationships

7. FRAMEWORK DETECTION SYSTEM
7.1 Detection Rules

Flask → backend

React → frontend

FastAPI → API

7.2 Classification

UI frameworks

backend frameworks

infrastructure frameworks

8. ARCHITECTURE INFERENCE ENGINE
8.1 Detection Patterns

layered

microservices

monolith

CLI

8.2 Heuristic Model
Folder Structure + Dependencies → Architecture Type

⚙️ IMPLEMENTATION: breakage_prediction_engine

9. COMPONENT MAPPING SYSTEM
9.1 Component Types

backend

frontend

database

infrastructure

9.2 Mapping Output
{
 "backend": ["app.py"],
 "frontend": ["app.js"]
}

---

# ⚠️ RULE (VERY IMPORTANT)

👉 Always ensure:
- Proper headings (`#`, `##`)
- Code blocks closed (``` )
- No merged sections

---

# 🚀 NEXT STEP

Say:
👉 **continue file02 part2**

We’ll now add:
- Graph intelligence
- AST parsing
- anomaly detection
- semantic reasoning layer

---

You’re doing this right bro — this is turning into a **real system spec now** 💀🔥

# Clockwork Project Specification
## File 02 — Repository Scanner System

Version: 2.0
Subsystem: Repository Scanner
Document Type: System Intelligence + Structural Analysis Engine

---

# 🚀 FEATURE MAP (FROM MASTER 62)

- dependency_awareness_engine
- anomaly_detection_system
- semantic_layer
- unified_task_graph_engine
- knowledge_compression_engine
- breakage_prediction_engine

---

# 0. SYSTEM ROLE (CRITICAL)

The Repository Scanner is the **primary perception system of Clockwork**.

It acts as:

> The Eyes + Sensor Layer of the Entire System

---

Clockwork cannot:
- reason
- validate
- execute

without first understanding the repository.

---

🧠 INTELLIGENCE: semantic_layer

The scanner must not just "read files" —
It must **understand structure, meaning, and relationships**.

---

# 1. PURPOSE (DEEP SYSTEM DEFINITION)

The Repository Scanner converts:

```text
Raw Codebase → Structured System Model

This transformation must produce:

structural understanding

dependency graph

architecture model

capability mapping

OUTPUT
.clockwork/repo_map.json
2. CORE RESPONSIBILITIES
2.1 Structural Analysis

directory tree traversal

file classification

module grouping

2.2 Language Intelligence

detect programming languages

calculate frequency distribution

2.3 Dependency Intelligence

⚙️ IMPLEMENTATION: dependency_awareness_engine

detect dependency systems

extract dependency lists

understand version constraints

2.4 Architectural Inference

detect system structure

identify layers

infer patterns

2.5 Relationship Mapping

file relationships

module dependencies

call graph

2.6 Skill Mapping

detect required developer skills

classify expertise areas

3. SCANNER EXECUTION MODEL

Triggered via:

clockwork scan
3.1 Execution Pipeline
Repository Root
   ↓
Directory Walker
   ↓
File Classifier
   ↓
Language Analyzer
   ↓
Dependency Analyzer
   ↓
Architecture Inference
   ↓
Graph Builder
   ↓
Repository Map Generator
4. DIRECTORY WALKER ENGINE
4.1 Exclusion Rules

.git

node_modules

pycache

.venv

build

dist

4.2 Ignore File Support

.gitignore

.clockworkignore

4.3 Traversal Strategy

recursive

memory-efficient

non-blocking

5. LANGUAGE ANALYSIS ENGINE
5.1 Language Mapping

.py → Python

.js → JavaScript

.ts → TypeScript

5.2 Frequency Model
{
 "python": 42,
 "javascript": 10
}
5.3 Advanced Detection

syntax patterns

keyword analysis

6. DEPENDENCY ANALYSIS ENGINE

⚙️ IMPLEMENTATION: dependency_awareness_engine

6.1 Detection Targets

requirements.txt

pyproject.toml

package.json

Cargo.toml

go.mod

6.2 Extraction Model
Dependency File
   ↓
Parse Structure
   ↓
Extract Packages
   ↓
Normalize Data
6.3 Dependency Graph

nodes → packages

edges → relationships

7. FRAMEWORK DETECTION SYSTEM
7.1 Detection Rules

Flask → backend

React → frontend

FastAPI → API

7.2 Classification

UI frameworks

backend frameworks

infrastructure frameworks

8. ARCHITECTURE INFERENCE ENGINE
8.1 Detection Patterns

layered

microservices

monolith

CLI

8.2 Heuristic Model
Folder Structure + Dependencies → Architecture Type

⚙️ IMPLEMENTATION: breakage_prediction_engine

9. COMPONENT MAPPING SYSTEM
9.1 Component Types

backend

frontend

database

infrastructure

9.2 Mapping Output
{
 "backend": ["app.py"],
 "frontend": ["app.js"]
}

---

# ⚠️ RULE (VERY IMPORTANT)

👉 Always ensure:
- Proper headings (`#`, `##`)
- Code blocks closed (``` )
- No merged sections

---

# 🚀 NEXT STEP

Say:
👉 **continue file02 part2**

We’ll now add:
- Graph intelligence
- AST parsing
- anomaly detection
- semantic reasoning layer

---

You’re doing this right bro — this is turning into a **real system spec now** 💀🔥

# 🔥 PART 2 — DEEP INTELLIGENCE LAYER (SCANNER CORE)

---

# 10. ABSTRACT SYNTAX TREE (AST) ANALYSIS ENGINE

The scanner must move beyond file-level analysis into **code-level structural understanding**.

---

🧠 INTELLIGENCE: semantic_layer

---

## 10.1 Purpose

AST parsing enables:

- function detection
- class detection
- variable relationships
- module interactions

---

## 10.2 Parsing Strategy

The scanner must:

- use language-specific parsers
- fallback to generic parsing if needed

---

Recommended:

- tree-sitter

---

## 10.3 AST Extraction Model

```text
Source Code
   ↓
Parser
   ↓
AST Tree
   ↓
Node Extraction
   ↓
Structured Representation
10.4 Extracted Entities

functions

classes

imports

exports

variables

11. REPOSITORY GRAPH ENGINE

The scanner must construct a full graph representation of the repository.

🔥 FEATURE: unified_task_graph_engine

11.1 Graph Definition

Graph G = (Nodes, Edges)

11.2 Node Types

files

modules

classes

functions

dependencies

11.3 Edge Types

import relationships

function calls

module usage

dependency links

11.4 Graph Construction Pipeline
AST Data
   ↓
Entity Extraction
   ↓
Relationship Mapping
   ↓
Graph Construction
11.5 Graph Use Cases

dependency tracking

execution planning

architecture validation

12. SEMANTIC UNDERSTANDING ENGINE

The scanner must interpret meaning, not just structure.

🧠 INTELLIGENCE: semantic_layer

12.1 Semantic Targets

function purpose

module role

data flow

system intent

12.2 Semantic Inference Model
Code Patterns + Context → Meaning
12.3 Example

function named get_user_data
→ semantic meaning: data retrieval

13. ANOMALY DETECTION SYSTEM

The scanner must detect abnormal patterns in the repository.

🔥 FEATURE: anomaly_detection_system

13.1 Detection Targets

inconsistent naming

irregular structure

unused files

suspicious dependencies

13.2 Detection Model
Expected Pattern
   ↓
Observed Pattern
   ↓
Deviation Detection
13.3 Anomaly Types

structural anomaly

dependency anomaly

behavioral anomaly

13.4 Response

flag anomaly

log issue

notify system

14. BREAKAGE PREDICTION SYSTEM

The scanner must detect potential breakages early.

🔥 FEATURE: breakage_prediction_engine

14.1 Prediction Scope

missing dependencies

circular imports

invalid references

14.2 Prediction Flow
Repository Graph
   ↓
Dependency Check
   ↓
Risk Analysis
   ↓
Breakage Prediction
15. KNOWLEDGE COMPRESSION ENGINE

The scanner must convert raw scan data into efficient knowledge.

🔥 FEATURE: knowledge_compression_engine

15.1 Compression Pipeline
Raw Scan Data
   ↓
Pattern Extraction
   ↓
Insight Generation
   ↓
Compact Representation
15.2 Compression Goals

reduce data size

improve reasoning speed

enable fast retrieval

16. SKILL INTELLIGENCE SYSTEM

The scanner must infer required developer skills.

16.1 Skill Mapping Model
File Type + Framework → Skill
16.2 Examples

Python → backend dev

React → frontend dev

SQL → database engineer

16.3 Output
{
 "skills": ["Python", "React", "SQL"]
}
17. PERFORMANCE OPTIMIZATION SYSTEM

The scanner must be optimized for speed.

17.1 Performance Targets

small repo < 1s

medium repo < 3s

large repo < 10s

17.2 Optimization Techniques

lazy loading

parallel processing

selective parsing

17.3 Memory Optimization

avoid full file loads

stream processing

🔗 PART 2 END

Awaiting continuation...


---

# 🚀 NEXT STEP

Say:
👉 **continue file02 part3**

Next we finish with:
- Output system
- Data schema
- Plugin system
- Security model
- AI execution instructions

---

Now your scanner is becoming:

> 💀 A real “codebase understanding engine” — not just a file reader 🚀
````
