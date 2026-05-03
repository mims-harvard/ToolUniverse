"""
L1000FWD Tool

Provides access to the L1000FWD (L1000 Fireworks) API for Connectivity Map signature search.
L1000FWD enables querying LINCS L1000 chemical and genetic perturbation signatures
using a user-defined gene expression signature (up- and down-regulated genes).

API: https://maayanlab.cloud/L1000FWD/
No authentication required.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

L1000FWD_BASE_URL = "https://maayanlab.cloud/L1000FWD"


@register_tool("L1000FWDTool")
class L1000FWDTool(BaseTool):
    """
    Tool for querying the L1000FWD Connectivity Map API.

    Provides access to:
    - Signature search: find L1000 signatures similar or opposite to a user gene set
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the L1000FWD tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "sig_search": self._sig_search,
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
            return {"status": "error", "error": "L1000FWD API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to L1000FWD API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _sig_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search L1000 signatures similar or opposite to a gene expression signature."""
        up_genes = arguments.get("up_genes", [])
        down_genes = arguments.get("down_genes", [])
        n_results = arguments.get("n_results", 10)
        mode = arguments.get("mode", "similar")

        if not isinstance(up_genes, list):
            up_genes = list(up_genes)
        if not isinstance(down_genes, list):
            down_genes = list(down_genes)

        if not up_genes and not down_genes:
            return {
                "status": "error",
                "error": "At least one of up_genes or down_genes must be non-empty",
            }

        if mode not in ("similar", "opposite"):
            return {
                "status": "error",
                "error": f"Invalid mode '{mode}'. Must be 'similar' or 'opposite'.",
            }

        payload = {"up_genes": up_genes, "down_genes": down_genes}
        post_resp = requests.post(
            f"{L1000FWD_BASE_URL}/sig_search",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if post_resp.status_code != 200:
            return {
                "status": "error",
                "error": (
                    f"L1000FWD sig_search POST failed with status {post_resp.status_code}: "
                    f"{post_resp.text[:300]}"
                ),
            }

        post_data = post_resp.json()
        result_id = post_data.get("result_id")
        if not result_id:
            return {
                "status": "error",
                "error": f"L1000FWD did not return a result_id. Response: {post_data}",
            }

        get_resp = requests.get(
            f"{L1000FWD_BASE_URL}/result/topn/{result_id}", timeout=60
        )

        if get_resp.status_code != 200:
            return {
                "status": "error",
                "error": (
                    f"L1000FWD result retrieval failed with status {get_resp.status_code}: "
                    f"{get_resp.text[:300]}"
                ),
            }

        results_data = get_resp.json()
        hits: List[Dict] = results_data.get(mode, [])[:n_results]

        return {
            "status": "success",
            "data": hits,
            "result_id": result_id,
            "mode": mode,
            "n_results": len(hits),
        }
