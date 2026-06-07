"""
MARRVEL tools for ToolUniverse — aggregated human gene & disease data.

MARRVEL (Model organism Aggregated Resources for Rare Variant ExpLoration, BCM)
aggregates human gene/disease annotation from many sources (OMIM, HGNC, Ensembl,
Entrez, UniProt, Pharos) behind one API. These tools expose the human gene-level
endpoints used in rare-disease / Mendelian variant triage.

API: http://api.marrvel.org/data  (public, no authentication, JSON)
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MARRVEL_BASE = "http://api.marrvel.org/data"
HUMAN_TAXON = "9606"


@register_tool("MARRVELGeneTool")
class MARRVELGeneTool(BaseTool):
    """Aggregated identity/annotation for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return {"status": "error", "error": "'symbol' (e.g. 'CFTR') is required"}

        url = f"{MARRVEL_BASE}/gene/taxonId/{HUMAN_TAXON}/symbol/{symbol}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "total_results": 0,
                        "query_symbol": symbol,
                        "note": f"No MARRVEL gene record for '{symbol}'.",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MARRVEL request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MARRVEL request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "MARRVEL returned a non-JSON response"}

        if not isinstance(rec, dict) or not rec:
            return {
                "status": "success",
                "data": {},
                "metadata": {"total_results": 0, "query_symbol": symbol},
            }
        xref = rec.get("xref", {}) or {}
        return {
            "status": "success",
            "data": {
                "symbol": rec.get("symbol"),
                "name": rec.get("name"),
                "entrez_id": rec.get("entrezId"),
                "hgnc_id": xref.get("hgncId"),
                "omim_id": xref.get("omimId"),
                "ensembl_id": xref.get("ensemblId"),
                "uniprot_id": rec.get("uniprotKBId"),
                "chromosome": rec.get("chr"),
                "location": rec.get("location"),
                "type": rec.get("type"),
                "aliases": rec.get("alias", []),
                "prev_symbols": rec.get("prevSymbols", []),
                "summary": rec.get("entrezSummary"),
            },
            "metadata": {
                "total_results": 1,
                "query_symbol": symbol,
                "source": "MARRVEL (aggregated)",
            },
        }


@register_tool("MARRVELOmimTool")
class MARRVELOmimTool(BaseTool):
    """OMIM phenotype/disease associations for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return {"status": "error", "error": "'symbol' (e.g. 'CFTR') is required"}

        url = f"{MARRVEL_BASE}/omim/gene/symbol/{symbol}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {"total_results": 0, "query_symbol": symbol},
                }
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MARRVEL request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MARRVEL request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "MARRVEL returned a non-JSON response"}

        phenos = []
        if isinstance(payload, dict):
            phenos = payload.get("phenotypes", []) or []
        elif isinstance(payload, list):
            phenos = payload
        results = [
            {
                "gene_mim_number": p.get("mimNumber"),
                "phenotype": p.get("phenotype"),
                "phenotype_mim_number": p.get("phenotypeMimNumber"),
                "inheritance": p.get("phenotypeInheritance"),
                "phenotypic_series": p.get("phenotypicSeriesNumber"),
            }
            for p in phenos
            if isinstance(p, dict)
        ]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "query_symbol": symbol,
                "source": "MARRVEL / OMIM",
            },
        }
