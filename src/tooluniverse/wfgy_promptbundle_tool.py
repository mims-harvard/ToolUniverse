"""
WFGY PromptBundle Tool (no-LLM, no-external-call)

This tool provides a structured "prompt bundle" for diagnosing LLM/RAG failures
using the WFGY 16 Problem Map, without calling any LLM API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


WFGY_PROBLEM_MAP_URL = "https://github.com/onestardao/WFGY/tree/main/ProblemMap#readme"
WFGY_REPO_URL = "https://github.com/onestardao/WFGY"
WFGY_DOI_URL = "https://doi.org/10.5281/zenodo.15320188"
WFGY_TXTOS_URL = "https://raw.githubusercontent.com/onestardao/WFGY/main/OS/TXTOS.txt"
WFGY_PROBLEM_MAP_RAW_URL = "https://raw.githubusercontent.com/onestardao/WFGY/main/ProblemMap/README.md"


DEFAULT_EXAMPLE_1 = """Example 1: retrieval hallucination (No.1 style)

Context:
I have a RAG chatbot that answers questions from a product FAQ. The FAQ only covers billing rules and does NOT mention crypto.

User prompt:
"Can I pay my subscription with Bitcoin?"

Retrieved context:
- "We only accept major credit cards and PayPal."
- "All payments are processed in USD."

Model answer:
"Yes, you can pay with Bitcoin. We support several cryptocurrencies..."

Observation:
The retrieved chunks do not support the answer, yet the model confidently invents info.
"""

DEFAULT_EXAMPLE_2 = """Example 2: bootstrap ordering / infra race (No.14 style)

Context:
RAG API has api-gateway, rag-worker, and vector-db (Qdrant). Local docker compose works.

Production:
Kubernetes deploy. Right after fresh deploy, api-gateway returns 500s for a few minutes.
Logs show timeouts from api-gateway to vector-db. After 5-10 minutes, it becomes normal.

Observation:
Likely startup race / readiness / dependency ordering problem.
"""

DEFAULT_EXAMPLE_3 = """Example 3: secrets / config drift around first deploy (No.16 style)

Context:
New env var SECRET_RAG_KEY required by middleware.

Local:
Developers set it in .env, works.

Production:
Deployed new version but forgot to add SECRET_RAG_KEY to prod environment.
Requests fail with "missing secret". Hot patch fixes it, but similar issues keep happening.

Observation:
First-deploy failure due to missing config/secret drift.
"""


def _safe_str(x: Any, max_len: int) -> str:
    s = "" if x is None else str(x)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.strip()
    if len(s) > max_len:
        return s[: max_len - 12] + "\n...[truncated]"
    return s


def build_prompt_bundle(bug_report: str, max_chars: int = 12000) -> Dict[str, Any]:
    """
    Build a prompt bundle that a user can paste into any strong LLM.
    This function never calls external services.
    """
    bug_report = _safe_str(bug_report, max_len=6000)

    system_prompt = """You are an LLM debugger that follows the WFGY 16 Problem Map.

Goal:
Given a description of a bug or failure in an LLM/RAG/tool pipeline, map it to the closest Problem Map number (No.1 to No.16),
explain why, and propose a minimal fix.

Output contract:
1) Return exactly one primary Problem Map number: "Primary: No.X"
2) Optionally return one secondary candidate: "Secondary: No.Y (optional)"
3) Explain the reasoning in plain language (short but concrete)
4) Provide a minimal patch plan (steps the engineer can actually do)
5) Provide a verification checklist (how to confirm the fix)

Rules:
- Prefer minimal structural patches over generic advice.
- Do not invent logs or facts. If missing, ask for the minimal missing evidence.
- If multiple failures exist, pick the most root-cause-like failure mode as Primary.

User will provide:
- Bug report (symptoms, prompt, retrieved context if any, answer, logs, environment)
"""

    user_template = f"""Bug report:
{bug_report}

Now do:
- Primary: No.X
- Secondary: No.Y (optional)
- Why this mapping
- Minimal fix plan
- Verification checklist
- One line: "Open ProblemMap: {WFGY_PROBLEM_MAP_URL}"
"""

    how_to_use = [
        "Paste the 'system_prompt' and 'user_prompt' into any strong LLM (ChatGPT/Claude/etc.).",
        "If you have RAG, include: user prompt, retrieved chunks, model answer, and any logs.",
        "Ask the model to follow the output contract exactly (Primary No.X, minimal patch plan, verification checklist).",
        f"Then open the WFGY ProblemMap for the full fix details: {WFGY_PROBLEM_MAP_URL}",
    ]

    bundle: Dict[str, Any] = {
        "mode": "prompt_bundle_only",
        "system_prompt": system_prompt,
        "user_prompt": user_template,
        "how_to_use": how_to_use,
        "links": {
            "problem_map": WFGY_PROBLEM_MAP_URL,
            "repo": WFGY_REPO_URL,
            "doi": WFGY_DOI_URL,
            "txtos_raw": WFGY_TXTOS_URL,
            "problem_map_raw": WFGY_PROBLEM_MAP_RAW_URL,
        },
        "examples": [DEFAULT_EXAMPLE_1, DEFAULT_EXAMPLE_2, DEFAULT_EXAMPLE_3],
        "notes": [
            "This tool does not call any LLM API.",
            "It provides a reusable prompt bundle for triage and diagnosis.",
            "Primary/Secondary mapping references WFGY ProblemMap No.1..No.16.",
        ],
    }

    # Enforce overall size limit.
    compact = str(bundle)
    if len(compact) > max_chars:
        # If oversized, drop examples first.
        bundle["examples"] = ["[omitted: bundle size limit]"]
    return bundle


@dataclass
class WFGYPromptBundleTool:
    """
    Minimal ToolUniverse-compatible wrapper.

    Some ToolUniverse setups instantiate tools by class name.
    We provide a simple 'run' method returning a JSON-serializable dict.
    """

    name: str = "WFGY_ProblemMap_PromptBundle"

    def run(self, bug_report: Optional[str] = None, max_chars: int = 12000) -> Dict[str, Any]:
        """
        Run the tool.

        Args:
            bug_report: A plain text description of the LLM/RAG failure.
            max_chars: Safety cap for output size.

        Returns:
            Dict payload with prompt bundle and links.
        """
        bug_report_text = _safe_str(bug_report, max_len=6000)
        if not bug_report_text:
            bug_report_text = (
                "No bug_report provided.\n\n"
                "Please paste:\n"
                "- user prompt\n"
                "- retrieved context (if any)\n"
                "- model answer\n"
                "- logs / environment details\n"
            )

        payload = {
            "status": "success",
            "tool": self.name,
            "result": build_prompt_bundle(bug_report_text, max_chars=max_chars),
        }
        return payload


# Optional module-level convenience for frameworks that call a function directly.
def wfgy_promptbundle(bug_report: Optional[str] = None, max_chars: int = 12000) -> Dict[str, Any]:
    tool = WFGYPromptBundleTool()
    return tool.run(bug_report=bug_report, max_chars=max_chars)
