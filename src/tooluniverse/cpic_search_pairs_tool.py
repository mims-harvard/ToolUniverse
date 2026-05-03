"""
CPIC Search Gene-Drug Pairs Tool.

Extends BaseRESTTool with automatic PostgREST operator normalization so users
can pass plain gene symbols (e.g., 'CYP2D6') instead of 'eq.CYP2D6'.
"""

from typing import Any, Dict, Optional, Tuple

import requests

from .base_rest_tool import BaseRESTTool
from .base_tool import BaseTool
from .tool_registry import register_tool

_CPIC_API = "https://api.cpicpgx.org/v1"


def _resolve_drug_to_guideline_id(
    drug_name: str,
) -> Optional[Tuple[int, Optional[str]]]:
    """Look up CPIC guideline ID and RxNorm ID for a drug name via CPIC API.

    Returns (guideline_id, rxnorm_id) tuple, or None if not found.
    rxnorm_id may be None if the drug has no RxNorm entry.
    """
    try:
        r = requests.get(
            f"{_CPIC_API}/drug",
            params={
                "select": "name,guidelineid,rxnormid",
                "name": f"ilike.*{drug_name}*",
            },
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if rows and rows[0].get("guidelineid"):
            return rows[0]["guidelineid"], rows[0].get("rxnormid")
    except Exception:
        pass
    return None


@register_tool("CPICGetRecommendationsTool")
class CPICGetRecommendationsTool(BaseTool):
    """
    Get CPIC dosing recommendations by guideline_id, or auto-resolve from drug name.

    Accepts either a numeric guideline_id directly, or a drug name that is
    resolved to a guideline_id via the CPIC /drug endpoint.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        guideline_id = arguments.get("guideline_id")
        rxnorm_id: Optional[str] = None

        if guideline_id is None:
            drug = arguments.get("drug") or arguments.get("drug_name")
            if not drug:
                return {
                    "status": "error",
                    "error": (
                        "Either guideline_id or drug name is required. "
                        "Use CPIC_list_guidelines to browse available guidelines."
                    ),
                }
            result = _resolve_drug_to_guideline_id(drug)
            if result is None:
                return {
                    "status": "error",
                    "error": (
                        f"No CPIC guideline found for drug '{drug}'. "
                        "Use CPIC_list_guidelines to find valid guideline IDs."
                    ),
                }
            guideline_id, rxnorm_id = result

        limit = arguments.get("limit", 50) or 50
        offset = arguments.get("offset", 0) or 0

        try:
            url = f"{_CPIC_API}/recommendation"
            params: Dict[str, Any] = {
                "select": "*,drug(name)",
                "guidelineid": f"eq.{guideline_id}",
                "limit": limit,
                "offset": offset,
            }
            # Filter by specific drug within multi-drug guidelines (e.g., CYP2D6/Opioids
            # covers codeine, tramadol, hydrocodone — filter to the requested drug).
            if rxnorm_id:
                params["drugid"] = f"eq.RxNorm:{rxnorm_id}"
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            result: Dict[str, Any] = {
                "guideline_id": guideline_id,
                "recommendations": data,
                "count": len(data),
            }
            # Some guidelines use dosing algorithms rather than discrete recommendations.
            # Guideline 100425 (warfarin) is the main example — it returns 0 rows here.
            if not data:
                result["note"] = (
                    f"No discrete recommendations found for guideline {guideline_id}. "
                    "Some guidelines (e.g. warfarin, guideline 100425) use a dosing "
                    "algorithm rather than a recommendation table. "
                    "See https://cpicpgx.org/guidelines/ for the full guideline document."
                )
            return {"status": "success", "data": result}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}


@register_tool("CPICListGuidelinesTool")
class CPICListGuidelinesTool(BaseTool):
    """
    List CPIC pharmacogenomic guidelines with optional gene-symbol filtering.

    Fetches all guidelines and optionally filters client-side by gene symbol,
    since the CPIC /guideline endpoint does not support server-side gene filtering.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").upper()
        original_drug = arguments.get("drug") or arguments.get("drug_name") or ""
        drug = original_drug.lower()

        try:
            r = requests.get(
                f"{_CPIC_API}/guideline",
                params={"select": "*,drug(name)"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}

        if gene:
            data = [
                g
                for g in data
                if any(s.upper() == gene for s in (g.get("genes") or []))
            ]

        # Client-side drug name filtering (Feature-123A-003)
        if drug:
            data = [
                g
                for g in data
                if any(
                    drug in (d.get("name") or "").lower() for d in (g.get("drug") or [])
                )
            ]

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "total": len(data),
                "gene_filter": gene or None,
                "drug_filter": original_drug or None,
            },
        }


# PostgREST filter operator prefixes
_POSTGREST_OPS = (
    "eq.",
    "neq.",
    "gt.",
    "gte.",
    "lt.",
    "lte.",
    "like.",
    "ilike.",
    "is.",
    "in.(",
    "not.",
    "cs.",
    "cd.",
)


@register_tool("CPICSearchPairsTool")
class CPICSearchPairsTool(BaseRESTTool):
    """
    Search CPIC gene-drug pairs with automatic PostgREST operator normalization.

    Accepts plain gene symbols and CPIC levels (e.g., 'CYP2D6', 'A') and
    auto-prepends the required 'eq.' PostgREST operator so users do not need
    to know the PostgREST filter syntax.
    """

    # Parameters that are PostgREST column filters requiring the eq. prefix
    _FILTER_PARAMS = ("genesymbol", "cpiclevel")

    def _resolve_aliases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve gene_symbol/gene aliases to genesymbol."""
        normalized = dict(args)
        if not normalized.get("genesymbol"):
            alias = normalized.pop("gene_symbol", None) or normalized.pop("gene", None)
            if alias:
                normalized["genesymbol"] = alias
        else:
            normalized.pop("gene_symbol", None)
            normalized.pop("gene", None)
        return normalized

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Resolve aliases then auto-prepend 'eq.' to bare PostgREST filter values.
        # Only done here (not in _build_url) because the URL template already
        # embeds 'eq.' inline (e.g. ?genesymbol=eq.{genesymbol}).
        normalized = self._resolve_aliases(args)
        for key in self._FILTER_PARAMS:
            val = normalized.get(key)
            if (
                val
                and isinstance(val, str)
                and not any(val.startswith(op) for op in _POSTGREST_OPS)
            ):
                normalized[key] = f"eq.{val}"
        return super()._build_params(normalized)

    def _build_url(self, args: Dict[str, Any]) -> str:
        return super()._build_url(self._resolve_aliases(args))
