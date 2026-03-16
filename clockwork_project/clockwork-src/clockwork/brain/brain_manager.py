"""
clockwork/brain/brain_manager.py

BrainManager — selects the reasoning engine and runs multi-layer validation.

Engine selection (from .clockwork/config.yaml  →  brain.mode):
  minibrain  — default, always available, deterministic
  ollama     — local LLM via Ollama
  external   — OpenAI / Anthropic / custom endpoint
  auto       — tries Ollama first, falls back to MiniBrain

Multi-layer validation (spec §15):
  Layer 1 — MiniBrain  (always runs)
  Layer 2 — AI engine  (if configured and available)

All decisions are appended to .clockwork/brain_log.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel
from .minibrain import MiniBrain
from .ollama_brain import OllamaBrain

_CLOCKWORK_DIR = Path(".clockwork")


class BrainManager:
    """Orchestrates reasoning engine selection and multi-layer validation."""

    def __init__(self, clockwork_dir: Path | None = None) -> None:
        self._clockwork_dir = clockwork_dir or _CLOCKWORK_DIR
        self._config = self._load_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        """Execute multi-layer validation and return the final BrainResult."""
        mini_result = MiniBrain().analyze_change(context, repo_diff, rules)
        self._log(mini_result, engine="MiniBrain")

        # Short-circuit: deterministic rejection — skip expensive AI layer
        if mini_result.status == BrainStatus.REJECTED:
            return mini_result

        mode = self._config.get("brain", {}).get("mode", "minibrain").lower()

        if mode in ("ollama", "auto"):
            ai_result = self._run_ollama(context, repo_diff, rules)
            if ai_result:
                self._log(ai_result, engine="OllamaBrain")
                return self._merge(mini_result, ai_result)

        if mode == "external":
            ai_result = self._run_external(context, repo_diff, rules)
            if ai_result:
                self._log(ai_result, engine="ExternalBrain")
                return self._merge(mini_result, ai_result)

        return mini_result

    # ------------------------------------------------------------------
    # Engine runners
    # ------------------------------------------------------------------

    def _run_ollama(
        self, context: dict[str, Any], repo_diff: dict[str, Any], rules: list[dict[str, Any]]
    ) -> BrainResult | None:
        if not OllamaBrain.is_available():
            return None
        model = self._config.get("brain", {}).get("model", "deepseek-coder")
        return OllamaBrain(model=model).analyze_change(context, repo_diff, rules)

    def _run_external(
        self, context: dict[str, Any], repo_diff: dict[str, Any], rules: list[dict[str, Any]]
    ) -> BrainResult | None:
        brain_cfg = self._config.get("brain", {})
        if not brain_cfg.get("provider"):
            return None
        from .external_brain import ExternalBrain  # noqa: PLC0415
        return ExternalBrain(config=brain_cfg).analyze_change(context, repo_diff, rules)

    # ------------------------------------------------------------------
    # Result merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge(layer1: BrainResult, layer2: BrainResult) -> BrainResult:
        """Combine two results, favouring the more severe outcome."""
        severity = {BrainStatus.VALID: 0, BrainStatus.WARNING: 1, BrainStatus.REJECTED: 2}
        dominant, other = (layer2, layer1) if severity[layer2.status] >= severity[layer1.status] \
                           else (layer1, layer2)
        return BrainResult(
            status=dominant.status,
            confidence=round((layer1.confidence + layer2.confidence) / 2, 4),
            risk_level=dominant.risk_level,
            explanation=dominant.explanation,
            violations=list(dict.fromkeys(dominant.violations + other.violations)),
            warnings=list(dict.fromkeys(dominant.warnings   + other.warnings)),
        )

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        config_path = self._clockwork_dir / "config.yaml"
        if not config_path.exists():
            return {}
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception:  # noqa: BLE001
            return {}

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, result: BrainResult, engine: str) -> None:
        """Append a brain decision to .clockwork/brain_log.json."""
        log_path = self._clockwork_dir / "brain_log.json"
        entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "engine": engine,
            **result.to_dict(),
        }
        existing: list[dict[str, Any]] = []
        if log_path.exists():
            try:
                with log_path.open("r", encoding="utf-8") as fh:
                    existing = json.load(fh)
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(entry)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as fh:
                json.dump(existing, fh, indent=2)
        except OSError:
            pass  # Non-fatal: logging must never block validation
