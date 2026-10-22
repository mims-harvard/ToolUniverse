"""
NPAtlas tools for ToolUniverse — microbial natural products.

The Natural Products Atlas (NPAtlas) is a curated database of microbial (bacterial
and fungal) natural products with structures, source organism, and references.
These tools search compounds and retrieve a single compound's full record.

API: https://www.npatlas.org/api/v1  (public, no authentication, JSON)
  - POST /compounds/basicSearch  (query params: name / inchikey / formula / smiles ...)
  - GET  /compound/{npaid}
"""

import re
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

NPATLAS_BASE = "https://www.npatlas.org/api/v1"


def _summarize(c: Dict[str, Any]) -> Dict[str, Any]:
    org = c.get("origin_organism") or {}
    return {
        "npaid": c.get("npaid"),
        "name": c.get("original_name"),
        "molecular_formula": c.get("mol_formula"),
        "molecular_weight": c.get("mol_weight"),
        "exact_mass": c.get("exact_mass"),
        "inchikey": c.get("inchikey"),
        "smiles": c.get("smiles"),
        "origin_organism": org.get("taxon")
        or (f"{org.get('genus', '')} {org.get('species', '')}".strip() or None),
    }


@register_tool("NPAtlasSearchTool")
class NPAtlasSearchTool(BaseTool):
    """Search NPAtlas microbial natural products by name, InChIKey, or formula."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        skip = arguments.get("skip", 0)
        if isinstance(skip, bool) or not isinstance(skip, int) or skip < 0:
            return {
                "status": "error",
                "error": "skip must be a non-negative integer",
                "parameter": "skip",
            }
        limit = arguments.get("limit", 10)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 100",
                "parameter": "limit",
            }
        params: Dict[str, Any] = {"method": "full", "threshold": 0, "skip": skip}
        provided = False
        for key in ("name", "inchikey", "formula", "smiles"):
            val = (arguments.get(key) or "").strip()
            if val:
                params[key] = val
                provided = True
        if not provided:
            return {
                "status": "error",
                "error": "Provide one of 'name', 'inchikey', 'formula', or 'smiles'.",
            }
        params["limit"] = limit + 1 if limit < 100 else 100

        try:
            resp = requests.post(
                f"{NPATLAS_BASE}/compounds/basicSearch",
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            if limit == 100 and isinstance(payload, list) and len(payload) == 100:
                probe_params = dict(params)
                probe_params.update({"skip": skip + 100, "limit": 1})
                probe = requests.post(
                    f"{NPATLAS_BASE}/compounds/basicSearch",
                    params=probe_params,
                    headers={"Accept": "application/json"},
                    timeout=self.timeout,
                )
                probe.raise_for_status()
                probe_payload = probe.json()
            else:
                probe_payload = None
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NPAtlas request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"NPAtlas request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "NPAtlas returned a non-JSON response"}

        if not isinstance(payload, list) or (
            probe_payload is not None and not isinstance(probe_payload, list)
        ):
            return {
                "status": "error",
                "error": "NPAtlas returned an unexpected search payload",
            }
        compounds = payload
        has_more = len(compounds) > limit or (
            isinstance(probe_payload, list) and bool(probe_payload)
        )
        compounds = compounds[:limit]
        results = [_summarize(c) for c in compounds if isinstance(c, dict)]
        total_is_exact = not has_more
        total = skip + len(compounds) if total_is_exact else None
        truncated = skip > 0 or has_more
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": total,
                "total_results_is_exact": total_is_exact,
                "matches_lower_bound": skip + len(compounds) + (1 if has_more else 0),
                "returned": len(results),
                "limit": limit,
                "skip": skip,
                "has_more": has_more,
                "next_skip": skip + len(compounds) if has_more else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
                "source": "NPAtlas",
            },
        }


@register_tool("NPAtlasCompoundTool")
class NPAtlasCompoundTool(BaseTool):
    """Get a single NPAtlas compound's full record by NPAID."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = dict(arguments or {})
        unknown = sorted(set(arguments) - {"npaid"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unknown parameter(s): {', '.join(unknown)}",
            }
        npaid_value = arguments.get("npaid")
        if not isinstance(npaid_value, str) or not npaid_value.strip():
            return {
                "status": "error",
                "error": "'npaid' is required (e.g. 'NPA000001')",
            }
        npaid = npaid_value.strip().upper()
        if not re.fullmatch(r"NPA\d{6}", npaid):
            return {
                "status": "error",
                "error": "npaid must match NPA followed by six digits (e.g. NPA000001)",
            }

        try:
            resp = requests.get(
                f"{NPATLAS_BASE}/compound/{npaid}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"NPAtlas compound not found: {npaid}",
                    "query_npaid": npaid,
                }
            resp.raise_for_status()
            c = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NPAtlas request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"NPAtlas request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "NPAtlas returned a non-JSON response"}

        if not isinstance(c, dict) or not c.get("npaid"):
            return {
                "status": "error",
                "error": "NPAtlas returned a malformed compound record",
            }
        if str(c["npaid"]).upper() != npaid:
            return {
                "status": "error",
                "error": (
                    f"NPAtlas compound identity mismatch: requested {npaid}, "
                    f"received {c['npaid']}"
                ),
            }
        ref = c.get("origin_reference") or {}
        data = _summarize(c)
        data.update(
            {
                "inchi": c.get("inchi"),
                "synonyms": c.get("synonyms", []),
                "origin_reference": {
                    "title": ref.get("title"),
                    "doi": ref.get("doi"),
                    "journal": ref.get("journal"),
                    "year": ref.get("year"),
                }
                if ref
                else None,
                "external_ids": c.get("external_ids", []),
                "source_record": c,
            }
        )
        return {
            "status": "success",
            "data": data,
            "metadata": {
                "query_npaid": npaid,
                "source": "NPAtlas",
                "source_record_complete": True,
                "source_field_count": len(c),
                "source_fields": sorted(c),
                "normalized_projection_field_count": len(data) - 1,
            },
        }
