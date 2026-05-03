"""
WFGY Prompt Bundle Tool for ToolUniverse

This tool does NOT call any LLM or external API.
It returns a reusable prompt bundle (system + user template) for triaging
LLM/RAG issues and mapping them to WFGY ProblemMap codes No.1..No.16.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("WFGYPromptBundleTool")
class WFGYPromptBundleTool(BaseTool):
    """Local prompt-bundle tool for triaging LLM/RAG failures via WFGY ProblemMap."""

    def __init__(self, tool_config: Dict[str, Any]) -> None:
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        bug = (arguments.get("bug_description") or "").strip()
        if not bug:
            return {"status": "error", "error": "bug_description is required"}

        audience = (arguments.get("audience") or "engineer").strip().lower()
        if audience not in {"beginner", "engineer", "infra"}:
            audience = "engineer"

        links = {
            "wfgy_repo": "https://github.com/onestardao/WFGY",
            "problem_map": "https://github.com/onestardao/WFGY/tree/main/ProblemMap#readme",
            "problem_map_readme_raw": "https://raw.githubusercontent.com/onestardao/WFGY/main/ProblemMap/README.md",
        }

        system_prompt = self._build_system_prompt(audience=audience, links=links)
        user_prompt = self._build_user_prompt(bug_description=bug)

        examples: List[str] = [
            "Example A: retrieval hallucination: retrieved chunks deny feature X, model claims feature X is supported.",
            "Example B: bootstrap ordering / infra race: fresh deploy causes temporary 500s until vector DB is ready.",
            "Example C: secret/config drift: missing env var after deploy causes runtime failure, fixed by hot patch.",
        ]

        return {
            "status": "success",
            "data": {
                "mode": "prompt_bundle_only",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "how_to_use": [
                    "Copy system_prompt into your LLM as the system message.",
                    "Copy user_prompt and replace the bug block with your real incident report.",
                    "Ask the LLM to output: primary WFGY ProblemMap No.X, why, minimal fix, and verification steps.",
                    "Use the links to open the full ProblemMap page for concrete remediation.",
                ],
                "checklist": [
                    "Include the exact user prompt that triggered the failure",
                    "Include retrieved context (top-k) verbatim",
                    "Include model answer verbatim",
                    "Include logs / errors / timestamps if any",
                    "State what 'correct behavior' should be",
                ],
                "links": links,
                "examples": examples,
            },
        }

    @staticmethod
    def _build_system_prompt(audience: str, links: Dict[str, str]) -> str:
        tone = {
            "beginner": "Use simple language. Avoid jargon. Give concrete steps.",
            "engineer": "Be concise and diagnostic. Prefer minimal structural patches.",
            "infra": "Be strict and ops-focused. Include rollout / gating / readiness checks.",
        }[audience]

        return "\n".join(
            [
                "You are a triage assistant for LLM/RAG failures.",
                "You MUST map the incident to exactly one primary WFGY ProblemMap code: No.1 .. No.16.",
                "You MAY provide one secondary candidate if extremely close, but still pick exactly one primary.",
                "",
                "Output format (strict):",
                "1) Primary: No.X",
                "2) Secondary (optional): No.Y",
                "3) Why this mapping (3-7 bullets)",
                "4) Minimal fix (concrete, ordered steps)",
                "5) Verification (how to prove it is fixed)",
                "6) Links (ProblemMap / WFGY repo) in plain text",
                "",
                f"Style: {tone}",
                "",
                "References:",
                f"- ProblemMap: {links['problem_map']}",
                f"- WFGY repo: {links['wfgy_repo']}",
            ]
        )

    @staticmethod
    def _build_user_prompt(bug_description: str) -> str:
        return "\n".join(
            [
                "Here is the incident report. Diagnose using WFGY ProblemMap No.1..No.16.",
                "",
                "INCIDENT:",
                bug_description,
                "",
                "Remember: pick exactly one primary No.X and provide minimal fix + verification.",
            ]
        )
