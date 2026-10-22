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

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate DataCite pagination and expose its 10k search window."""
        is_search = self.tool_config.get("name") in {
            "DataCite_search_dois",
            "DataCite_search_datasets",
        }
        if not is_search:
            return super().run(arguments)

        props = self.tool_config.get("parameter", {}).get("properties", {})
        page_size = arguments.get(
            "page_size", props.get("page_size", {}).get("default", 10)
        )
        page_number = arguments.get(
            "page_number", props.get("page_number", {}).get("default", 1)
        )
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 1000
        ):
            return {
                "status": "error",
                "error": "page_size must be an integer between 1 and 1000",
                "parameter": "page_size",
            }
        if (
            isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or page_number < 1
        ):
            return {
                "status": "error",
                "error": "page_number must be an integer greater than or equal to 1",
                "parameter": "page_number",
            }

        normalized = dict(arguments)
        normalized["page_size"] = page_size
        normalized["page_number"] = page_number
        result = super().run(normalized)
        if result.get("status") != "success":
            return result

        records = result.get("data")
        if not isinstance(records, list):
            records = []
        meta = result.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        total = meta.get("total")
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)
        upstream_page = meta.get("page")
        page = (
            upstream_page
            if isinstance(upstream_page, int) and not isinstance(upstream_page, bool)
            else page_number
        )
        upstream_pages = meta.get("totalPages")
        pages_known = isinstance(upstream_pages, int) and not isinstance(
            upstream_pages, bool
        )
        accessible = (
            min(total, upstream_pages * page_size)
            if total_is_exact and pages_known
            else None
        )
        returned = len(records)
        has_more = bool(pages_known and returned and page < upstream_pages)
        upstream_truncated = bool(
            total_is_exact and accessible is not None and accessible < total
        )
        result["metadata"] = {
            "returned": returned,
            "total_results": total if total_is_exact else None,
            "total_results_is_exact": total_is_exact,
            "accessible_results": accessible,
            "accessible_pages": upstream_pages if pages_known else None,
            "upstream_truncated": upstream_truncated,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "truncated": page > 1 or has_more or upstream_truncated,
            "result_set_complete": bool(
                total_is_exact and page == 1 and returned == total
            ),
            "pagination_scope": "datacite_jsonapi_10000_result_window",
            "warning": (
                "DataCite matched more records than its approximately 10,000-record "
                "deep-pagination window exposes. Refine the query or add filters to "
                "reach records outside accessible_results."
                if upstream_truncated
                else None
            ),
        }
        return result
