import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("CrossrefRESTTool")
class CrossrefRESTTool(BaseRESTTool):
    """Generic REST tool for Crossref API endpoints."""

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map Crossref-specific parameter names."""
        return {
            "limit": "rows",  # limit -> rows
            # query uses its original name
        }

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Process Crossref API response, extracting message wrapper."""
        data = response.json()

        # Crossref wraps responses in a "message" field
        if isinstance(data, dict) and "message" in data:
            message = data["message"]

            # For list endpoints, extract items from message
            if isinstance(message, dict) and "items" in message:
                items = message.get("items", [])
                return {
                    "status": "success",
                    "data": items,
                    "count": len(items),
                    "url": url,
                }
            else:
                # For detail endpoints, return the message directly
                return {
                    "status": "success",
                    "data": message,
                    "url": url,
                }

        # Fallback if no message wrapper
        return {
            "status": "success",
            "data": data,
            "url": url,
        }
