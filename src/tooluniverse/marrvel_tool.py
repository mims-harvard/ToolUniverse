"""
MARRVEL tools for ToolUniverse — aggregated human gene & disease data.

MARRVEL (Model organism Aggregated Resources for Rare Variant ExpLoration, BCM)
aggregates human gene/disease annotation from many sources (OMIM, HGNC, Ensembl,
Entrez, UniProt, Pharos) behind one API. These tools expose the human gene-level
endpoints used in rare-disease / Mendelian variant triage.

API: http://api.marrvel.org/data  (public, no authentication, JSON)
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MARRVEL_BASE = "http://api.marrvel.org/data"
HUMAN_TAXON = "9606"

# Fix-R27A-3: MARRVEL indexes only *current* approved HGNC symbols. Asking it
# for a retired symbol or an alias returns HTTP 200 with an empty body -- `{}`
# from the gene endpoint and `null` from the omim endpoint (both confirmed
# live for 'RP20') -- which is byte-for-byte the same answer it gives for a
# symbol that does not exist at all. That collapses "you used the old name"
# into "no such gene", and old locus names (RP20 / LCA2 for RPE65) are exactly
# what turns up in the rare-disease triage workflows these tools advertise.
# HGNC's public keyless REST search resolves previous symbols and aliases to
# the current approved symbol, so an empty MARRVEL answer is re-checked there
# once and the lookup retried with the approved symbol.
HGNC_SEARCH_BASE = "https://rest.genenames.org/search"
# Deliberately short and independent of the tool's own timeout: this is a
# fallback on an already-empty answer and must not double worst-case latency.
HGNC_TIMEOUT = 8
# Only feed simple symbol-shaped tokens into the HGNC Solr query -- spaces,
# quotes or boolean operators from a caller would change the query's meaning.
_SYMBOL_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,30}$")


def _hgnc_lookup(symbol: str) -> Tuple[str, Optional[str], List[str]]:
    """Resolve a retired symbol/alias to its current approved HGNC symbol.

    Returns ``(outcome, resolved_symbol, candidates)`` where *outcome* is one
    of ``"resolved"`` (exactly one current symbol, different from *symbol*),
    ``"ambiguous"`` (the token is an alias of several genes -- never guess
    which one the caller meant), ``"none"`` (HGNC knows no such prev/alias
    symbol) or ``"unavailable"`` (HGNC could not be reached / parsed).

    Never raises: any HGNC problem degrades to ``"unavailable"`` so a working
    MARRVEL call is never turned into an error by this fallback.
    """
    if not _SYMBOL_SAFE.match(symbol):
        return "none", None, []
    url = f"{HGNC_SEARCH_BASE}/prev_symbol:{symbol}+OR+alias_symbol:{symbol}"
    try:
        resp = requests.get(
            url, headers={"Accept": "application/json"}, timeout=HGNC_TIMEOUT
        )
        if resp.status_code != 200:
            return "unavailable", None, []
        docs = (resp.json() or {}).get("response", {}).get("docs", []) or []
    except (requests.exceptions.RequestException, ValueError, AttributeError):
        return "unavailable", None, []

    candidates: List[str] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        cand = (doc.get("symbol") or "").strip()
        if cand and cand not in candidates:
            candidates.append(cand)
    if not candidates:
        return "none", None, []
    if len(candidates) > 1:
        return "ambiguous", None, candidates
    if candidates[0].upper() == symbol.upper():
        # Same symbol back -- retrying would just repeat the empty answer.
        return "none", None, candidates
    return "resolved", candidates[0], candidates


def _not_found_note(symbol: str, outcome: str, candidates: List[str]) -> str:
    """Actionable note for an empty MARRVEL answer that stayed empty."""
    base = (
        f"No MARRVEL record for '{symbol}'. MARRVEL indexes only current "
        f"approved HGNC symbols."
    )
    if outcome == "ambiguous":
        return (
            f"{base} '{symbol}' is a previous symbol or alias of several genes "
            f"({', '.join(candidates)}); re-run with the intended one."
        )
    if outcome == "unavailable":
        return (
            f"{base} The HGNC previous-symbol/alias lookup used to check for a "
            f"renamed gene was unavailable, so '{symbol}' could not be checked "
            f"against retired symbols -- retry, or supply the current approved "
            f"symbol."
        )
    return (
        f"{base} HGNC's previous-symbol/alias search did not resolve '{symbol}' "
        f"to a current approved symbol -- check the spelling or supply the "
        f"current approved symbol."
    )


def _substitution_note(symbol: str, resolved: str) -> str:
    return (
        f"'{symbol}' has no MARRVEL record because it is not a current approved "
        f"HGNC symbol; HGNC resolves it to '{resolved}' (previous symbol or "
        f"alias). The data below is for '{resolved}', not for '{symbol}' as "
        f"typed."
    )


def _resolve_symbol(arguments: Dict[str, Any]) -> str:
    # Fix-R32B-4: unlike most other gene-input tools in this codebase
    # (DGIdb, OpenTargets, ensembl_lookup_gene, ...), these tools only
    # accepted the bare "symbol" param with no gene/gene_symbol alias --
    # confirmed live that the natural-language guess {"gene_symbol":
    # "PTPN22"} failed schema validation entirely.
    return (
        arguments.get("symbol")
        or arguments.get("gene_symbol")
        or arguments.get("gene")
        or ""
    ).strip()


@register_tool("MARRVELGeneTool")
class MARRVELGeneTool(BaseTool):
    """Aggregated identity/annotation for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def _fetch(
        self, symbol: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Return ``(record_or_None, error_response_or_None)``.

        A 404 and an HTTP 200 with an empty body are the same user-visible
        situation ("MARRVEL has nothing under this symbol"), so both come back
        as ``(None, None)`` and share one not-found path.
        """
        url = f"{MARRVEL_BASE}/gene/taxonId/{HUMAN_TAXON}/symbol/{symbol}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return None, None
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return None, {
                "status": "error",
                "error": f"MARRVEL request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return None, {"status": "error", "error": f"MARRVEL request failed: {e}"}
        except ValueError:
            return None, {
                "status": "error",
                "error": "MARRVEL returned a non-JSON response",
            }
        if not isinstance(rec, dict) or not rec:
            return None, None
        return rec, None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = _resolve_symbol(arguments)
        if not symbol:
            return {"status": "error", "error": "'symbol' (e.g. 'CFTR') is required"}

        rec, err = self._fetch(symbol)
        if err:
            return err

        resolved: Optional[str] = None
        if rec is None:
            # Fix-R27A-3: empty answer -- ask HGNC once whether this is a
            # retired symbol/alias, and if so retry once with the current
            # approved symbol. At most one resolution, no recursion.
            outcome, candidate, candidates = _hgnc_lookup(symbol)
            if outcome == "resolved" and candidate:
                retried, retry_err = self._fetch(candidate)
                if retried is not None and not retry_err:
                    rec, resolved = retried, candidate
            if rec is None:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "total_results": 0,
                        "query_symbol": symbol,
                        "note": _not_found_note(symbol, outcome, candidates),
                    },
                }

        xref = rec.get("xref", {}) or {}
        metadata: Dict[str, Any] = {
            "total_results": 1,
            "query_symbol": symbol,
            "source": "MARRVEL (aggregated)",
        }
        if resolved:
            # Never silently answer about a different gene than the caller
            # typed -- name both symbols in the metadata.
            metadata["resolved_symbol"] = resolved
            metadata["resolved_note"] = _substitution_note(symbol, resolved)
        return {
            "status": "success",
            "data": {
                "symbol": rec.get("symbol"),
                "name": rec.get("name"),
                "entrez_id": rec.get("entrezId"),
                "hgnc_id": xref.get("hgncId"),
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
                "chromosome": rec.get("chr"),
                "location": rec.get("location"),
                "type": rec.get("type"),
                "aliases": rec.get("alias", []),
                "prev_symbols": rec.get("prevSymbols", []),
                "summary": rec.get("entrezSummary"),
            },
            "metadata": metadata,
        }


@register_tool("MARRVELOmimTool")
class MARRVELOmimTool(BaseTool):
    """OMIM phenotype/disease associations for a human gene by symbol."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def _fetch(
        self, symbol: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """Return ``(phenotype_rows_or_None, error_response_or_None)``.

        This endpoint answers an unknown/retired symbol with HTTP 200 and a
        body of literal ``null`` (confirmed live for 'RP20'), i.e. the same
        user-visible situation as the gene endpoint's ``{}`` and as a 404 --
        all three come back as ``(None, None)``.
        """
        url = f"{MARRVEL_BASE}/omim/gene/symbol/{symbol}"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return None, None
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return None, {
                "status": "error",
                "error": f"MARRVEL request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return None, {"status": "error", "error": f"MARRVEL request failed: {e}"}
        except ValueError:
            return None, {
                "status": "error",
                "error": "MARRVEL returned a non-JSON response",
            }

        if not payload:
            return None, None
        phenos = []
        if isinstance(payload, dict):
            phenos = payload.get("phenotypes", []) or []
        elif isinstance(payload, list):
            phenos = payload
        return [
            {
                "gene_mim_number": p.get("mimNumber"),
                "phenotype": p.get("phenotype"),
                "phenotype_mim_number": p.get("phenotypeMimNumber"),
                "inheritance": p.get("phenotypeInheritance"),
                "phenotypic_series": p.get("phenotypicSeriesNumber"),
            }
            for p in phenos
            if isinstance(p, dict)
        ], None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        symbol = _resolve_symbol(arguments)
        if not symbol:
            return {"status": "error", "error": "'symbol' (e.g. 'CFTR') is required"}

        results, err = self._fetch(symbol)
        if err:
            return err

        resolved: Optional[str] = None
        if results is None:
            # Fix-R27A-3: same retired-symbol/alias resolution as the gene
            # tool -- shared helper, one attempt, no recursion.
            outcome, candidate, candidates = _hgnc_lookup(symbol)
            if outcome == "resolved" and candidate:
                retried, retry_err = self._fetch(candidate)
                if retried is not None and not retry_err:
                    results, resolved = retried, candidate
            if results is None:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "total_results": 0,
                        "query_symbol": symbol,
                        "note": _not_found_note(symbol, outcome, candidates),
                    },
                }

        metadata: Dict[str, Any] = {
            "total_results": len(results),
            "query_symbol": symbol,
            "source": "MARRVEL / OMIM",
        }
        if resolved:
            metadata["resolved_symbol"] = resolved
            metadata["resolved_note"] = _substitution_note(symbol, resolved)
        return {
            "status": "success",
            "data": results,
            "metadata": metadata,
        }
