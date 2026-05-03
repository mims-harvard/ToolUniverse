import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool


def _http_get(
    url: str, headers: Dict[str, str] | None = None, timeout: int = 30
) -> Dict[str, Any]:
    # WikiPathways API requires User-Agent header to avoid 403 Forbidden
    default_headers = {"User-Agent": "ToolUniverse/1.0"}
    if headers:
        default_headers.update(headers)
    req = Request(url, headers=default_headers)
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        try:
            return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": data.decode("utf-8", errors="ignore")}


@register_tool(
    "WikiPathwaysSearchTool",
    config={
        "name": "WikiPathways_search",
        "type": "WikiPathwaysSearchTool",
        "description": "Search pathways by text via WikiPathways",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search, e.g., p53"},
                "organism": {"type": "string", "description": "Optional organism"},
            },
            "required": ["query"],
        },
        "settings": {"base_url": "https://webservice.wikipathways.org", "timeout": 30},
    },
)
class WikiPathwaysSearchTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://webservice.wikipathways.org"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query = {"query": arguments.get("query", ""), "format": "json"}
        if arguments.get("organism"):
            query["organism"] = arguments.get("organism")
        url = f"{base}/findPathwaysByText?{urlencode(query)}"
        try:
            api_data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "data": api_data,
                "url": url,
            }
        except Exception as e:
            return {
                "status": "error",
                "data": {"error": str(e)},
                "url": url,
            }


@register_tool(
    "WikiPathwaysGetTool",
    config={
        "name": "WikiPathways_get_pathway",
        "type": "WikiPathwaysGetTool",
        "description": "Get pathway by WPID",
        "parameter": {
            "type": "object",
            "properties": {
                "wpid": {"type": "string", "description": "Pathway ID, e.g., WP254"},
                "format": {
                    "type": "string",
                    "enum": ["json", "gpml"],
                    "default": "json",
                },
            },
            "required": ["wpid"],
        },
        "settings": {"base_url": "https://webservice.wikipathways.org", "timeout": 30},
    },
)
class WikiPathwaysGetTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://webservice.wikipathways.org"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        fmt = arguments.get("format", "json")
        query = {"pwId": arguments.get("wpid"), "format": fmt}
        url = f"{base}/getPathway?{urlencode(query)}"
        try:
            headers = {"Accept": "application/json"} if fmt == "json" else {}
            api_data = _http_get(url, headers=headers, timeout=timeout)
            return {
                "status": "success",
                "data": api_data,
                "url": url,
            }
        except Exception as e:
            return {
                "status": "error",
                "data": {"error": str(e)},
                "url": url,
            }
