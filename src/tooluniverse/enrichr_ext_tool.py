"""
Extended Enrichr API tools for ToolUniverse.

Enrichr is a comprehensive gene set enrichment analysis tool developed by
the Ma'ayan Lab. These extended tools provide direct access to enrichment
results, library listing, and gene set lookup.

API: https://maayanlab.cloud/Enrichr/
No authentication required.
"""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ENRICHR_BASE = "https://maayanlab.cloud/Enrichr"


@register_tool("EnrichrExtTool")
class EnrichrExtTool(BaseTool):
    """
    Extended Enrichr tools for gene set enrichment analysis.

    Operations:
    - list_libraries: List all available gene set libraries with statistics
    - enrich: Submit a gene list and get enrichment results for a library
    - get_top_enriched: Submit genes and return top enriched terms across libraries
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate operation."""
        operation = params.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()
        dispatch = {
            "list_libraries": self._list_libraries,
            "enrich": self._enrich,
            "get_top_enriched": self._get_top_enriched,
        }
        handler = dispatch.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Valid: {list(dispatch.keys())}",
            }
        return handler(params)

    def _list_libraries(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all available Enrichr gene set libraries with statistics."""
        category = params.get("category")
        try:
            resp = requests.get(
                f"{ENRICHR_BASE}/datasetStatistics",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            libraries = data.get("statistics", [])
            if category:
                cat_lower = category.lower()
                libraries = [
                    lib
                    for lib in libraries
                    if cat_lower in lib.get("libraryName", "").lower()
                ]
            result = []
            for lib in libraries:
                result.append(
                    {
                        "library_name": lib.get("libraryName"),
                        "num_terms": lib.get("numTerms"),
                        "gene_coverage": lib.get("geneCoverage"),
                        "genes_per_term": lib.get("genesPerTerm"),
                        "category_id": lib.get("categoryId"),
                    }
                )
            return {"status": "success", "data": result}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _submit_genes(self, gene_list: List[str]) -> Dict[str, Any]:
        """Submit a gene list to Enrichr and return the user list ID."""
        gene_str = "\n".join(gene_list)
        resp = requests.post(
            f"{ENRICHR_BASE}/addList",
            files={
                "list": (None, gene_str),
                "description": (None, "ToolUniverse enrichment query"),
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _enrich(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit gene list and get enrichment results for a specific library."""
        gene_list = params.get("gene_list", [])
        library = params.get("library", "GO_Biological_Process_2023")
        top_n = params.get("top_n", 10)
        if not gene_list:
            return {"status": "error", "error": "gene_list is required."}
        try:
            submit_resp = self._submit_genes(gene_list)
            user_list_id = submit_resp.get("userListId")
            if not user_list_id:
                return {"status": "error", "error": "Failed to submit gene list."}
            resp = requests.get(
                f"{ENRICHR_BASE}/enrich",
                params={"userListId": user_list_id, "backgroundType": library},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_results = data.get(library, [])
            enriched = []
            for r in raw_results[:top_n]:
                enriched.append(
                    {
                        "rank": r[0],
                        "term": r[1],
                        "p_value": r[2],
                        "z_score": r[3],
                        "combined_score": r[4],
                        "overlapping_genes": r[5],
                        "adjusted_p_value": r[6],
                        "overlap_count": len(r[5]),
                    }
                )
            return {
                "status": "success",
                "data": {
                    "library": library,
                    "gene_count": len(gene_list),
                    "total_terms": len(raw_results),
                    "enriched_terms": enriched,
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _get_top_enriched(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get top enriched terms across multiple libraries."""
        gene_list = params.get("gene_list", [])
        libraries = params.get(
            "libraries",
            [
                "GO_Biological_Process_2023",
                "KEGG_2021_Human",
                "Reactome_2022",
                "WikiPathways_2024_Human",
            ],
        )
        top_n = params.get("top_n", 5)
        if not gene_list:
            return {"status": "error", "error": "gene_list is required."}
        try:
            submit_resp = self._submit_genes(gene_list)
            user_list_id = submit_resp.get("userListId")
            if not user_list_id:
                return {"status": "error", "error": "Failed to submit gene list."}
            all_results: Dict[str, Any] = {}
            for library in libraries:
                resp = requests.get(
                    f"{ENRICHR_BASE}/enrich",
                    params={
                        "userListId": user_list_id,
                        "backgroundType": library,
                    },
                    timeout=self.timeout,
                )
                if resp.status_code != 200:
                    all_results[library] = {"error": f"HTTP {resp.status_code}"}
                    continue
                data = resp.json()
                raw_results = data.get(library, [])
                enriched = []
                for r in raw_results[:top_n]:
                    enriched.append(
                        {
                            "term": r[1],
                            "p_value": r[2],
                            "combined_score": r[4],
                            "overlapping_genes": r[5],
                            "adjusted_p_value": r[6],
                        }
                    )
                all_results[library] = {
                    "total_terms": len(raw_results),
                    "top_terms": enriched,
                }
            return {
                "status": "success",
                "data": {
                    "gene_count": len(gene_list),
                    "results_by_library": all_results,
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
