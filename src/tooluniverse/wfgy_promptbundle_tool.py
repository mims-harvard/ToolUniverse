"""
WFGY Prompt Bundle Tool for ToolUniverse

This tool does NOT call any LLM.
It returns a reusable prompt bundle (system + user template) for triaging LLM/RAG issues
and mapping them to WFGY ProblemMap entries "No.1" ... "No.16".
"""

from __future__ import annotations

from typing import Any, Dict, List

from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool


TOOL_CONFIG: Dict[str, Any] = {
    "name": "wfgy_promptbundle_triage",
    "type": "WFGYPromptBundleTool",
    "description": (
        "Return a pure prompt bundle (no LLM call) to triage an LLM/RAG failure and map it "
        "to WFGY ProblemMap No.1..No.16, with a minimal-fix checklist and reference links."
    ),
    "parameter": {
        "type": "object",
        "properties": {
            "bug_description": {
                "type": "string",
                "description": (
                    "Short description of the LLM/RAG failure. Include prompt, retrieved context, "
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
            "success": {
                "type": "boolean",
                "description": "Whether the prompt bundle was created successfully.",
            },
            "status": {
                "type": "string",
                "description": "Text status code, e.g. 'ok' or 'error'.",
            },
            "tool": {
                "type": "string",
                "description": "Tool name used for this response.",
            },
            "result": {
                "type": "object",
                "description": "Prompt bundle payload or error information.",
            },
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
class WFGYPromptBundleTool(BaseTool):
    """Return a system+user prompt bundle for WFGY ProblemMap triage."""

    def run(self, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        arguments = arguments or {}

        bug = (arguments.get("bug_description") or "").strip()
        if not bug:
            return {
                "success": False,
                "status": "error",
                "tool": TOOL_CONFIG["name"],
                "result": {"error": "bug_description is required"},
            }

        audience = (arguments.get("audience") or "engineer").strip().lower()
        if audience not in {"beginner", "engineer", "infra"}:
            audience = "engineer"

        links: Dict[str, str] = {
            "wfgy_repo": "https://github.com/onestardao/WFGY",
            "problem_map": "https://github.com/onestardao/WFGY/tree/main/ProblemMap#readme",
            "problem_map_readme_raw": (
                "https://raw.githubusercontent.com/onestardao/WFGY/main/ProblemMap/README.md"
            ),
            "txtos_raw": (
                "https://raw.githubusercontent.com/onestardao/WFGY/main/OS/TXTOS.txt"
            ),
            # Main technical report DOI for WFGY 1.0
            "doi": "https://doi.org/10.5281/zenodo.15320188",
        }

        system_prompt = self._build_system_prompt(audience=audience, links=links)
        user_prompt = self._build_user_prompt(bug_description=bug)

        examples: List[str] = [
            "Example A (No.1 style): retrieval hallucination – retrieved chunks deny feature X, model claims feature X is supported.",
            "Example B (No.14 style): bootstrap ordering / infra race – fresh deploy causes temporary 500s until vector DB or search stack is ready.",
            "Example C (No.16 style): secret / config drift – missing env var after first deploy causes runtime failure, fixed by hot patch.",
        ]

        return {
            "success": True,
            "status": "ok",
            "tool": TOOL_CONFIG["name"],
            "result": {
                "mode": "prompt_bundle_only",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "how_to_use": [
                    "Copy system_prompt into your LLM as the system / instruction message.",
                    "Copy user_prompt and replace the INCIDENT block with your real incident report.",
                    "Ask the LLM to output: primary WFGY ProblemMap No.X, optional secondary No.Y, minimal fix steps, and verification steps.",
                    "Open the ProblemMap link in the response for concrete remediation details.",
                ],
                "checklist": [
                    "Include the exact user prompt that triggered the failure.",
                    "Include retrieved context (top-k) verbatim.",
                    "Include the model answer verbatim.",
                    "Include logs / errors / timestamps if available.",
                    "State what the correct or expected behavior should be.",
                ],
                "links": links,
                "examples": examples,
            },
        }

    @staticmethod
    def _build_system_prompt(audience: str, links: Dict[str, str]) -> str:
        if audience == "beginner":
            tone = "Use simple language. Avoid jargon. Give concrete, small steps."
        elif audience == "infra":
            tone = "Be strict and ops-focused. Include rollout, gating, monitoring, and rollback checks."
        else:
            tone = "Be concise and diagnostic. Prefer minimal structural patches over vague advice."

        lines: List[str] = [
            "You are a triage assistant for LLM and RAG failures.",
            "Your job is to map each incident to exactly one primary WFGY ProblemMap code: No.1 .. No.16.",
            "You may optionally list ONE secondary candidate if it is extremely close, but always choose a single primary.",
            "",
            "Output format (strict):",
            "1) Primary: No.X",
            "2) Secondary (optional): No.Y or 'None'",
            "3) Why this mapping (3–7 bullet points)",
            "4) Minimal fix (concrete, ordered steps, not generic advice)",
            "5) Verification (how to prove the fix worked in practice)",
            "6) References (plain-text links to ProblemMap / DOI only)",
            "",
            f"Style: {tone}",
            "",
            "Important behavioral rules:",
            "- Stay within WFGY ProblemMap No.1..No.16, do not invent new codes.",
            "- Prefer structural and configuration-level fixes over prompt-only tuning.",
            "- Be honest about uncertainty; if the mapping is not perfect, say so and explain.",
            "",
            "References:",
            f"- WFGY ProblemMap overview: {links['problem_map']}",
            f"- Main WFGY 1.0 technical report (PDF, DOI): {links['doi']}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_user_prompt(bug_description: str) -> str:
        lines: List[str] = [
            "Here is an incident report from an LLM or RAG system.",
            "Diagnose it using WFGY ProblemMap No.1..No.16.",
            "",
            "INCIDENT REPORT START",
            bug_description,
            "INCIDENT REPORT END",
            "",
            "Remember:",
            "- Pick exactly one primary No.X.",
            "- Optionally mention one secondary No.Y if very close.",
            "- Propose a minimal structural fix and a verification plan.",
        ]
        return "\n".join(lines)


def wfgy_promptbundle_triage(bug_description: str, audience: str = "engineer") -> Dict[str, Any]:
    """
    Convenience function so users can call this tool directly in Python
    without going through the full ToolUniverse runtime.

    Example:
        from wfgy_promptbundle_tool import wfgy_promptbundle_triage

        bundle = wfgy_promptbundle_triage(
            bug_description=\"\"\"
            RAG chatbot answers with facts not in retrieved context.
            Chunks say "credit cards only", model claims "Bitcoin supported".
            \"\"\",
            audience="engineer",
        )
    """
    tool = WFGYPromptBundleTool(TOOL_CONFIG)
    return tool.run({"bug_description": bug_description, "audience": audience})
