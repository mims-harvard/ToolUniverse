"""
FDA GSRS Tool

Substance registration and identification tools using the FDA Global Substance
Registration System (GSRS / Substance Registration System) public API:

  - search_substances:       Search for substances by name, UNII, or InChIKey
  - get_substance:           Get full substance record by UNII code or UUID
  - get_structure:           Get structure (SMILES, molfile, formula) for a substance
  - get_substance_relationships: Get the relationship graph (salts/solvates,
                             impurities, metabolites, prodrug links, active moiety)
                             plus regulatory references from the ?view=full record

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
      - get_substance_relationships: Relationship graph + references (view=full)
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
        if op == "get_substance_relationships":
            return self._get_substance_relationships(arguments)
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

    # ------------------------------------------------------------------
    # operation: get_substance_relationships
    # ------------------------------------------------------------------

    def _get_substance_relationships(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the relationship graph + regulatory references for a substance.

        The default substance view leaves the ``relationships`` and
        ``references`` collections as unexpanded link stubs. Requesting
        ``?view=full`` materializes the full graph (salts/solvates, impurities,
        metabolites, prodrug->metabolite links, active moiety, ...).
        """
        unii = arguments.get("unii") or arguments.get("id")
        if not unii:
            return {
                "status": "error",
                "error": "Provide 'unii' (e.g., 'R16CO5Y76E' for aspirin).",
            }

        rel_type_filter = arguments.get("relationship_type") or arguments.get("type")
        include_references = arguments.get("include_references", True)
        max_refs = min(int(arguments.get("max_references", 100)), 500)

        result = self._api_get(
            f"{GSRS_BASE}/substances/{unii.strip().upper()}",
            {"view": "full"},
        )
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

        raw_rels = r.get("relationships", []) or []
        relationships = []
        type_counts: Dict[str, int] = {}
        for rel in raw_rels:
            rel_type = rel.get("type", "")
            if (
                rel_type_filter
                and rel_type_filter.strip().upper() not in rel_type.upper()
            ):
                continue
            related = rel.get("relatedSubstance", {}) or {}
            relationships.append(
                {
                    "type": rel_type,
                    "relatedSubstanceName": related.get("name", "")
                    or related.get("refPname", ""),
                    "relatedSubstanceUnii": related.get("approvalID", "")
                    or related.get("linkingID", ""),
                    "relatedSubstanceClass": related.get("substanceClass", ""),
                    "interactionType": rel.get("interactionType", ""),
                    "qualification": rel.get("qualification", ""),
                    "amount": self._format_amount(rel.get("amount")),
                    "comments": rel.get("comments", ""),
                }
            )
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        references = []
        raw_refs = r.get("references", []) or []
        if include_references:
            for ref in raw_refs[:max_refs]:
                references.append(
                    {
                        "docType": ref.get("docType", ""),
                        "citation": ref.get("citation", ""),
                        "publicDomain": ref.get("publicDomain", False),
                        "tags": ref.get("tags", []),
                    }
                )

        return {
            "status": "success",
            "data": {
                "uuid": r.get("uuid", ""),
                "unii": r.get("approvalID") or r.get("unii", ""),
                "name": r.get("_name", ""),
                "substanceClass": r.get("substanceClass", ""),
                "relationships": relationships,
                "references": references,
            },
            "metadata": {
                "unii": unii,
                "relationship_count": len(relationships),
                "relationship_type_counts": type_counts,
                "total_relationships": len(raw_rels),
                "reference_count": len(references),
                "total_references": len(raw_refs),
                "relationship_type_filter": rel_type_filter or None,
            },
        }

    @staticmethod
    def _format_amount(amount: Any) -> str:
        """Render a GSRS amount object as a short human-readable string."""
        if not isinstance(amount, dict) or not amount:
            return ""
        parts = []
        if amount.get("average") not in (None, ""):
            parts.append(str(amount["average"]))
        elif amount.get("highLimit") not in (None, "") or amount.get(
            "lowLimit"
        ) not in (None, ""):
            low = amount.get("lowLimit", "")
            high = amount.get("highLimit", "")
            parts.append(f"{low}-{high}".strip("-"))
        elif amount.get("nonNumericValue"):
            parts.append(str(amount["nonNumericValue"]))
        units = amount.get("units", "")
        amt_type = amount.get("type", "")
        rendered = " ".join(p for p in parts if p)
        if units:
            rendered = f"{rendered} {units}".strip()
        if amt_type:
            rendered = f"{rendered} ({amt_type})".strip()
        return rendered
