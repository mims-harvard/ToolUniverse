"""
CPIC Search Gene-Drug Pairs Tool.

Extends BaseRESTTool with automatic PostgREST operator normalization so users
can pass plain gene symbols (e.g., 'CYP2D6') instead of 'eq.CYP2D6'.
"""

from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

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
