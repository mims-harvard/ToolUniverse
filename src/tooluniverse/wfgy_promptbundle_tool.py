"""
WFGY Prompt Bundle Tool for ToolUniverse

This tool does NOT call any LLM.
It returns a reusable prompt bundle (system + user template) for triaging LLM/RAG issues
and mapping them to WFGY ProblemMap "No.1" ... "No.16".
"""

from __future__ import annotations

from typing import Any, Dict, List

from tooluniverse.tool_registry import register_tool


TOOL_CONFIG: Dict[str, Any] = {
    "name": "wfgy_promptbundle_triage",
    "type": "WFGYPromptBundleTool",
    "description": (
        "Return a pure prompt bundle (no LLM call) to triage an LLM/RAG failure and map it "
        "to WFGY ProblemMap No.1..No.16, with minimal-fix checklist and links."
    ),
    "parameter": {
        "type": "object",
        "properties": {
            "bug_description": {
                "type": "string",
                "description": (
                    "A short description of the LLM/RAG issue. Include prompt, retrieved context, "
                    "model answer, and logs if available."
                ),
            },
            "audience": {
                "type": "string",
                "description": "Target audience for the returned prompt bundle.",
                "enum": ["beginner", "engineer", "infra"],
                "default": "engineer",
            },
        },
        "required": ["bug_description"],
    },
    "return_schema": {
        "type": "object",
        "description": "Structured prompt bundle for triage (no tool chaining required).",
        "properties": {
            "status": {"type": "string"},
            "tool": {"type": "string"},
            "result": {"type": "object"},
        },
    },
    "test_examples": [
        {
            "bug_description": (
                "RAG chatbot answers with facts not present in retrieved context. "
                "Retrieved chunks talk about credit cards only, but model claims Bitcoin is supported."
            ),
            "audience": "engineer",
        }
    ],
}


@register_tool("WFGYPromptBundleTool", config=TOOL_CONFIG)
class WFGYPromptBundleTool:
    def __init__(self, tool_config: Dict[str, Any] | None = None) -> None:
        self.tool_config = tool_config or TOOL_CONFIG

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        bug = (arguments.get("bug_description") or "").strip()
        if not bug:
            return {
                "status": "error",
                "tool": self.tool_config["name"],
                "result": {"error": "bug_description is required"},
            }

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
            "tool": self.tool_config["name"],
            "result": {
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


def wfgy_promptbundle_triage(bug_description: str, audience: str = "engineer") -> Dict[str, Any]:
    """
    Convenience function so users can call it directly without ToolUniverse runtime.
    """
    tool = WFGYPromptBundleTool()
    return tool.run({"bug_description": bug_description, "audience": audience})
