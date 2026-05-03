import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool


def _http_get(
    url: str, headers: Dict[str, str] | None = None, timeout: int = 30
) -> Dict[str, Any]:
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        try:
            return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": data.decode("utf-8", errors="ignore")}


@register_tool(
    "RNAcentralSearchTool",
    config={
        "name": "RNAcentral_search",
        "type": "RNAcentralSearchTool",
        "description": "Search RNA records via RNAcentral API",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword or accession"},
                "page_size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["query"],
        },
        "settings": {"base_url": "https://rnacentral.org/api/v1", "timeout": 60},
    },
)
class RNAcentralSearchTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://rnacentral.org/api/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query = {
            "query": arguments.get("query"),
            "page_size": int(arguments.get("page_size", 10)),
        }
        url = f"{base}/rna/?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "RNAcentral",
                "endpoint": "rna",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "RNAcentral",
                "endpoint": "rna",
                "success": False,
            }


@register_tool(
    "RNAcentralGetTool",
    config={
        "name": "RNAcentral_get_by_accession",
        "type": "RNAcentralGetTool",
        "description": "Get RNAcentral entry by accession",
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {"type": "string", "description": "RNAcentral accession"}
            },
            "required": ["accession"],
        },
        "settings": {"base_url": "https://rnacentral.org/api/v1", "timeout": 60},
    },
)
class RNAcentralGetTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://rnacentral.org/api/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        acc = arguments.get("accession")
        url = f"{base}/rna/{acc}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "RNAcentral",
                "endpoint": "rna/{accession}",
                "accession": acc,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "RNAcentral",
                "endpoint": "rna/{accession}",
                "accession": acc,
                "success": False,
            }
