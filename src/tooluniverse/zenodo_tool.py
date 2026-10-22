import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("ZenodoRESTTool")
class ZenodoRESTTool(BaseRESTTool):
    """Generic REST tool for Zenodo API endpoints."""

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map Zenodo-specific parameter names."""
        return {
            "query": "q",  # query -> q
            "limit": "size",  # limit -> size
            "community": "communities",  # community -> communities
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.tool_config.get("name") != "Zenodo_search_records":
            return super().run(arguments)

        arguments = dict(arguments or {})
        limit = arguments.get("limit", 10)
        page = arguments.get("page", 1)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 200",
                "parameter": "limit",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be a positive integer",
                "parameter": "page",
            }
        arguments["limit"] = limit
        arguments["page"] = page
        result = super().run(arguments)
        if result.get("status") != "success":
            return result

        data = result.get("data") or {}
        hits_block = data.get("hits") or {} if isinstance(data, dict) else {}
        hits = hits_block.get("hits") or [] if isinstance(hits_block, dict) else []
        total = hits_block.get("total") if isinstance(hits_block, dict) else None
        if isinstance(total, dict):
            total = total.get("value")
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)
        returned = len(hits) if isinstance(hits, list) else 0
        links = data.get("links") or {} if isinstance(data, dict) else {}
        has_more = bool(links.get("next"))
        if total_is_exact:
            has_more = page * limit < total
        result["metadata"] = {
            "page": page,
            "limit": limit,
            "returned": returned,
            "total_results": total if total_is_exact else None,
            "total_results_is_exact": total_is_exact,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "result_set_complete": page == 1
            and total_is_exact
            and returned == total,
        }
        return result

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Process Zenodo API response with search result handling."""
        data = response.json()

        # Handle extract_path for nested data (e.g., files from record)
        extract_path = self.tool_config.get("fields", {}).get("extract_path")
        if extract_path and isinstance(data, dict):
            data = data.get(extract_path, data)

        # Build result
        result = {
            "status": "success",
            "data": data,
            "url": url,
        }

        # Add count - handle both list and search results
        if isinstance(data, list):
            result["count"] = len(data)
        elif isinstance(data, dict) and "hits" in data:
            # For search results
            result["count"] = len(data.get("hits", {}).get("hits", []))

        return result
