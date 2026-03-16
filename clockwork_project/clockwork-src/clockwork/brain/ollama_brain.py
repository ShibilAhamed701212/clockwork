"""
clockwork/brain/ollama_brain.py

OllamaBrain — reasoning engine that delegates to a locally-running Ollama LLM.

Pipeline:
  Repository Diff -> Prompt Generation -> Ollama REST API -> BrainResult

Requires Ollama: https://ollama.ai
Default model  : deepseek-coder (configurable via .clockwork/config.yaml)
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_OLLAMA_API_URL          = "http://localhost:11434/api/generate"
_DEFAULT_MODEL           = "deepseek-coder"
_REQUEST_TIMEOUT_SECONDS = 30

_SYSTEM_PROMPT = """\
You are Clockwork Brain, a repository intelligence engine.
Respond ONLY with a valid JSON object — no prose, no markdown.

JSON schema:
{
  "status": "VALID" | "WARNING" | "REJECTED",
  "confidence": <float 0.0-1.0>,
  "risk_level": "low" | "medium" | "high",
  "explanation": "<one paragraph>",
  "violations": ["<violation>", ...],
  "warnings": ["<warning>", ...]
}
"""


class OllamaBrain(BrainInterface):
    """Reasoning engine powered by a locally-running Ollama model."""

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self.model = model

    @staticmethod
    def is_available() -> bool:
        """Return True if Ollama is installed and responding."""
        try:
            result = subprocess.run(
                ["ollama", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        prompt = self._build_prompt(context, repo_diff, rules)
        try:
            raw = self._call_ollama(prompt)
            return self._parse_response(raw)
        except Exception as exc:  # noqa: BLE001
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.20,
                risk_level=RiskLevel.MEDIUM,
                explanation=f"OllamaBrain failed: {exc}. Manual review recommended.",
                warnings=[f"Ollama error: {exc}"],
            )

    def _build_prompt(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> str:
        return (
            f"PROJECT CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            f"REPOSITORY DIFF:\n{json.dumps({k: repo_diff.get(k, []) for k in ('added','deleted','modified')}, indent=2)}\n\n"
            f"ACTIVE RULES:\n{json.dumps([{'id': r.get('id'), 'description': r.get('description')} for r in rules], indent=2)}\n\n"
            "Analyse this repository modification. Respond ONLY with the required JSON."
        )

    def _call_ollama(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "system": _SYSTEM_PROMPT, "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            _OLLAMA_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "")

    def _parse_response(self, raw: str) -> BrainResult:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.30,
                risk_level=RiskLevel.MEDIUM,
                explanation="OllamaBrain returned non-JSON. Manual review required.",
                warnings=["Could not parse Ollama response as JSON."],
            )
        try:
            status = BrainStatus(data.get("status", "WARNING").upper())
        except ValueError:
            status = BrainStatus.WARNING
        try:
            risk = RiskLevel(data.get("risk_level", "medium").lower())
        except ValueError:
            risk = RiskLevel.MEDIUM
        return BrainResult(
            status=status,
            confidence=float(data.get("confidence", 0.5)),
            risk_level=risk,
            explanation=data.get("explanation", "No explanation provided."),
            violations=data.get("violations", []),
            warnings=data.get("warnings", []),
        )
