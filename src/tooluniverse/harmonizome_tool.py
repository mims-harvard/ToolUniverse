# harmonizome_tool.py
"""
Harmonizome tool for ToolUniverse.

Harmonizome (Ma'ayan Lab, Mount Sinai) integrates data from 100+ genomics
datasets covering gene expression, protein interactions, pathways, diseases,
drug targets, and more into a unified gene-centric resource.

API: https://maayanlab.cloud/Harmonizome/api/1.0/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

HARMONIZOME_BASE_URL = "https://maayanlab.cloud/Harmonizome/api/1.0"


@register_tool("HarmonizomeTool")
class HarmonizomeTool(BaseTool):
    """
    Tool for querying Harmonizome gene and dataset information.

    Supports:
    - Gene details (symbol, name, description, synonyms, proteins)
    - Dataset catalog (100+ integrated genomics datasets)

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_gene")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Harmonizome API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Harmonizome API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Harmonizome API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Gene not found in Harmonizome. Check the gene symbol."
                }
            return {"error": f"Harmonizome API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_gene":
            return self._get_gene(arguments)
        elif self.endpoint == "list_datasets":
            return self._list_datasets(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene details from Harmonizome."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {"error": "gene_symbol is required (e.g., 'TP53')."}

        url = f"{HARMONIZOME_BASE_URL}/gene/{gene_symbol}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Check if we got an error response
        if data.get("status") == 404 or "message" in data:
            return {
                "error": f"Gene '{gene_symbol}' not found: {data.get('message', 'unknown')}"
            }

        proteins = []
        for p in data.get("proteins", []):
            proteins.append(
                {
                    "symbol": p.get("symbol"),
                    "href": p.get("href"),
                }
            )

        return {
            "data": {
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "ncbi_entrez_gene_id": data.get("ncbiEntrezGeneId"),
                "ncbi_entrez_gene_url": data.get("ncbiEntrezGeneUrl"),
                "description": data.get("description"),
                "synonyms": data.get("synonyms", []),
                "proteins": proteins,
            },
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
            },
        }

    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available Harmonizome datasets."""
        url = f"{HARMONIZOME_BASE_URL}/dataset"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entities = data.get("entities", [])
        datasets = []
        for e in entities:
            datasets.append(
                {
                    "name": e.get("name"),
                    "href": e.get("href"),
                }
            )

        return {
            "data": datasets,
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "total_datasets": len(datasets),
            },
        }
