"""
ImmPort immunology database search tool for ToolUniverse.

Provides search for ImmPort studies (vaccine trials, flow cytometry, ELISPOT,
RNA-seq, clinical immunology data) using the public Elasticsearch-based API.

API: https://www.immport.org/data/query/api/search/study
No authentication required for study search.
"""

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


IMMPORT_SEARCH_URL = "https://www.immport.org/data/query/api/search/study"


@register_tool("ImmPortTool")
class ImmPortTool(BaseTool):
    """
    Tool for searching ImmPort, the NIAID-funded immunology database with
    900+ open studies covering vaccine trials, flow cytometry, ELISPOT,
    RNA-seq, and clinical immunology data.

    No authentication required for study search.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search_studies")

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "search_studies":
                return self._search_studies(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ImmPort API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ImmPort API",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_studies(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search ImmPort studies by keyword with optional filters."""
        query = arguments.get("query") or arguments.get("term", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        condition = arguments.get("condition_or_disease")
        assay = arguments.get("assay_method")
        focus = arguments.get("research_focus")
        species = arguments.get("species")
        limit = min(int(arguments.get("limit", 10)), 100)

        pageSize = limit * 3 if (condition or assay or focus) else limit
        params = {"term": query, "pageSize": pageSize}
        if species:
            params["species"] = species

        resp = requests.get(
            IMMPORT_SEARCH_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        hits_data = data.get("hits", {})
        total = hits_data.get("total", {}).get("value", 0)
        raw_hits = hits_data.get("hits", [])

        filtered = []
        for hit in raw_hits:
            src = hit.get("_source", {})
            if condition:
                conds = [c.lower() for c in (src.get("condition_or_disease") or [])]
                if not any(condition.lower() in c for c in conds):
                    continue
            if assay:
                assays = [a.lower() for a in (src.get("assay_method") or [])]
                if not any(assay.lower() in a for a in assays):
                    continue
            if focus:
                focuses = [f.lower() for f in (src.get("research_focus") or [])]
                if not any(focus.lower() in f for f in focuses):
                    continue
            filtered.append(src)
            if len(filtered) >= limit:
                break

        studies = [
            {
                "study_accession": src.get("study_accession"),
                "title": src.get("brief_title"),
                "brief_description": src.get("brief_description"),
                "condition_or_disease": src.get("condition_or_disease"),
                "research_focus": src.get("research_focus"),
                "species": src.get("species"),
                "assay_methods": src.get("assay_method"),
                "assay_method_counts": src.get("assay_method_count"),
                "biosample_types": src.get("biosample_type"),
                "actual_enrollment": src.get("actual_enrollment"),
                "age_range": src.get("age_range"),
                "gender_included": src.get("gender_included"),
                "pubmed_ids": src.get("pubmed_id"),
                "doi": src.get("doi"),
                "program_name": src.get("program_name"),
                "study_pi": src.get("study_pi"),
                "clinical_trial": src.get("clinical_trial"),
                "latest_data_release_date": src.get("latest_data_release_date"),
            }
            for src in filtered
        ]

        return {
            "status": "success",
            "data": studies,
            "metadata": {
                "total_matches": total,
                "returned": len(studies),
                "query": query,
                "filters_applied": {
                    k: v
                    for k, v in {
                        "condition_or_disease": condition,
                        "assay_method": assay,
                        "research_focus": focus,
                        "species": species,
                    }.items()
                    if v
                },
                "source": "ImmPort (www.immport.org)",
            },
        }
