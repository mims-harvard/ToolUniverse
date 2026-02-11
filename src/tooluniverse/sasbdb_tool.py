import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("SASBDBRESTTool")
class SASBDBRESTTool(BaseTool):
    """SASBDB API tool for small-angle scattering (SAXS/SANS) data."""

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build the full API URL, substituting path parameters."""
        url = self.tool_config["fields"]["endpoint"]
        for k, v in args.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _build_query_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Return query parameters (those not used as path parameters)."""
        endpoint = self.tool_config["fields"]["endpoint"]
        return {k: v for k, v in args.items() if f"{{{k}}}" not in endpoint and v is not None}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SASBDB API request."""
        url = None
        try:
            url = self._build_url(arguments)
            params = self._build_query_params(arguments)

            response = request_with_retry(
                self.session, "GET", url,
                params=params or None,
                timeout=self.timeout,
                max_attempts=3,
            )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "SASBDB API error",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }

            return {"status": "success", "data": response.json(), "url": url}

        except Exception as e:
            return {"status": "error", "error": f"SASBDB API error: {e}", "url": url}
