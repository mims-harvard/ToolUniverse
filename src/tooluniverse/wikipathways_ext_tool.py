# wikipathways_ext_tool.py
"""
WikiPathways Extended tool for ToolUniverse.

Provides additional WikiPathways endpoints for extracting gene lists
from pathways and finding pathways by gene identifier.

API: https://webservice.wikipathways.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


WP_BASE_URL = "https://webservice.wikipathways.org"

CODE_TO_NAME = {
    "H": "HGNC Symbol",
    "En": "Ensembl",
    "S": "UniProt",
    "L": "Entrez Gene",
    "Ce": "ChEBI",
}


class WikiPathwaysExtTool(BaseTool):
    """
    Tool for WikiPathways extended API endpoints.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_pathway_genes")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the WikiPathways API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"WikiPathways API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to WikiPathways API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"error": f"WikiPathways API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying WikiPathways: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_pathway_genes":
            return self._get_pathway_genes(arguments)
        elif self.endpoint == "find_pathways_by_gene":
            return self._find_pathways_by_gene(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_pathway_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all genes in a WikiPathways pathway."""
        pathway_id = arguments.get("pathway_id", "")
        if not pathway_id:
            return {"error": "pathway_id parameter is required (e.g., 'WP254')"}

        code = arguments.get("code", "H")
        id_type_name = CODE_TO_NAME.get(code, code)

        url = f"{WP_BASE_URL}/getXrefList"
        params = {
            "pwId": pathway_id,
            "code": code,
            "format": "json",
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        xrefs = data.get("xrefs", [])
        # Deduplicate and sort
        unique_genes = sorted(set(xrefs))

        return {
            "data": {
                "pathway_id": pathway_id,
                "gene_count": len(unique_genes),
                "identifier_type": id_type_name,
                "genes": unique_genes,
            },
            "metadata": {
                "source": "WikiPathways API",
                "pathway_id": pathway_id,
                "code": code,
            },
        }

    def _find_pathways_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find pathways containing a specific gene."""
        gene = arguments.get("gene", "")
        if not gene:
            return {"error": "gene parameter is required (e.g., 'TP53', 'BRCA1')"}

        species = arguments.get("species", "Homo sapiens")

        url = f"{WP_BASE_URL}/findPathwaysByXref"
        params = {
            "ids": gene,
            "codes": "H",
            "format": "json",
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])

        # Filter by species
        if species:
            results = [
                r for r in results if species.lower() in r.get("species", "").lower()
            ]

        # Deduplicate by pathway ID (some genes appear multiple times in same pathway)
        seen = set()
        unique_pathways = []
        for r in results:
            pid = r.get("id", "")
            if pid not in seen:
                seen.add(pid)
                unique_pathways.append(
                    {
                        "id": pid,
                        "name": r.get("name", ""),
                        "species": r.get("species", ""),
                        "url": r.get("url"),
                    }
                )

        return {
            "data": {
                "gene": gene,
                "total_pathways": len(unique_pathways),
                "pathways": unique_pathways,
            },
            "metadata": {
                "source": "WikiPathways API",
                "gene": gene,
                "species": species,
            },
        }
