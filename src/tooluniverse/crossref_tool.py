import requests
import urllib.parse
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool


def _requested_offset(response: requests.Response) -> int:
    """The `offset` Crossref was actually asked for, or 0.

    Read off the URL requests assembled for the request: `_process_response`
    is handed the endpoint template only (see BaseRESTTool.run), so the
    query params are not otherwise reachable from here. A missing or
    unparseable offset means the first page.

    The isinstance check is load-bearing, not defensive typing: tests stub
    the response with a MagicMock, whose `url` attribute is a truthy Mock
    rather than a string, and urlparse raises TypeError on it.
    """
    url = getattr(response, "url", None)
    if not isinstance(url, str):
        return 0
    try:
        query = urllib.parse.urlparse(url).query
        return int(urllib.parse.parse_qs(query).get("offset", ["0"])[0])
    except ValueError:
        return 0


# Crossref refuses offset + rows beyond this, answering HTTP 400 ("offset must
# be a positive integer less than or equal to 9998 ... Use the cursor parameter
# to page further"). Measured live: offset=9000 succeeds, offset=9999 does not.
# The truncation note must not advise a page that cannot be fetched.
_MAX_REACHABLE = 10000


def _truncation_fields(offset: int, shown: int, total: int) -> Dict[str, Any]:
    """The repo's disclosure vocabulary for "you are seeing part of a set".

    Named and module-level so the sentence has one home, and so `truncated`
    is always emitted alongside it -- a caller must never have to infer
    partiality by string-matching on prose.
    """
    end = offset + shown
    truncated = bool(shown) and end < total
    fields: Dict[str, Any] = {"truncated": truncated}
    if truncated:
        note = (
            f"Showing results {offset + 1}-{end} of {total} Crossref matches. "
            f"Re-run with offset={end} for the next page, or raise 'limit' "
            "(max 100)."
        )
        if total > _MAX_REACHABLE:
            note += (
                f" Note that Crossref caps offset+limit at {_MAX_REACHABLE}, so "
                f"only the first {_MAX_REACHABLE} of these {total} matches are "
                "reachable by paging -- narrow the search with 'filter' to get "
                "at the rest."
            )
        fields["truncation_note"] = note
    return fields


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
                # Fix-R60-1: `count` is the size of the returned page and was
                # the only number in the response, so with the documented
                # `limit` defaults (10 for works, 20 for funders/members) a
                # search of a million-work corpus came back looking like a
                # ten-work corpus. Crossref publishes the match total on
                # every list endpoint; it was simply being dropped. See
                # tests/unit/test_crossref_total_not_page_size.py for the
                # live figures. Purely additive: `count`, `data` and `url`
                # keep the values they always had.
                total = message.get("total-results")
                # bool is an int subclass; a JSON `true` here is not a total.
                if isinstance(total, int) and not isinstance(total, bool):
                    result["total_count"] = total
                    result.update(
                        _truncation_fields(
                            _requested_offset(response), len(items), total
                        )
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
