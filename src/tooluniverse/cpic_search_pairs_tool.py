"""
CPIC Search Gene-Drug Pairs Tool.

Extends BaseRESTTool with automatic PostgREST operator normalization so users
can pass plain gene symbols (e.g., 'CYP2D6') instead of 'eq.CYP2D6'.
"""

from typing import Any, Dict

import requests

from .base_rest_tool import BaseRESTTool
from .base_tool import BaseTool
from .tool_registry import register_tool

_CPIC_API = "https://api.cpicpgx.org/v1"


def _resolve_drug_to_guideline_id(drug_name: str) -> int | None:
    """Look up CPIC guideline ID for a drug name via CPIC API."""
    try:
        r = requests.get(
            f"{_CPIC_API}/drug",
            params={"select": "name,guidelineid", "name": f"ilike.*{drug_name}*"},
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if rows and rows[0].get("guidelineid"):
            return rows[0]["guidelineid"]
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
            guideline_id = _resolve_drug_to_guideline_id(drug)
            if guideline_id is None:
                return {
                    "status": "error",
                    "error": (
                        f"No CPIC guideline found for drug '{drug}'. "
                        "Use CPIC_list_guidelines to find valid guideline IDs."
                    ),
                }

        limit = arguments.get("limit", 50) or 50
        offset = arguments.get("offset", 0) or 0

        try:
            url = f"{_CPIC_API}/recommendation"
            params = {
                "select": "*,drug(name)",
                "guidelineid": f"eq.{guideline_id}",
                "limit": limit,
                "offset": offset,
            }
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            return {
                "status": "success",
                "data": {
                    "guideline_id": guideline_id,
                    "recommendations": data,
                    "count": len(data),
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CPIC API error: {e}"}


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
