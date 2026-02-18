# uniprot_taxonomy_tool.py
"""
UniProt Taxonomy tool for ToolUniverse.

Provides taxonomy information from UniProt including species details,
lineage, protein statistics, and taxonomy search.

API: https://rest.uniprot.org/taxonomy/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPROT_BASE_URL = "https://rest.uniprot.org/taxonomy"


@register_tool("UniProtTaxonomyTool")
class UniProtTaxonomyTool(BaseTool):
    """
    Tool for querying UniProt taxonomy data.

    Supports:
    - Get taxonomy details by NCBI taxon ID
    - Search taxonomy by name

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_taxon")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniProt Taxonomy API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"UniProt API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to UniProt REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"UniProt API HTTP {status}: taxon may not exist"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_taxon":
            return self._get_taxon(arguments)
        elif self.endpoint == "search":
            return self._search(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy details by NCBI taxon ID."""
        taxon_id = arguments.get("taxon_id")
        if not taxon_id:
            return {"error": "taxon_id is required (e.g., 9606 for human)."}

        url = f"{UNIPROT_BASE_URL}/{taxon_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Process lineage
        lineage = []
        for item in data.get("lineage", []):
            lineage.append(
                {
                    "taxon_id": item.get("taxonId"),
                    "scientific_name": item.get("scientificName"),
                    "rank": item.get("rank"),
                    "hidden": item.get("hidden", False),
                }
            )

        stats = data.get("statistics", {})

        return {
            "data": {
                "taxon_id": data.get("taxonId"),
                "scientific_name": data.get("scientificName"),
                "common_name": data.get("commonName"),
                "mnemonic": data.get("mnemonic"),
                "rank": data.get("rank"),
                "lineage": lineage,
                "statistics": {
                    "reviewed_protein_count": stats.get("reviewedProteinCount", 0),
                    "unreviewed_protein_count": stats.get("unreviewedProteinCount", 0),
                },
            },
            "metadata": {
                "source": "UniProt Taxonomy (rest.uniprot.org)",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search taxonomy by name."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query is required (e.g., 'arabidopsis')."}

        size = arguments.get("size", 10)

        url = f"{UNIPROT_BASE_URL}/search"
        response = requests.get(
            url,
            params={"query": query, "size": size},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", []):
            stats = item.get("statistics", {})
            results.append(
                {
                    "taxon_id": item.get("taxonId"),
                    "scientific_name": item.get("scientificName"),
                    "common_name": item.get("commonName"),
                    "mnemonic": item.get("mnemonic"),
                    "rank": item.get("rank"),
                    "reviewed_protein_count": stats.get("reviewedProteinCount", 0),
                    "unreviewed_protein_count": stats.get("unreviewedProteinCount", 0),
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "UniProt Taxonomy (rest.uniprot.org)",
                "total_results": len(results),
                "query": query,
            },
        }
