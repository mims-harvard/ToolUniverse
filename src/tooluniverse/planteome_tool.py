# planteome_tool.py
"""
Planteome tools for ToolUniverse -- plant ontologies and gene annotations.

Planteome (planteome.org), a Global Core Biodata Resource with no prior
ToolUniverse coverage, hosts the Plant Ontology, Plant Trait Ontology,
Plant Stress Ontology, and crop-specific ontologies (e.g. banana,
soybean), plus a GOlr-style search index of gene-to-ontology-term
annotations across plant species. This is distinct from ToolUniverse's
generic GO tools (OLS/QuickGO): Planteome indexes plant-specific trait
and structure ontologies those don't carry, and its annotation search
resolves a specific plant gene (e.g. an Arabidopsis AGI locus code) to
every ontology term it has been annotated with, across GO, PO, TO, and
crop ontologies together.

API: https://browser.planteome.org/api (documented at
planteome.org/web_services)
No authentication required.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

PLANTEOME_API_URL = "https://browser.planteome.org/api"

_TERM_FIELDS = (
    "id",
    "annotation_class_label",
    "description",
    "source",
    "is_obsolete",
    "synonym",
)

_ANNOTATION_FIELDS = (
    "bioentity",
    "bioentity_label",
    "annotation_class",
    "annotation_class_label",
    "aspect",
    "taxon_label",
    "evidence_type",
    "reference",
)


def _planteome_get(path: str, params: Dict[str, Any], timeout: int):
    """GET a Planteome endpoint, returning (payload, error_envelope)."""
    try:
        resp = requests.get(f"{PLANTEOME_API_URL}{path}", params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        return None, {
            "status": "error",
            "error": f"Planteome request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"Planteome request failed: {e}"}
    resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError:
        return None, {"status": "error", "error": "Planteome returned a non-JSON response."}
    return payload, None


def _summarize(hit: Dict[str, Any], fields) -> Dict[str, Any]:
    return {f: hit.get(f) for f in fields}


@register_tool("PlanteomeTool")
class PlanteomeTool(BaseTool):
    """
    Tool for querying Planteome, dispatched by fields.operation:
      - "search_terms"       : keyword search over plant ontology terms
      - "get_term"            : a single ontology term by its accession ID
      - "search_annotations"  : gene/bioentity to ontology-term annotations

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "search_terms")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation == "search_terms":
            return self._search_terms(arguments)
        if self.operation == "get_term":
            return self._get_term(arguments)
        if self.operation == "search_annotations":
            return self._search_annotations(arguments)
        return {"status": "error", "error": f"Unknown operation: {self.operation}"}

    def _limit(self, arguments: Dict[str, Any], default: int = 20) -> int:
        try:
            return max(1, min(int(arguments.get("limit") or default), 100))
        except (TypeError, ValueError):
            return default

    def _search_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'pollen development'.",
            }

        payload, err = _planteome_get(
            "/search/ontology", {"q": query}, self.timeout
        )
        if err is not None:
            return err

        hits = payload.get("data") or []
        limit = self._limit(arguments)
        return {
            "status": "success",
            "data": [_summarize(h, _TERM_FIELDS) for h in hits[:limit]],
            "metadata": {
                "query": query,
                "returned": min(len(hits), limit),
                "source": "Planteome (planteome.org)",
            },
        }

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        term_id = (arguments.get("term_id") or "").strip()
        if not term_id:
            return {
                "status": "error",
                "error": "term_id is required, e.g. 'GO:0009555' or 'PO:0025281'.",
            }

        payload, err = _planteome_get("/entity/terms", {"entity": term_id}, self.timeout)
        if err is not None:
            return err

        if payload.get("status") != "success" or not payload.get("data"):
            return {
                "status": "error",
                "error": f"No Planteome ontology term found for '{term_id}'.",
            }

        hits = payload["data"] if isinstance(payload["data"], list) else list(payload["data"].values())
        if not hits:
            return {
                "status": "error",
                "error": f"No Planteome ontology term found for '{term_id}'.",
            }

        return {
            "status": "success",
            "data": _summarize(hits[0], _TERM_FIELDS),
            "metadata": {"term_id": term_id, "source": "Planteome (planteome.org)"},
        }

    def _search_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. a gene id like 'AT4G32150'.",
            }

        payload, err = _planteome_get(
            "/search/annotation", {"q": query}, self.timeout
        )
        if err is not None:
            return err

        hits = payload.get("data") or []
        limit = self._limit(arguments)
        return {
            "status": "success",
            "data": [_summarize(h, _ANNOTATION_FIELDS) for h in hits[:limit]],
            "metadata": {
                "query": query,
                "returned": min(len(hits), limit),
                "source": "Planteome (planteome.org)",
            },
        }
