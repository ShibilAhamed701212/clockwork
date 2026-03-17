
# Clockwork Project Specification
## File 02 — Repository Scanner Design

Version: 0.1
Subsystem: Repository Scanner
Document Type: Technical Architecture Specification

---

# 1. Purpose

The Repository Scanner is responsible for analyzing a software repository and building a structured understanding of the project.

This subsystem forms the foundation of Clockwork's intelligence because every other subsystem depends on the data produced by the scanner.

The scanner must detect:

• repository structure
• programming languages
• dependency systems
• architectural layers
• file relationships
• development domains
• skill requirements

The scanner produces a machine-readable representation of the repository known as the **Repository Map**.

Output file:

.clockwork/repo_map.json

---

# 2. Responsibilities

The repository scanner must perform the following tasks.

1. Walk the repository directory tree.
2. Identify relevant project files.
3. Detect programming languages.
4. Detect frameworks and libraries.
5. Identify dependency systems.
6. Identify architectural patterns.
7. Build a project component map.
8. Generate a machine-readable repository model.

---

# 3. Scanner Execution

The scanner runs through the CLI command:

clockwork scan

Execution pipeline:

Repository Root
    ↓
Directory Walker
    ↓
Language Detection
    ↓
Dependency Detection
    ↓
Architecture Detection
    ↓
Skill Detection
    ↓
Repository Map Generation

---

# 4. Directory Walking

The scanner must recursively walk the repository directory.

Excluded directories:

• .git
• node_modules
• __pycache__
• .venv
• build
• dist

The scanner must respect ignore files when present:

• .gitignore
• .clockworkignore

---

# 5. Language Detection

The scanner must detect programming languages using file extensions.

Example mapping:

.py → Python
.js → JavaScript
.ts → TypeScript
.go → Go
.rs → Rust
.java → Java
.cpp → C++
.c → C
.rb → Ruby

The scanner should maintain a language frequency map.

Example:

{
 "python": 42,
 "javascript": 10
}

---

# 6. Dependency Detection

The scanner must detect dependency management systems.

Examples:

Python → requirements.txt / pyproject.toml
Node → package.json
Rust → Cargo.toml
Go → go.mod

Dependencies must be extracted when possible.

Example output:

{
 "python_dependencies": ["flask", "sqlalchemy"],
 "node_dependencies": ["react", "express"]
}

---

# 7. Framework Detection

Frameworks should be detected from dependencies.

Example rules:

Flask → Python web backend
Django → Python web backend
React → frontend UI framework
FastAPI → Python API framework

Example output:

{
 "frameworks": ["Flask", "React"]
}

---

# 8. Architecture Detection

The scanner should infer project architecture patterns.

Common patterns:

Frontend + Backend
Microservices
API Server
CLI Tool
Library

Example inference:

Presence of:

frontend/
backend/

indicates layered architecture.

Example output:

{
 "architecture": "layered"
}

---

# 9. Component Detection

The scanner should group files into logical components.

Examples:

backend/
frontend/
database/
scripts/

Example repository map:

{
 "backend": ["app.py", "routes.py"],
 "frontend": ["index.html", "app.js"],
 "database": ["schema.sql"]
}

---

# 10. Skill Detection

Clockwork must detect which developer skills are required to work on the repository.

Examples:

Python files → Python developer
Dockerfile → DevOps
SQL files → Database engineer
React code → Frontend engineer

Example output:

{
 "skills": ["Python", "SQL", "React"]
}

---

# 11. AST Parsing (Advanced)

For deeper analysis the scanner should optionally parse source code using AST.

Recommended library:

tree-sitter

AST analysis enables:

• function detection
• class detection
• module relationships

This information will later feed the Clockwork Brain.

---

# 12. Repository Graph

The scanner should eventually build a graph representation of the repository.

Nodes:

• files
• modules
• dependencies

Edges:

• imports
• function calls
• module usage

This graph will support advanced reasoning.

---

# 13. Performance Requirements

The scanner must remain fast.

Target:

• small repos < 1 second
• medium repos < 3 seconds
• large repos < 10 seconds

The scanner must avoid loading entire files into memory when unnecessary.

---

# 14. Data Storage

The scanner outputs repository information to:

.clockwork/repo_map.json

Example structure:

{
 "languages": {
   "python": 40,
   "javascript": 12
 },
 "frameworks": ["Flask"],
 "architecture": "layered",
 "skills": ["Python", "Flask", "SQL"]
}

---

# 15. Error Handling

If the scanner fails to analyze a file it must skip the file and continue.

Clockwork must never crash due to a malformed file.

---

# 16. Extensibility

The scanner must support plugin detectors.

Future detectors may include:

• AI model files
• infrastructure detection
• Kubernetes configs
• CI/CD pipelines

---

# 17. Security Considerations

The scanner must never execute code from the repository.

All analysis must be static.

---

# 18. Future Enhancements

Future versions of the scanner may include:

• semantic code analysis
• test coverage detection
• documentation analysis
• architecture validation

These capabilities will strengthen Clockwork's understanding of the repository.
