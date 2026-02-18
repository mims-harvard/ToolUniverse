# disprot_tool.py
"""
DisProt tool for ToolUniverse.

DisProt is a manually curated database of intrinsically disordered proteins
and regions, providing experimentally validated disorder annotations with
evidence codes and literature references.

API: https://disprot.org/api/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

DISPROT_BASE_URL = "https://disprot.org/api"


@register_tool("DisProtTool")
class DisProtTool(BaseTool):
    """
    Tool for querying DisProt intrinsically disordered protein database.

    Supports:
    - Search disordered proteins by text query
    - Get detailed disorder region annotations for a specific protein

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DisProt API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"DisProt API timed out after {self.timeout}s."}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to DisProt API (disprot.org)."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {"error": "Entry not found in DisProt. Check the accession."}
            return {"error": f"DisProt API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_entry":
            return self._get_entry(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search DisProt for disordered proteins."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query is required (e.g., 'TP53', 'kinase', 'amyloid')."}

        params = {
            "q": query,
            "release": "current",
            "page_size": min(arguments.get("page_size", 10), 20),
        }

        url = f"{DISPROT_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        results = data.get("data", [])
        entries = []
        for entry in results:
            genes = entry.get("genes", [])
            gene_name = genes[0].get("name", {}).get("value", "") if genes else ""
            entries.append(
                {
                    "disprot_id": entry.get("disprot_id"),
                    "acc": entry.get("acc"),
                    "name": entry.get("name"),
                    "gene": gene_name,
                    "organism": entry.get("organism"),
                    "length": entry.get("length"),
                    "disorder_content": entry.get("disorder_content"),
                    "regions_counter": entry.get("regions_counter"),
                    "dataset": entry.get("dataset", []),
                }
            )

        return {
            "data": entries,
            "metadata": {
                "source": "DisProt (disprot.org)",
                "query": query,
                "returned": len(entries),
            },
        }

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed disorder regions for a DisProt entry."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "error": "accession is required. Use DisProt ID (e.g., 'DP00086') or UniProt accession (e.g., 'P04637')."
            }

        # Determine whether it's a DisProt ID (DP*) or UniProt accession
        url = f"{DISPROT_BASE_URL}/search"
        if accession.upper().startswith("DP"):
            params = {"disprot_id": accession.upper(), "page_size": 1}
        else:
            params = {"acc": accession, "page_size": 1}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        search_result = response.json()

        results = search_result.get("data", [])
        if not results:
            return {"error": f"Entry not found in DisProt for accession '{accession}'."}
        data = results[0]

        # Extract regions
        regions = []
        for region in data.get("regions", []):
            cross_refs = []
            for xr in region.get("cross_refs", []):
                cross_refs.append(
                    {
                        "db": xr.get("db"),
                        "id": xr.get("id"),
                    }
                )
            regions.append(
                {
                    "region_id": region.get("region_id"),
                    "start": region.get("start"),
                    "end": region.get("end"),
                    "term_name": region.get("term_name"),
                    "term_namespace": region.get("term_namespace"),
                    "evidence_code": region.get("ec_name"),
                    "method": region.get("method_name"),
                    "cross_refs": cross_refs[:5],  # Limit refs
                }
            )

        genes = data.get("genes", [])
        gene_name = genes[0].get("name", {}).get("value", "") if genes else ""

        return {
            "data": {
                "disprot_id": data.get("disprot_id"),
                "acc": data.get("acc"),
                "name": data.get("name"),
                "gene": gene_name,
                "organism": data.get("organism"),
                "length": data.get("length"),
                "disorder_content": data.get("disorder_content"),
                "regions_counter": data.get("regions_counter"),
                "dataset": data.get("dataset", []),
                "regions": regions[:30],  # Limit to 30 regions
            },
            "metadata": {
                "source": "DisProt (disprot.org)",
                "total_regions": data.get("regions_counter", len(regions)),
            },
        }
