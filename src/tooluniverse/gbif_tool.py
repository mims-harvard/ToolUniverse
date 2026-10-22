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
                    "maximum": 1000,
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
        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        if not isinstance(query_text, str) or not query_text.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        if offset + limit > 100000:
            return {
                "status": "error",
                "error": "GBIF species search requires offset + limit <= 100000",
                "parameter": "offset",
            }

        query = {"q": query_text, "limit": limit, "offset": offset}
        url = f"{base}/species/search?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            result = {
                "status": "success",
                "source": "GBIF",
                "endpoint": "species/search",
                "query": query,
                "data": data,
                "success": True,
            }
            result["metadata"] = _gbif_pagination_metadata(
                data, offset, limit, accessible_window=100000
            )
            return result
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

        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 300
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 300",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        if offset + limit > 100001:
            return {
                "status": "error",
                "error": "GBIF occurrence search requires offset + limit <= 100001",
                "parameter": "offset",
            }
        taxon_key = arguments.get("taxonKey")
        if taxon_key is not None and (
            isinstance(taxon_key, bool)
            or not isinstance(taxon_key, int)
            or taxon_key < 1
        ):
            return {
                "status": "error",
                "error": "taxonKey must be a positive integer",
                "parameter": "taxonKey",
            }
        has_coordinate = arguments.get("hasCoordinate", True)
        if not isinstance(has_coordinate, bool):
            return {
                "status": "error",
                "error": "hasCoordinate must be a boolean",
                "parameter": "hasCoordinate",
            }
        country = arguments.get("country")
        if country is not None and (
            not isinstance(country, str) or len(country.strip()) != 2
        ):
            return {
                "status": "error",
                "error": "country must be a two-letter ISO 3166-1 alpha-2 code",
                "parameter": "country",
            }

        normalized = dict(arguments)
        normalized["limit"] = limit
        normalized["offset"] = offset
        normalized["hasCoordinate"] = has_coordinate
        if country is not None:
            normalized["country"] = country.strip().upper()

        query = {}
        for key in ("taxonKey", "country", "hasCoordinate", "limit", "offset"):
            if key in normalized and normalized[key] is not None:
                query[key] = normalized[key]

        url = f"{base}/occurrence/search?{urlencode(query)}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            result = {
                "status": "success",
                "source": "GBIF",
                "endpoint": "occurrence/search",
                "query": query,
                "data": data,
                "success": True,
            }
            result["metadata"] = _gbif_pagination_metadata(
                data, offset, limit, accessible_window=100001
            )
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "GBIF",
                "endpoint": "occurrence/search",
                "success": False,
            }


def _gbif_pagination_metadata(
    data: Dict[str, Any], requested_offset: int, requested_limit: int, accessible_window: int
) -> Dict[str, Any]:
    """Interpret GBIF's exact count and finite deep-pagination windows."""
    records = data.get("results", []) if isinstance(data, dict) else []
    if not isinstance(records, list):
        records = []
    total = data.get("count") if isinstance(data, dict) else None
    total_is_exact = isinstance(total, int) and not isinstance(total, bool)
    reported_offset = data.get("offset") if isinstance(data, dict) else None
    offset = (
        reported_offset
        if isinstance(reported_offset, int) and not isinstance(reported_offset, bool)
        else requested_offset
    )
    reported_limit = data.get("limit") if isinstance(data, dict) else None
    limit = (
        reported_limit
        if isinstance(reported_limit, int) and not isinstance(reported_limit, bool)
        else requested_limit
    )
    accessible = min(total, accessible_window) if total_is_exact else accessible_window
    returned = len(records)
    end_of_records = data.get("endOfRecords") if isinstance(data, dict) else None
    has_more = bool(
        returned
        and offset + returned < accessible
        and end_of_records is not True
    )
    upstream_truncated = bool(total_is_exact and total > accessible_window)
    return {
        "returned": returned,
        "total_results": total if total_is_exact else None,
        "total_results_is_exact": total_is_exact,
        "accessible_results": accessible,
        "upstream_truncated": upstream_truncated,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": offset + returned if has_more else None,
        "end_of_records": end_of_records,
        "truncated": offset > 0 or has_more or upstream_truncated,
        "result_set_complete": bool(
            total_is_exact and offset == 0 and returned == total
        ),
        "pagination_scope": f"gbif_exact_count_{accessible_window}_record_window",
        "warning": (
            f"GBIF matched more records than its {accessible_window:,}-record search "
            "window exposes. Use narrower taxonomic, geographic, or other filters, "
            "or GBIF's download API for the complete occurrence set."
            if upstream_truncated
            else None
        ),
    }
