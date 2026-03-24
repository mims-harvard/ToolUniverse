# itis_tool.py
"""
ITIS (Integrated Taxonomic Information System) API tool for ToolUniverse.

ITIS provides authoritative taxonomic information on plants, animals,
fungi, and microbes of North America and the world. It is maintained by
a partnership of US, Canadian, and Mexican agencies.

API: https://www.itis.gov/ITISWebService/jsonservice/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ITIS_BASE_URL = "https://www.itis.gov/ITISWebService/jsonservice"


@register_tool("ITISTool")
class ITISTool(BaseTool):
    """
    Tool for querying the ITIS taxonomic database.

    ITIS provides standardized species names, classification hierarchies,
    common names, and authority references. Supports search by scientific
    name, common name, TSN (Taxonomic Serial Number), and hierarchy retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_scientific")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ITIS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ITIS API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ITIS API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ITIS API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ITIS: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate ITIS endpoint."""
        if self.endpoint == "search_scientific":
            return self._search_scientific(arguments)
        elif self.endpoint == "search_common":
            return self._search_common(arguments)
        elif self.endpoint == "hierarchy":
            return self._get_hierarchy(arguments)
        elif self.endpoint == "full_record":
            return self._get_full_record(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_scientific(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by scientific name."""
        name = arguments.get("scientific_name", "")
        if not name:
            return {"status": "error", "error": "scientific_name parameter is required"}

        url = f"{ITIS_BASE_URL}/searchByScientificName"
        params = {"srchKey": name}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        names = data.get("scientificNames", [])

        # Filter out null entries
        results = []
        for n in names:
            if n and n.get("tsn"):
                results.append(
                    {
                        "tsn": n.get("tsn"),
                        "combined_name": n.get("combinedName"),
                        "author": n.get("author"),
                        "kingdom": n.get("kingdom"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query": name,
                "total_results": len(results),
            },
        }

    def _search_common(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by common name."""
        name = arguments.get("common_name", "")
        if not name:
            return {"status": "error", "error": "common_name parameter is required"}

        url = f"{ITIS_BASE_URL}/searchByCommonName"
        params = {"srchKey": name}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        names = data.get("commonNames", [])

        results = []
        for n in names:
            if n and n.get("tsn"):
                results.append(
                    {
                        "tsn": n.get("tsn"),
                        "common_name": n.get("commonName"),
                        "language": n.get("language"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query": name,
                "total_results": len(results),
            },
        }

    def _get_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get full taxonomic hierarchy for a TSN."""
        tsn = arguments.get("tsn", "")
        if not tsn:
            return {"status": "error", "error": "tsn parameter is required"}

        url = f"{ITIS_BASE_URL}/getFullHierarchyFromTSN"
        params = {"tsn": tsn}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        hierarchy_list = data.get("hierarchyList", [])

        results = []
        for h in hierarchy_list:
            if h and h.get("tsn"):
                results.append(
                    {
                        "tsn": h.get("tsn"),
                        "taxon_name": h.get("taxonName"),
                        "rank_name": h.get("rankName"),
                        "parent_tsn": h.get("parentTsn"),
                    }
                )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ITIS",
                "query_tsn": str(tsn),
                "hierarchy_depth": len(results),
            },
        }

    def _get_full_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete taxonomic record for a TSN."""
        tsn = arguments.get("tsn", "")
        if not tsn:
            return {"status": "error", "error": "tsn parameter is required"}

        url = f"{ITIS_BASE_URL}/getFullRecordFromTSN"
        params = {"tsn": tsn}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract key fields from the full record
        sci_name = data.get("scientificName", {})
        usage = data.get("usage", {})
        taxon_author = data.get("taxonAuthor", {})

        # Get common names
        common_names_data = data.get("commonNameList", {})
        common_names_list = common_names_data.get("commonNames", [])
        common_names = []
        if isinstance(common_names_list, list):
            for cn in common_names_list:
                if cn and cn.get("commonName"):
                    common_names.append(
                        {
                            "name": cn.get("commonName"),
                            "language": cn.get("language"),
                        }
                    )

        # Get parent TSN
        parent_tsn_data = data.get("parentTSN", {})

        result = {
            "tsn": str(tsn),
            "scientific_name": sci_name.get("combinedName"),
            "kingdom": sci_name.get("kingdom"),
            "author": taxon_author.get("authorship"),
            "usage_rating": usage.get("taxonUsageRating"),
            "common_names": common_names,
            "parent_tsn": parent_tsn_data.get("parentTsn"),
            "rank": data.get("taxRank", {}).get("rankName"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ITIS",
                "query_tsn": str(tsn),
            },
        }
