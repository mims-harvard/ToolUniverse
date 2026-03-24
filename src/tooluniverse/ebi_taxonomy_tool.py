# ebi_taxonomy_tool.py
"""
EBI Taxonomy REST API tool for ToolUniverse.

The EBI Taxonomy service provides access to the NCBI Taxonomy database
through a RESTful interface. It supports lookup by taxonomy ID, scientific
name, common name, and provides name suggestions for search/submission.

API: https://www.ebi.ac.uk/ena/taxonomy/rest
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EBI_TAXONOMY_BASE = "https://www.ebi.ac.uk/ena/taxonomy/rest"


@register_tool("EBITaxonomyTool")
class EBITaxonomyTool(BaseTool):
    """
    Tool for querying the EBI Taxonomy REST API.

    Provides taxonomy lookup by ID, scientific name, common/any name,
    and name suggestion for search or submission. Returns taxonomic
    classification including lineage, rank, division, and genetic codes.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "tax_by_id"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Taxonomy API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EBI Taxonomy API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to EBI Taxonomy API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"EBI Taxonomy API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying EBI Taxonomy: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate EBI Taxonomy endpoint."""
        endpoint_type = self.endpoint_type

        if endpoint_type == "tax_by_id":
            return self._get_by_tax_id(arguments)
        elif endpoint_type == "tax_by_scientific_name":
            return self._get_by_scientific_name(arguments)
        elif endpoint_type == "tax_by_any_name":
            return self._get_by_any_name(arguments)
        elif endpoint_type == "tax_suggest":
            return self._get_suggestions(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {endpoint_type}",
            }

    def _get_by_tax_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy information by NCBI Taxonomy ID."""
        tax_id = arguments.get("tax_id", "")
        if not tax_id:
            return {"status": "error", "error": "tax_id parameter is required"}

        url = f"{EBI_TAXONOMY_BASE}/tax-id/{tax_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        return {
            "status": "success",
            "data": {
                "tax_id": data.get("taxId"),
                "scientific_name": data.get("scientificName"),
                "common_name": data.get("commonName"),
                "rank": data.get("rank"),
                "division": data.get("division"),
                "lineage": data.get("lineage"),
                "genetic_code": data.get("geneticCode"),
                "mitochondrial_genetic_code": data.get("mitochondrialGeneticCode"),
                "authority": data.get("authority"),
                "other_names": data.get("otherNames", []),
                "submittable": data.get("submittable"),
                "binomial": data.get("binomial"),
                "formal_name": data.get("formalName"),
            },
            "metadata": {
                "query_tax_id": str(tax_id),
                "source": "EBI Taxonomy REST API",
            },
        }

    def _get_by_scientific_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy information by scientific name."""
        name = arguments.get("scientific_name", "")
        if not name:
            return {"status": "error", "error": "scientific_name parameter is required"}

        url = f"{EBI_TAXONOMY_BASE}/scientific-name/{name}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = data if isinstance(data, list) else [data]
        items = []
        for item in results:
            items.append(
                {
                    "tax_id": item.get("taxId"),
                    "scientific_name": item.get("scientificName"),
                    "common_name": item.get("commonName"),
                    "rank": item.get("rank"),
                    "division": item.get("division"),
                    "lineage": item.get("lineage"),
                    "genetic_code": item.get("geneticCode"),
                    "authority": item.get("authority"),
                }
            )

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "total_results": len(items),
                "query_name": name,
                "source": "EBI Taxonomy REST API",
            },
        }

    def _get_by_any_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy by any name (scientific, common, synonym)."""
        name = arguments.get("name", "")
        if not name:
            return {"status": "error", "error": "name parameter is required"}

        url = f"{EBI_TAXONOMY_BASE}/any-name/{name}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = data if isinstance(data, list) else [data]
        items = []
        for item in results:
            items.append(
                {
                    "tax_id": item.get("taxId"),
                    "scientific_name": item.get("scientificName"),
                    "common_name": item.get("commonName"),
                    "rank": item.get("rank"),
                    "division": item.get("division"),
                    "lineage": item.get("lineage"),
                    "authority": item.get("authority"),
                }
            )

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "total_results": len(items),
                "query_name": name,
                "source": "EBI Taxonomy REST API",
            },
        }

    def _get_suggestions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy name suggestions for search."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        url = f"{EBI_TAXONOMY_BASE}/suggest-for-search/{query}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        results = data if isinstance(data, list) else [data]
        items = []
        for item in results:
            items.append(
                {
                    "tax_id": item.get("taxId"),
                    "scientific_name": item.get("scientificName"),
                    "common_name": item.get("commonName"),
                    "rank": item.get("rank"),
                    "display_name": item.get("displayName"),
                }
            )

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "total_results": len(items),
                "query": query,
                "source": "EBI Taxonomy REST API",
            },
        }
