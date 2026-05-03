"""
DataCite REST tool with proper parameter mapping for the DataCite API.

The DataCite API uses hyphenated query parameter names (e.g., resource-type-id,
page[size]) which need mapping from the snake_case tool parameter names.
"""

import requests
from typing import Any, Dict
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


@register_tool("DataCiteRESTTool")
class DataCiteRESTTool(BaseRESTTool):
    """REST tool for DataCite API endpoints with custom parameter mapping."""

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map tool parameter names to DataCite API query parameter names."""
        return {
            "resource_type_general": "resource-type-id",
            "resource_type": "resource-type-id",
            "page_size": "page[size]",
            "page_number": "page[number]",
            "publisher": "publisher",
            "year": "published",
        }

    def _process_response(
        self, response: requests.Response, url: str
    ) -> Dict[str, Any]:
        """Process DataCite API response.

        For search endpoints: data is the list of items, meta has total.
        For single-item endpoints: data is the single record object.
        """
        raw = response.json()

        # Search endpoint returns {"data": [...], "meta": {...}}
        # Single-item endpoint returns {"data": {...}}
        items = raw.get("data", raw)
        meta = raw.get("meta", {})

        result = {
            "status": "success",
            "data": items,
            "url": url,
        }

        if meta:
            result["meta"] = meta
            result["total"] = meta.get("total", 0)

        if isinstance(items, list):
            result["count"] = len(items)

        return result
