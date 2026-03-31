"""
clockwork/scanner/git_diff.py
-------------------------------
GitDiffScanner — compute structured diff between HEAD and working tree.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json, time

@dataclass
class RepoDiff:
    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    staged: list[str] = field(default_factory=list)
    unstaged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    is_git_repo: bool = False
    current_branch: str = ""
    last_commit_sha: str = ""
    last_commit_message: str = ""
    is_dirty: bool = False

    def all_changed(self) -> list[str]:
        seen = set()
        result = []
        for f in self.added + self.modified + self.deleted:
            if f not in seen:
                seen.add(f)
                result.append(f)
        return result

    def to_dict(self) -> dict:
        return {
            "added": self.added, "deleted": self.deleted,
            "modified": self.modified, "staged": self.staged,
            "untracked": self.untracked, "is_git_repo": self.is_git_repo,
            "current_branch": self.current_branch,
            "last_commit_sha": self.last_commit_sha[:8] if self.last_commit_sha else "",
            "last_commit_message": self.last_commit_message,
            "is_dirty": self.is_dirty,
        }


class GitDiffScanner:
    LAST_SCAN_FILE = ".clockwork/last_scan.json"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self._repo = None
        self._try_open()

    def _try_open(self) -> None:
        try:
            import git
            self._repo = git.Repo(self.repo_root)
        except Exception:
            self._repo = None

    def is_git_repo(self) -> bool:
        return self._repo is not None

    def current_branch(self) -> str:
        if not self._repo:
            return ""
        try:
            return self._repo.active_branch.name
        except Exception:
            return "HEAD"

    def last_commit(self) -> tuple[str, str]:
        if not self._repo:
            return "", ""
        try:
            commit = self._repo.head.commit
            return commit.hexsha, commit.message.strip().split("\n")[0]
        except Exception:
            return "", ""

    def diff_staged(self) -> RepoDiff:
        """Files staged for commit (for pre-commit hook)."""
        if not self._repo:
            return RepoDiff()
        try:
            staged = [item.a_path for item in self._repo.index.diff("HEAD")]
            sha, msg = self.last_commit()
            return RepoDiff(
                staged=staged,
                modified=[f for f in staged
                          if f not in [item.a_path
                                       for item in self._repo.index.diff("HEAD",
                                       diff_filter="A")]],
                added=[item.a_path for item in
                       self._repo.index.diff("HEAD", diff_filter="A")],
                is_git_repo=True,
                current_branch=self.current_branch(),
                last_commit_sha=sha,
                last_commit_message=msg,
            )
        except Exception:
            return RepoDiff(is_git_repo=True)

    def diff_since_last_scan(self) -> RepoDiff:
        """All changes since clockwork last ran."""
        if not self._repo:
            return RepoDiff()

        last_sha = self._load_last_scan_sha()
        sha, msg = self.last_commit()

        try:
            if last_sha and last_sha != sha:
                diff = self._repo.commit(last_sha).diff(self._repo.head.commit)
                added = [d.b_path for d in diff if d.new_file]
                deleted = [d.a_path for d in diff if d.deleted_file]
                modified = [d.a_path for d in diff
                            if not d.new_file and not d.deleted_file]
            else:
                diff = self._repo.index.diff(None)
                added = [item.a_path for item in self._repo.untracked_files
                         if isinstance(item, str)]
                modified = [d.a_path for d in diff]
                deleted = []

            is_dirty = self._repo.is_dirty(untracked_files=True)
            untracked = list(self._repo.untracked_files)[:50]

            return RepoDiff(
                added=added, deleted=deleted, modified=modified,
                untracked=untracked, is_git_repo=True,
                current_branch=self.current_branch(),
                last_commit_sha=sha, last_commit_message=msg,
                is_dirty=is_dirty,
            )
        except Exception:
            return RepoDiff(is_git_repo=True, current_branch=self.current_branch(),
                           last_commit_sha=sha, last_commit_message=msg)

    def record_scan(self) -> None:
        sha, _ = self.last_commit()
        scan_file = self.repo_root / self.LAST_SCAN_FILE
        scan_file.parent.mkdir(parents=True, exist_ok=True)
        scan_file.write_text(
            json.dumps({"sha": sha, "timestamp": time.time()}),
            encoding="utf-8",
        )

    def _load_last_scan_sha(self) -> Optional[str]:
        scan_file = self.repo_root / self.LAST_SCAN_FILE
        if not scan_file.exists():
            return None
        try:
            return json.loads(scan_file.read_text())["sha"]
        except Exception:
            return None
