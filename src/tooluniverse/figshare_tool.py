"""Figshare public article search with truthful keyword and page handling."""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("FigshareTool")
class FigshareTool(BaseTool):
    """Use Figshare's POST search endpoint instead of the unfiltered GET listing."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        self.session = requests.Session()
        self.timeout = 30

    @staticmethod
    def _validate_page(value: Any, name: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
        return value

    def _post(self, body: Dict[str, Any]) -> requests.Response:
        return request_with_retry(
            self.session,
            "POST",
            self.endpoint,
            json=body,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
            max_attempts=3,
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            arguments = dict(arguments or {})
            query = arguments.get("search_for")
            if not isinstance(query, str) or not query.strip():
                return {
                    "status": "error",
                    "error": "search_for must be a non-empty string",
                    "parameter": "search_for",
                }
            page = self._validate_page(arguments.get("page", 1), "page", 1, 1000000)
            page_size = self._validate_page(
                arguments.get("page_size", 10), "page_size", 1, 1000
            )
            body = {
                key: value
                for key, value in arguments.items()
                if key in {"search_for", "item_type", "published_since"}
                and value is not None
            }
            body["search_for"] = query.strip()
            body.update({"page": page, "page_size": page_size})

            response = self._post(body)
            if not 200 <= response.status_code < 300:
                return {
                    "status": "error",
                    "error": "Figshare search API error",
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }
            data = response.json()
            if not isinstance(data, list):
                return {
                    "status": "error",
                    "error": "Figshare search returned an unexpected non-list payload",
                }

            # Figshare does not return a total. Probe the next page only when the
            # current page is full, using the same page_size so offsets stay exact.
            has_more = False
            if len(data) == page_size:
                probe_body = dict(body)
                probe_body["page"] = page + 1
                probe = self._post(probe_body)
                if 200 <= probe.status_code < 300:
                    probe_data = probe.json()
                    has_more = isinstance(probe_data, list) and bool(probe_data)

            returned = len(data)
            lower_bound = (page - 1) * page_size + returned + (1 if has_more else 0)
            return {
                "status": "success",
                "data": data,
                "url": self.endpoint,
                "count": returned,
                "metadata": {
                    "query_applied": query.strip(),
                    "page": page,
                    "page_size": page_size,
                    "returned": returned,
                    "total_results": None,
                    "total_results_is_exact": False,
                    "matches_lower_bound": lower_bound,
                    "has_more": has_more,
                    "next_page": page + 1 if has_more else None,
                    "result_set_complete": page == 1 and not has_more,
                },
            }
        except Exception as exc:
            return {"status": "error", "error": f"Figshare search API error: {exc}"}
