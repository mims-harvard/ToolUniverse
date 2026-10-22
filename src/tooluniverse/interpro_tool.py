import requests
from typing import Any, Dict
from urllib.parse import parse_qs, quote, urlparse
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("InterProRESTTool")
class InterProRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/interpro/api"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments.

        Applies schema defaults for any template placeholders not in args.
        """
        url = self.tool_config["fields"]["endpoint"]
        # Merge schema defaults for any missing template parameters
        merged = dict(args)
        props = self.tool_config.get("parameter", {}).get("properties", {})
        for k, schema in props.items():
            if k not in merged and "default" in schema:
                merged[k] = schema["default"]
        for k, v in merged.items():
            url = url.replace(f"{{{k}}}", str(v))
        return url

    def _extract_data(self, data: Dict, extract_path: str = None) -> Any:
        """Extract specific data from API response"""
        if not extract_path:
            return data

        # Handle specific InterPro extraction patterns
        if extract_path == "results":
            return data.get("results", [])
        elif extract_path == "count":
            return data.get("count", 0)
        elif extract_path == "metadata":
            return data.get("metadata", {})

        return data

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterPro API call"""
        url = ""
        try:
            url = self._build_url(arguments)
            cursor = arguments.get("cursor")
            if cursor:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}cursor={quote(str(cursor), safe='')}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            extract_path = self.tool_config["fields"].get("extract_path")
            if extract_path:
                result = self._extract_data(data, extract_path)
            else:
                result = data

            page_count = len(result) if isinstance(result, list) else 1
            total_count = (
                data.get("count", page_count) if isinstance(data, dict) else page_count
            )
            next_url = data.get("next") if isinstance(data, dict) else None
            previous_url = data.get("previous") if isinstance(data, dict) else None

            def cursor_from_url(page_url: str | None) -> str | None:
                if not page_url:
                    return None
                return parse_qs(urlparse(page_url).query).get("cursor", [None])[0]

            return {
                "status": "success",
                "data": result,
                "url": url,
                "count": page_count,
                "metadata": {
                    "total_results": total_count,
                    "returned": page_count,
                    "has_more": bool(next_url),
                    "truncated": bool(next_url),
                    "next_cursor": cursor_from_url(next_url),
                    "previous_cursor": cursor_from_url(previous_url),
                    "next_url": next_url,
                    "previous_url": previous_url,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"InterPro API error: {str(e)}",
                "url": url,
            }
