"""
tests/test_scanner.py
----------------------
Unit tests for the Clockwork Repository Scanner subsystem.

Tests:
  • LanguageDetector
  • ScanFilter
  • SymbolExtractor
  • FrameworkDetector
  • RepositoryScanner (integration)
  • ScanResult serialisation round-trip

Run with:  pytest tests/test_scanner.py -v
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from clockwork.scanner.language import LanguageDetector, EXTENSION_MAP, FILENAME_MAP
from clockwork.scanner.filters import ScanFilter
from clockwork.scanner.symbols import SymbolExtractor
from clockwork.scanner.frameworks import FrameworkDetector
from clockwork.scanner.scanner import RepositoryScanner
from clockwork.scanner.models import ScanResult, FileEntry, SymbolInfo


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

def _make_repo(root: Path) -> Path:
    """Build a small multi-language repository for integration tests."""
    # Python
    (root / "main.py").write_text(textwrap.dedent("""\
        import os
        from pathlib import Path

        class App:
            def run(self) -> None:
                pass

        def start():
            app = App()
            app.run()
    """))
    (root / "utils.py").write_text("def helper(): pass\n")

    # Tests
    tests = root / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_main.py").write_text("def test_start(): pass\n")

    # Config
    (root / "requirements.txt").write_text("fastapi\npydantic\npytest\n")
    (root / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )

    # JavaScript
    (root / "app.js").write_text(textwrap.dedent("""\
        import express from 'express';
        const app = express();
        function startServer() { app.listen(3000); }
    """))

    # Markdown
    (root / "README.md").write_text("# Test Project\n")

    # Dockerfile
    (root / "Dockerfile").write_text("FROM python:3.11\nCMD [\"python\", \"main.py\"]\n")

    # Sensitive — must not be indexed
    (root / ".env").write_text("SECRET=abc\n")
    (root / "credentials.json").write_text('{"key": "secret"}\n')

    # Binary-like — must be skipped
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    return root


# ─────────────────────────────────────────────
# LanguageDetector
# ─────────────────────────────────────────────

class TestLanguageDetector:
    def test_extension_detection(self):
        d = LanguageDetector()
        assert d.detect(Path("foo.py"))   == "Python"
        assert d.detect(Path("bar.ts"))   == "TypeScript"
        assert d.detect(Path("main.go"))  == "Go"
        assert d.detect(Path("app.rs"))   == "Rust"
        assert d.detect(Path("Main.java"))== "Java"
        assert d.detect(Path("style.css"))== "CSS"

    def test_filename_detection(self):
        d = LanguageDetector()
        assert d.detect(Path("Makefile"))    == "Makefile"
        assert d.detect(Path("Dockerfile"))  == "Dockerfile"
        assert d.detect(Path("Gemfile"))     == "Ruby"

    def test_shebang_detection(self, tmp_path):
        d = LanguageDetector()
        f = tmp_path / "myscript"
        f.write_text("#!/usr/bin/env python3\nprint('hi')")
        assert d.detect(f) == "Python"

    def test_shebang_bash(self, tmp_path):
        d = LanguageDetector()
        f = tmp_path / "deploy"
        f.write_text("#!/bin/bash\necho hello")
        assert d.detect(f) == "Shell"

    def test_unknown_returns_other(self):
        d = LanguageDetector()
        assert d.detect(Path("mystery.xyz")) == "Other"

    def test_primary_language_prefers_code(self):
        d = LanguageDetector()
        counts = {"Python": 30, "YAML": 50, "JSON": 40, "Markdown": 20}
        assert d.detect_primary_language(counts) == "Python"

    def test_primary_language_empty(self):
        d = LanguageDetector()
        assert d.detect_primary_language({}) == ""


# ─────────────────────────────────────────────
# ScanFilter
# ─────────────────────────────────────────────

class TestScanFilter:
    def setup_method(self):
        self.f = ScanFilter()

    def test_sensitive_env(self):
        assert self.f.is_sensitive(Path(".env")) is True

    def test_sensitive_credentials(self):
        assert self.f.is_sensitive(Path("credentials.json")) is True

    def test_sensitive_pem(self):
        assert self.f.is_sensitive(Path("server.pem")) is True

    def test_not_sensitive(self):
        assert self.f.is_sensitive(Path("context.yaml")) is False

    def test_skip_pyc(self):
        assert self.f.should_skip_file(Path("app.pyc")) is True

    def test_skip_png(self):
        assert self.f.should_skip_file(Path("logo.png")) is True

    def test_keep_python(self):
        assert self.f.should_skip_file(Path("main.py")) is False

    def test_entry_point_main(self):
        assert self.f.is_entry_point(Path("main.py")) is True

    def test_entry_point_appjs(self):
        assert self.f.is_entry_point(Path("app.js")) is True

    def test_not_entry_point(self):
        assert self.f.is_entry_point(Path("utils.py")) is False

    def test_test_file_prefix(self):
        assert self.f.is_test_file(Path("tests/test_main.py")) is True

    def test_test_file_spec(self):
        assert self.f.is_test_file(Path("app.spec.ts")) is True

    def test_not_test_file(self):
        assert self.f.is_test_file(Path("src/main.py")) is False

    def test_skip_dir_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        assert self.f.should_skip_directory(nm, tmp_path) is True

    def test_skip_dir_git(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        assert self.f.should_skip_directory(git, tmp_path) is True

    def test_keep_src_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        assert self.f.should_skip_directory(src, tmp_path) is False


# ─────────────────────────────────────────────
# SymbolExtractor
# ─────────────────────────────────────────────

class TestSymbolExtractor:
    def setup_method(self):
        self.ex = SymbolExtractor()

    def test_python_class(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("class Foo:\n    def bar(self): pass\n")
        symbols, _ = self.ex.extract(f, "Python")
        names = {s.name for s in symbols}
        assert "Foo" in names
        assert "bar" in names

    def test_python_function(self, tmp_path):
        f = tmp_path / "b.py"
        f.write_text("def hello(): pass\ndef world(): pass\n")
        symbols, _ = self.ex.extract(f, "Python")
        names = {s.name for s in symbols}
        assert "hello" in names
        assert "world" in names

    def test_python_imports(self, tmp_path):
        f = tmp_path / "c.py"
        f.write_text("import os\nfrom pathlib import Path\n")
        _, imports = self.ex.extract(f, "Python")
        assert "os" in imports
        assert "pathlib.Path" in imports

    def test_python_method_has_parent(self, tmp_path):
        f = tmp_path / "d.py"
        f.write_text("class MyClass:\n    def my_method(self): pass\n")
        symbols, _ = self.ex.extract(f, "Python")
        method = next((s for s in symbols if s.name == "my_method"), None)
        assert method is not None
        assert method.parent == "MyClass"
        assert method.kind == "method"

    def test_python_syntax_error_returns_empty(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def (broken syntax")
        symbols, imports = self.ex.extract(f, "Python")
        assert symbols == []
        assert imports == []

    def test_js_class_and_function(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text(
            "export class MyService {}\n"
            "export function doWork() {}\n"
            "export const handler = () => {}\n"
        )
        symbols, _ = self.ex.extract(f, "JavaScript")
        names = {s.name for s in symbols}
        assert "MyService" in names
        assert "doWork" in names

    def test_js_imports(self, tmp_path):
        f = tmp_path / "index.js"
        f.write_text("import React from 'react';\nimport { useState } from 'react';\n")
        _, imports = self.ex.extract(f, "JavaScript")
        assert "react" in imports

    def test_go_structs_and_funcs(self, tmp_path):
        f = tmp_path / "main.go"
        f.write_text(
            'package main\nimport "fmt"\ntype Server struct {}\n'
            "func main() {}\nfunc (s *Server) Start() {}\n"
        )
        symbols, imports = self.ex.extract(f, "Go")
        names = {s.name for s in symbols}
        assert "Server" in names
        assert "main" in names
        assert "fmt" in imports

    def test_unsupported_language_returns_empty(self, tmp_path):
        f = tmp_path / "style.css"
        f.write_text("body { color: red; }")
        symbols, imports = self.ex.extract(f, "CSS")
        assert symbols == []
        assert imports == []


# ─────────────────────────────────────────────
# FrameworkDetector
# ─────────────────────────────────────────────

class TestFrameworkDetector:
    def setup_method(self):
        self.d = FrameworkDetector()

    def test_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\npydantic\nrequests\n")
        fw = self.d.detect(tmp_path, ["requirements.txt"])
        assert "FastAPI" in fw
        assert "Pydantic" in fw
        assert "Requests" in fw

    def test_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18", "express": "^4"}})
        )
        fw = self.d.detect(tmp_path, ["package.json"])
        assert "React" in fw
        assert "Express" in fw

    def test_dockerfile_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        fw = self.d.detect(tmp_path, ["Dockerfile"])
        assert "Docker" in fw

    def test_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module example.com/app\nrequire github.com/gin-gonic/gin v1.9.0\n"
        )
        fw = self.d.detect(tmp_path, ["go.mod"])
        assert "Gin" in fw

    def test_cargo_toml(self, tmp_path):
        (tmp_path / "cargo.toml").write_text(
            '[dependencies]\naxum = "0.7"\ntokio = "1"\n'
        )
        fw = self.d.detect(tmp_path, ["cargo.toml"])
        assert "Axum" in fw
        assert "Tokio" in fw

    def test_empty_repo_no_frameworks(self, tmp_path):
        fw = self.d.detect(tmp_path, [])
        assert fw == []


# ─────────────────────────────────────────────
# RepositoryScanner (integration)
# ─────────────────────────────────────────────

class TestRepositoryScanner:
    def test_scan_returns_result(self, tmp_path):
        _make_repo(tmp_path)
        s = RepositoryScanner(repo_root=tmp_path, extract_symbols=True)
        r = s.scan()
        assert isinstance(r, ScanResult)

    def test_total_files_positive(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert r.total_files > 0

    def test_python_detected(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert "Python" in r.languages

    def test_primary_language_python(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert r.primary_language == "Python"

    def test_sensitive_files_excluded(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        paths = {f.path for f in r.files}
        assert ".env" not in paths
        assert "credentials.json" not in paths

    def test_binary_files_excluded(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        paths = {f.path for f in r.files}
        assert "logo.png" not in paths

    def test_entry_points_detected(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert len(r.entry_points) > 0
        assert any("main.py" in ep for ep in r.entry_points)

    def test_test_files_detected(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert len(r.test_files) > 0

    def test_frameworks_detected(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert "FastAPI" in r.frameworks or "Pydantic" in r.frameworks

    def test_python_symbols_extracted(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path, extract_symbols=True).scan()
        main_file = next((f for f in r.files if f.path == "main.py"), None)
        assert main_file is not None
        names = {s.name for s in main_file.symbols}
        assert "App" in names
        assert "start" in names

    def test_line_counts_nonzero(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert r.total_lines > 0

    def test_directory_tree_populated(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        assert len(r.directory_tree) > 0

    def test_save_and_load(self, tmp_path):
        _make_repo(tmp_path)
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        r = RepositoryScanner(repo_root=tmp_path).scan()
        saved_path = r.save(cw)
        assert saved_path.exists()
        loaded = ScanResult.load(cw)
        assert loaded.total_files == r.total_files
        assert loaded.primary_language == r.primary_language


# ─────────────────────────────────────────────
# ScanResult serialisation
# ─────────────────────────────────────────────

class TestScanResultSerialisation:
    def test_json_roundtrip(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        as_json = r.to_json()
        loaded  = ScanResult.from_json(as_json)
        assert loaded.total_files == r.total_files
        assert loaded.primary_language == r.primary_language
        assert len(loaded.files) == len(r.files)

    def test_files_by_language(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        py_files = r.files_by_language("Python")
        assert all(f.language == "Python" for f in py_files)
        assert len(py_files) > 0

    def test_entry_point_files_method(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        ep_files = r.entry_point_files()
        assert all(f.is_entry_point for f in ep_files)

    def test_test_file_entries_method(self, tmp_path):
        _make_repo(tmp_path)
        r = RepositoryScanner(repo_root=tmp_path).scan()
        test_entries = r.test_file_entries()
        assert all(f.is_test for f in test_entries)
        assert len(test_entries) > 0
