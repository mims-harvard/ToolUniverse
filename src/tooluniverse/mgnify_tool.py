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
    "MGnifyStudiesTool",
    config={
        "name": "MGnify_search_studies",
        "type": "MGnifyStudiesTool",
        "description": "Search MGnify studies via /studies with optional biome/search filters",
        "parameter": {
            "type": "object",
            "properties": {
                "biome": {
                    "type": "string",
                    "description": "Biome identifier, e.g., 'root:Host-associated'",
                },
                "search": {
                    "type": "string",
                    "description": "Keyword to search in study title/description",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
        },
        "settings": {
            "base_url": "https://www.ebi.ac.uk/metagenomics/api/latest",
            "timeout": 30,
        },
    },
)
class MGnifyStudiesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://www.ebi.ac.uk/metagenomics/api/latest"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {}
        if arguments.get("biome"):
            query["biome"] = arguments["biome"]
        if arguments.get("search"):
            query["search"] = arguments["search"]
        if arguments.get("size") is not None:
            query["size"] = int(arguments["size"])
        else:
            query["size"] = 10

        url = f"{base}/studies?{urlencode(query)}"
        try:
            api_response = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            # API returns {"data": [...], "links": {...}, "meta": {...}}
            # Extract the data array directly
            if isinstance(api_response, dict) and "data" in api_response:
                data_array = api_response.get("data", [])
            else:
                # Fallback if response format is unexpected
                data_array = api_response if isinstance(api_response, list) else []

            return {
                "status": "success",
                "source": "MGnify",
                "endpoint": "studies",
                "query": query,
                "data": data_array,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "MGnify",
                "endpoint": "studies",
                "success": False,
            }


@register_tool(
    "MGnifyAnalysesTool",
    config={
        "name": "MGnify_list_analyses",
        "type": "MGnifyAnalysesTool",
        "description": "List MGnify analyses via /analyses for a given study_accession",
        "parameter": {
            "type": "object",
            "properties": {
                "study_accession": {
                    "type": "string",
                    "description": "MGnify study accession, e.g., 'MGYS00000001'",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["study_accession"],
        },
        "settings": {
            "base_url": "https://www.ebi.ac.uk/metagenomics/api/latest",
            "timeout": 30,
        },
    },
)
class MGnifyAnalysesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://www.ebi.ac.uk/metagenomics/api/latest"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {
            "study_accession": arguments.get("study_accession"),
        }
        if arguments.get("size") is not None:
            query["size"] = int(arguments["size"])
        else:
            query["size"] = 10

        url = f"{base}/analyses?{urlencode(query)}"
        try:
            api_response = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            # API returns {"data": [...], "links": {...}, "meta": {...}}
            # Extract the data array directly
            if isinstance(api_response, dict) and "data" in api_response:
                data_array = api_response.get("data", [])
            else:
                # Fallback if response format is unexpected
                data_array = api_response if isinstance(api_response, list) else []

            return {
                "status": "success",
                "source": "MGnify",
                "endpoint": "analyses",
                "query": query,
                "data": data_array,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "MGnify",
                "endpoint": "analyses",
                "success": False,
            }
