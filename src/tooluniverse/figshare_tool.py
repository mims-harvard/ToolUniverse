"""Figshare tools.

Figshare's ``GET /v2/articles`` ignores ``search_for`` (every query lists the same
newest articles, and a nonsense string matches as many as a real word); text search
only works as ``POST /v2/articles/search`` with a JSON body. ``BaseRESTTool`` issues
GET requests only, so search tools mark themselves with ``fields.http_method: POST``
and are sent that way; everything else behaves exactly like ``BaseRESTTool``.

The search endpoint returns a bare list with no total, so a POST search validates
its page inputs locally and reports truthful page metadata (``has_more``,
``next_page``, ``matches_lower_bound``) instead of a page that looks complete.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("FigshareRESTTool")
class FigshareRESTTool(BaseRESTTool):
    @staticmethod
    def _validate_page(value: Any, name: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{name} must be an integer between {minimum} and {maximum}"
            )
        if not minimum <= value <= maximum:
            raise ValueError(
                f"{name} must be an integer between {minimum} and {maximum}"
            )
        return value

    def _post(self, url: str, body: Dict[str, Any], headers: Dict[str, Any]):
        return request_with_retry(
            self.session,
            "POST",
            url,
            json=body,
            headers=headers,
            timeout=self.timeout,
            max_attempts=3,
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.tool_config.get("fields", {})
        if str(fields.get("http_method", "GET")).upper() != "POST":
            return super().run(arguments)

        url = fields["endpoint"]
        body = {k: v for k, v in (arguments or {}).items() if v is not None}
        for key, prop in self.tool_config["parameter"]["properties"].items():
            if key not in body and prop.get("default") is not None:
                body[key] = prop["default"]

        paginated = "search_for" in self.tool_config["parameter"]["properties"]
        if paginated:
            query = body.get("search_for")
            if not isinstance(query, str) or not query.strip():
                return {
                    "status": "error",
                    "error": "search_for must be a non-empty string",
                    "parameter": "search_for",
                }
            body["search_for"] = query.strip()
            try:
                page = self._validate_page(body.get("page", 1), "page", 1, 1000000)
                page_size = self._validate_page(
                    body.get("page_size", 10), "page_size", 1, 1000
                )
            except ValueError as e:
                return {"status": "error", "error": str(e)}
            body.update({"page": page, "page_size": page_size})

        headers = dict(fields.get("headers") or {})
        try:
            response = self._post(url, body, headers)
        except Exception as e:
            return {
                "status": "error",
                "error": f"{self.api_name} request failed: {e}",
                "url": url,
            }
        if not (200 <= response.status_code < 300):
            return {
                "status": "error",
                "error": f"{self.api_name} API error",
                "url": url,
                "status_code": response.status_code,
                "detail": (response.text or "")[:500],
            }
        result = self._process_response(response, url)
        if not paginated or result.get("status") != "success":
            return result
        data = result.get("data")
        if not isinstance(data, list):
            return {
                "status": "error",
                "error": "Figshare search returned an unexpected non-list payload",
                "url": url,
            }

        # Figshare does not return a total. Probe the next page only when the
        # current page is full, using the same page_size so offsets stay exact.
        has_more = False
        if len(data) == page_size:
            try:
                probe = self._post(url, dict(body, page=page + 1), headers)
                if 200 <= probe.status_code < 300:
                    probe_data = probe.json()
                    has_more = isinstance(probe_data, list) and bool(probe_data)
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"{self.api_name} next-page check failed: {e}",
                    "url": url,
                }

        returned = len(data)
        result["metadata"] = {
            "query_applied": body["search_for"],
            "page": page,
            "page_size": page_size,
            "returned": returned,
            "total_results": None,
            "total_results_is_exact": False,
            "matches_lower_bound": (page - 1) * page_size
            + returned
            + (1 if has_more else 0),
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "result_set_complete": page == 1 and not has_more,
        }
        return result
