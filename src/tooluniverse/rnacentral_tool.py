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
        if not acc:
            return {
                "status": "error",
                "error": "accession is required (e.g., 'URS000063A371').",
                "source": "RNAcentral",
                "success": False,
            }

        fields = self.tool_config.get("fields", {}) or {}

        # 'sub_resources': list of rna/{accession}/{name} sub-endpoints to fetch
        # and merge into one response (e.g. ['xrefs', 'publications']). This
        # lets the same class serve the base record plus resolved
        # cross-references and literature without adding a new @register_tool
        # class. Falls back to the base rna/{accession} record when unset.
        sub_resources = fields.get("sub_resources")

        if sub_resources:
            return self._get_sub_resources(base, acc, sub_resources, timeout)

        endpoint = "rna/{accession}"
        url = f"{base}/rna/{acc}"
        try:
            data = _http_get(
                url, headers={"Accept": "application/json"}, timeout=timeout
            )
            return {
                "status": "success",
                "source": "RNAcentral",
                "endpoint": endpoint,
                "accession": acc,
                "data": data,
                "success": True,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "source": "RNAcentral",
                "endpoint": endpoint,
                "accession": acc,
                "success": False,
            }

    def _get_sub_resources(self, base, acc, sub_resources, timeout):
        """Fetch and merge one or more rna/{accession}/{name} sub-endpoints."""
        data: Dict[str, Any] = {}
        errors = []
        for name in sub_resources:
            url = f"{base}/rna/{acc}/{name}?format=json"
            try:
                payload = _http_get(
                    url, headers={"Accept": "application/json"}, timeout=timeout
                )
                results = (
                    payload.get("results", []) if isinstance(payload, dict) else []
                )
                count = (
                    payload.get("count")
                    if isinstance(payload, dict) and payload.get("count") is not None
                    else len(results)
                )
                data[name] = {"count": count, "results": results}
            except Exception as e:
                errors.append(f"{name}: {e}")

        # Only a hard failure (no sub-resource succeeded) returns an error.
        if not data and errors:
            return {
                "status": "error",
                "error": "; ".join(errors),
                "source": "RNAcentral",
                "endpoint": "rna/{accession}/[xrefs,publications]",
                "accession": acc,
                "success": False,
            }

        return {
            "status": "success",
            "source": "RNAcentral",
            "endpoint": "rna/{accession}/[" + ",".join(sub_resources) + "]",
            "accession": acc,
            "data": data,
            "partial_errors": errors or None,
            "success": True,
        }
