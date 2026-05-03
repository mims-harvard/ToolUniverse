from typing import Dict, Any, List, Optional
import requests
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("BioModelsRESTTool")
class BioModelsRESTTool(BaseRESTTool):
    """Generic REST tool for BioModels API endpoints."""

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map BioModels-specific parameter names."""
        return {
            "limit": "numResults",  # limit -> numResults
            # query and filename use their original names
        }

    def _handle_special_endpoint(
        self, url: str, response: requests.Response, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle download endpoints specially."""
        if "download" in url:
            content_disposition = response.headers.get("Content-Disposition", "")
            content_type = response.headers.get("Content-Type", "")

            # Wrap in data field for schema validation
            return {
                "status": "success",
                "data": {
                    "download_url": url,
                    "filename": content_disposition,
                    "content_type": content_type,
                },
                "url": url,
            }
        return None

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Process BioModels API response."""
        data = response.json()

        # Build result
        result = {
            "status": "success",
            "data": data,
            "url": url,
        }

        # Add count for lists or search results
        if isinstance(data, list):
            result["count"] = len(data)
        elif isinstance(data, dict) and "matches" in data:
            # matches is an integer count, not a list
            result["count"] = data.get("matches", 0)

        return result
