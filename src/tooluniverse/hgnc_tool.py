# hgnc_tool.py
"""
HGNC (HUGO Gene Nomenclature Committee) REST API tool for ToolUniverse.

HGNC is the worldwide authority that assigns standardised nomenclature to
human genes. The REST API provides access to approved gene symbols, names,
aliases, chromosomal locations, and cross-references to external databases.

API: https://rest.genenames.org/
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

HGNC_BASE_URL = "https://rest.genenames.org"

# Stored HGNC fields that carry a *retired* name for a gene whose record now
# lives under a different (current) symbol.  ``fetch/<field>/<value>`` is an
# exact, case-insensitive match on the stored field and returns the complete
# gene record -- verified live against rest.genenames.org:
#   fetch/symbol/CYP2E        -> numFound 0
#   fetch/prev_symbol/CYP2E   -> numFound 1, the full CYP2E1 record
#   fetch/alias_symbol/p65    -> numFound 3 (RELA, SYT1, GORASP1)
# Ordered by strength of the relation: an official rename (prev_symbol) is a
# stronger signal than an informal alias.
SYMBOL_FALLBACK_FIELDS = ("prev_symbol", "alias_symbol")

_RELATION_LABEL = {
    "prev_symbol": "previous symbol",
    "alias_symbol": "alias symbol",
}


@register_tool("HGNCTool")
class HGNCTool(BaseTool):
    """
    Tool for querying the HGNC gene nomenclature database.

    HGNC provides authoritative human gene naming. Supports fetching genes by
    symbol, HGNC ID, or searching by various fields including name, location,
    and aliases.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint_type = fields.get("endpoint", "search")
        self.default_search_field = fields.get("search_field")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HGNC API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HGNC API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HGNC API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HGNC API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying HGNC: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HGNC query and return structured results."""
        headers = {"Accept": "application/json"}

        if self.endpoint_type == "fetch":
            return self._fetch(arguments, headers)
        else:
            return self._search(arguments, headers)

    def _fetch(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Fetch a specific gene record by symbol or HGNC ID.

        For ``gene_group_id`` the fetch endpoint returns every member gene of
        the family/group, so all docs are returned as a list rather than a
        single record.
        """
        search_field = self.default_search_field

        if search_field == "symbol":
            value = arguments.get("symbol", "")
            if not value:
                return {"status": "error", "error": "symbol parameter is required"}
        elif search_field == "hgnc_id":
            value = arguments.get("hgnc_id", "")
            if not value:
                return {"status": "error", "error": "hgnc_id parameter is required"}
            # Ensure HGNC: prefix
            if not value.startswith("HGNC:"):
                value = f"HGNC:{value}"
        elif search_field == "gene_group_id":
            value = arguments.get("gene_group_id", "")
            if value is None or str(value).strip() == "":
                return {
                    "status": "error",
                    "error": "gene_group_id parameter is required",
                }
            value = str(value).strip()
        else:
            return {"status": "error", "error": f"Unknown fetch field: {search_field}"}

        resp = self._fetch_field(search_field, value, headers)
        docs = resp.get("docs", [])

        # gene_group_id enumerates every member gene of a family → return all
        if search_field == "gene_group_id":
            metadata = {
                "source": "HGNC",
                "query_field": search_field,
                "query_value": value,
                "num_found": resp.get("numFound", len(docs)),
            }
            if not docs:
                metadata["no_results_note"] = (
                    f"HGNC has no gene family/group with gene_group_id "
                    f"'{value}'. Find a valid gene_group_id in the "
                    f"'gene_group_id' field of any record returned by "
                    f"HGNC_fetch_gene_by_symbol."
                )
            return {
                "status": "success",
                "data": docs,
                "metadata": metadata,
            }

        if docs:
            # A current-symbol (or HGNC ID) hit always wins; no resolution
            # happened, so no disclosure keys are added.
            return {
                "status": "success",
                "data": docs[0],
                "metadata": {
                    "source": "HGNC",
                    "query_field": search_field,
                    "query_value": value,
                    "num_found": resp.get("numFound", len(docs)),
                },
            }

        if search_field == "symbol":
            return self._resolve_retired_symbol(value, headers)

        # hgnc_id miss: nothing to fall back to, but never a bare empty success.
        return {
            "status": "success",
            "data": {},
            "metadata": {
                "source": "HGNC",
                "query_field": search_field,
                "query_value": value,
                "num_found": 0,
                "no_results_note": (
                    f"No HGNC record has {search_field} '{value}'. The ID may "
                    f"be withdrawn or malformed. Use HGNC_search_genes to look "
                    f"the gene up by symbol or name instead."
                ),
            },
        }

    def _fetch_field(self, field: str, value: str, headers: Dict) -> Dict[str, Any]:
        """GET ``/fetch/<field>/<value>`` and return the ``response`` object.

        The HGNC ``fetch`` endpoint is an exact (case-insensitive) match on a
        stored field and returns complete gene records -- unlike ``search``,
        which is a scored Solr query returning only stubs.
        """
        url = f"{HGNC_BASE_URL}/fetch/{field}/{value}"
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("response", {}) or {}

    def _resolve_retired_symbol(self, requested: str, headers: Dict) -> Dict[str, Any]:
        """Resolve a symbol that is not a *current* HGNC symbol.

        ``fetch/symbol/<X>`` only matches genes whose approved symbol is
        exactly ``X``. Genes are routinely renamed (CYP2E → CYP2E1 in 2002,
        DIA4 → NQO1), and the retired string survives on the current record as
        ``prev_symbol``/``alias_symbol``. Look ``X`` up in those fields so the
        caller gets the same rich record a direct hit would have produced,
        with the substitution disclosed in ``metadata``.
        """
        for field in SYMBOL_FALLBACK_FIELDS:
            resp = self._fetch_field(field, requested, headers)
            docs = resp.get("docs", [])
            if not docs:
                continue

            relation = _RELATION_LABEL[field]

            if len(docs) > 1:
                # Never silently pick one of several genes -- name them all.
                candidates = [
                    {
                        "symbol": d.get("symbol"),
                        "hgnc_id": d.get("hgnc_id"),
                        "name": d.get("name"),
                    }
                    for d in docs
                ]
                listed = ", ".join(
                    f"{c['symbol']} ({c['hgnc_id']})" for c in candidates
                )
                return {
                    "status": "error",
                    "error": (
                        f"'{requested}' is not a current HGNC gene symbol, and "
                        f"it is ambiguous: it is the {relation} of "
                        f"{len(candidates)} different genes: {listed}. Re-query "
                        f"HGNC_fetch_gene_by_symbol with the intended current "
                        f"symbol."
                    ),
                    "metadata": {
                        "source": "HGNC",
                        "query_field": "symbol",
                        "query_value": requested,
                        "num_found": resp.get("numFound", len(docs)),
                        "resolved_from": requested,
                        "resolution_relation": field,
                        "ambiguous_candidates": candidates,
                    },
                }

            gene = docs[0]
            current = gene.get("symbol")
            return {
                "status": "success",
                "data": gene,
                "metadata": {
                    "source": "HGNC",
                    "query_field": "symbol",
                    "query_value": requested,
                    "num_found": 1,
                    "resolved_from": requested,
                    "resolved_symbol": current,
                    "resolution_relation": field,
                    "symbol_resolution_note": (
                        f"'{requested}' is not a current HGNC gene symbol. It "
                        f"is listed as a {relation} of '{current}', whose "
                        f"record is returned here."
                    ),
                },
            }

        return {
            "status": "success",
            "data": {},
            "metadata": {
                "source": "HGNC",
                "query_field": "symbol",
                "query_value": requested,
                "num_found": 0,
                "no_results_note": (
                    f"'{requested}' is not known to HGNC as a current symbol, "
                    f"a previous symbol, or an alias symbol. Check the "
                    f"spelling, or use HGNC_search_genes (which supports "
                    f"wildcards and free-text search) to find the gene."
                ),
            },
        }

    def _search(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Search for genes by various criteria."""
        search_field = arguments.get("search_field", self.default_search_field)

        # Determine the query value
        query = arguments.get("query") or arguments.get("location", "")
        if not query:
            return {
                "status": "error",
                "error": "query or location parameter is required",
            }

        if search_field:
            url = f"{HGNC_BASE_URL}/search/{search_field}/{query}"
        else:
            url = f"{HGNC_BASE_URL}/search/{query}"

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        resp = data.get("response", {})
        docs = resp.get("docs", [])

        metadata = {
            "source": "HGNC",
            "total_results": resp.get("numFound", len(docs)),
            "query": query,
            "query_location": arguments.get("location", query),
        }
        if not docs:
            if search_field == "location":
                metadata["no_results_note"] = (
                    f"No HGNC genes are mapped to location '{query}'. "
                    f"Locations are cytogenetic bands such as '17p13.1'; "
                    f"a broader band (e.g. '17p13') may return results."
                )
            else:
                metadata["no_results_note"] = (
                    f"No HGNC genes matched '{query}'"
                    + (f" in field '{search_field}'" if search_field else "")
                    + ". Try a wildcard (e.g. 'BRCA*'), drop the "
                    "search_field to search symbol and name together, or "
                    "search 'prev_symbol'/'alias_symbol' for a retired name."
                )
        return {
            "status": "success",
            "data": docs,
            "metadata": metadata,
        }
