"""Figshare tools.

Figshare's ``GET /v2/articles`` ignores ``search_for`` (every query lists the same
newest articles, and a nonsense string matches as many as a real word); text search
only works as ``POST /v2/articles/search`` with a JSON body. ``BaseRESTTool`` issues
GET requests only, so search tools mark themselves with ``fields.http_method: POST``
and are sent that way; everything else behaves exactly like ``BaseRESTTool``.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("FigshareRESTTool")
class FigshareRESTTool(BaseRESTTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fields = self.tool_config.get("fields", {})
        if str(fields.get("http_method", "GET")).upper() != "POST":
            return super().run(arguments)

        url = fields["endpoint"]
        body = {k: v for k, v in arguments.items() if v is not None}
        for key, prop in self.tool_config["parameter"]["properties"].items():
            if key not in body and prop.get("default") is not None:
                body[key] = prop["default"]
        try:
            response = request_with_retry(
                self.session,
                "POST",
                url,
                json=body,
                headers=dict(fields.get("headers") or {}),
                timeout=self.timeout,
                max_attempts=3,
            )
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
        return self._process_response(response, url)
