import json
from typing import Any, Dict
from urllib.parse import quote, urlencode
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
        size = arguments.get("size", 10)
        offset = arguments.get("offset", 0)
        if not isinstance(scientificname, str) or not scientificname.strip():
            return {
                "status": "error",
                "error": "scientificname must be a non-empty string",
            }
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 100:
            return {
                "status": "error",
                "error": "size must be an integer between 1 and 100",
                "parameter": "size",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }

        query = {"scientificname": scientificname, "size": size, "offset": offset}
        url = f"{base}/taxon/{quote(scientificname.strip(), safe='')}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            upstream = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(upstream, list):
                upstream = []
            total = (
                data.get("total", len(upstream))
                if isinstance(data, dict)
                else len(upstream)
            )
            total_is_exact = isinstance(total, int) and not isinstance(total, bool)
            page_records = []
            for record in upstream[offset : offset + size]:
                normalized = dict(record)
                normalized.setdefault("aphiaID", record.get("taxonID"))
                normalized.setdefault("rank", record.get("taxonRank"))
                page_records.append(normalized)
            returned = len(page_records)
            has_more = bool(total_is_exact and offset + returned < total)
            wrapped_data = {"results": page_records, "total": total}

            return {
                "status": "success",
                "source": "OBIS",
                "endpoint": "taxon/{scientificname}",
                "query": query,
                "data": wrapped_data,
                "success": True,
                "metadata": {
                    "returned": returned,
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "offset": offset,
                    "size": size,
                    "has_more": has_more,
                    "next_offset": offset + returned if has_more else None,
                    "truncated": offset > 0 or has_more,
                    "result_set_complete": bool(
                        total_is_exact and offset == 0 and returned == total
                    ),
                    "pagination_scope": "obis_exact_name_local_offset",
                },
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

        size = arguments.get("size", 10)
        after = arguments.get("after")
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 100:
            return {
                "status": "error",
                "error": "size must be an integer between 1 and 100",
                "parameter": "size",
            }
        if after is not None and (not isinstance(after, str) or not after.strip()):
            return {
                "status": "error",
                "error": "after must be a non-empty OBIS occurrence UUID",
                "parameter": "after",
            }
        query: Dict[str, Any] = {}
        for key in ("scientificname", "areaid", "after"):
            if key in arguments and arguments[key] is not None:
                query[key] = arguments[key]
        # Fetch one extra UUID so has_more never relies on page fullness alone.
        query["size"] = size + 1

        url = f"{base}/occurrence?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            records = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(records, list):
                records = []
            has_more = len(records) > size
            page_records = records[:size]
            total = data.get("total") if isinstance(data, dict) else None
            total_is_exact = isinstance(total, int) and not isinstance(total, bool)
            next_after = (
                page_records[-1].get("id") if has_more and page_records else None
            )
            output_data = dict(data) if isinstance(data, dict) else {}
            output_data["results"] = page_records
            return {
                "status": "success",
                "source": "OBIS",
                "endpoint": "occurrence",
                "query": {**query, "size": size},
                "data": output_data,
                "success": True,
                "metadata": {
                    "returned": len(page_records),
                    "total_results": total if total_is_exact else None,
                    "total_results_is_exact": total_is_exact,
                    "size": size,
                    "after": after,
                    "has_more": has_more,
                    "next_after": next_after,
                    "truncated": after is not None or has_more,
                    "result_set_complete": bool(
                        total_is_exact and after is None and len(page_records) == total
                    ),
                    "cursor_field": "id",
                    "cursor_is_not_occurrenceID": True,
                    "pagination_scope": "obis_occurrence_uuid_after_lookahead",
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "OBIS",
                "endpoint": "occurrence",
                "success": False,
            }
