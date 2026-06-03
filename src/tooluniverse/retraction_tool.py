"""
Publication retraction-status tool for ToolUniverse.

Checks whether a published paper (by DOI) has been retracted, corrected, or
flagged with an expression of concern, using Crossref's ``update`` metadata
(populated from the Retraction Watch database, ``source: retraction-watch``).
This is a research-integrity guardrail for literature workflows: an agent
should confirm a paper is not retracted before citing it or building an
argument on its claims. Complements the discovery tools (PubMed, OpenAlex,
Europe PMC, BGPT), which return papers without retraction status.

API: https://api.crossref.org/works/{doi} (public, no key; a contact email
via CROSSREF_MAILTO is encouraged for Crossref's faster "polite pool").
"""

import os
from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

CROSSREF_WORKS_URL = "https://api.crossref.org/works"

# Crossref update "type" values, grouped by how serious they are.
_RETRACTION_TYPES = {"retraction", "withdrawal", "removal"}
_CONCERN_TYPES = {"expression_of_concern", "concern"}
_CORRECTION_TYPES = {"correction", "erratum", "corrigendum", "addendum"}


def _notice_date(update: Dict[str, Any]) -> str | None:
    parts = (update.get("updated") or {}).get("date-parts") or [[]]
    if parts and parts[0]:
        return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts[0]))
    return None


@register_tool("RetractionCheckTool")
class RetractionCheckTool(BaseTool):
    """Check a DOI's retraction / correction / expression-of-concern status."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        doi = arguments.get("doi")
        if not doi or not str(doi).strip():
            return {"status": "error", "error": "Parameter 'doi' is required."}
        # Accept a full URL or a 'doi:'-prefixed value.
        doi = (
            str(doi).strip().replace("https://doi.org/", "").replace("doi:", "").strip()
        )

        params = {}
        mailto = os.environ.get("CROSSREF_MAILTO")
        if mailto:
            params["mailto"] = mailto

        try:
            resp = requests.get(
                f"{CROSSREF_WORKS_URL}/{doi}",
                params=params,
                headers={"User-Agent": "ToolUniverse/RetractionCheck"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return {
                "status": "error",
                "error": f"Crossref request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to reach Crossref: {str(e)}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"DOI '{doi}' not found in Crossref.",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"Crossref returned HTTP {resp.status_code}",
            }
        try:
            message = resp.json().get("message", {})
        except ValueError:
            return {
                "status": "error",
                "error": "Crossref returned a non-JSON response.",
            }

        # Deduplicate notices by (type, notice DOI) — Crossref sometimes lists
        # the same retraction twice.
        seen = set()
        notices: List[Dict[str, Any]] = []
        for update in message.get("updated-by", []) or []:
            utype = str(update.get("type", "")).lower()
            key = (utype, update.get("DOI"))
            if key in seen:
                continue
            seen.add(key)
            notices.append(
                {
                    "type": utype,
                    "label": update.get("label"),
                    "notice_doi": update.get("DOI"),
                    "date": _notice_date(update),
                    "source": update.get("source"),
                }
            )

        types = {n["type"] for n in notices}
        is_retracted = bool(types & _RETRACTION_TYPES)
        title = message.get("title") or [None]
        return {
            "status": "success",
            "data": {
                "doi": doi,
                "title": title[0] if isinstance(title, list) else title,
                "is_retracted": is_retracted,
                "has_expression_of_concern": bool(types & _CONCERN_TYPES),
                "has_correction": bool(types & _CORRECTION_TYPES),
                "notices": notices,
            },
            "metadata": {
                "source": "Crossref update metadata (Retraction Watch)",
                "notice_count": len(notices),
            },
        }
