# smartapi_tool.py
"""
SmartAPI registry tool for ToolUniverse.

SmartAPI is the machine-readable registry of ~270 biomedical web APIs
(OpenAPI-described, many part of the NCATS Biomedical Data Translator),
searchable by keyword or tag. ToolUniverse already wraps a large fraction
of the APIs registered here individually, but had no way to discover what
else is registered, or resolve an API name mentioned in a paper or Translator
component list to its actual base URL and endpoint list.

The full per-API document is the complete OpenAPI spec (often hundreds of
KB with every path/schema/component); this tool asks the API's own `fields`
parameter for a slimmed summary rather than returning that raw.

API: https://smart-api.info/api
No authentication required.
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

SMARTAPI_BASE_URL = "https://smart-api.info/api"

_SEARCH_FIELDS = (
    "_id,_meta.slug,info.title,info.description,info.contact,tags,servers"
)


def _summarize_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Condense one SmartAPI search hit to its useful summary fields."""
    info = hit.get("info") or {}
    servers = hit.get("servers") or []
    return {
        "api_id": hit.get("_id"),
        "slug": (hit.get("_meta") or {}).get("slug"),
        "title": info.get("title"),
        "description": info.get("description"),
        "base_url": servers[0].get("url") if servers else None,
        "tags": [t.get("name") for t in hit.get("tags") or [] if t.get("name")],
    }


@register_tool("SmartAPITool")
class SmartAPITool(BaseTool):
    """
    Tool for searching the SmartAPI registry of biomedical web APIs.

    Supports keyword/tag search across ~270 registered OpenAPI specs, and
    fetching one API's full metadata (servers, tags, endpoint count,
    contact) by its registry id or slug.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_apis"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SmartAPI lookup."""
        try:
            if self.operation == "search_apis":
                return self._search_apis(arguments)
            if self.operation == "get_api":
                return self._get_api(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SmartAPI request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SmartAPI. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"SmartAPI returned HTTP {code}"}
        except ValueError:
            return {
                "status": "error",
                "error": "SmartAPI returned a non-JSON response",
            }
        except Exception as e:
            return {"status": "error", "error": f"Error querying SmartAPI: {str(e)}"}

    def _search_apis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the SmartAPI registry by keyword or tag."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'variant' or "
                "'tags.name:translator'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{SMARTAPI_BASE_URL}/query",
            params={
                "q": query,
                "size": limit,
                "raw": 1,
                "fields": _SEARCH_FIELDS,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits") or []

        if not hits:
            return {
                "status": "error",
                "error": f"No SmartAPI entries matching '{query}'.",
            }

        rows = [_summarize_hit(h) for h in hits]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": payload.get("total"),
                "returned": len(rows),
                "note": "api_id (or slug, when present) is what get_api "
                "expects for the full record.",
                "source": "SmartAPI registry",
            },
        }

    def _get_api(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one API's full metadata by its registry id or slug."""
        api_id = (arguments.get("api_id") or "").strip()
        if not api_id:
            return {
                "status": "error",
                "error": "api_id is required: a SmartAPI registry id or "
                "slug, e.g. 'myvariant'. Use search_apis to find one.",
            }

        response = requests.get(
            f"{SMARTAPI_BASE_URL}/metadata/{api_id}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No SmartAPI entry with id or slug '{api_id}'.",
            }
        response.raise_for_status()
        spec = response.json()
        info = spec.get("info") or {}
        servers = spec.get("servers") or []
        paths = spec.get("paths") or {}

        endpoints: List[str] = list(paths.keys())

        return {
            "status": "success",
            "data": {
                "title": info.get("title"),
                "description": info.get("description"),
                "version": info.get("version"),
                "contact": (info.get("contact") or {}).get("email"),
                "terms_of_service": info.get("termsOfService"),
                "base_urls": [s.get("url") for s in servers if s.get("url")],
                "tags": [
                    t.get("name") for t in spec.get("tags") or [] if t.get("name")
                ],
                "endpoint_count": len(endpoints),
                "endpoints": endpoints[:50],
            },
            "metadata": {
                "api_id": api_id,
                "endpoints_truncated": len(endpoints) > 50,
                "source": "SmartAPI registry",
            },
        }
