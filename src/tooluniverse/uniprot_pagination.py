"""Shared pagination helpers for UniProt REST collection endpoints."""

import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


def next_cursor(response: Any) -> Optional[str]:
    """Return UniProt's opaque next-page cursor from the Link header."""

    headers = getattr(response, "headers", {})
    link = headers.get("Link", "")
    if not isinstance(link, str):
        return None
    match = re.search(r'<([^>]+)>;\s*rel="next"', link)
    if not match:
        return None
    return parse_qs(urlparse(match.group(1)).query).get("cursor", [None])[0]


def pagination_metadata(response: Any, returned: int) -> Dict[str, Any]:
    """Build honest paging metadata from official UniProt response headers."""

    headers = getattr(response, "headers", {})
    raw_total = headers.get("x-total-results")
    try:
        total = (
            int(raw_total)
            if isinstance(raw_total, (str, int)) and not isinstance(raw_total, bool)
            else None
        )
    except (TypeError, ValueError):
        total = None
    cursor = next_cursor(response)
    return {
        "total_results": total,
        "returned": returned,
        "has_more": bool(cursor),
        "truncated": bool(cursor),
        "next_cursor": cursor,
    }
