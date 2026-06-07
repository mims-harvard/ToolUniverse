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


def _names(items: Any) -> List[str]:
    return (
        [i.get("name") for i in items if isinstance(i, dict) and i.get("name")]
        if isinstance(items, list)
        else []
    )


def _evidence_counts(researches: Any) -> Dict[str, int]:
    if not isinstance(researches, dict):
        return {}
    return {k: (len(v) if isinstance(v, list) else v) for k, v in researches.items()}


def _fetch_json(path: str, timeout: int, params: Dict[str, Any] = None) -> Any:
    """GET a JSON resource from Open Genes.

    Returns the parsed JSON on success, or a {"status": "error", ...} dict on
    any network/parse failure so callers can return it directly.
    """
    try:
        resp = requests.get(
            f"{OPEN_GENES_BASE}/{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
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
        "disease_categories": _names(g.get("diseaseCategories")),
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

        g = _fetch_json(f"gene/{symbol}", self.timeout)
        if isinstance(g, dict) and g.get("status") == "error":
            return g

        # Unknown symbols return a string/error page rather than a gene object.
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
