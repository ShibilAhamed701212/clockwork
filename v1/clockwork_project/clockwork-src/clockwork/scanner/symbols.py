"""
clockwork/scanner/symbols.py
------------------------------
Static symbol extractor for Python source files.

Uses the stdlib ``ast`` module — no external dependencies.
Extracts:
  • top-level and nested class definitions
  • top-level and method-level function definitions
  • import statements (import X / from X import Y)

For non-Python files a lightweight regex-based fallback is used to
extract function/class-like constructs from common languages.

All analysis is static — no code is executed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

from clockwork.scanner.models import SymbolInfo


class SymbolExtractor:
    """
    Extracts named symbols from source files.

    Usage::

        extractor = SymbolExtractor()
        symbols, imports = extractor.extract(path)
    """

    def extract(
        self, path: Path, language: str = ""
    ) -> tuple[list[SymbolInfo], list[str]]:
        """
        Return (symbols, imports) for the given file.

        Falls back to an empty result if the file cannot be parsed.
        """
        lang = language.lower() if language else ""

        if lang == "python" or path.suffix.lower() in (".py", ".pyi"):
            return self._extract_python(path)

        if lang in ("javascript", "typescript") or path.suffix.lower() in (
            ".js", ".ts", ".jsx", ".tsx", ".mjs"
        ):
            return self._extract_js_ts(path)

        if lang == "go" or path.suffix.lower() == ".go":
            return self._extract_go(path)

        if lang == "java" or path.suffix.lower() == ".java":
            return self._extract_java(path)

        return [], []

    # ------------------------------------------------------------------ #
    # Python — ast-based
    # ------------------------------------------------------------------ #

    def _extract_python(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        # Track which function nodes are methods so we can skip them in the
        # top-level walk (ast.walk visits all nodes regardless of nesting).
        method_nodes: set[int] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolInfo(name=node.name, kind="class", line=node.lineno)
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(
                            SymbolInfo(
                                name=item.name,
                                kind="method",
                                line=item.lineno,
                                parent=node.name,
                            )
                        )
                        method_nodes.add(id(item))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if id(node) not in method_nodes:
                    symbols.append(
                        SymbolInfo(name=node.name, kind="function", line=node.lineno)
                    )

            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        # Deduplicate imports while preserving order
        seen: set[str] = set()
        unique_imports = []
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)

        return symbols, unique_imports

    # ------------------------------------------------------------------ #
    # JavaScript / TypeScript — regex-based
    # ------------------------------------------------------------------ #

    _JS_CLASS_RE    = re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE)
    _JS_FUNC_RE     = re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
    )
    _JS_ARROW_RE    = re.compile(
        r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE
    )
    _JS_IMPORT_RE   = re.compile(
        r"""^import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE
    )

    def _extract_js_ts(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._JS_CLASS_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._JS_FUNC_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JS_ARROW_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JS_IMPORT_RE.finditer(source):
            imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))

    # ------------------------------------------------------------------ #
    # Go — regex-based
    # ------------------------------------------------------------------ #

    _GO_FUNC_RE   = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE)
    _GO_STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct", re.MULTILINE)
    _GO_IMPORT_RE = re.compile(r'"([^"]+)"')

    def _extract_go(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._GO_STRUCT_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._GO_FUNC_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        # Go imports — handle both block and single-line forms
        import_block = re.search(r'import\s*\(([^)]+)\)', source, re.DOTALL)
        if import_block:
            for m in self._GO_IMPORT_RE.finditer(import_block.group(1)):
                imports.append(m.group(1))
        else:
            # Single-line: import "pkg"
            for m in re.finditer(r'^\s*import\s+"([^"]+)"', source, re.MULTILINE):
                imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))

    # ------------------------------------------------------------------ #
    # Java — regex-based
    # ------------------------------------------------------------------ #

    _JAVA_CLASS_RE  = re.compile(
        r"(?:public|private|protected|abstract|final)?\s*class\s+(\w+)", re.MULTILINE
    )
    _JAVA_METHOD_RE = re.compile(
        r"(?:public|private|protected|static|final|abstract|synchronized|\s)+\s+\w[\w<>\[\]]*\s+(\w+)\s*\(",
        re.MULTILINE,
    )
    _JAVA_IMPORT_RE = re.compile(r"^import\s+([\w.]+);", re.MULTILINE)

    def _extract_java(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._JAVA_CLASS_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._JAVA_METHOD_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JAVA_IMPORT_RE.finditer(source):
            imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))
