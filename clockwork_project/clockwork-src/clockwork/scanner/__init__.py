"""
clockwork/scanner/__init__.py
-------------------------------
Repository Scanner subsystem.

Public API::

    from clockwork.scanner import RepositoryScanner, ScanResult

    scanner = RepositoryScanner(repo_root=Path("/path/to/repo"))
    result  = scanner.scan()
    result.save(clockwork_dir)
"""

from clockwork.scanner.models import (
    FileEntry,
    DirectoryEntry,
    ScanResult,
    LanguageSummary,
)
from clockwork.scanner.scanner import RepositoryScanner
from clockwork.scanner.language import LanguageDetector
from clockwork.scanner.symbols import SymbolExtractor

__all__ = [
    "RepositoryScanner",
    "ScanResult",
    "FileEntry",
    "DirectoryEntry",
    "LanguageSummary",
    "LanguageDetector",
    "SymbolExtractor",
]
