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
        offset = arguments.get("offset")
        cursor = arguments.get("cursor", "*")
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 100",
                "parameter": "limit",
            }
        if offset is not None and (
            isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
        ):
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        if not isinstance(cursor, str) or not cursor:
            return {
                "status": "error",
                "error": "cursor must be '*' or a non-empty cursor returned by Crossref",
                "parameter": "cursor",
            }
        # Crossref pages either by offset or by cursor, not both.
        if offset is not None and cursor != "*":
            return {
                "status": "error",
                "error": "Pass either offset or cursor, not both",
                "parameter": "cursor",
            }
        arguments["limit"] = limit
        arguments["cursor"] = None if offset is not None else cursor
        result = super().run(arguments)
        if result.get("status") != "success":
            return result

        metadata = result.setdefault("metadata", {})
        total = metadata.get("total_results")
        returned = result.get("count", 0)
        next_cursor = metadata.get("upstream_next_cursor")
        first_page = cursor == "*" and not offset
        if offset is not None and isinstance(total, int):
            has_more = offset + returned < total
        elif cursor == "*" and isinstance(total, int):
            has_more = returned < total
        else:
            has_more = returned == limit and bool(next_cursor)
        metadata.update(
            {
                "returned": returned,
                "limit": limit,
                "total_results_is_exact": isinstance(total, int),
                "has_more": has_more,
                "next_cursor": next_cursor if has_more and offset is None else None,
                "result_set_complete": first_page
                and isinstance(total, int)
                and returned == total,
            }
        )
        if offset is not None:
            metadata["offset"] = offset
            metadata["next_offset"] = offset + returned if has_more else None
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
                next_cursor = message.get("next-cursor")
                if total is not None or next_cursor is not None:
                    result["metadata"] = {
                        "total_results": total
                        if isinstance(total, int) and not isinstance(total, bool)
                        else None,
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
