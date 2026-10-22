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

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        paginated = self.tool_config.get("name") in {
            "Crossref_search_works",
            "Crossref_list_funders",
            "Crossref_search_members",
        }
        if not paginated:
            return super().run(arguments)

        arguments = dict(arguments or {})
        limit = arguments.get("limit", 10)
        cursor = arguments.get("cursor", "*")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 100",
                "parameter": "limit",
            }
        if not isinstance(cursor, str) or not cursor:
            return {
                "status": "error",
                "error": "cursor must be '*' or a non-empty cursor returned by Crossref",
                "parameter": "cursor",
            }
        arguments["limit"] = limit
        arguments["cursor"] = cursor
        result = super().run(arguments)
        if result.get("status") != "success":
            return result

        metadata = result.setdefault("metadata", {})
        total = metadata.get("total_results")
        returned = result.get("count", 0)
        next_cursor = metadata.get("upstream_next_cursor")
        if cursor == "*" and isinstance(total, int):
            has_more = returned < total
        else:
            has_more = returned == limit and bool(next_cursor)
        metadata.update(
            {
                "returned": returned,
                "limit": limit,
                "total_results_is_exact": isinstance(total, int),
                "has_more": has_more,
                "next_cursor": next_cursor if has_more else None,
                "result_set_complete": cursor == "*"
                and isinstance(total, int)
                and returned == total,
            }
        )
        metadata.pop("upstream_next_cursor", None)
        return result

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
                result = {
                    "status": "success",
                    "data": items,
                    "count": len(items),
                    "url": url,
                }
                total = message.get("total-results")
                next_cursor = message.get("next-cursor")
                if total is not None or next_cursor is not None:
                    result["metadata"] = {
                        "total_results": total if isinstance(total, int) else None,
                        "upstream_next_cursor": next_cursor,
                    }
                return result
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
