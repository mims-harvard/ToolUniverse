import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool


def _http_get(
    url: str,
    headers: Dict[str, str] | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        try:
            return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": data.decode("utf-8", errors="ignore")}


@register_tool(
    "GBIFTool",
    config={
        "name": "GBIF_search_species",
        "type": "GBIFTool",
        "description": "Search species via GBIF species/search",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query keyword, e.g., Homo",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 300,
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                },
            },
            "required": ["query"],
        },
        "settings": {
            "base_url": "https://api.gbif.org/v1",
            "timeout": 30,
        },
    },
)
class GBIFTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gbif.org/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))
        query_text = arguments.get("query")
        limit = int(arguments.get("limit", 10))
        offset = int(arguments.get("offset", 0))

        query = {"q": query_text, "limit": limit, "offset": offset}
        url = f"{base}/species/search?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GBIF",
                "endpoint": "species/search",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GBIF",
                "endpoint": "species/search",
                "success": False,
            }


@register_tool(
    "GBIFOccurrenceTool",
    config={
        "name": "GBIF_search_occurrences",
        "type": "GBIFOccurrenceTool",
        "description": "Search occurrences via GBIF occurrence/search",
        "parameter": {
            "type": "object",
            "properties": {
                "taxonKey": {
                    "type": "integer",
                    "description": "GBIF taxonKey filter",
                },
                "country": {
                    "type": "string",
                    "description": "Country code, e.g., US",
                },
                "hasCoordinate": {"type": "boolean", "default": True},
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 300,
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                },
            },
        },
        "settings": {
            "base_url": "https://api.gbif.org/v1",
            "timeout": 30,
        },
    },
)
class GBIFOccurrenceTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.gbif.org/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query = {}
        for key in ("taxonKey", "country", "hasCoordinate", "limit", "offset"):
            if key in arguments and arguments[key] is not None:
                query[key] = arguments[key]

        if "limit" not in query:
            query["limit"] = 10
        if "offset" not in query:
            query["offset"] = 0

        url = f"{base}/occurrence/search?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "GBIF",
                "endpoint": "occurrence/search",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GBIF",
                "endpoint": "occurrence/search",
                "success": False,
            }
