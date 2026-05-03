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
