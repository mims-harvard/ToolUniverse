"""
FDA GSRS Tool

Substance registration and identification tools using the FDA Global Substance
Registration System (GSRS / Substance Registration System) public API:

  - search_substances:  Search for substances by name, UNII, or InChIKey
  - get_substance:      Get full substance record by UNII code or UUID
  - get_structure:      Get structure (SMILES, molfile, formula) for a substance

API base: https://gsrs.ncats.nih.gov/api/v1
No authentication required. Free public FDA/NLM API.

UNII = Unique Ingredient Identifier. Official FDA identifier for drug ingredients.
Cross-references include DrugBank, WHO-ATC, CAS, CFR, EC/EINECS, and more.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GSRS_BASE = "https://gsrs.ncats.nih.gov/api/v1"


@register_tool("FDAGSRSTool")
class FDAGSRSTool(BaseTool):
    """
    FDA GSRS substance lookup and search tools.

    Operations:
      - search_substances: Search substances by name, UNII, InChIKey, or formula
      - get_substance:     Retrieve full substance record by UNII or UUID
      - get_structure:     Get structure data (SMILES, formula, InChI) by UNII
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_substances"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        op = self.operation
        if op == "search_substances":
            return self._search_substances(arguments)
        if op == "get_substance":
            return self._get_substance(arguments)
        if op == "get_structure":
            return self._get_structure(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _clean_substance(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key fields from a raw substance record."""
        codes = r.get("codes", [])
        xrefs = {}
        for c in codes:
            sys_name = c.get("codeSystem", "")
            code_val = c.get("code", "")
            if sys_name and code_val:
                xrefs.setdefault(sys_name, []).append(code_val)

        names = r.get("names", [])
        synonyms = [n.get("name", "") for n in names if n.get("name")]

        return {
            "uuid": r.get("uuid", ""),
            "unii": r.get("approvalID") or r.get("unii", ""),
            "name": r.get("_name", ""),
            "substanceClass": r.get("substanceClass", ""),
            "status": r.get("status", ""),
            "formula": r.get("structure", {}).get("formula", "")
            if r.get("structure")
            else "",
            "smiles": r.get("structure", {}).get("smiles", "")
            if r.get("structure")
            else "",
            "synonyms": synonyms[:10],
            "xrefs": xrefs,
        }

    def _api_get(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Shared HTTP GET with consistent error handling."""
        try:
            resp = requests.get(url, params=params or {}, timeout=self.timeout)
            resp.raise_for_status()
            return {"ok": True, "data": resp.json()}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "FDA GSRS API timeout", "retryable": True}
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code
            return {
                "ok": False,
                "error": f"FDA GSRS HTTP {sc}",
                "retryable": sc in (408, 429, 500, 502, 503, 504),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "ok": False,
                "error": "FDA GSRS returned non-JSON response",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "FDA GSRS may be under maintenance. Retry in a few minutes.",
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "retryable": False}

    # ------------------------------------------------------------------
    # operation: search_substances
    # ------------------------------------------------------------------

    def _search_substances(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (
            arguments.get("query")
            or arguments.get("name")
            or arguments.get("drug_name")
        )
        substance_class = arguments.get("substance_class", "")
        limit = min(int(arguments.get("limit", 10)), 50)

        if not query:
            return {
                "status": "error",
                "error": "Provide 'query' (name, UNII, InChIKey, or formula).",
            }

        params: Dict[str, Any] = {"q": query.strip(), "top": limit}
        if substance_class:
            params["fdim"] = f"substanceClass:{substance_class}"

        result = self._api_get(f"{GSRS_BASE}/substances/search", params)
        if not result["ok"]:
            result.pop("ok", None)
            return {"status": "error", **result}

        content = result["data"].get("content", [])
        total = result["data"].get("total", len(content))

        substances = [self._clean_substance(r) for r in content]

        return {
            "status": "success",
            "data": substances,
            "metadata": {
                "query": query,
                "total": total,
                "returned": len(substances),
                "substance_class_filter": substance_class or None,
            },
        }

    # ------------------------------------------------------------------
    # operation: get_substance
    # ------------------------------------------------------------------

    def _get_substance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        unii = arguments.get("unii") or arguments.get("id")
        if not unii:
            return {
                "status": "error",
                "error": "Provide 'unii' (e.g., 'R16CO5Y76E' for aspirin).",
            }

        result = self._api_get(f"{GSRS_BASE}/substances/{unii.strip().upper()}")
        if not result["ok"]:
            result.pop("ok", None)
            return {"status": "error", **result}

        r = result["data"]
        if not isinstance(r, dict) or not r.get("uuid"):
            return {
                "status": "error",
                "error": f"No substance found for UNII: {unii}",
                "suggestion": "Use FDAGSRS_search_substances to find the correct UNII code.",
            }

        # Full record - include all codes and names
        codes = r.get("codes", [])
        all_codes = [
            {
                "codeSystem": c.get("codeSystem", ""),
                "code": c.get("code", ""),
                "type": c.get("type", ""),
            }
            for c in codes
            if c.get("codeSystem") and c.get("code")
        ]

        names = r.get("names", [])
        all_names = [
            {
                "name": n.get("name", ""),
                "type": n.get("type", ""),
                "preferred": n.get("preferred", False),
            }
            for n in names
            if n.get("name")
        ]

        structure = r.get("structure", {}) or {}

        return {
            "status": "success",
            "data": {
                "uuid": r.get("uuid", ""),
                "unii": r.get("approvalID") or r.get("unii", ""),
                "name": r.get("_name", ""),
                "substanceClass": r.get("substanceClass", ""),
                "status": r.get("status", ""),
                "structure": {
                    "smiles": structure.get("smiles", ""),
                    "formula": structure.get("formula", ""),
                    "molfile": structure.get("molfile", ""),
                    "inchiKey": structure.get("inchiKey", ""),
                    "charge": structure.get("charge", ""),
                    "mwt": structure.get("mwt", ""),
                },
                "names": all_names[:20],
                "codes": all_codes,
            },
            "metadata": {"unii": unii},
        }

    # ------------------------------------------------------------------
    # operation: get_structure
    # ------------------------------------------------------------------

    def _get_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        unii = arguments.get("unii") or arguments.get("id")
        if not unii:
            return {
                "status": "error",
                "error": "Provide 'unii' (e.g., 'R16CO5Y76E' for aspirin).",
            }

        result = self._api_get(
            f"{GSRS_BASE}/substances/{unii.strip().upper()}/structure"
        )
        if not result["ok"]:
            result.pop("ok", None)
            return {"status": "error", **result}

        s = result["data"]
        if not isinstance(s, dict) or not s.get("id"):
            return {
                "status": "error",
                "error": f"No structure found for UNII: {unii}. This may be a non-chemical substance (protein, mixture, etc.).",
            }

        return {
            "status": "success",
            "data": {
                "id": s.get("id", ""),
                "smiles": s.get("smiles", ""),
                "formula": s.get("formula", ""),
                "molfile": s.get("molfile", ""),
                "inchiKey": s.get("inchiKey", ""),
                "mwt": s.get("mwt", ""),
                "charge": s.get("charge", ""),
                "stereoChemistry": s.get("stereoChemistry", ""),
                "opticalActivity": s.get("opticalActivity", ""),
                "atropisomerism": s.get("atropisomerism", ""),
            },
            "metadata": {"unii": unii},
        }
