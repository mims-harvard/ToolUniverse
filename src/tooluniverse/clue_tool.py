"""
CLUE.io (L1000 Connectivity Map) Tool

Provides access to the CLUE.io REST API for querying L1000 Connectivity Map data,
including perturbation signatures, gene expression profiles, and compound information.

API: https://api.clue.io/api/
Authentication: Requires CLUE_API_KEY environment variable (free key from clue.io).
"""

import json
import os

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

CLUE_BASE_URL = "https://api.clue.io/api"


@register_tool("ClueTool")
class ClueTool(BaseTool):
    """
    Tool for querying the CLUE.io L1000 Connectivity Map API.

    Provides access to:
    - Perturbation signatures (genetic and chemical)
    - Gene expression profiles
    - Cell line information
    - Compound/drug information
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CLUE.io API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_signatures": self._search_signatures,
            "get_perturbation": self._get_perturbation,
            "get_gene_expression": self._get_gene_expression,
            "get_cell_lines": self._get_cell_lines,
            "search_compounds": self._search_compounds,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "CLUE.io API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to CLUE.io API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        api_key = os.environ.get("CLUE_API_KEY")
        if api_key:
            headers["user_key"] = api_key
        return headers

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make GET request to CLUE.io API."""
        api_key = os.environ.get("CLUE_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "error": "CLUE_API_KEY environment variable not set. Get a free key at https://clue.io",
            }
        url = f"{CLUE_BASE_URL}/{endpoint}"
        response = requests.get(
            url, params=params or {}, headers=self._get_headers(), timeout=30
        )
        if response.status_code == 200:
            return {"ok": True, "data": response.json()}
        elif response.status_code == 401:
            return {
                "ok": False,
                "error": "CLUE.io API authentication failed. Check your CLUE_API_KEY.",
                "detail": response.text[:200],
            }
        else:
            return {
                "ok": False,
                "error": f"API request failed with status {response.status_code}",
                "detail": response.text[:500],
            }

    def _unwrap_list(self, data) -> list:
        """Extract the list payload from an API response that may be a list or a dict with a 'data' key."""
        return data if isinstance(data, list) else data.get("data", [])

    def _list_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Build a standard success response with unwrapped list data, or an error response."""
        if not result["ok"]:
            return {
                "status": "error",
                "error": result["error"],
                "detail": result.get("detail", ""),
            }
        items = self._unwrap_list(result["data"])
        return {"status": "success", "data": items, "num_results": len(items)}

    def _search_signatures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search L1000 perturbation signatures."""
        pert_type = arguments.get("pert_type")
        pert_iname = arguments.get("pert_iname")
        limit = arguments.get("limit", 50)

        where_clause = {}
        if pert_type:
            where_clause["pert_type"] = pert_type
        if pert_iname:
            where_clause["pert_iname"] = {"like": f"%{pert_iname}%"}

        params = {"limit": limit}
        if where_clause:
            params["where"] = json.dumps(where_clause)

        return self._list_response(self._make_request("perts", params))

    def _get_perturbation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get perturbation details by ID or name."""
        pert_id = arguments.get("pert_id")
        pert_iname = arguments.get("pert_iname")

        if not pert_id and not pert_iname:
            return {
                "status": "error",
                "error": "Either pert_id or pert_iname is required",
            }

        if pert_id:
            result = self._make_request(f"perts/{pert_id}")
            if not result["ok"]:
                return {
                    "status": "error",
                    "error": result["error"],
                    "detail": result.get("detail", ""),
                }
            return {"status": "success", "data": result["data"]}

        params = {"where": json.dumps({"pert_iname": pert_iname}), "limit": 10}
        return self._list_response(self._make_request("perts", params))

    def _get_gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information from L1000."""
        gene_symbol = arguments.get("gene_symbol")
        limit = arguments.get("limit", 50)

        params = {"limit": limit}
        if gene_symbol:
            params["where"] = json.dumps({"pr_gene_symbol": gene_symbol})

        return self._list_response(self._make_request("genes", params))

    def _get_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cell line information from L1000."""
        cell_id = arguments.get("cell_id")
        limit = arguments.get("limit", 50)

        params = {"limit": limit}
        if cell_id:
            params["where"] = json.dumps({"cell_id": cell_id})

        return self._list_response(self._make_request("cells", params))

    def _search_compounds(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search chemical compounds in L1000."""
        pert_iname = arguments.get("pert_iname")
        moa = arguments.get("moa")
        limit = arguments.get("limit", 50)

        where_clause = {"pert_type": "trt_cp"}
        if pert_iname:
            where_clause["pert_iname"] = {"like": f"%{pert_iname}%"}
        if moa:
            where_clause["moa"] = {"like": f"%{moa}%"}

        params = {"where": json.dumps(where_clause), "limit": limit}
        return self._list_response(self._make_request("perts", params))
