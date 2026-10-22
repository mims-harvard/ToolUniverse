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
        query_params = dict(self.tool_config.get("fields", {}).get("params", {}))
        param_mapping = self.tool_config.get("fields", {}).get("param_mapping", {})
        for k, v in args.items():
            token = f"{{{k}}}"
            if token in url:
                url = url.replace(token, str(v))
            else:
                query_params[param_mapping.get(k, k)] = v
        return url, query_params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = None
        try:
            if self.tool_config.get("fields", {}).get("pagination") == "ebi_search_start":
                rows = arguments.get("rows", 10)
                start = arguments.get("start", 0)
                if (
                    isinstance(rows, bool)
                    or not isinstance(rows, int)
                    or not 1 <= rows <= 100
                ):
                    return {
                        "status": "error",
                        "error": "rows must be an integer between 1 and 100",
                        "parameter": "rows",
                    }
                if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                    return {
                        "status": "error",
                        "error": "start must be a non-negative integer",
                        "parameter": "start",
                    }
                arguments = dict(arguments)
                arguments["rows"] = rows
                arguments["start"] = start
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
            result = {"status": "success", "data": data, "url": url}
            if self.tool_config.get("fields", {}).get("pagination") == "ebi_search_start":
                entries = data.get("entries", []) if isinstance(data, dict) else []
                if not isinstance(entries, list):
                    entries = []
                total = data.get("hitCount") if isinstance(data, dict) else None
                total_is_exact = isinstance(total, int) and not isinstance(total, bool)
                returned = len(entries)
                start = arguments["start"]
                rows = arguments["rows"]
                has_more = bool(total_is_exact and returned and start + returned < total)
                stalled = bool(total_is_exact and not returned and start < total)
                result["metadata"] = {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "start": start,
                    "rows": rows,
                    "has_more": has_more,
                    "next_start": start + returned if has_more else None,
                    "truncated": start > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and start == 0 and returned == total
                    ),
                    "pagination_stalled": stalled,
                    "pagination_scope": "ebi_search_emdb_start_hit_count",
                    "warning": (
                        "EBI Search reported additional EMDB entries but returned an empty page at this start."
                        if stalled
                        else None
                    ),
                }
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": f"EMDB API error: {str(e)}",
                "url": url,
            }
