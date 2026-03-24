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

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Feature-68A-004: auto-prepend 'eq.' to PostgREST filter params if user
        # provides a plain value like 'CYP2D6' instead of 'eq.CYP2D6'.
        normalized = dict(args)
        if "genesymbol" not in normalized:
            alias = normalized.pop("gene_symbol", None) or normalized.pop("gene", None)
            if alias:
                normalized["genesymbol"] = alias
        for key in self._FILTER_PARAMS:
            val = normalized.get(key)
            if val and isinstance(val, str):
                if not any(val.startswith(op) for op in _POSTGREST_OPS):
                    normalized[key] = f"eq.{val}"
        return super()._build_params(normalized)
