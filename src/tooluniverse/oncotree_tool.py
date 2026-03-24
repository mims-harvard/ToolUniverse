"""OncoTree API tool for ToolUniverse.

OncoTree is a cancer type ontology developed at Memorial Sloan Kettering
Cancer Center (MSK). It provides a hierarchical classification of cancers
with standardized codes, cross-references to UMLS and NCI thesaurus, and
tissue-based organization.

API: https://oncotree.mskcc.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

ONCOTREE_BASE_URL = "https://oncotree.mskcc.org/api"


class OncoTreeBaseTool(BaseTool):
    """Base class for OncoTree API tools."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{ONCOTREE_BASE_URL}{endpoint}"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _handle_request(self, fn, *args, **kwargs) -> Dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "OncoTree API request timed out",
                "retryable": True,
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to OncoTree API",
                "retryable": True,
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"OncoTree API HTTP {code}",
                "retryable": code in (429, 502, 503),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"OncoTree error: {e}",
                "retryable": False,
            }


@register_tool("OncoTreeSearchTool")
class OncoTreeSearchTool(OncoTreeBaseTool):
    """Search OncoTree cancer types by name, code, main type, or tissue."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle_request(self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "").strip()
        field = arguments.get("field", "name").strip().lower()
        exact_match = bool(arguments.get("exact_match", False))
        version = arguments.get("version", "oncotree_latest_stable")

        if not query:
            return {"status": "error", "error": "query is required", "retryable": False}

        valid_fields = ("name", "code", "main_type", "tissue")
        if field not in valid_fields:
            return {
                "status": "error",
                "error": f"field must be one of: {', '.join(valid_fields)}",
                "retryable": False,
            }

        if field in ("tissue", "main_type"):
            all_types = self._get("/tumorTypes", {"version": version})
            if not isinstance(all_types, list):
                return {
                    "status": "error",
                    "error": "Unexpected response from OncoTree API",
                    "retryable": False,
                }
            attr = "tissue" if field == "tissue" else "mainType"
            q_lower = query.lower()
            if exact_match:
                raw = [t for t in all_types if (t.get(attr) or "").lower() == q_lower]
            else:
                raw = [t for t in all_types if q_lower in (t.get(attr) or "").lower()]
        else:
            params = {"exactMatch": str(exact_match).lower(), "version": version}
            raw = self._get(
                f"/tumorTypes/search/{field}/{requests.utils.quote(query)}", params
            )
            if not isinstance(raw, list):
                return {
                    "status": "error",
                    "error": "Unexpected response from OncoTree API",
                    "retryable": False,
                }

        items = [
            {
                "code": t.get("code"),
                "name": t.get("name"),
                "main_type": t.get("mainType"),
                "tissue": t.get("tissue"),
                "parent": t.get("parent"),
                "level": t.get("level"),
                "external_references": t.get("externalReferences", {}),
            }
            for t in raw
        ]

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "query": query,
                "field": field,
                "exact_match": exact_match,
                "count": len(items),
                "version": version,
            },
        }


@register_tool("OncoTreeGetTypeTool")
class OncoTreeGetTypeTool(OncoTreeBaseTool):
    """Get a specific OncoTree cancer type by its unique code."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle_request(self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        code = arguments.get("code", "").strip().upper()
        version = arguments.get("version", "oncotree_latest_stable")

        if not code:
            return {
                "status": "error",
                "error": "code is required (e.g. 'BRCA', 'LUAD')",
                "retryable": False,
            }

        results = self._get(
            f"/tumorTypes/search/code/{requests.utils.quote(code)}",
            {"exactMatch": "true", "version": version},
        )

        if not isinstance(results, list) or not results:
            return {
                "status": "error",
                "error": f"OncoTree code '{code}' not found",
                "retryable": False,
            }

        t = results[0]
        return {
            "status": "success",
            "data": {
                "code": t.get("code"),
                "name": t.get("name"),
                "main_type": t.get("mainType"),
                "tissue": t.get("tissue"),
                "color": t.get("color"),
                "parent": t.get("parent"),
                "level": t.get("level"),
                "history": t.get("history", []),
                "external_references": t.get("externalReferences", {}),
            },
            "metadata": {"source": "OncoTree MSK", "version": version},
        }


@register_tool("OncoTreeListTissuesTool")
class OncoTreeListTissuesTool(OncoTreeBaseTool):
    """List all top-level tissue categories in the OncoTree hierarchy."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle_request(self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        version = arguments.get("version", "oncotree_latest_stable")

        all_types = self._get("/tumorTypes", {"version": version})
        if not isinstance(all_types, list):
            return {
                "status": "error",
                "error": "Unexpected response from OncoTree API",
                "retryable": False,
            }

        tissues = sorted(
            {t.get("tissue") for t in all_types if t.get("tissue")},
        )

        return {
            "status": "success",
            "data": tissues,
            "metadata": {"count": len(tissues), "version": version},
        }
