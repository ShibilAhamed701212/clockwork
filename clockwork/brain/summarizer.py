"""
clockwork/brain/summarizer.py
-------------------------------
CodebaseSummarizer — generates human-readable project descriptions
from scan data using deterministic heuristics.

MiniBrain fallback (default, no AI):
  - Count files per top-level directory → infer architecture type
  - Detect primary framework → describe stack
  - Check test file ratio → describe testing coverage
  - Scan __init__.py exports → describe public API
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


# ── Architecture type patterns ─────────────────────────────────────────────

_ARCH_PATTERNS: dict[str, list[str]] = {
    "monolith": ["src", "app", "lib"],
    "microservices": ["services", "api", "gateway"],
    "cli_tool": ["cli", "commands", "main"],
    "library": ["src", "lib", "core"],
    "web_app": ["frontend", "backend", "api", "static", "templates"],
    "data_pipeline": ["pipeline", "etl", "data", "transforms"],
    "full_stack": ["frontend", "backend", "api", "client", "server"],
}

_FRAMEWORK_DESCRIPTIONS: dict[str, str] = {
    "FastAPI": "asynchronous web API framework",
    "Flask": "lightweight web framework",
    "Django": "full-stack web framework",
    "React": "component-based UI library",
    "Vue": "progressive JavaScript framework",
    "Angular": "TypeScript web application framework",
    "Next.js": "React-based full-stack framework",
    "Express": "minimal Node.js web framework",
    "Typer": "type-driven CLI framework",
    "Click": "composable CLI toolkit",
    "pytest": "testing framework",
    "SQLAlchemy": "SQL toolkit and ORM",
    "Pydantic": "data validation library",
}


class CodebaseSummarizer:
    """
    Generates human-readable project summaries from scan data.

    Uses deterministic MiniBrain heuristics by default.
    No external services or AI models required.
    """

    def summarize(
        self,
        scan_result: Any,
        graph_stats: Optional[dict] = None,
    ) -> str:
        """
        Generate a one-paragraph project description.

        Args:
            scan_result: A ScanResult object or dict with scan data.
            graph_stats: Optional graph statistics dict.

        Returns:
            A human-readable project description string.
        """
        data = self._normalize(scan_result)
        parts: list[str] = []

        project_name = data.get("project_name", "This project")
        primary_lang = data.get("primary_language", "")
        frameworks = data.get("frameworks", [])
        total_files = data.get("total_files", 0)
        total_lines = data.get("total_lines", 0)
        test_files = data.get("test_files", [])

        # Opening
        if primary_lang:
            parts.append(f"{project_name} is a {primary_lang} project")
        else:
            parts.append(f"{project_name} is a software project")

        # Framework description
        if frameworks:
            desc_parts = []
            for fw in frameworks[:3]:
                fw_desc = _FRAMEWORK_DESCRIPTIONS.get(fw, fw)
                desc_parts.append(fw_desc)
            parts[-1] += f" built with {', '.join(desc_parts)}"

        # Size
        if total_files > 0:
            parts.append(
                f"containing {total_files} files and {total_lines:,} lines of code"
            )

        # Architecture type
        arch = self._detect_architecture_type(data)
        if arch:
            parts.append(f"following a {arch} architecture")

        # Testing
        test_ratio = len(test_files) / max(total_files, 1)
        if test_ratio > 0.15:
            parts.append("with comprehensive test coverage")
        elif test_ratio > 0.05:
            parts.append("with moderate test coverage")

        return ". ".join(". ".join(parts).split(". ")).rstrip(".") + "."

    def architecture_overview(
        self,
        scan_result: Any,
        graph_stats: Optional[dict] = None,
    ) -> str:
        """
        Generate an architecture description including layers and key modules.

        Returns:
            A multi-line architecture overview string.
        """
        data = self._normalize(scan_result)
        lines: list[str] = []

        # Detect architecture type
        arch = self._detect_architecture_type(data)
        primary_lang = data.get("primary_language", "")

        if arch:
            lines.append(f"The project follows a {arch} architecture")
            if primary_lang:
                lines[-1] += f" implemented in {primary_lang}"
            lines[-1] += "."
        else:
            if primary_lang:
                lines.append(f"A {primary_lang} project.")

        # Top-level structure
        dir_tree = data.get("directory_tree", {})
        if dir_tree:
            top_dirs = [d for d in dir_tree.keys() if d != "." and "/" not in d.replace("\\", "/")]
            if top_dirs:
                lines.append("")
                lines.append("Key modules:")
                for d in sorted(top_dirs)[:10]:
                    file_count = len(dir_tree.get(d, []))
                    desc = self._describe_directory(d, data)
                    lines.append(f"  - {d}/ — {desc} ({file_count} files)")

        # Framework layers
        frameworks = data.get("frameworks", [])
        if frameworks:
            lines.append("")
            lines.append(f"Technology stack: {', '.join(frameworks)}")

        # Entry points
        entry_points = data.get("entry_points", [])
        if entry_points:
            lines.append("")
            lines.append("Entry points:")
            for ep in entry_points[:5]:
                lines.append(f"  - {ep}")

        # Graph stats if available
        if graph_stats:
            total_nodes = graph_stats.get("total_nodes", 0)
            total_edges = graph_stats.get("total_edges", 0)
            if total_nodes:
                lines.append("")
                lines.append(
                    f"Knowledge graph: {total_nodes} nodes, {total_edges} edges"
                )

        return "\n".join(lines)

    def detect_conventions(self, scan_result: Any) -> list[str]:
        """
        Infer coding conventions from the codebase.

        Returns:
            List of inferred convention descriptions.
        """
        data = self._normalize(scan_result)
        conventions: list[str] = []
        primary_lang = data.get("primary_language", "")
        files = data.get("files", [])

        # Python-specific conventions
        if primary_lang == "Python":
            # Check for dataclass usage
            has_dataclass = any(
                any(s.get("kind") == "class" for s in f.get("symbols", []))
                and "dataclass" in " ".join(f.get("imports", []))
                for f in files
                if isinstance(f, dict)
            )
            if has_dataclass:
                conventions.append("Uses dataclasses for data models")

            # Check for type hints
            has_typehints = any(
                "from __future__ import annotations" in " ".join(f.get("imports", []))
                for f in files
                if isinstance(f, dict)
            )
            if has_typehints:
                conventions.append("Uses type hints with future annotations")

            # Check for src layout
            dir_tree = data.get("directory_tree", {})
            if "src" in dir_tree:
                conventions.append("Follows src layout pattern")

        # General conventions
        test_files = data.get("test_files", [])
        if test_files:
            # Check if tests mirror source structure
            src_names = {Path(f["path"]).stem for f in files
                        if isinstance(f, dict) and not f.get("is_test")}
            test_names = {Path(t).stem.replace("test_", "") for t in test_files}
            overlap = src_names & test_names
            if len(overlap) > 3:
                conventions.append("Tests mirror source structure in tests/")

        # Config files
        config_files = data.get("config_files", [])
        if any("pyproject.toml" in c for c in config_files):
            conventions.append("Project configuration via pyproject.toml")
        if any(".env" in c for c in config_files):
            conventions.append("Environment variables via .env files")

        # Framework conventions
        frameworks = data.get("frameworks", [])
        for fw in frameworks:
            if fw in ("pytest",):
                conventions.append(f"Uses {fw} for testing")
            elif fw in ("Typer", "Click"):
                conventions.append(f"CLI built with {fw}")

        return conventions

    # ── Internal helpers ──────────────────────────────────────────────────

    def _normalize(self, scan_result: Any) -> dict:
        """Convert ScanResult object to dict if needed."""
        if isinstance(scan_result, dict):
            return scan_result
        if hasattr(scan_result, "to_dict"):
            return scan_result.to_dict()
        return {}

    def _detect_architecture_type(self, data: dict) -> str:
        """Detect architecture type from directory structure."""
        dir_tree = data.get("directory_tree", {})
        top_dirs = {d.lower() for d in dir_tree.keys()
                    if d != "." and "/" not in d.replace("\\", "/")}

        best_match = ""
        best_score = 0
        for arch_type, patterns in _ARCH_PATTERNS.items():
            score = len([p for p in patterns if p in top_dirs])
            if score > best_score:
                best_score = score
                best_match = arch_type

        return best_match if best_score >= 2 else ""

    def _describe_directory(self, dir_name: str, data: dict) -> str:
        """Generate a brief description for a directory."""
        lower = dir_name.lower()
        descriptions: dict[str, str] = {
            "cli": "command-line interface",
            "commands": "CLI commands",
            "api": "API endpoints",
            "models": "data models",
            "views": "view layer",
            "controllers": "request handlers",
            "services": "business logic services",
            "utils": "utility functions",
            "helpers": "helper functions",
            "config": "configuration",
            "tests": "test suite",
            "test": "test suite",
            "docs": "documentation",
            "static": "static assets",
            "templates": "template files",
            "migrations": "database migrations",
            "scripts": "automation scripts",
            "core": "core logic",
            "lib": "shared library code",
            "src": "source code",
            "frontend": "frontend application",
            "backend": "backend server",
            "scanner": "repository scanning",
            "brain": "reasoning engine",
            "context": "context management",
            "graph": "knowledge graph",
            "index": "file indexing",
            "rules": "rule engine",
            "handoff": "agent handoff",
            "validation": "validation pipeline",
            "recovery": "failure recovery",
            "packaging": "packaging system",
            "security": "security controls",
            "registry": "plugin registry",
            "agents": "agent management",
            "agent": "agent runtime",
            "state": "state management",
        }
        return descriptions.get(lower, "project module")
