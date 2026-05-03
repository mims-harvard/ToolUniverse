# hgnc_tool.py
"""
HGNC (HUGO Gene Nomenclature Committee) REST API tool for ToolUniverse.

HGNC is the worldwide authority that assigns standardised nomenclature to
human genes. The REST API provides access to approved gene symbols, names,
aliases, chromosomal locations, and cross-references to external databases.

API: https://rest.genenames.org/
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

HGNC_BASE_URL = "https://rest.genenames.org"


@register_tool("HGNCTool")
class HGNCTool(BaseTool):
    """
    Tool for querying the HGNC gene nomenclature database.

    HGNC provides authoritative human gene naming. Supports fetching genes by
    symbol, HGNC ID, or searching by various fields including name, location,
    and aliases.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint_type = fields.get("endpoint", "search")
        self.default_search_field = fields.get("search_field")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HGNC API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HGNC API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HGNC API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HGNC API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying HGNC: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HGNC query and return structured results."""
        headers = {"Accept": "application/json"}

        if self.endpoint_type == "fetch":
            return self._fetch(arguments, headers)
        else:
            return self._search(arguments, headers)

    def _fetch(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Fetch a specific gene record by symbol or HGNC ID."""
        search_field = self.default_search_field

        if search_field == "symbol":
            value = arguments.get("symbol", "")
            if not value:
                return {"status": "error", "error": "symbol parameter is required"}
        elif search_field == "hgnc_id":
            value = arguments.get("hgnc_id", "")
            if not value:
                return {"status": "error", "error": "hgnc_id parameter is required"}
            # Ensure HGNC: prefix
            if not value.startswith("HGNC:"):
                value = f"HGNC:{value}"
        else:
            return {"status": "error", "error": f"Unknown fetch field: {search_field}"}

        url = f"{HGNC_BASE_URL}/fetch/{search_field}/{value}"
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        resp = data.get("response", {})
        docs = resp.get("docs", [])

        if not docs:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "source": "HGNC",
                    "query_field": search_field,
                    "query_value": value,
                    "num_found": 0,
                },
            }

        gene = docs[0]
        return {
            "status": "success",
            "data": gene,
            "metadata": {
                "source": "HGNC",
                "query_field": search_field,
                "query_value": value,
                "num_found": resp.get("numFound", len(docs)),
            },
        }

    def _search(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Search for genes by various criteria."""
        search_field = arguments.get("search_field", self.default_search_field)

        # Determine the query value
        query = arguments.get("query") or arguments.get("location", "")
        if not query:
            return {
                "status": "error",
                "error": "query or location parameter is required",
            }

        if search_field:
            url = f"{HGNC_BASE_URL}/search/{search_field}/{query}"
        else:
            url = f"{HGNC_BASE_URL}/search/{query}"

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        resp = data.get("response", {})
        docs = resp.get("docs", [])

        return {
            "status": "success",
            "data": docs,
            "metadata": {
                "source": "HGNC",
                "total_results": resp.get("numFound", len(docs)),
                "query": query,
                "query_location": arguments.get("location", query),
            },
        }
