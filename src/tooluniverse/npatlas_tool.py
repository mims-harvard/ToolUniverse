"""
NPAtlas tools for ToolUniverse — microbial natural products.

The Natural Products Atlas (NPAtlas) is a curated database of microbial (bacterial
and fungal) natural products with structures, source organism, and references.
These tools search compounds and retrieve a single compound's full record.

API: https://www.npatlas.org/api/v1  (public, no authentication, JSON)
  - POST /compounds/basicSearch  (query params: name / inchikey / formula / smiles ...)
  - GET  /compound/{npaid}
"""

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
        params: Dict[str, Any] = {"method": "full", "threshold": 0, "skip": 0}
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
        try:
            params["limit"] = max(1, min(int(arguments.get("limit") or 10), 100))
        except (TypeError, ValueError):
            params["limit"] = 10

        try:
            resp = requests.post(
                f"{NPATLAS_BASE}/compounds/basicSearch",
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NPAtlas request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"NPAtlas request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "NPAtlas returned a non-JSON response"}

        compounds = payload if isinstance(payload, list) else []
        results = [_summarize(c) for c in compounds if isinstance(c, dict)]
        return {
            "status": "success",
            "data": results,
            "metadata": {"total_results": len(results), "source": "NPAtlas"},
        }


@register_tool("NPAtlasCompoundTool")
class NPAtlasCompoundTool(BaseTool):
    """Get a single NPAtlas compound's full record by NPAID."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        npaid = (arguments.get("npaid") or "").strip()
        if not npaid:
            return {
                "status": "error",
                "error": "'npaid' is required (e.g. 'NPA000001')",
            }

        try:
            resp = requests.get(
                f"{NPATLAS_BASE}/compound/{npaid}",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "query_npaid": npaid,
                        "note": f"No NPAtlas compound '{npaid}'.",
                    },
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
            return {"status": "success", "data": {}, "metadata": {"query_npaid": npaid}}
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
            }
        )
        return {
            "status": "success",
            "data": data,
            "metadata": {"query_npaid": npaid, "source": "NPAtlas"},
        }
