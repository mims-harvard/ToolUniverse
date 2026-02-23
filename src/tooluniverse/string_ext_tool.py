# string_ext_tool.py
"""
STRING Extended API tool for ToolUniverse.

Provides access to STRING API endpoints not covered by existing tools:
- functional_annotation: Per-protein GO, KEGG, disease, compartment annotations

API: https://string-db.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


STRING_API_BASE_URL = "https://string-db.org/api/json"


class STRINGExtTool(BaseTool):
    """
    Extended STRING API tool for functional annotation queries.

    Complements existing STRING tools (interactions, enrichment, network,
    PPI enrichment) by providing per-protein functional annotations
    from GO, KEGG, DISEASES, TISSUES, COMPARTMENTS, and other databases.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "functional_annotation")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the STRING API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"STRING API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to STRING API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"STRING API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying STRING API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "functional_annotation":
            return self._get_functional_annotations(arguments)
        elif self.endpoint == "enrichment":
            return self._get_enrichment(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_functional_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get functional annotations for a protein from STRING."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "error": "identifiers parameter is required (gene name or protein ID, e.g., 'TP53')"
            }

        species = arguments.get("species", 9606)
        category = arguments.get("category", None)

        url = f"{STRING_API_BASE_URL}/functional_annotation"
        params = {
            "identifiers": identifiers,
            "species": species,
        }
        if category:
            params["category"] = category

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Organize by category
        by_category = {}
        for ann in data:
            cat = ann.get("category", "Unknown")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(
                {
                    "term": ann.get("term"),
                    "description": ann.get("description"),
                    "number_of_genes": ann.get("number_of_genes"),
                    "input_genes": ann.get("inputGenes", []),
                }
            )

        # Summary of categories
        category_summary = {cat: len(items) for cat, items in by_category.items()}

        # Return top annotations per category (limit to avoid huge responses)
        top_annotations = {}
        for cat, items in by_category.items():
            top_annotations[cat] = items[:15]

        return {
            "data": {
                "identifiers": identifiers,
                "species": species,
                "total_annotations": len(data),
                "category_summary": category_summary,
                "annotations": top_annotations,
            },
            "metadata": {
                "source": "STRING API - Functional Annotation",
                "identifiers": identifiers,
                "species": species,
            },
        }

    def _get_enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform functional enrichment analysis on a set of proteins."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "error": "identifiers parameter is required (newline-separated gene names, e.g., 'BRCA1\\nTP53\\nEGFR')"
            }

        species = arguments.get("species", 9606)
        background = arguments.get("background_string_identifiers", None)

        url = f"{STRING_API_BASE_URL}/enrichment"
        params = {
            "identifiers": identifiers,
            "species": species,
        }
        if background:
            params["background_string_identifiers"] = background

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return {
            "data": {
                "identifiers": identifiers,
                "species": species,
                "enrichments": data,
            },
            "metadata": {
                "source": "STRING API - Functional Enrichment",
                "identifiers": identifiers,
                "species": species,
            },
        }
