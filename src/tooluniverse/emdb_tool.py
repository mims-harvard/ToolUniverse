import requests
from typing import Any, Dict, Tuple
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("EMDBRESTTool")
class EMDBRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/emdb/api"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Substitute `{placeholder}` tokens in the endpoint template.

        Fix-R18A-1: args with no matching `{placeholder}` (e.g.
        EMDB_search_structures's `rows`) were silently dropped -- there was
        no query-string fallback, so `rows` had zero effect on the request
        regardless of value (confirmed live: rows=2 and rows=10 both
        returned the same 10 results; the raw EMDB API honors `?rows=N` as
        a query param). Return them separately so the caller can pass them
        through as query params instead.
        """
        url = self.tool_config["fields"]["endpoint"]
        query_params = {}
        for k, v in args.items():
            token = f"{{{k}}}"
            if token in url:
                url = url.replace(token, str(v))
            else:
                query_params[k] = v
        return url, query_params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        try:
            url, query_params = self._build_url(arguments)
            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=query_params,
                timeout=self.timeout,
                max_attempts=3,
            )
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "EMDB API error",
                    "url": url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }
            data = response.json()
            return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {
                "status": "error",
                "error": f"EMDB API error: {str(e)}",
                "url": url,
            }
