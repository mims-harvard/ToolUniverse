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
    "OBISTaxaTool",
    config={
        "name": "OBIS_search_taxa",
        "type": "OBISTaxaTool",
        "description": "Resolve marine taxa by scientific name via OBIS /v3/taxon",
        "parameter": {
            "type": "object",
            "properties": {
                "scientificname": {
                    "type": "string",
                    "description": "Scientific name to search, e.g., 'Gadus'",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["scientificname"],
        },
        "settings": {"base_url": "https://api.obis.org/v3", "timeout": 30},
    },
)
class OBISTaxaTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.obis.org/v3"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        scientificname = arguments.get("scientificname")
        size = int(arguments.get("size", 10))

        # Note: OBIS v3 API does not have /taxon endpoint
        # Use occurrence search with scientificname filter instead
        # This returns occurrences which can be used to identify taxa
        query = {
            "scientificname": scientificname,
            "size": size,
        }
        url = f"{base}/occurrence?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            # Extract unique taxa from occurrences
            if isinstance(data, dict) and "results" in data:
                results = data.get("results", [])
                # Extract unique scientific names and taxonomic info
                taxa_list = []
                seen_names = set()
                for occ in results:
                    sci_name = occ.get("scientificName")
                    if sci_name and sci_name not in seen_names:
                        seen_names.add(sci_name)
                        taxa_list.append(
                            {
                                "scientificName": sci_name,
                                "aphiaID": occ.get("aphiaID"),
                                "rank": occ.get("taxonRank"),
                                "kingdom": occ.get("kingdom"),
                                "phylum": occ.get("phylum"),
                                "class": occ.get("class_"),
                                "order": occ.get("order"),
                                "family": occ.get("family"),
                                "genus": occ.get("genus"),
                            }
                        )
                        if len(taxa_list) >= size:
                            break
                # Return in expected schema format
                wrapped_data = {
                    "results": taxa_list,
                    "total": len(taxa_list),
                }
            else:
                wrapped_data = {"results": [], "total": 0}

            return {
                "status": "success",
                "source": "OBIS",
                "endpoint": "occurrence",  # Note: taxon endpoint not available, using occurrence
                "query": query,
                "data": wrapped_data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "OBIS",
                "endpoint": "occurrence",
                "success": False,
            }


@register_tool(
    "OBISOccurrenceTool",
    config={
        "name": "OBIS_search_occurrences",
        "type": "OBISOccurrenceTool",
        "description": "Search OBIS occurrences via /v3/occurrence",
        "parameter": {
            "type": "object",
            "properties": {
                "scientificname": {
                    "type": "string",
                    "description": "Scientific name filter (optional)",
                },
                "areaid": {
                    "type": "string",
                    "description": "Area identifier filter (optional)",
                },
                "size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
        },
        "settings": {"base_url": "https://api.obis.org/v3", "timeout": 30},
    },
)
class OBISOccurrenceTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        base = self.tool_config.get("settings", {}).get(
            "base_url", "https://api.obis.org/v3"
        )
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        query: Dict[str, Any] = {}
        for key in ("scientificname", "areaid", "size"):
            if key in arguments and arguments[key] is not None:
                query[key] = arguments[key]
        if "size" not in query:
            query["size"] = 10

        url = f"{base}/occurrence?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "OBIS",
                "endpoint": "occurrence",
                "query": query,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "OBIS",
                "endpoint": "occurrence",
                "success": False,
            }
