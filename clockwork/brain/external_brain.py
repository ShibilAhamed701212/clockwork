"""
clockwork/brain/external_brain.py

ExternalBrain — reasoning engine backed by OpenAI, Anthropic, or custom LLM API.

Configuration via .clockwork/config.yaml:
  brain:
    mode: external
    provider: openai        # openai | anthropic | custom
    model: gpt-4o
    api_key: sk-...
    endpoint: https://...   # only for 'custom'
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_TIMEOUT = 30

_SYSTEM_PROMPT = """\
You are Clockwork Brain, a repository intelligence verification engine.
Respond ONLY with a valid JSON object — no prose, no markdown fences.

JSON schema:
{
  "status": "VALID" | "WARNING" | "REJECTED",
  "confidence": <float 0.0-1.0>,
  "risk_level": "low" | "medium" | "high",
  "explanation": "<one paragraph>",
  "violations": ["<violation>", ...],
  "warnings":   ["<warning>",   ...]
}
"""


class ExternalBrain(BrainInterface):
    """Reasoning engine backed by an external LLM API."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.provider: str = config.get("provider", "openai").lower()
        self.model:    str = config.get("model", "gpt-4o")
        self.api_key:  str = self._resolve_api_key(config)
        self.endpoint: str = config.get("endpoint", self._default_endpoint())

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        user_prompt = self._build_prompt(context, repo_diff, rules)
        try:
            raw = self._call_api(user_prompt)
            return self._parse_response(raw)
        except Exception as exc:  # noqa: BLE001
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.15,
                risk_level=RiskLevel.MEDIUM,
                explanation=f"ExternalBrain API call failed: {exc}. Manual review required.",
                warnings=[f"API error: {exc}"],
            )

    def _build_prompt(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> str:
        return (
            f"PROJECT CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            f"REPOSITORY DIFF:\n{json.dumps({k: repo_diff.get(k,[]) for k in ('added','deleted','modified')}, indent=2)}\n\n"
            f"ACTIVE RULES:\n{json.dumps([{'id': r.get('id'), 'description': r.get('description')} for r in rules], indent=2)}\n\n"
            "Analyse the diff. Respond ONLY with the required JSON."
        )

    def _call_api(self, user_prompt: str) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(user_prompt)
        return self._call_openai_compatible(user_prompt)

    def _call_openai_compatible(self, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]

    def _call_anthropic(self, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 1024,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["content"][0]["text"]

    def _parse_response(self, raw: str) -> BrainResult:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            return BrainResult(
                status=BrainStatus.WARNING, confidence=0.25, risk_level=RiskLevel.MEDIUM,
                explanation="ExternalBrain returned non-JSON. Manual review required.",
                warnings=["Could not parse external API response as JSON."],
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

    def _default_endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages" if self.provider == "anthropic" \
               else "https://api.openai.com/v1/chat/completions"

    def _resolve_api_key(self, config: dict[str, Any]) -> str:
        if config.get("api_key"):
            return config["api_key"]
        env_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
        return os.environ.get(env_map.get(self.provider, "EXTERNAL_BRAIN_API_KEY"), "")
