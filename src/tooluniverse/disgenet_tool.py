"""
DisGeNET API tool for ToolUniverse.

DisGeNET is one of the largest public collections of genes and variants
associated with human diseases, aggregating data from multiple sources.

API Documentation: https://api.disgenet.com/
Requires API key: Register at https://www.disgenet.com/

Note: the DisGeNET v1 API exposes gene/variant-disease associations through the
`/gda/summary` and `/vda/summary` endpoints using QUERY parameters
(`gene_symbol`, `gene_ncbi_id`, `disease`, `variant`), authenticated with an
`Authorization: <api_key>` header (no "Bearer " prefix). Academic API keys can
only access CURATED sources (CLINGEN, CLINVAR, ORPHANET, GENCC, UNIPROT, ...).
"""

import os
import re
import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for DisGeNET API
DISGENET_API_URL = "https://api.disgenet.com/api/v1"

# A disease passed as a bare UMLS CUI looks like "C0006142".
_CUI_RE = re.compile(r"^C\d+$")

# Fix-R13B-2: DisGeNET's /summary endpoints emit one "warning" per
# *unset* optional filter param (e.g. "min_pli > The parameter value is
# unspecified or not a double number."), regardless of whether the
# caller ever intended to supply it. A plain gene-only query returns
# ~30 of these alongside the one warning that's actually actionable
# (the academic-key CURATED-sources-only note), burying it. These are
# recognizable by their fixed "unspecified" phrasing and are dropped;
# any other warning text (real data-quality notes) is kept.
_UNSET_PARAM_WARNING_RE = re.compile(
    r"is (?:empty / unspecified|unspecified or not an? [\w\s]+)\.?\s*$"
)


def _drop_unset_param_noise(warnings: List[str]) -> List[str]:
    return [w for w in warnings if not _UNSET_PARAM_WARNING_RE.search(w)]


