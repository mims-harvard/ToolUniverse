# reactome_analysis_tool.py
"""
Reactome Analysis Service tool for ToolUniverse.

The Reactome Analysis Service provides pathway overrepresentation analysis,
expression data analysis, and species comparison for gene/protein lists.
This is separate from the Reactome Content Service (already in ToolUniverse).

API: https://reactome.org/AnalysisService
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ANALYSIS_BASE_URL = "https://reactome.org/AnalysisService"


@register_tool("ReactomeAnalysisTool")
class ReactomeAnalysisTool(BaseTool):
    """
    Tool for Reactome pathway analysis (enrichment/overrepresentation).

    Accepts gene/protein identifiers and performs overrepresentation
    analysis or species comparison against Reactome pathways. Returns
    enriched pathways with p-values, FDR, and entity counts.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "pathway_enrichment")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Reactome Analysis API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Reactome Analysis request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Reactome Analysis Service.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Reactome Analysis HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate analysis endpoint."""
        if self.endpoint == "pathway_enrichment":
            return self._pathway_enrichment(arguments)
        elif self.endpoint == "species_comparison":
            return self._species_comparison(arguments)
        elif self.endpoint == "token_result":
            return self._token_result(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _pathway_enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform pathway overrepresentation analysis."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter required (newline-separated gene/protein IDs)",
            }

        # Ensure identifiers is newline-separated
        if isinstance(identifiers, list):
            identifiers = "\n".join(identifiers)

        page_size = arguments.get("page_size", 20)
        include_disease = arguments.get("include_disease", True)
        projection = arguments.get("projection", True)

        url = (
            f"{ANALYSIS_BASE_URL}/identifiers/projection"
            if projection
            else f"{ANALYSIS_BASE_URL}/identifiers/"
        )
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
            "includeDisease": str(include_disease).lower(),
        }

        response = requests.post(
            url,
            data=identifiers,
            headers={"Content-Type": "text/plain"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, identifiers)

    def _species_comparison(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform species comparison analysis."""
        identifiers = arguments.get("identifiers", "")
        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter required (newline-separated gene/protein IDs)",
            }

        if isinstance(identifiers, list):
            identifiers = "\n".join(identifiers)

        arguments.get("species", 9606)
        page_size = arguments.get("page_size", 20)

        url = f"{ANALYSIS_BASE_URL}/identifiers/projection"
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
        }

        response = requests.post(
            url,
            data=identifiers,
            headers={"Content-Type": "text/plain"},
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, identifiers)

    def _token_result(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve analysis results by token."""
        token = arguments.get("token", "")
        if not token:
            return {"status": "error", "error": "token parameter is required"}

        page_size = arguments.get("page_size", 20)

        url = f"{ANALYSIS_BASE_URL}/token/{token}"
        params = {
            "pageSize": min(page_size, 50),
            "page": 1,
        }

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        return self._format_analysis_result(data, "")

    def _format_analysis_result(self, data: Dict, identifiers: str) -> Dict[str, Any]:
        """Format analysis result into standard output."""
        summary = data.get("summary", {})
        pathways_raw = data.get("pathways", [])

        pathways = []
        for pw in pathways_raw:
            entities = pw.get("entities", {})
            reactions = pw.get("reactions", {})
            species = pw.get("species", {})

            pathways.append(
                {
                    "pathway_id": pw.get("stId"),
                    "name": pw.get("name"),
                    "species": species.get("name"),
                    "is_disease": pw.get("inDisease", False),
                    "is_lowest_level": pw.get("llp", False),
                    "entities_found": entities.get("found"),
                    "entities_total": entities.get("total"),
                    "entities_ratio": entities.get("ratio"),
                    "p_value": entities.get("pValue"),
                    "fdr": entities.get("fdr"),
                    "reactions_found": reactions.get("found"),
                    "reactions_total": reactions.get("total"),
                }
            )

        return {
            "status": "success",
            "data": {
                "token": summary.get("token"),
                "analysis_type": summary.get("type"),
                "projection": summary.get("projection"),
                "identifiers_not_found": data.get("identifiersNotFound", 0),
                "pathways_found": data.get("pathwaysFound", 0),
                "pathways": pathways,
            },
            "metadata": {
                "source": "Reactome Analysis Service",
                "total_pathways": data.get("pathwaysFound", 0),
                "returned": len(pathways),
            },
        }
