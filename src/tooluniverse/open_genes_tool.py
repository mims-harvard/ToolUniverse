"""
Open Genes tools for ToolUniverse — curated aging/longevity gene database.

Open Genes is a manually-curated database of genes associated with aging and
longevity, each backed by experimental evidence (lifespan-change studies, longevity
associations, age-related expression changes, progeria associations). These tools
look up a gene's aging profile and browse the catalog.

API: https://open-genes.com/api  (public, no authentication, JSON)
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

OPEN_GENES_BASE = "https://open-genes.com/api"


def _names(items: Any, key: str = "name") -> List[str]:
    return (
        [i.get(key) for i in items if isinstance(i, dict) and i.get(key)]
        if isinstance(items, list)
        else []
    )


def _evidence_counts(researches: Any) -> Dict[str, int]:
    if not isinstance(researches, dict):
        return {}
    return {k: (len(v) if isinstance(v, list) else v) for k, v in researches.items()}


def _fetch_json(
    path: str, timeout: int, params: Dict[str, Any] = None, not_found_ok: bool = False
) -> Any:
    """GET a JSON resource from Open Genes.

    Returns the parsed JSON on success, or a {"status": "error", ...} dict on
    any network/parse failure so callers can return it directly.

    Fix-R30D-5: for a single-resource lookup like gene/{symbol}, Open Genes
    signals "unknown symbol" via a genuine HTTP 404 (confirmed live:
    gene/FAKEGENE123 -> 404 with body {"message":"Gene FAKEGENE123 not
    found",...}) -- the same conceptual outcome as when it instead returns
    200 with a body missing the expected fields, which callers already
    handle gracefully. Without not_found_ok, a 404 was previously
    indistinguishable from a real network failure, giving two different
    envelopes for the same "not in Open Genes" case depending on which way
    the upstream happened to signal it. `not_found_ok=True` returns None on
    404 instead, letting the caller route it through its existing
    graceful-empty-result handling.
    """
    try:
        resp = requests.get(
            f"{OPEN_GENES_BASE}/{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        if not_found_ok and resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error": f"Open Genes request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"Open Genes request failed: {e}"}
    except ValueError:
        return {"status": "error", "error": "Open Genes returned a non-JSON response"}


def _summarize(g: Dict[str, Any]) -> Dict[str, Any]:
    conf = g.get("confidenceLevel")
    return {
        "symbol": g.get("symbol"),
        "name": g.get("name"),
        "ncbi_id": g.get("ncbiId"),
        "uniprot": g.get("uniprot"),
        "ensembl": g.get("ensembl"),
        "aging_mechanisms": _names(g.get("agingMechanisms")),
        "functional_clusters": _names(g.get("functionalClusters")),
        # diseaseCategories entries key their label as "icdCategoryName", not
        # "name" (confirmed live), so pass that key explicitly.
        "disease_categories": _names(g.get("diseaseCategories"), "icdCategoryName"),
        # Specific named disease associations (e.g. "Progeria", "Dilated
        # cardiomyopathy") -- a separate, more specific field from
        # diseaseCategories's broad ICD chapter groupings, and previously
        # not surfaced at all.
        "diseases": _names(g.get("diseases")),
        "confidence_level": conf.get("name") if isinstance(conf, dict) else conf,
        "expression_change": g.get("expressionChange"),
    }


@register_tool("OpenGenesGeneTool")
class OpenGenesGeneTool(BaseTool):
    """Get the aging/longevity profile of a gene by symbol from Open Genes."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return {
                "status": "error",
                "error": "'symbol' is required (e.g. 'GHR', 'FOXO3', 'TP53')",
            }

        g = _fetch_json(f"gene/{symbol}", self.timeout, not_found_ok=True)
        if isinstance(g, dict) and g.get("status") == "error":
            return g

        # Unknown symbols 404, or return a string/error page instead of a
        # gene object; both mean the same thing to a caller.
        if not isinstance(g, dict) or not g.get("symbol"):
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "query_symbol": symbol,
                    "note": f"'{symbol}' is not in Open Genes (not an annotated aging gene).",
                },
            }
        data = _summarize(g)
        data["evidence_counts"] = _evidence_counts(g.get("researches"))
        data["protein_description"] = g.get("proteinDescriptionOpenGenes") or g.get(
            "proteinDescriptionUniProt"
        )
        return {
            "status": "success",
            "data": data,
            "metadata": {"query_symbol": symbol, "source": "Open Genes"},
        }


@register_tool("OpenGenesSearchTool")
class OpenGenesSearchTool(BaseTool):
    """Browse the Open Genes catalog of aging/longevity genes (paginated)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        try:
            params["pageSize"] = max(1, min(int(arguments.get("limit") or 20), 100))
        except (TypeError, ValueError):
            params["pageSize"] = 20
        try:
            params["page"] = max(1, int(arguments.get("page") or 1))
        except (TypeError, ValueError):
            params["page"] = 1

        payload = _fetch_json("gene/search", self.timeout, params=params)
        if isinstance(payload, dict) and payload.get("status") == "error":
            return payload

        items = payload.get("items", []) if isinstance(payload, dict) else []
        opts = payload.get("options", {}) if isinstance(payload, dict) else {}
        return {
            "status": "success",
            "data": [_summarize(g) for g in items if isinstance(g, dict)],
            "metadata": {
                "total_aging_genes": opts.get("total"),
                "page": params["page"],
                "returned": len(items),
                "source": "Open Genes",
            },
        }
