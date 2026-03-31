# Clockwork

**Clockwork** is a local-first repository intelligence system and multi-agent coordination framework. Designed for the age of AI-assisted engineering, it shifts the source of truth back to your local filesystem. Clockwork maintains an incredibly deep understanding of your codebase, enforces architectural constraints statically, routes autonomous tasks, and keeps the environment mathematically safe—all without requiring a persistent cloud connection.

By leveraging static AST parsing, SQLite properties, and rigid YAML configurations isolated within the `.clockwork` directory, Clockwork bridges the gap between chaotic autonomous agents and strictly governed software development.

---

## 🚀 Key Architectural Pillars

Clockwork is heavily modular, dividing execution responsibilities across specialized engines precisely designed to maintain repository state cleanly.

### 1. Local-First Context & State Tracking
At the heart of Clockwork lies the **Context Engine**, which maintains the `context.yaml` timeline. Rather than executing git checks on every operation, the Context Engine logs a progressive history of task starts, agent notes, architectural decisions, and structural errors locally. 

This state is powered by the **Live Context Index System**, an ultra-fast OS-level filesystem watchdog that hashes files to determine true cryptographic modifications. It prevents expensive, runaway full-repository operations by relying strictly on single-file incremental updates against `.clockwork/index.db`.

### 2. Static Intelligence & Knowledge Graph topologies 
To enable agents to reason about code safely:
- The **Repository Scanner** executes deep static traversal over the directory, evaluating file dialects, checking frameworks dynamically, and using advanced AST string-parsing logic to map explicit function imports, tracking it all down in a `repo_map.json`.
- The **Knowledge Graph System** takes these raw symbol-imports and links them explicitly in `.clockwork/knowledge_graph.db`. This SQLite-backed property schema solves the “blind-delete” constraint: allowing queries like `who_depends_on()` to prevent agents from breaking upstream dependencies.

### 3. The 4-Layer Autonomous Validation Pipeline
Clockwork enforces absolute codebase fidelity via a cascading validation sequence before any agent-proposed code is written to disk:
1. **Security Sandboxing:** A restrictive `FileGuard` checks all operational bounds mechanically, preventing edits near `.env` or `.git` files, preventing accidental secrets exposure. 
2. **Rule Engine:** User-defined `.clockwork/rules.yaml` standards are mapped actively to instances (`ArchitectureEvaluator`, `SafetyEvaluator`), applying regex checks and deterministic architectural standards against incoming diffs.
3. **The Brain (MiniBrain):** Fast programmatic Python checkers execute heuristics checking boundaries (function depths, basic static risks) deterministically to fail-fast.
4. **The Brain (Generative):** A restrictive Prompt bridges the context bounds entirely to local `Ollama` models (e.g., DeepSeek) or external endpoints. It uses generative AI strictly to grade structural `confidence` dynamically.

### 4. Agent Runtime & Secure Handoff
Clockwork enables autonomous operations natively via the **Agent Runtime System**, matching required task configurations to locally registered Agent modules using capabilities matrices.

Once an agent finishes (or errors out), the **Agent Handoff System** aggregates timelines, graph topology, and open tasks into a human-readable `next_agent_brief.md` alongside a prompted `handoff.json`. This design seamlessly persists machine context memory gracefully when passing projects back to human operators (like Cursor/Windsurf).

### 5. Packaging & Ecosystem Extensions
Clockwork instances are easily portable:
- **Packaging:** The `.clockwork` directory state is zipped safely to a `project.clockwork` artifact, tracking cryptographic checksums. Teams can load instances across CI/CD runners to instantly hydrate timeline context mappings.
- **Registry:** Fully offline-capable extension ecosystem supporting local caching, fetching, scanning checksums, verifying potentially untrustworthy manifest permissions dynamically via `PluginVerifier`, and safely installing them modularly to the `.clockwork/plugins` architecture.

---

## 🚦 Installation

Ensure you have Python 3.10+ installed.

```bash
# Install directly from GitHub
pip install "git+https://github.com/ShibilAhamed701212/clockwork.git"

# Or include extras
pip install "clockwork[mcp] @ git+https://github.com/ShibilAhamed701212/clockwork.git"

# Local development install
git clone https://github.com/ShibilAhamed701212/clockwork.git
cd clockwork
pip install -e .
```

---

## 📦 Publish Releases

Clockwork now includes GitHub Actions workflows for package validation and publishing.

1. Bump `version` in `pyproject.toml`.
2. Push the commit to `main` and confirm `Package Validate` passes.
3. Create and push a stable version tag for production PyPI:

```bash
git tag v0.2.1
git push origin v0.2.1
```

4. `Publish PyPI` runs automatically on stable tag push.

For prerelease validation on TestPyPI, push an RC tag:

```bash
git tag v0.2.1-rc1
git push origin v0.2.1-rc1
```

`Publish TestPyPI` runs automatically for `v*-rc*` tags.
After a successful TestPyPI publish, `TestPyPI Smoke Test` runs automatically, installs the exact RC version from that tag, and checks `clockwork --help` and `clockwork-mcp --help`.

Authentication options:
- Preferred: PyPI Trusted Publishing (OIDC), with a PyPI project environment named `pypi`.
- Fallback: add `PYPI_API_TOKEN` in GitHub repository secrets.
- For TestPyPI, use environment `testpypi` or fallback secret `TEST_PYPI_API_TOKEN`.

---

## 🛠 Command Line Interface (CLI)

The CLI layer exposes functionality distinctly using the Typer framework for comprehensive, human-readable terminal orchestration.

### Initialisation & Discovery
- `clockwork init` - Initialise `.clockwork/context.yaml` as the foundation of project intelligence.
- `clockwork scan` - Analyse the entire repository structure and compile `repo_map.json`.
- `clockwork update` - Merge updated scan results locally into timeline memory.

### Fast Index & Graph Daemons
- `clockwork index` - Generate the OS-level file mapping into the SQLite `index.db`.
- `clockwork watch` - Fire up the memory-safe asynchronous watchdog tracking filesystem interrupts incrementally in the background. 
- `clockwork repair` - Clean, wipe, and forcefully rebuild the database and symbolic AST mappings efficiently.
- `clockwork graph` - Interrogate or forcefully assemble the dependency nodes within `knowledge_graph.db`.

### Autonomous Operations & System Rules
- `clockwork agent` - Manage locally registered agent pools executing work tasks.
- `clockwork task` - Push actionable work tasks up to the `TaskRouter` to evaluate assignment natively.
- `clockwork verify` - Scan timeline stability and evaluate structural differences via the strict `Rule Engine`.

### Security, Portability & Registry
- `clockwork security` - Interrogate paths to prevent access to protected credentials, initiating repository audits dynamically.
- `clockwork handoff` - Pull human-readable summaries (`next_agent_brief.md`) to smoothly carry project timelines into an LLM session.
- `clockwork pack` - Consolidate `.clockwork` state contexts into highly transportable archive files.
- `clockwork load` - Ingest an archive file and reinstate the repository's logic tracking layer.
- `clockwork registry` - Discover tools locally cached from standard repositories, validating sandbox constraints offline natively.
- `clockwork plugin` - Validate internal registry manifests resolving local plugin development lifecycles.

---

## 🔒 Governance & Philosophy 

Clockwork explicitly believes code modification decisions shouldn't primarily revolve around unconstrained LLMs writing unguided text diffs. Core system behavior is isolated completely. **Code reading, analysis operations, bounding, and validation run natively in classic Python classes.** Generative models are invoked *strictly as evaluation layers* after deterministic tests succeed or fail, drastically mitigating logical regressions.
