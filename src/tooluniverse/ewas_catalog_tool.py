# ewas_catalog_tool.py
"""
EWAS Catalog tool for ToolUniverse.

The EWAS Catalog (MRC-IEU, Bristol) aggregates published epigenome-wide
association study results: which CpG sites' methylation is associated with
which trait, in which tissue, cohort, and effect size. ToolUniverse has no
methylation-association layer at all today, only GWAS-style variant
association (GWAS Catalog, PheWAS).

The API's `trait` search has no result cap and returns its entire match set
in one response; a broad query like trait='smoking' took ~80s and 22 MB in
testing. This tool exposes only `cpg` and `gene` search, both single-digit-
seconds even for heavily studied genes, and truncates client-side.

API: http://ewascatalog.org/api/
No authentication required.
"""

from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

EWAS_CATALOG_URL = "http://ewascatalog.org/api/"

_NUMERIC_FIELDS = {"p", "beta", "se"}
_INT_FIELDS = {"n", "n_cohorts"}


def _coerce(field: str, value: Any) -> Any:
    """Convert the catalog's string-typed numeric fields."""
    if value is None or value == "":
        return None
    if field in _NUMERIC_FIELDS:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if field in _INT_FIELDS:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    return value


@register_tool("EWASCatalogTool")
class EWASCatalogTool(BaseTool):
    """
    Tool for querying the EWAS Catalog of epigenome-wide association results.

    Supports looking up all published associations for a CpG site or a gene,
    ranked by significance.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_by_cpg"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EWAS Catalog lookup."""
        try:
            if self.operation == "search_by_cpg":
                return self._search(arguments, "cpg", "cpg_id")
            if self.operation == "search_by_gene":
                return self._search(arguments, "gene", "gene_symbol")
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EWAS Catalog request timed out after {self.timeout}s. "
                "Heavily studied genes (e.g. AHRR, F2RL3) can be slow.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the EWAS Catalog. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"EWAS Catalog returned HTTP {code}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "EWAS Catalog returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying EWAS Catalog: {str(e)}",
            }

    def _search(
        self, arguments: Dict[str, Any], api_param: str, arg_name: str
    ) -> Dict[str, Any]:
        """Query by CpG id or gene symbol and rank hits by significance."""
        term = (arguments.get(arg_name) or "").strip()
        if not term:
            example = "cg05575921 (AHRR)" if api_param == "cpg" else "AHRR"
            return {
                "status": "error",
                "error": f"{arg_name} is required, e.g. '{example}'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        limit = min(limit, 200)

        response = requests.get(
            EWAS_CATALOG_URL, params={api_param: term}, timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        field_names: List[str] = payload.get("fields") or []
        raw_rows = payload.get("results") or []

        if not raw_rows:
            return {
                "status": "error",
                "error": f"No EWAS Catalog associations found for {arg_name}="
                f"'{term}'.",
            }

        rows = [
            {name: _coerce(name, val) for name, val in zip(field_names, row)}
            for row in raw_rows
        ]
        rows.sort(key=lambda r: r.get("p") if r.get("p") is not None else 1.0)

        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                arg_name: term,
                "total_matching": len(rows),
                "returned": len(rows[:limit]),
                "note": "Sorted by p-value ascending (most significant first). "
                "beta is the effect size in outcome_units per exposure_units.",
                "source": "EWAS Catalog (MRC-IEU)",
            },
        }
