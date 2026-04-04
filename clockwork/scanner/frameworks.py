"""
clockwork/scanner/frameworks.py
---------------------------------
Framework and dependency detection from repository manifest files.

Reads:
  • requirements.txt / requirements-*.txt
  • pyproject.toml         (Python)
  • package.json           (JS / TS)
  • go.mod                 (Go)
  • cargo.toml             (Rust)
  • pom.xml / build.gradle (JVM)
  • dockerfile             (Docker)
  • docker-compose.yml     (Docker Compose)

All parsing is static — no code is executed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# ── Python framework map ───────────────────────────────────────────────────

PYTHON_FRAMEWORKS: dict[str, str] = {
    "fastapi":      "FastAPI",
    "flask":        "Flask",
    "django":       "Django",
    "starlette":    "Starlette",
    "tornado":      "Tornado",
    "aiohttp":      "aiohttp",
    "sanic":        "Sanic",
    "falcon":       "Falcon",
    "pyramid":      "Pyramid",
    "typer":        "Typer",
    "click":        "Click",
    "argparse":     "argparse",
    "sqlalchemy":   "SQLAlchemy",
    "alembic":      "Alembic",
    "pydantic":     "Pydantic",
    "celery":       "Celery",
    "dramatiq":     "Dramatiq",
    "rq":           "RQ",
    "pytest":       "pytest",
    "unittest":     "unittest",
    "numpy":        "NumPy",
    "pandas":       "Pandas",
    "scipy":        "SciPy",
    "sklearn":      "scikit-learn",
    "scikit-learn": "scikit-learn",
    "tensorflow":   "TensorFlow",
    "torch":        "PyTorch",
    "transformers": "HuggingFace Transformers",
    "langchain":    "LangChain",
    "anthropic":    "Anthropic SDK",
    "openai":       "OpenAI SDK",
    "boto3":        "AWS Boto3",
    "redis":        "Redis",
    "pymongo":      "MongoDB (pymongo)",
    "motor":        "MongoDB (motor)",
    "asyncpg":      "PostgreSQL (asyncpg)",
    "psycopg2":     "PostgreSQL (psycopg2)",
    "httpx":        "HTTPX",
    "requests":     "Requests",
    "grpcio":       "gRPC",
}

# ── JS/TS framework map ────────────────────────────────────────────────────

JS_FRAMEWORKS: dict[str, str] = {
    "react":        "React",
    "vue":          "Vue",
    "angular":      "Angular",
    "svelte":       "Svelte",
    "solid-js":     "SolidJS",
    "next":         "Next.js",
    "nuxt":         "Nuxt",
    "remix":        "Remix",
    "gatsby":       "Gatsby",
    "express":      "Express",
    "fastify":      "Fastify",
    "koa":          "Koa",
    "nestjs":       "NestJS",
    "@nestjs/core": "NestJS",
    "hono":         "Hono",
    "trpc":         "tRPC",
    "graphql":      "GraphQL",
    "prisma":       "Prisma",
    "typeorm":      "TypeORM",
    "sequelize":    "Sequelize",
    "mongoose":     "Mongoose",
    "jest":         "Jest",
    "vitest":       "Vitest",
    "playwright":   "Playwright",
    "cypress":      "Cypress",
    "vite":         "Vite",
    "webpack":      "Webpack",
    "esbuild":      "esbuild",
    "tailwindcss":  "Tailwind CSS",
}

# ── Go module map ──────────────────────────────────────────────────────────

GO_FRAMEWORKS: dict[str, str] = {
    "gin-gonic/gin":    "Gin",
    "labstack/echo":    "Echo",
    "gofiber/fiber":    "Fiber",
    "gorilla/mux":      "Gorilla Mux",
    "go-chi/chi":       "Chi",
    "beego":            "Beego",
    "gorm.io/gorm":     "GORM",
    "go.uber.org/zap":  "Zap",
    "sirupsen/logrus":  "Logrus",
    "grpc":             "gRPC",
}

# ── Rust crate map ─────────────────────────────────────────────────────────

RUST_FRAMEWORKS: dict[str, str] = {
    "actix-web":    "Actix-Web",
    "axum":         "Axum",
    "rocket":       "Rocket",
    "warp":         "Warp",
    "tokio":        "Tokio",
    "serde":        "Serde",
    "sqlx":         "SQLx",
    "diesel":       "Diesel",
    "tonic":        "Tonic (gRPC)",
}


class FrameworkDetector:
    """
    Detects frameworks and libraries used in a repository by analysing
    manifest files found during scanning.
    """

    def detect(self, repo_root: Path, file_paths: list[str]) -> list[str]:
        """
        Return a deduplicated list of framework names detected in the repo.

        *file_paths* is the list of relative paths from ScanResult.files.
        """
        file_names_lower = {Path(p).name.lower() for p in file_paths}
        detected: list[str] = []

        # Python
        if "requirements.txt" in file_names_lower:
            detected += self._parse_requirements(repo_root / "requirements.txt")
        for name in file_names_lower:
            if name.startswith("requirements") and name.endswith(".txt"):
                path = repo_root / name
                if path.exists():
                    detected += self._parse_requirements(path)
        if "pyproject.toml" in file_names_lower:
            detected += self._parse_pyproject(repo_root / "pyproject.toml")
        if "setup.py" in file_names_lower:
            detected += self._parse_setup_py(repo_root / "setup.py")

        # JavaScript / TypeScript
        if "package.json" in file_names_lower:
            detected += self._parse_package_json(repo_root / "package.json")

        # Go
        if "go.mod" in file_names_lower:
            detected += self._parse_go_mod(repo_root / "go.mod")

        # Rust
        if "cargo.toml" in file_names_lower:
            detected += self._parse_cargo_toml(repo_root / "cargo.toml")

        # Infrastructure
        if "dockerfile" in file_names_lower:
            detected.append("Docker")
        if "docker-compose.yml" in file_names_lower or "docker-compose.yaml" in file_names_lower:
            detected.append("Docker Compose")
        if any(n.endswith(".tf") or n == "terraform" for n in file_names_lower):
            detected.append("Terraform")
        if ".github" in file_names_lower or any("github/workflows" in p for p in file_paths):
            detected.append("GitHub Actions")

        # JVM
        if "pom.xml" in file_names_lower:
            detected.append("Maven")
        if "build.gradle" in file_names_lower:
            detected.append("Gradle")

        return list(dict.fromkeys(detected))  # deduplicate, preserve order

    # ------------------------------------------------------------------ #
    # Parsers
    # ------------------------------------------------------------------ #

    def _parse_requirements(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                pkg = re.split(r"[>=<!;\[]", line)[0].strip().lower()
                if pkg in PYTHON_FRAMEWORKS:
                    found.append(PYTHON_FRAMEWORKS[pkg])
        except OSError:
            pass
        return found

    def _parse_pyproject(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            for keyword, name in PYTHON_FRAMEWORKS.items():
                # Match as a quoted string in dependencies arrays
                if f'"{keyword}' in content or f"'{keyword}" in content or f"\n{keyword}" in content:
                    found.append(name)
        except OSError:
            pass
        return found

    def _parse_setup_py(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            for keyword, name in PYTHON_FRAMEWORKS.items():
                if f'"{keyword}' in content or f"'{keyword}" in content:
                    found.append(name)
        except OSError:
            pass
        return found

    def _parse_package_json(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, json.JSONDecodeError):
            return []

        all_deps: dict[str, str] = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))
        all_deps.update(data.get("peerDependencies", {}))

        for raw_name in all_deps:
            # Strip scope: @nestjs/core → nestjs/core → check full then base
            name_lower = raw_name.lower().lstrip("@")
            if raw_name.lower() in JS_FRAMEWORKS:
                found.append(JS_FRAMEWORKS[raw_name.lower()])
            elif name_lower in JS_FRAMEWORKS:
                found.append(JS_FRAMEWORKS[name_lower])
            else:
                base = name_lower.split("/")[-1]
                if base in JS_FRAMEWORKS:
                    found.append(JS_FRAMEWORKS[base])

        return found

    def _parse_go_mod(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        for module_prefix, name in GO_FRAMEWORKS.items():
            if module_prefix in content:
                found.append(name)

        return found

    def _parse_cargo_toml(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            return []

        for crate, name in RUST_FRAMEWORKS.items():
            if crate.lower() in content:
                found.append(name)

        return found
