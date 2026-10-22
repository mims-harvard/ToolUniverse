"""World Bank tools.

The World Bank ``/v2/indicator`` endpoint has no text search: it ignores every
search parameter and lists the same first page of all 29,544 indicators (for "GDP"
that meant poverty rows from the LAC Equity Lab). The World Development Indicators
source (id 2) has only ~1,500 indicators, so the search tool downloads that catalog
once per process and matches the query against it here.
"""

import re
import threading
from typing import Any, Dict, List

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

WDI_URL = "https://api.worldbank.org/v2/sources/2/indicators"

_catalog: List[Dict[str, Any]] = []
_catalog_lock = threading.Lock()


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _score(indicator: Dict[str, Any], words: List[str], phrase: str):
    """Rank a match: every query word must occur; name hits outweigh description hits."""
    name = (indicator.get("name") or "").lower()
    code = (indicator.get("id") or "").lower()
    note = (indicator.get("sourceNote") or "").lower()
    score = 0
    for word in words:
        if word in _words(name) or word in code.split("."):
            score += 3
        elif word in name or word in code:
            score += 2
        elif word in note:
            score += 1
        else:
            return None
    if phrase and phrase in name:
        score += 5
        if name.startswith(phrase):
            score += 4
    return score


@register_tool("WorldBankIndicatorSearchTool")
class WorldBankIndicatorSearchTool(BaseRESTTool):
    def _wdi_catalog(self) -> List[Dict[str, Any]]:
        with _catalog_lock:
            if _catalog:
                return _catalog
            page, pages, found = 1, 1, []
            while page <= pages:
                response = request_with_retry(
                    self.session,
                    "GET",
                    WDI_URL,
                    params={"format": "json", "per_page": 1000, "page": page},
                    timeout=self.timeout,
                    max_attempts=3,
                )
                response.raise_for_status()
                envelope = response.json()
                pages = int(envelope[0].get("pages") or 1)
                found.extend(envelope[1] or [])
                page += 1
            _catalog.extend(found)
            return _catalog

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "error",
                "error": "query is required (e.g. 'GDP').",
                "parameter": "query",
            }
        query = query.strip()
        limit = arguments.get("per_page")
        if limit is None:
            limit = 10
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "per_page must be an integer between 1 and 1000",
                "parameter": "per_page",
            }
        offset = arguments.get("offset")
        if offset is None:
            offset = 0
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        try:
            catalog = self._wdi_catalog()
        except Exception as e:
            return {
                "status": "error",
                "error": f"{self.api_name} request failed: {e}",
                "url": WDI_URL,
            }

        words, phrase = _words(query), " ".join(_words(query))
        scored = []
        for indicator in catalog:
            score = _score(indicator, words, phrase)
            if score is not None:
                scored.append((-score, len(indicator.get("name") or ""), indicator))
        scored.sort(key=lambda row: row[:2])
        items = [row[2] for row in scored[offset : offset + limit]]
        total = len(scored)
        returned = len(items)
        has_more = offset + returned < total
        meta = {
            "page": offset // limit + 1,
            "pages": (total + limit - 1) // limit,
            "per_page": str(limit),
            "total": total,
            "offset": offset,
            "catalog": "World Development Indicators (source 2)",
        }
        return {
            "status": "success",
            "data": [meta, items],
            "url": WDI_URL,
            "count": returned,
            "metadata": {
                "returned": returned,
                "total_results": total,
                # Every catalog page is downloaded, so the match count is exact.
                "total_results_is_exact": True,
                "offset": offset,
                "per_page": limit,
                "has_more": has_more,
                "next_offset": offset + returned if returned and has_more else None,
                "truncated": offset > 0 or has_more,
                "result_set_complete": offset == 0 and not has_more,
                "pagination_scope": "client_filtered_wdi_catalog",
            },
        }
