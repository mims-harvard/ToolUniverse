# panelapp_tool.py
"""PanelApp panel search tool for ToolUniverse.

PanelApp's `/panels/` endpoint silently ignores substring search params --
confirmed live: `search=`, `q=`, and `name__icontains=` all return the
unfiltered, unranked list of all 434 panels regardless of value; only an
exact full-string `name=` match filters anything (its OpenAPI schema
documents no search param at all, only `type` and `page`). Since the API
can't filter server-side, this fetches every panel (paginating the
API's fixed page_size=100) and filters client-side by substring match
against name/disease_group/disease_sub_group.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

PANELS_URL = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"
_MAX_PAGES = 10  # safety cap; ~434 panels / 100 per page = 5 pages today


@register_tool("PanelAppSearchTool")
class PanelAppSearchTool(BaseRESTTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search = (arguments.get("search") or "").strip().lower()
        if not search:
            return {"status": "error", "error": "'search' is required"}

        panels = []
        url = PANELS_URL
        params = {"format": "json"}
        for _ in range(_MAX_PAGES):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                page = resp.json()
            except Exception as e:
                return {"status": "error", "error": f"PanelApp API error: {e}"}
            panels.extend(page.get("results", []))
            url = page.get("next")
            params = None  # `next` already includes all query params
            if not url:
                break

        def matches(p: Dict[str, Any]) -> bool:
            haystack = " ".join(
                str(p.get(k) or "")
                for k in ("name", "disease_group", "disease_sub_group")
            ).lower()
            return search in haystack

        results = [p for p in panels if matches(p)]
        return {
            "status": "success",
            "data": {
                "count": len(results),
                "next": None,
                "previous": None,
                "results": results,
            },
            "metadata": {
                "query": arguments.get("search"),
                "total_panels_searched": len(panels),
                "note": (
                    "PanelApp's API has no server-side search filter, so this "
                    "matches client-side against name/disease_group/"
                    "disease_sub_group across all panels."
                ),
            },
        }
