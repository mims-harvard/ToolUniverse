"""DailyMed drug classes, searchable by name.

The upstream endpoint cannot filter. `/drugclasses.json` accepts only `page`
and `pagesize`: `drug_class_name`, `class_name` and `code` each make it answer
HTTP 500 with the body `{"data": [], "metadata": {}}`, and `drug_name` and
`name` are accepted but ignored -- the response still carries all 1210 classes.
The generic REST tool passed `drug_class_name` straight through, so every
search this tool advertised returned that 500.

So the filtering happens here. The whole list is small and fixed-size: 1210
classes over 13 pages, because DailyMed caps a page at 100 however large a
`pagesize` is asked for (measured: pagesize=2000 still returns 100). Fetching
it costs 13 requests per call, which is the price of the filter the tool
advertises; `drug_class_name` is a required parameter, so there is no
unfiltered path to keep cheap.
"""

from typing import Any, Dict, List, Optional

import requests

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

# DailyMed's own ceiling, not a choice: a larger pagesize is silently clamped.
_UPSTREAM_PAGE_SIZE = 100
# A guard, not an expectation. The catalogue is 13 pages today; this stops a
# changed upstream contract from turning one call into an unbounded crawl.
_MAX_PAGES = 40


@register_tool("DailyMedDrugClassesTool")
class DailyMedDrugClassesTool(BaseRESTTool):
    """DailyMed drug classes with the name filter applied client-side."""

    @property
    def _endpoint(self) -> str:
        return self.tool_config["fields"]["endpoint"]

    def _fetch_page(self, page: int) -> Optional[Dict[str, Any]]:
        # Go through the base class's pooled session and retry helper rather
        # than a bare requests.get, so these 13 calls share the transport pool
        # and the User-Agent with every other REST tool.
        try:
            response = request_with_retry(
                self.session,
                "GET",
                self._endpoint,
                params={"page": page, "pagesize": _UPSTREAM_PAGE_SIZE},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
                max_attempts=3,
            )
        except requests.exceptions.RequestException as exc:
            return {"error": f"DailyMed request failed: {exc}"}
        if response.status_code != 200:
            return {
                "error": (
                    f"DailyMed returned HTTP {response.status_code} for page {page}"
                )
            }
        try:
            return {"body": response.json()}
        except ValueError:
            return {"error": "DailyMed returned a response that is not JSON"}

    def _all_classes(self) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        page = 1
        while page <= _MAX_PAGES:
            fetched = self._fetch_page(page)
            if fetched is None or "error" in fetched:
                return {"error": (fetched or {}).get("error", "unknown error")}
            body = fetched["body"]
            rows.extend(body.get("data") or [])
            total_pages = (body.get("metadata") or {}).get("total_pages") or 1
            if page >= total_pages:
                return {"rows": rows, "pages_read": page}
            page += 1
        return {
            "error": (
                f"DailyMed reported more than {_MAX_PAGES} pages of drug classes; "
                "refusing to keep paging"
            )
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        needle = (arguments.get("drug_class_name") or "").strip()
        if not needle:
            # The schema makes drug_class_name required, so BaseTool rejects a
            # call without it before reaching here. Reported rather than
            # silently listing all 1210 classes, which is not what a caller
            # that passed an empty string asked for.
            return {
                "status": "error",
                "error": "drug_class_name is required and must not be empty",
                "url": self._endpoint,
            }

        fetched = self._all_classes()
        if "error" in fetched:
            return {
                "status": "error",
                "error": fetched["error"],
                "url": self._endpoint,
            }

        rows = fetched["rows"]
        lowered = needle.lower()
        matches = [r for r in rows if lowered in (r.get("name") or "").lower()]

        try:
            page = max(1, int(arguments.get("page") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(arguments.get("pagesize") or _UPSTREAM_PAGE_SIZE)
        except (TypeError, ValueError):
            page_size = _UPSTREAM_PAGE_SIZE
        page_size = max(1, page_size)

        start = (page - 1) * page_size
        window = matches[start : start + page_size]

        return {
            "status": "success",
            "data": window,
            "metadata": {
                "drug_class_name": needle,
                "total_matches": len(matches),
                "returned": len(window),
                "page": page,
                "pagesize": page_size,
                "classes_searched": len(rows),
                "upstream_pages_read": fetched["pages_read"],
                "filtered_by": (
                    "ToolUniverse, case-insensitive substring of the class name: "
                    "DailyMed's /drugclasses.json accepts only page and pagesize "
                    "and answers HTTP 500 to a name filter"
                ),
            },
            "url": self._endpoint,
        }
