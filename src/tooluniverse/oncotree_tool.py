"""OncoTree API tool for ToolUniverse.

OncoTree is a cancer type ontology developed at Memorial Sloan Kettering
Cancer Center (MSK). It provides a hierarchical classification of cancers
with standardized codes, cross-references to UMLS and NCI thesaurus, and
tissue-based organization.

API: https://oncotree.mskcc.org/api/
No authentication required. Free public access.
"""

from typing import Dict, Any, Optional

import requests

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

    @staticmethod
    def _string_argument(
        arguments: Dict[str, Any], name: str, default: Optional[str] = None
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        value = arguments.get(name, default)
        if not isinstance(value, str) or not value.strip():
            return None, {
                "status": "error",
                "error": f"{name} must be a non-empty string",
                "retryable": False,
            }
        return value.strip(), None

    @staticmethod
    def _normalize_tumor_type(record: Any) -> Dict[str, Any]:
        if not isinstance(record, dict) or not isinstance(record.get("code"), str):
            raise ValueError("OncoTree returned a malformed tumor-type record")
        structured_fields = {
            "externalReferences": dict,
            "history": list,
            "children": (dict, list),
            "precursors": list,
            "revocations": list,
        }
        for field, expected_type in structured_fields.items():
            default = {} if field in ("externalReferences", "children") else []
            if not isinstance(record.get(field, default), expected_type):
                raise ValueError(
                    f"OncoTree returned malformed {field} for code {record['code']}"
                )
        return {
            "code": record.get("code"),
            "name": record.get("name"),
            "main_type": record.get("mainType"),
            "tissue": record.get("tissue"),
            "color": record.get("color"),
            "parent": record.get("parent"),
            "level": record.get("level"),
            "history": record.get("history", []),
            "children": record.get("children", {}),
            "precursors": record.get("precursors", []),
            "revocations": record.get("revocations", []),
            "external_references": record.get("externalReferences", {}),
        }

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
        query, error = self._string_argument(arguments, "query")
        if error:
            return error
        field, error = self._string_argument(arguments, "field", "name")
        if error:
            return error
        version, error = self._string_argument(
            arguments, "version", "oncotree_latest_stable"
        )
        if error:
            return error
        assert query is not None and field is not None and version is not None
        field = field.lower()
        exact_match = arguments.get("exact_match", False)
        if not isinstance(exact_match, bool):
            return {
                "status": "error",
                "error": "exact_match must be a boolean",
                "retryable": False,
            }

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
            try:
                raw = self._get(
                    f"/tumorTypes/search/{field}/{requests.utils.quote(query)}", params
                )
            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    raw = []
                else:
                    raise
            if not isinstance(raw, list):
                return {
                    "status": "error",
                    "error": "Unexpected response from OncoTree API",
                    "retryable": False,
                }

        items = [self._normalize_tumor_type(t) for t in raw]

        if exact_match and field in ("name", "code"):
            key = "name" if field == "name" else "code"
            mismatches = [
                item.get(key)
                for item in items
                if (item.get(key) or "").lower() != query.lower()
            ]
            if mismatches:
                return {
                    "status": "error",
                    "error": "OncoTree returned non-matching records for an exact search",
                    "mismatched_values": mismatches,
                    "retryable": False,
                }

        return {
            "status": "success",
            "data": items,
            "metadata": {
                "query": query,
                "field": field,
                "exact_match": exact_match,
                "count": len(items),
                "version": version,
                "source_records_complete": True,
                "preserved_fields": [
                    "code",
                    "name",
                    "mainType",
                    "tissue",
                    "color",
                    "parent",
                    "level",
                    "history",
                    "children",
                    "precursors",
                    "revocations",
                    "externalReferences",
                ],
            },
        }


@register_tool("OncoTreeGetTypeTool")
class OncoTreeGetTypeTool(OncoTreeBaseTool):
    """Get a specific OncoTree cancer type by its unique code."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle_request(self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        code, error = self._string_argument(arguments, "code")
        if error:
            return error
        version, error = self._string_argument(
            arguments, "version", "oncotree_latest_stable"
        )
        if error:
            return error
        assert code is not None and version is not None
        code = code.upper()

        try:
            results = self._get(
                f"/tumorTypes/search/code/{requests.utils.quote(code)}",
                {"exactMatch": "true", "version": version},
            )
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                results = []
            else:
                raise

        if not isinstance(results, list) or not results:
            return {
                "status": "error",
                "error": f"OncoTree code '{code}' not found",
                "retryable": False,
            }

        if len(results) != 1 or not isinstance(results[0], dict):
            return {
                "status": "error",
                "error": f"OncoTree exact code lookup for '{code}' was not unique",
                "returned": len(results),
                "retryable": False,
            }
        if (results[0].get("code") or "").upper() != code:
            return {
                "status": "error",
                "error": f"OncoTree returned a different code for exact lookup '{code}'",
                "returned_code": results[0].get("code"),
                "retryable": False,
            }
        item = self._normalize_tumor_type(results[0])
        return {
            "status": "success",
            "data": item,
            "metadata": {
                "source": "OncoTree MSK",
                "version": version,
                "exact_code_verified": True,
                "source_record_complete": True,
            },
        }


@register_tool("OncoTreeListTissuesTool")
class OncoTreeListTissuesTool(OncoTreeBaseTool):
    """List all top-level tissue categories in the OncoTree hierarchy."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._handle_request(self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        version, error = self._string_argument(
            arguments, "version", "oncotree_latest_stable"
        )
        if error:
            return error
        assert version is not None

        all_types = self._get("/tumorTypes", {"version": version})
        if not isinstance(all_types, list):
            return {
                "status": "error",
                "error": "Unexpected response from OncoTree API",
                "retryable": False,
            }

        normalized = [self._normalize_tumor_type(t) for t in all_types]
        tissues = sorted({t["tissue"] for t in normalized if t["tissue"]})

        return {
            "status": "success",
            "data": tissues,
            "metadata": {
                "count": len(tissues),
                "version": version,
                "tumor_types_scanned": len(normalized),
                "complete_source_scan": True,
            },
        }
