"""
MARRVEL tools for ToolUniverse — aggregated human gene & disease data.

MARRVEL (Model organism Aggregated Resources for Rare Variant ExpLoration, BCM)
aggregates human gene/disease annotation from many sources (OMIM, HGNC, Ensembl,
Entrez, UniProt, Pharos) behind one API. These tools expose the human gene-level
endpoints used in rare-disease / Mendelian variant triage.

API: http://api.marrvel.org/data  (public, no authentication, JSON)
"""

from typing import Any, Dict, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MARRVEL_BASE = "http://api.marrvel.org/data"
HUMAN_TAXON = "9606"


def _resolve_symbol(
    arguments: Dict[str, Any],
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    # Fix-R32B-4: unlike most other gene-input tools in this codebase
    # (DGIdb, OpenTargets, ensembl_lookup_gene, ...), these tools only
    # accepted the bare "symbol" param with no gene/gene_symbol alias --
    # confirmed live that the natural-language guess {"gene_symbol":
    # "PTPN22"} failed schema validation entirely.
    supplied = []
    for name in ("symbol", "gene_symbol", "gene"):
        if name not in arguments or arguments[name] is None:
            continue
        value = arguments[name]
        if not isinstance(value, str) or not value.strip():
            return None, {
                "status": "error",
                "error": f"'{name}' must be a non-empty string",
            }
        supplied.append((name, value.strip()))
    if not supplied:
        return None, {
            "status": "error",
            "error": "'symbol' (or gene_symbol/gene alias) is required",
        }
    normalized = {value.upper() for _, value in supplied}
    if len(normalized) != 1:
        return None, {
            "status": "error",
            "error": "Conflicting gene symbols were supplied through aliases",
        }
    # MARRVEL's gene endpoint is case-sensitive and returns HTTP 200 with an
    # empty object for a lowercase HGNC symbol, so canonicalize before request.
    return next(iter(normalized)), None


@register_tool("MARRVELGeneTool")
class MARRVELGeneTool(BaseTool):
    """Aggregated identity/annotation for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol, argument_error = _resolve_symbol(arguments)
        if argument_error:
            return argument_error
        assert symbol is not None

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
                        "transport_security": "unencrypted_http_upstream",
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
                "metadata": {
                    "total_results": 0,
                    "query_symbol": symbol,
                    "transport_security": "unencrypted_http_upstream",
                },
            }
        returned_symbol = rec.get("symbol")
        if (
            not isinstance(returned_symbol, str)
            or returned_symbol.upper() != symbol.upper()
        ):
            return {
                "status": "error",
                "error": "MARRVEL returned a different gene than requested",
                "requested_symbol": symbol,
                "returned_symbol": returned_symbol,
            }
        xref = rec.get("xref", {}) or {}
        if not isinstance(xref, dict):
            return {"status": "error", "error": "MARRVEL returned malformed xref data"}
        list_fields = (
            "alias",
            "prevSymbols",
            "pharosLigandsIds",
            "pharosLegandsIds",
            "pharosTargetIds",
        )
        if any(not isinstance(rec.get(field, []), list) for field in list_fields):
            return {
                "status": "error",
                "error": "MARRVEL returned a malformed list-valued gene field",
            }
        direct_hgnc = rec.get("hgncId")
        xref_hgnc = xref.get("hgncId")
        if (
            direct_hgnc is not None
            and xref_hgnc is not None
            and str(direct_hgnc) != str(xref_hgnc)
        ):
            return {
                "status": "error",
                "error": "MARRVEL returned conflicting HGNC identifiers",
                "direct_hgnc_id": direct_hgnc,
                "xref_hgnc_id": xref_hgnc,
            }
        pharos_ligands = rec.get("pharosLigandsIds", [])
        legacy_pharos_ligands = rec.get("pharosLegandsIds", [])
        if pharos_ligands and legacy_pharos_ligands != pharos_ligands:
            return {
                "status": "error",
                "error": "MARRVEL returned conflicting Pharos ligand ID fields",
            }
        return {
            "status": "success",
            "data": {
                "symbol": returned_symbol,
                "name": rec.get("name"),
                "description": rec.get("description"),
                "entrez_id": rec.get("entrezId"),
                "hgnc_id": str(xref_hgnc or direct_hgnc)
                if (xref_hgnc is not None or direct_hgnc is not None)
                else None,
                # Fix-R78A-1: MARRVEL's own /gene/taxonId/.../symbol/... endpoint
                # returns a bogus small placeholder integer in xref.omimId (e.g.
                # "1" for BRCA1/EGFR/APOE/MYH7/TP53, "6" for CFTR/PTEN) instead
                # of the real 6-digit OMIM MIM number -- confirmed live across
                # multiple genes, so this isn't a per-gene data gap. The correct
                # gene_mim_number is only available from MARRVEL's dedicated OMIM
                # endpoint, exposed here as MARRVEL_get_omim_phenotypes -- point
                # callers there instead of surfacing this misleading value.
                "ensembl_id": xref.get("ensemblId"),
                "uniprot_id": rec.get("uniprotKBId"),
                "taxon_id": rec.get("taxonId"),
                "chromosome": rec.get("chr"),
                "location": rec.get("location"),
                "grch38_start": rec.get("grch38Start"),
                "grch38_stop": rec.get("grch38Stop"),
                "grch39_stop_upstream": rec.get("grch39Stop"),
                "hg19_chromosome": rec.get("hg19Chr"),
                "hg19_start": rec.get("hg19Start"),
                "hg19_stop": rec.get("hg19Stop"),
                "type": rec.get("type"),
                "aliases": rec.get("alias", []),
                "prev_symbols": rec.get("prevSymbols", []),
                "summary": rec.get("entrezSummary"),
                "status": rec.get("status"),
                "last_modified": rec.get("lastModified"),
                "pharos_ligand_ids": pharos_ligands or legacy_pharos_ligands,
                "pharos_target_ids": rec.get("pharosTargetIds", []),
            },
            "metadata": {
                "total_results": 1,
                "query_symbol": symbol,
                "source": "MARRVEL (aggregated)",
                "returned_symbol_verified": True,
                "source_record_complete": True,
                "transport_security": "unencrypted_http_upstream",
            },
        }


@register_tool("MARRVELOmimTool")
class MARRVELOmimTool(BaseTool):
    """OMIM phenotype/disease associations for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol, argument_error = _resolve_symbol(arguments)
        if argument_error:
            return argument_error
        assert symbol is not None

        url = f"{MARRVEL_BASE}/omim/gene/symbol/{symbol}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "total_results": 0,
                        "phenotype_count": 0,
                        "phenotype_records_complete": True,
                        "allelic_variant_count": 0,
                        "allelic_variants_returned": False,
                        "query_symbol": symbol,
                        "transport_security": "unencrypted_http_upstream",
                    },
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
        record_metadata = {}
        allelic_variants = []
        if isinstance(payload, dict):
            phenos = payload.get("phenotypes", [])
            allelic_variants = payload.get("allelicVariants", [])
            if not isinstance(phenos, list) or not isinstance(allelic_variants, list):
                return {
                    "status": "error",
                    "error": "MARRVEL returned malformed OMIM phenotype or allelic-variant data",
                }
            record_metadata = {
                "gene_mim_number": payload.get("mimNumber"),
                "title": payload.get("title"),
                "description": payload.get("description"),
                "status": payload.get("status"),
                "last_update": payload.get("lastUpdate"),
            }
        elif isinstance(payload, list):
            phenos = payload
        else:
            return {
                "status": "error",
                "error": "MARRVEL returned an unexpected OMIM response shape",
            }
        if any(not isinstance(p, dict) for p in phenos):
            return {
                "status": "error",
                "error": "MARRVEL returned a malformed OMIM phenotype record",
            }
        results = []
        for phenotype in phenos:
            results.append(
                {
                    "gene_mim_number": phenotype.get("mimNumber"),
                    "phenotype": phenotype.get("phenotype"),
                    "phenotype_mim_number": phenotype.get("phenotypeMimNumber"),
                    "inheritance": phenotype.get("phenotypeInheritance"),
                    "phenotype_mapping_key": phenotype.get("phenotypeMappingKey"),
                    "phenotypic_series": phenotype.get("phenotypicSeriesNumber"),
                }
            )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "phenotype_count": len(phenos),
                "phenotype_records_complete": True,
                "omim_record": record_metadata,
                "allelic_variant_count": len(allelic_variants),
                "allelic_variants_returned": False,
                "allelic_variants_note": (
                    "This phenotype-focused tool reports the source count but does not "
                    "return OMIM allelic-variant narratives."
                ),
                "query_symbol": symbol,
                "source": "MARRVEL / OMIM",
                "transport_security": "unencrypted_http_upstream",
            },
        }
