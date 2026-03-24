# opentree_tool.py
"""
Open Tree of Life API tool for ToolUniverse.

The Open Tree of Life synthesizes phylogenetic and taxonomic data from
thousands of studies into a comprehensive tree of all life. It provides
name resolution, taxonomy lookup, MRCA computation, and subtree extraction.

API: https://api.opentreeoflife.org/v3/
No authentication required. Free public access.
All endpoints use POST with JSON body.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

OPENTREE_BASE_URL = "https://api.opentreeoflife.org/v3"


@register_tool("OpenTreeTool")
class OpenTreeTool(BaseTool):
    """
    Tool for querying the Open Tree of Life.

    The Open Tree synthesizes published phylogenetic trees and taxonomy
    from NCBI, GBIF, IRMNG, and other sources into a single comprehensive
    tree of all life on Earth (~2.3 million tips).

    Supports: name resolution (TNRS), taxonomy lookup, MRCA computation,
    and induced subtree extraction.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "match_names")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Open Tree of Life API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Open Tree API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Open Tree of Life API",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Open Tree API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Open Tree: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Open Tree endpoint."""
        if self.endpoint == "match_names":
            return self._match_names(arguments)
        elif self.endpoint == "taxon_info":
            return self._get_taxon_info(arguments)
        elif self.endpoint == "mrca":
            return self._get_mrca(arguments)
        elif self.endpoint == "induced_subtree":
            return self._get_induced_subtree(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _match_names(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve species names to OTT IDs via TNRS."""
        names_str = arguments.get("names", "")
        if not names_str:
            return {"status": "error", "error": "names parameter is required"}

        names = [n.strip() for n in names_str.split(",") if n.strip()]

        url = f"{OPENTREE_BASE_URL}/tnrs/match_names"
        payload = {"names": names}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        results_list = data.get("results", [])

        results = []
        for result in results_list:
            matches = result.get("matches", [])
            if matches:
                best = matches[0]
                taxon = best.get("taxon", {})
                results.append(
                    {
                        "query_name": best.get("search_string", ""),
                        "matched_name": best.get("matched_name"),
                        "ott_id": taxon.get("ott_id"),
                        "is_synonym": best.get("is_synonym", False),
                        "score": best.get("score", 0),
                        "nomenclature_code": best.get("nomenclature_code"),
                    }
                )
            else:
                results.append(
                    {
                        "query_name": result.get("name", ""),
                        "matched_name": None,
                        "ott_id": None,
                        "is_synonym": False,
                        "score": 0,
                        "nomenclature_code": None,
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Open Tree of Life TNRS",
                "context": data.get("context"),
                "total_results": len(results),
            },
        }

    def _get_taxon_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy info for an OTT ID."""
        ott_id = arguments.get("ott_id")
        if ott_id is None:
            return {"status": "error", "error": "ott_id parameter is required"}

        url = f"{OPENTREE_BASE_URL}/taxonomy/taxon_info"
        payload = {"ott_id": int(ott_id)}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        return {
            "status": "success",
            "data": {
                "ott_id": data.get("ott_id"),
                "name": data.get("name"),
                "rank": data.get("rank"),
                "synonyms": data.get("synonyms", []),
                "tax_sources": data.get("tax_sources", []),
                "flags": data.get("flags", []),
                "is_suppressed": data.get("is_suppressed", False),
            },
            "metadata": {
                "source": "Open Tree of Life Taxonomy",
                "taxonomy_version": data.get("source"),
            },
        }

    def _get_mrca(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find Most Recent Common Ancestor of given OTT IDs."""
        ott_ids_str = arguments.get("ott_ids", "")
        if not ott_ids_str:
            return {
                "status": "error",
                "error": "ott_ids parameter is required (comma-separated)",
            }

        ott_ids = [int(x.strip()) for x in ott_ids_str.split(",") if x.strip()]
        if len(ott_ids) < 2:
            return {"status": "error", "error": "At least 2 OTT IDs are required"}

        url = f"{OPENTREE_BASE_URL}/tree_of_life/mrca"
        payload = {"ott_ids": ott_ids}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        mrca = data.get("mrca", {})
        nearest_taxon = data.get("nearest_taxon", {})

        return {
            "status": "success",
            "data": {
                "mrca_name": nearest_taxon.get("name"),
                "mrca_ott_id": nearest_taxon.get("ott_id"),
                "mrca_rank": nearest_taxon.get("rank"),
                "mrca_node_id": mrca.get("node_id"),
                "num_tips": mrca.get("num_tips"),
            },
            "metadata": {
                "source": "Open Tree of Life Synthetic Tree",
                "input_ott_ids": ott_ids,
            },
        }

    def _get_induced_subtree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Newick subtree for a set of OTT IDs."""
        ott_ids_str = arguments.get("ott_ids", "")
        if not ott_ids_str:
            return {
                "status": "error",
                "error": "ott_ids parameter is required (comma-separated)",
            }

        ott_ids = [int(x.strip()) for x in ott_ids_str.split(",") if x.strip()]
        if len(ott_ids) < 2:
            return {"status": "error", "error": "At least 2 OTT IDs are required"}

        url = f"{OPENTREE_BASE_URL}/tree_of_life/induced_subtree"
        payload = {"ott_ids": ott_ids}
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        return {
            "status": "success",
            "data": {
                "newick": data.get("newick", ""),
                "supporting_studies": data.get("supporting_studies", []),
            },
            "metadata": {
                "source": "Open Tree of Life Synthetic Tree",
                "input_ott_ids": ott_ids,
                "num_taxa": len(ott_ids),
            },
        }
