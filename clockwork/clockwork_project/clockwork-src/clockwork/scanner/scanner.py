"""
clockwork/scanner/scanner.py
------------------------------
RepositoryScanner — the main orchestrator for the scan subsystem.

Scan pipeline:
  1. Walk repository tree
  2. Filter directories and files
  3. Classify each file (entry point / test / config)
  4. Detect language per file
  5. Count lines and bytes
  6. Extract symbols and imports (Python + JS/TS + Go + Java)
  7. Detect frameworks from dependency manifests
  8. Aggregate language statistics
  9. Build directory tree
  10. Produce ScanResult

All operations are static — no code is executed.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from clockwork.scanner.filters import ScanFilter, DEPENDENCY_FILES
from clockwork.scanner.frameworks import FrameworkDetector
from clockwork.scanner.language import LanguageDetector
from clockwork.scanner.models import (
    DirectoryEntry,
    FileEntry,
    LanguageSummary,
    ScanResult,
    SymbolInfo,
)
from clockwork.scanner.symbols import SymbolExtractor


class RepositoryScanner:
    """
    Performs a full static analysis of a repository.

    Usage::

        scanner = RepositoryScanner(repo_root=Path("/path/to/repo"))
        result  = scanner.scan()
        result.save(Path("/path/to/repo/.clockwork"))
    """

    # Maximum file size to attempt symbol extraction (bytes)
    MAX_SYMBOL_EXTRACT_SIZE = 512_000   # 512 KB

    def __init__(
        self,
        repo_root: Path,
        extract_symbols: bool = True,
        verbose: bool = False,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.extract_symbols = extract_symbols
        self.verbose = verbose

        # Load config-driven ignore rules if .clockwork/config.yaml exists
        extra_ignore_dirs, extra_ignore_exts = self._load_config_ignores()

        self._filter     = ScanFilter(extra_ignore_dirs, extra_ignore_exts)
        self._lang       = LanguageDetector()
        self._symbols    = SymbolExtractor()
        self._frameworks = FrameworkDetector()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def scan(self) -> ScanResult:
        """
        Execute the full scan pipeline and return a ScanResult.

        This is the only public method external code needs to call.
        """
        start = time.perf_counter()

        if self.verbose:
            print(f"Scanning: {self.repo_root}")

        files: list[FileEntry]       = []
        directories: list[DirectoryEntry] = []
        lang_counts: dict[str, int]  = defaultdict(int)
        lang_details: dict[str, LanguageSummary] = {}
        dir_tree: dict[str, list[str]] = defaultdict(list)

        entry_points: list[str]  = []
        test_files: list[str]    = []
        config_files: list[str]  = []
        dep_files: list[str]     = []

        # ── Walk the tree ──────────────────────────────────────────────
        for abs_path in sorted(self.repo_root.rglob("*")):

            # Skip ignored directories
            if abs_path.is_dir():
                if self._filter.should_skip_directory(abs_path, self.repo_root):
                    continue
                continue   # directories processed at end from dir_tree

            if not abs_path.is_file():
                continue

            # Skip files in ignored dirs
            if self._filter.should_skip_directory(abs_path.parent, self.repo_root):
                continue

            # Skip filtered-out files
            if self._filter.should_skip_file(abs_path):
                continue

            rel = str(abs_path.relative_to(self.repo_root))

            # Language
            language = self._lang.detect(abs_path)

            # Size / lines
            size_bytes = 0
            line_count = 0
            try:
                size_bytes = abs_path.stat().st_size
                if language not in {"Other"} and size_bytes < self.MAX_SYMBOL_EXTRACT_SIZE:
                    line_count = _count_lines(abs_path)
            except OSError:
                pass

            # Classification
            is_entry  = self._filter.is_entry_point(abs_path)
            is_test   = self._filter.is_test_file(abs_path)
            is_config = self._filter.is_config_file(abs_path)
            is_dep    = self._filter.is_dependency_file(abs_path)

            # Last modified timestamp
            try:
                mtime = datetime.fromtimestamp(
                    abs_path.stat().st_mtime, tz=timezone.utc
                ).isoformat()
            except OSError:
                mtime = None

            # Symbol extraction
            symbols: list[SymbolInfo] = []
            imports: list[str] = []
            if (
                self.extract_symbols
                and size_bytes <= self.MAX_SYMBOL_EXTRACT_SIZE
                and language in {"Python", "JavaScript", "TypeScript", "Go", "Java"}
            ):
                symbols, imports = self._symbols.extract(abs_path, language)

            # Build FileEntry
            entry = FileEntry(
                path=rel,
                extension=abs_path.suffix.lower(),
                language=language,
                size_bytes=size_bytes,
                lines=line_count,
                is_entry_point=is_entry,
                is_test=is_test,
                is_config=is_config,
                symbols=symbols,
                imports=imports,
                last_modified=mtime,
            )
            files.append(entry)

            # Accumulators
            if language != "Other":
                lang_counts[language] += 1
                if language not in lang_details:
                    lang_details[language] = LanguageSummary(
                        name=language,
                        extensions=[abs_path.suffix.lower()],
                    )
                ls = lang_details[language]
                ls.file_count += 1
                ls.total_lines += line_count
                ls.total_bytes += size_bytes
                if abs_path.suffix.lower() not in ls.extensions:
                    ls.extensions.append(abs_path.suffix.lower())

            parent_rel = str(abs_path.parent.relative_to(self.repo_root)) or "."
            dir_tree[parent_rel].append(abs_path.name)

            if is_entry:  entry_points.append(rel)
            if is_test:   test_files.append(rel)
            if is_config: config_files.append(rel)
            if is_dep:    dep_files.append(rel)

        # ── Build directory entries ────────────────────────────────────
        for dir_rel, members in dir_tree.items():
            abs_dir = self.repo_root / dir_rel
            subdirs = [
                d.name for d in abs_dir.iterdir()
                if d.is_dir() and not self._filter.should_skip_directory(d, self.repo_root)
            ] if abs_dir.exists() else []

            member_langs = list({
                f.language for f in files
                if str(Path(f.path).parent) == dir_rel and f.language != "Other"
            })

            directories.append(DirectoryEntry(
                path=dir_rel,
                file_count=len(members),
                subdirectory_count=len(subdirs),
                languages=member_langs,
                has_init="__init__.py" in members,
                has_tests=any(
                    self._filter.is_test_file(Path(m)) for m in members
                ),
            ))

        # ── Framework detection ────────────────────────────────────────
        all_rel_paths = [f.path for f in files]
        frameworks = self._frameworks.detect(self.repo_root, all_rel_paths)

        # ── Primary language ───────────────────────────────────────────
        primary = self._lang.detect_primary_language(dict(lang_counts))

        elapsed = time.perf_counter() - start

        if self.verbose:
            print(
                f"Scan complete: {len(files)} files, "
                f"{len(lang_counts)} languages, "
                f"{elapsed*1000:.0f} ms"
            )

        # ── Git metadata ──────────────────────────────────────────────
        git_branch = ""
        git_commit = ""
        git_is_dirty = False
        git_untracked_count = 0
        try:
            from clockwork.scanner.git_diff import GitDiffScanner
            git_scanner = GitDiffScanner(self.repo_root)
            if git_scanner.is_git_repo():
                git_branch = git_scanner.current_branch()
                sha, _ = git_scanner.last_commit()
                git_commit = sha
        except Exception:
            pass

        return ScanResult(
            scanned_at=datetime.now(timezone.utc).isoformat(),
            root=str(self.repo_root),
            project_name=self.repo_root.name,
            clockwork_version="0.1",
            total_files=len(files),
            total_lines=sum(f.lines for f in files),
            total_bytes=sum(f.size_bytes for f in files),
            primary_language=primary,
            languages=dict(sorted(lang_counts.items(), key=lambda x: -x[1])),
            language_details=list(lang_details.values()),
            files=files,
            directories=directories,
            directory_tree=dict(dir_tree),
            entry_points=entry_points,
            test_files=test_files,
            config_files=config_files,
            frameworks=frameworks,
            dependency_files=dep_files,
            git_branch=git_branch,
            git_commit=git_commit,
            git_is_dirty=git_is_dirty,
            git_untracked_count=git_untracked_count,
        )

    # ------------------------------------------------------------------ #
    # Config loading
    # ------------------------------------------------------------------ #

    def _load_config_ignores(self) -> tuple[set[str], set[str]]:
        """Read extra ignore rules from .clockwork/config.yaml if present."""
        config_path = self.repo_root / ".clockwork" / "config.yaml"
        try:
            if config_path.exists():
                cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                scanner_cfg = cfg.get("scanner", {})
                dirs = set(scanner_cfg.get("ignore_dirs", []))
                exts = set(scanner_cfg.get("ignore_extensions", []))
                return dirs, exts
        except Exception:
            pass
        return set(), set()


# ── Helpers ────────────────────────────────────────────────────────────────

def _count_lines(path: Path) -> int:
    """Count newlines in a file. Returns 0 on read error."""
    try:
        with path.open("rb") as fh:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: fh.read(65_536), b""))
    except OSError:
        return 0
