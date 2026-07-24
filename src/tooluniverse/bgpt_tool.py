"""
BGPT structured scientific-evidence tool for ToolUniverse.

BGPT searches scientific papers and returns structured, full-text-derived
evidence fields for each study — methods, sample size/population, results,
limitations and biases, conflicts of interest, data/code availability,
quality scores, study blind spots, and a `how_to_falsify` statement — rather
than only titles and abstracts. This is complementary to the PubMed /
EuropePMC / OpenAlex discovery tools, which return bibliographic metadata.

API: https://bgpt.pro/api/mcp-search (POST, JSON). OpenAPI:
https://raw.githubusercontent.com/connerlambden/bgpt-mcp/main/openapi.yaml
License: MIT. The first 50 results are free (no key); set BGPT_API_KEY for
the paid tier once the free allowance is exhausted. Structured fields are
model-generated, so treat them as an appraisal aid, not curated ground truth.

Requested in mims-harvard/ToolUniverse issue #204.
"""

import os
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BGPT_SEARCH_URL = "https://bgpt.pro/api/mcp-search"


@register_tool("BGPTPaperEvidenceTool")
class BGPTPaperEvidenceTool(BaseTool):
    """
    Search scientific papers via BGPT and return structured study-evidence
    fields for critical appraisal.

    The BGPT_API_KEY environment variable (or an `api_key` argument) is
    optional — it is only needed once the free result allowance is used up.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        # Full-text evidence extraction is slow; allow more than the usual 30s.
        self.timeout: int = tool_config.get("timeout", 60)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query") or arguments.get("search_keywords")
        if not query or not str(query).strip():
            return {
                "status": "error",
                "error": "Parameter 'query' is required (a natural-language scientific search query).",
            }

        try:
            num_results = int(arguments.get("num_results", arguments.get("limit", 10)))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "Parameter 'num_results' must be an integer (1-100).",
            }
        num_results = max(1, min(num_results, 100))

        payload: Dict[str, Any] = {"query": str(query), "num_results": num_results}

        days_back = arguments.get("days_back")
        if days_back is not None:
            try:
                payload["days_back"] = max(1, int(days_back))
            except (TypeError, ValueError):
                return {
                    "status": "error",
                    "error": "Parameter 'days_back' must be a positive integer (number of days).",
                }

        # api_key is optional: explicit argument first, then BGPT_API_KEY env var.
        api_key = arguments.get("api_key") or os.environ.get("BGPT_API_KEY")
        if api_key:
            payload["api_key"] = api_key

        try:
            response = requests.post(
                BGPT_SEARCH_URL, json=payload, timeout=self.timeout
            )
        except requests.Timeout:
            return {
                "status": "error",
                "error": f"BGPT request timed out after {self.timeout}s. Try a narrower query or fewer num_results.",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Failed to reach BGPT: {str(e)}"}

        # 402 = free allowance exhausted; the user needs a paid-tier key.
        if response.status_code == 402:
            return {
                "status": "error",
                "error": (
                    "BGPT free result allowance is exhausted. Set the BGPT_API_KEY "
                    "environment variable (or pass 'api_key') to continue. See https://bgpt.pro/mcp/"
                ),
            }
        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"BGPT API returned HTTP {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            body = response.json()
        except ValueError:
            return {
                "status": "error",
                "error": "BGPT returned a non-JSON response.",
                "detail": response.text[:500],
            }

        results = body.get("results", []) if isinstance(body, dict) else []
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "BGPT (bgpt.pro)",
                "query": str(query),
                "returned": len(results),
                "evidence_fields_are_model_generated": True,
            },
        }
