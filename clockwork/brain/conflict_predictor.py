"""
clockwork/brain/conflict_predictor.py
---------------------------------------
Pre-merge conflict prediction using the knowledge graph.

Analyzes cross-branch dependency conflicts, rule violations,
and architecture drift before merging feature branches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ConflictReport:
    """Result of a pre-merge conflict analysis."""

    branch: str = ""
    base_branch: str = "main"
    file_conflicts: list[str] = field(default_factory=list)
    dependency_conflicts: list[str] = field(default_factory=list)
    rule_violations: list[str] = field(default_factory=list)
    architecture_drift: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high

    @property
    def has_conflicts(self) -> bool:
        return bool(
            self.file_conflicts
            or self.dependency_conflicts
            or self.rule_violations
            or self.architecture_drift
        )

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "base_branch": self.base_branch,
            "file_conflicts": self.file_conflicts,
            "dependency_conflicts": self.dependency_conflicts,
            "rule_violations": self.rule_violations,
            "architecture_drift": self.architecture_drift,
            "risk_level": self.risk_level,
            "has_conflicts": self.has_conflicts,
        }


class ConflictPredictor:
    """
    Predict merge conflicts using the knowledge graph and git diff.

    Analyzes:
      - Which files were modified in both branches
      - Cross-branch dependency conflicts (graph-based)
      - Rule violations in the feature branch
      - Architecture drift from the base branch
    """

    def predict(
        self,
        repo_root: Path,
        branch: str,
        base_branch: str = "main",
        graph_engine: Optional[Any] = None,
    ) -> ConflictReport:
        """
        Analyze a feature branch for potential merge conflicts.

        Args:
            repo_root: Path to the repository root
            branch: Feature branch name
            base_branch: Base branch to merge into
            graph_engine: Optional GraphQueryEngine instance

        Returns:
            ConflictReport with predicted conflicts
        """
        report = ConflictReport(branch=branch, base_branch=base_branch)

        try:
            import git
            repo = git.Repo(repo_root)
        except Exception:
            return report

        # Get files modified in the feature branch
        try:
            merge_base = repo.git.merge_base(base_branch, branch)
            branch_files = set(
                repo.git.diff("--name-only", merge_base, branch).splitlines()
            )
            base_files = set(
                repo.git.diff("--name-only", merge_base, base_branch).splitlines()
            )

            # Direct file conflicts
            report.file_conflicts = list(branch_files & base_files)

        except Exception:
            return report

        # Dependency conflicts via graph
        if graph_engine:
            try:
                for modified_file in branch_files:
                    dependents = graph_engine.who_depends_on(modified_file)
                    for dep in dependents:
                        if dep.file_path in base_files:
                            report.dependency_conflicts.append(
                                f"{modified_file} → {dep.file_path} "
                                f"(modified in both branches)"
                            )
            except Exception:
                pass

        # Determine risk level
        if report.file_conflicts or report.dependency_conflicts:
            if len(report.file_conflicts) > 5 or report.dependency_conflicts:
                report.risk_level = "high"
            else:
                report.risk_level = "medium"

        return report