@register_tool("DisGeNETTool")
class DisGeNETTool(BaseTool):
    """
    Tool for querying DisGeNET gene-disease association database.

    Supports:
    - Gene-disease associations (GDAs)
    - Variant-disease associations (VDAs)
    - Disease -> associated genes

    Requires API key via DISGENET_API_KEY environment variable.
    Register for free at https://www.disgenet.com/
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})
        self.api_key = os.environ.get("DISGENET_API_KEY", "")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        The DisGeNET v1 API expects the raw key in the Authorization header
        (NOT an OAuth "Bearer <key>" form).
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "ToolUniverse/DisGeNET",
        }
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _normalize_disease(disease: str):
        """Return a DisGeNET-acceptable disease code, or None if the input is a
        free-text name (which the summary endpoint does not accept)."""
        d = (disease or "").strip()
        if not d:
            return None
        if d.upper().startswith("UMLS_"):
            return "UMLS_" + d[5:]
        if _CUI_RE.match(d):
            return "UMLS_" + d
        # Already a vocabulary-prefixed code (e.g. MONDO_..., DO_..., HPO_...)
        if "_" in d and d.split("_", 1)[0].isupper():
            return d
        return None

    @staticmethod
    def _cui_format_error(disease: str) -> Dict[str, Any]:
        """Feature-14C-01: shared by every '{disease}' is not a UMLS CUI'
        error path. 'C0006142' is a fixed format example (breast cancer),
        never a resolution of the caller's own input -- state that
        explicitly so it can't be mistaken for a dynamically-resolved CUI."""
        return {
            "status": "error",
            "error": (
                f"'{disease}' is not a UMLS CUI. Resolve '{disease}' to its "
                f"own CUI via umls_search_concepts -- 'C0006142' (breast "
                f"cancer) is only a format example and unrelated to "
                f"'{disease}'."
            ),
        }

    def _query_summary(self, kind: str, query: Dict[str, Any]):
        """Call /{gda,vda}/summary with query params. Returns (payload, warnings).
        Raises requests exceptions on HTTP error (handled by callers)."""
        params = {"page_number": 0}
        params.update({k: v for k, v in query.items() if v not in (None, "")})
        response = requests.get(
            f"{DISGENET_API_URL}/{kind}/summary",
            params=params,
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        payload = body.get("payload") or []
        warnings = _drop_unset_param_noise(body.get("warnings") or [])
        return payload, warnings

    @staticmethod
    def _fmt_gda(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "gene_symbol": row.get("symbolOfGene"),
            "gene_ncbi_id": row.get("geneNcbiID"),
            "disease_name": row.get("diseaseName"),
            "disease_umls_cui": row.get("diseaseUMLSCUI"),
            "score": row.get("score"),
            "n_pmids": row.get("numPMIDs"),
            "ei": row.get("ei"),
        }

    @staticmethod
    def _fmt_vda(row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "variant": row.get("variantStrID"),
            "gene_symbol": row.get("symbolOfGene"),
            "disease_name": row.get("diseaseName"),
            "disease_umls_cui": row.get("diseaseUMLSCUI"),
            "score": row.get("score"),
            "n_pmids": row.get("numPMIDs"),
        }

    @staticmethod
    def _apply_filters(rows: List[Dict[str, Any]], min_score, limit):
        if min_score is not None:
            rows = [
                r
                for r in rows
                if (r.get("score") is not None and r["score"] >= min_score)
            ]
        if limit:
            rows = rows[: int(limit)]
        return rows

    def _declared_limit_default(self, fallback):
        # _gene_disease and _disease_genes each back 2 registered tool names
        # (e.g. DisGeNET_search_gene default=10 vs DisGeNET_get_gda
        # default=25, both routed through _gene_disease). Read the
        # per-instance declared default instead of hardcoding one limit for
        # both, or the tool with the smaller declared default silently
        # returns more rows than documented whenever `limit` is omitted.
        return (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("limit", {})
            .get("default", fallback)
        )

    def _err(self, e) -> Dict[str, Any]:
        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
            code = e.response.status_code
            if code in (401, 403):
                return {
                    "status": "error",
                    "error": "DisGeNET API key invalid or unauthorized for this resource (academic keys only access CURATED sources).",
                }
            return {"status": "error", "error": f"DisGeNET HTTP error: {code}"}
        return {"status": "error", "error": f"DisGeNET request failed: {str(e)}"}

    # --------------------------------------------------------------- dispatch

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DisGeNET API call based on operation type."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "DisGeNET API key required. Set DISGENET_API_KEY environment variable. Register at https://www.disgenet.com/",
            }

        operation = arguments.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()

        if operation in ("search_gene", "get_gda"):
            return self._gene_disease(arguments)
        elif operation in ("search_disease", "get_disease_genes"):
            return self._disease_genes(arguments)
        elif operation == "get_vda":
            return self._variant_disease(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_gene, search_disease, get_gda, get_vda, get_disease_genes",
            }

    # ---------------------------------------------------------------- operations

    def _gene_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Gene-disease associations by gene symbol (or NCBI gene id)."""
        gene = (arguments.get("gene") or "").strip()
        disease = (arguments.get("disease") or "").strip()
        if not gene and not disease:
            return {
                "status": "error",
                "error": "Provide 'gene' (symbol or NCBI id) or 'disease' (UMLS CUI).",
            }

        query: Dict[str, Any] = {}
        if gene:
            if gene.isdigit():
                query["gene_ncbi_id"] = gene
            else:
                query["gene_symbol"] = gene
        if disease:
            code = self._normalize_disease(disease)
            if code is None:
                return self._cui_format_error(disease)
            query["disease"] = code
        if arguments.get("source"):
            query["source"] = arguments["source"]

        try:
            payload, warnings = self._query_summary("gda", query)
        except Exception as e:  # noqa: BLE001 - never raise out of run()
            return self._err(e)

        rows = self._apply_filters(
            [self._fmt_gda(r) for r in payload],
            arguments.get("min_score"),
            arguments.get("limit", self._declared_limit_default(25)),
        )
        metadata: Dict[str, Any] = {
            "source": "DisGeNET GDA",
            "warnings": warnings,
            "note": "Academic keys return CURATED sources only.",
        }
        # Fix-R13B-2: DisGeNET matches gene_symbol exactly, so a legacy/
        # alias symbol (e.g. 'CARD15', the old official symbol for NOD2)
        # silently returns an empty list with no hint that a symbol
        # mismatch -- not a real absence of associations -- is the cause.
        # Confirmed live: gene='CARD15' -> 0 associations, gene='NOD2' ->
        # real Crohn/Blau-syndrome associations. We can't safely
        # auto-resolve the alias ourselves (that needs a maintained
        # gene-symbol synonym table we don't have), so just flag the
        # ambiguity instead of leaving an empty result unexplained.
        if gene and not rows and not gene.isdigit():
            metadata["note"] += (
                f" No associations found for gene symbol '{gene}'. DisGeNET "
                "matches the current HGNC-approved symbol only, not older "
                "aliases -- if this might be a legacy/alias symbol, resolve "
                "it to its current official symbol first (e.g. via "
                "NCBIGene_search_genes or HGNC) and retry."
            )
        return {
            "status": "success",
            "data": {
                "gene": gene or None,
                "disease": disease or None,
                "associations": rows,
                "count": len(rows),
            },
            "metadata": metadata,
        }

    def _disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """All genes associated with a disease (UMLS CUI)."""
        disease = (arguments.get("disease") or "").strip()
        if not disease:
            return {
                "status": "error",
                "error": "Missing required parameter: disease (UMLS CUI, e.g. 'C0006142' for breast cancer -- an example format, not a default value).",
            }
        code = self._normalize_disease(disease)
        if code is None:
            return {
                "status": "error",
                "error": f"'{disease}' is not a UMLS CUI. Resolve '{disease}' to its own CUI via umls_search_concepts -- 'C0006142' (breast cancer) is only a format example and unrelated to '{disease}'.",
            }

        query: Dict[str, Any] = {"disease": code}
        if arguments.get("source"):
            query["source"] = arguments["source"]
        try:
            payload, warnings = self._query_summary("gda", query)
        except Exception as e:  # noqa: BLE001
            return self._err(e)

        genes, seen = [], set()
        for row in payload:
            sym = row.get("symbolOfGene")
            if sym and sym not in seen:
                seen.add(sym)
                genes.append(
                    {
                        "symbol": sym,
                        "ncbi_id": row.get("geneNcbiID"),
                        "score": row.get("score"),
                        "n_pmids": row.get("numPMIDs"),
                    }
                )
        genes = self._apply_filters(
            genes,
            arguments.get("min_score"),
            arguments.get("limit", self._declared_limit_default(50)),
        )
        return {
            "status": "success",
            "data": {
                "disease": disease,
                "disease_code": code,
                "genes": genes,
                "gene_count": len(genes),
            },
            "metadata": {
                "source": "DisGeNET",
                "warnings": warnings,
                "note": "Academic keys return CURATED sources only.",
            },
        }

    def _variant_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Variant-disease associations by variant rsID or gene symbol."""
        variant = (arguments.get("variant") or "").strip()
        gene = (arguments.get("gene") or "").strip()
        if not variant and not gene:
            return {
                "status": "error",
                "error": "Provide 'variant' (rsID) or 'gene' (symbol).",
            }
        query: Dict[str, Any] = {}
        if variant:
            query["variant"] = variant
        elif gene:
            query["gene_symbol"] = gene
        try:
            payload, warnings = self._query_summary("vda", query)
        except Exception as e:  # noqa: BLE001
            return self._err(e)
        rows = self._apply_filters(
            [self._fmt_vda(r) for r in payload],
            arguments.get("min_score"),
            arguments.get("limit", 25),
        )
        return {
            "status": "success",
            "data": {
                "variant": variant or None,
                "gene": gene or None,
                "associations": rows,
                "count": len(rows),
            },
            "metadata": {
                "source": "DisGeNET VDA",
                "warnings": warnings,
                "note": "Academic keys return CURATED sources only.",
            },
        }
