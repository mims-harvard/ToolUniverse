import requests
import urllib.parse
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


def _requested_offset(response: requests.Response) -> int:
    """The `offset` Crossref was actually asked for, or 0.

    Read off the URL requests assembled for the request, so it cannot drift
    from what was sent. A missing or unparseable offset means the first page.
    """
    try:
        query = urllib.parse.urlparse(getattr(response, "url", "") or "").query
        return int(urllib.parse.parse_qs(query).get("offset", ["0"])[0])
    except (ValueError, TypeError):
        return 0


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
                result = {
                    "status": "success",
                    "data": items,
                    "count": len(items),
                    "url": url,
                }
                # Fix-R60-1: `count` is the size of the returned page, and it
                # was the only number in the response -- so with the documented
                # `limit` defaults (10 for works, 20 for funders/members) a
                # search of a million-work corpus came back looking like a
                # ten-work corpus. Confirmed live: `Crossref_search_works
                # {"query": "CRISPR gene editing", "limit": 3}` reported
                # `count: 3` while Crossref's own `total-results` for that
                # query was 1037333; `Crossref_search_members {"query":
                # "university"}` reported the page against a true 4032.
                # Crossref publishes the match total on every list endpoint,
                # and it was simply being dropped here. Report it, and say so
                # when the page is only part of it. Purely additive: `count`,
                # `data` and `url` keep the values they always had.
                total = message.get("total-results")
                # bool is an int subclass; a JSON `true` here is not a total.
                if isinstance(total, int) and not isinstance(total, bool):
                    result["total_count"] = total
                    offset = _requested_offset(response)
                    end = offset + len(items)
                    if items and end < total:
                        result["note"] = (
                            f"Showing results {offset + 1}-{end} of {total} "
                            f"Crossref matches. Re-run with offset={end} for "
                            "the next page, or raise 'limit' (max 100)."
                        )
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
