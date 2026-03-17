
# Clockwork Project Specification
## File 05 — Clockwork Brain Design

Version: 0.1
Subsystem: Clockwork Brain
Document Type: Technical Architecture Specification

---

# 1. Purpose

The Clockwork Brain is the **verification and reasoning engine** of the Clockwork system.

Its primary responsibility is to analyze repository changes and determine whether those changes are safe, valid, and consistent with the repository context and rules.

The brain acts as a **guardian of repository integrity**.

Without the Brain, AI agents could introduce harmful changes such as:

• incorrect architectural modifications  
• context corruption  
• logical inconsistencies  
• unsafe dependency changes  

The Clockwork Brain ensures that all changes align with the repository's intended design.

---

# 2. Core Responsibilities

The Clockwork Brain must perform the following functions:

• analyze repository diffs  
• verify architecture consistency  
• validate context integrity  
• detect rule violations  
• detect potential logical inconsistencies  
• produce validation reports  

The brain must operate before the Context Engine commits updates.

---

# 3. Brain Architecture

The Clockwork Brain is managed by the **Brain Manager**.

Brain Manager loads one of three reasoning engines:

MiniBrain  
OllamaBrain  
ExternalBrain  

Architecture:

Brain Manager  
     │
 ┌──────────┬──────────┬──────────┐
 │          │          │
MiniBrain  OllamaBrain ExternalBrain

Each brain implements the same reasoning interface.

---

# 4. Brain Interface

All reasoning engines must implement the following interface.

analyze_change(context, repo_diff, rules)

Expected output:

{
 "status": "valid",
 "confidence": 0.92,
 "risk_level": "low",
 "explanation": "Pagination added correctly."
}

This standardized interface allows any reasoning engine to be swapped in.

---

# 5. MiniBrain (Built-In)

MiniBrain is the **default reasoning engine**.

MiniBrain does not require AI models.

It uses deterministic analysis techniques including:

• repository diff analysis  
• AST inspection  
• dependency verification  
• architecture rule matching  

MiniBrain ensures Clockwork can run fully offline.

---

# 6. MiniBrain Capabilities

MiniBrain must detect:

• deleted files  
• new modules  
• dependency modifications  
• architecture violations  
• context mismatch  

Example detection:

Context claims Flask backend exists.

But repository no longer contains Flask dependency.

MiniBrain must flag this inconsistency.

---

# 7. Diff Analysis

MiniBrain must analyze Git diffs to determine repository modifications.

Example detection pipeline:

Repository Diff  
       ↓  
File Classification  
       ↓  
Modification Analysis  
       ↓  
Rule Validation  

MiniBrain must identify:

• added files  
• deleted files  
• modified files  

---

# 8. Architecture Validation

MiniBrain must verify that architecture rules remain intact.

Example rule:

Frontend → API → Database

If frontend code accesses database directly, violation must be raised.

Example violation report:

Architecture violation detected  
Frontend module attempted direct database access.

---

# 9. Context Consistency Verification

The brain must verify that the context.yaml file remains accurate.

Example checks:

• frameworks listed in context exist in dependencies  
• repository architecture matches context description  
• modules referenced in context exist in repository  

If mismatches are detected, the context update must be rejected.

---

# 10. Ollama Brain

Clockwork supports local AI reasoning through Ollama.

Ollama provides access to locally running LLMs.

Supported models may include:

• deepseek-coder  
• qwen-coder  
• llama3  
• mistral  

Clockwork must detect Ollama automatically.

Command:

ollama --version

If Ollama is available, the Brain Manager can enable OllamaBrain.

---

# 11. Ollama Reasoning Pipeline

Example pipeline:

Repository Diff  
       ↓  
Prompt Generation  
       ↓  
Send to Ollama Model  
       ↓  
Receive Reasoning Output  
       ↓  
Convert to Validation Result

Example reasoning prompt:

Analyze this repository modification and determine if it violates architecture rules.

---

# 12. External Brain

Clockwork may also support external AI providers.

Supported APIs may include:

• OpenAI  
• Anthropic  
• Custom LLM endpoints  

External reasoning engines are configured through:

.clockwork/config.yaml

Example:

brain:
  mode: external
  provider: openai
  model: gpt-4o

---

# 13. Brain Decision Model

The Brain produces a final decision.

Possible statuses:

VALID  
WARNING  
REJECTED  

Example:

{
 "status": "REJECTED",
 "risk_level": "high",
 "explanation": "Core module deletion detected."
}

---

# 14. Confidence Scoring

The brain must assign a confidence score to decisions.

Range:

0.0 → 1.0

Example:

confidence: 0.87

Low confidence results may trigger manual confirmation.

---

# 15. Multi-Layer Validation

Clockwork validation occurs in layers.

Layer 1 — Rule Engine  
Layer 2 — MiniBrain Analysis  
Layer 3 — AI Reasoning (optional)

This layered approach improves reliability.

---

# 16. Brain Logging

All decisions must be logged.

Log file:

.clockwork/brain_log.json

Example entry:

{
 "timestamp": "2026-03-14",
 "status": "valid",
 "confidence": 0.92
}

---

# 17. Performance Requirements

Brain analysis must remain efficient.

Targets:

MiniBrain analysis < 200 ms  
Ollama analysis < 2 seconds  
External analysis < 5 seconds

---

# 18. Safety Requirements

The Brain must never execute repository code.

All analysis must remain static.

Dynamic execution introduces security risks.

---

# 19. Extensibility

Future reasoning engines may include:

• graph-based reasoning  
• architecture inference models  
• security scanners  
• code quality evaluators

The Brain Manager must support plugin-based engines.

---

# 20. Future Enhancements

Future versions of the Brain may support:

• repository knowledge graphs  
• autonomous debugging  
• multi-agent orchestration  
• architectural refactoring suggestions

These features will transform Clockwork into a full **repository intelligence system**.
