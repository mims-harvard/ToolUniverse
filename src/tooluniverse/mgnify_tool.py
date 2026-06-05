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
                    "description": "Biome lineage identifier, e.g., 'root:Host-associated' or 'root:Host-associated:Human:Digestive system'",
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
            "base_url": "https://www.ebi.ac.uk/metagenomics/api/v1",
            "timeout": 30,
        },
    },
)
class MGnifyStudiesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://www.ebi.ac.uk/metagenomics/api/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        # The MGnify API (Django REST / JSON:API) filters studies by biome via the
        # `lineage` query param and paginates with `page_size` -- NOT `biome`/`size`.
        # Sending the wrong names returns an unfiltered/empty page silently, so map
        # the friendly argument names onto the API's actual parameters.
        query: Dict[str, Any] = {}
        biome = arguments.get("biome") or arguments.get("lineage")
        if biome:
            query["lineage"] = biome
        if arguments.get("search"):
            query["search"] = arguments["search"]
        size = arguments.get("size")
        query["page_size"] = int(size) if size is not None else 10

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
            "base_url": "https://www.ebi.ac.uk/metagenomics/api/v1",
            "timeout": 30,
        },
    },
)
class MGnifyAnalysesTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://www.ebi.ac.uk/metagenomics/api/v1"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        # MGnify paginates with `page_size`, not `size` (see MGnifyStudiesTool note).
        query: Dict[str, Any] = {
            "study_accession": arguments.get("study_accession"),
        }
        size = arguments.get("size")
        query["page_size"] = int(size) if size is not None else 10

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
