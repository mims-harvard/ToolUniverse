# disprot_tool.py
"""
DisProt tool for ToolUniverse.

DisProt is a manually curated database of intrinsically disordered proteins
and regions, providing experimentally validated disorder annotations with
evidence codes and literature references.

API: https://disprot.org/api/
No authentication required.
"""

import re
import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

DISPROT_BASE_URL = "https://www.disprot.org/api"

_DISPROT_ID = re.compile(r"^DP\d{5}$", re.I)
_UNIPROT_ACC = re.compile(
    r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$",
    re.I,
)


STATEMENT_CHARACTERS = 1200


def _gene_names(genes) -> list:
    """Every gene name on the entry, not only the first.

    Both handlers took `genes[0]` with no count. P0DN86 is CGB3, CGB5 and
    CGB8 -- three names for one DisProt entry -- and a caller searching for
    CGB8 was answered with CGB3. `gene` keeps its old meaning as the first
    name so existing callers are unaffected.
    """
    names = []
    for gene in genes or []:
        if not isinstance(gene, dict):
            continue
        value = (gene.get("name") or {}).get("value")
        if value and value not in names:
            names.append(value)
    return names


def _statements(block: dict) -> list:
    """The curator's quoted evidence for an annotation.

    A DisProt region's `statement` is the sentence from the paper that the
    annotation rests on, typed by the section it came from (Introduction,
    Methods, Results). It is the content of the curation: the term name says
    "protein binding", the statement says what was shown and how.
    """
    rows = []
    for st in block.get("statements") or block.get("statement") or []:
        if not isinstance(st, dict):
            continue
        text = st.get("text") or ""
        truncated = len(text) > STATEMENT_CHARACTERS
        if truncated:
            text = text[:STATEMENT_CHARACTERS].rstrip() + "..."
        rows.append(
            {
                "type": st.get("type"),
                "text": text or None,
                "text_truncated": truncated,
            }
        )
    return rows


def _partners(region: dict) -> list:
    """The molecules a binding region binds.

    26 of P04637's 63 regions are annotated `protein binding`; the partner
    is a cross-reference in `interaction_partner` and the annotation means
    little without it.
    """
    rows = []
    for partner in region.get("interaction_partner") or []:
        if not isinstance(partner, dict):
            continue
        rows.append(
            {
                "database": partner.get("db"),
                "id": partner.get("id"),
                "partner_start": partner.get("partner_start"),
                "partner_end": partner.get("partner_end"),
            }
        )
    return rows


@register_tool("DisProtTool")
class DisProtTool(BaseTool):
    """
    Tool for querying DisProt intrinsically disordered protein database.

    Supports:
    - Search disordered proteins by text query
    - Get detailed disorder region annotations for a specific protein

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DisProt API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DisProt API timed out after {self.timeout}s.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to DisProt API (www.disprot.org).",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Entry not found in DisProt. Check the accession.",
                }
            return {"status": "error", "error": f"DisProt API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_entry":
            return self._get_entry(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_fields(self, query: str) -> List[str]:
        """Which DisProt filters to try for this query, in order.

        DisProt's /search ignores a free-text ``q`` and returns every entry, so the
        query has to be sent as a real filter: an exact identifier when it looks
        like one, otherwise the gene and protein-name filters (substring,
        case-insensitive), then the organism filter.
        """
        if _DISPROT_ID.match(query):
            return ["disprot_id"]
        if _UNIPROT_ACC.match(query):
            return ["acc"]
        return ["gene", "name", "organism"]

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search DisProt for disordered proteins."""
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "error",
                "error": "query must be a non-empty string",
                "parameter": "query",
            }
        page_size = arguments.get("page_size", 10)
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 500
        ):
            return {
                "status": "error",
                "error": "page_size must be an integer between 1 and 500",
                "parameter": "page_size",
            }
        page = arguments.get("page", 0)
        if isinstance(page, bool) or not isinstance(page, int) or page < 0:
            return {
                "status": "error",
                "error": "page must be a non-negative integer",
                "parameter": "page",
            }
        query = query.strip()

        url = f"{DISPROT_BASE_URL}/search"
        entries: List[Dict[str, Any]] = []
        seen = set()
        matches: Dict[str, int] = {}
        has_more = False
        page_start = page * page_size
        for field in self._search_fields(query):
            # The organism filter is only a fallback for queries that name no
            # gene or protein; it would otherwise flood the list with a proteome.
            # Decided on match totals, not this page's rows, so later pages
            # take the same branch as page 0.
            if field == "organism" and any(matches.values()):
                break
            value = query.upper() if field in ("disprot_id", "acc") else query
            params = {
                field: value,
                "release": "current",
                "page_size": page_size,
                "page": page,
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            results = data.get("data", [])
            try:
                matches[field] = int(data.get("size", len(results)))
            except (TypeError, ValueError):
                matches[field] = len(results)
            if results and page_start + len(results) < matches[field]:
                has_more = True
            for entry in results:
                key = entry.get("acc") or entry.get("disprot_id")
                if key in seen:
                    continue
                seen.add(key)
                genes = entry.get("genes", [])
                gene_names = _gene_names(genes)
                gene_name = gene_names[0] if gene_names else ""
                entries.append(
                    {
                        "disprot_id": entry.get("disprot_id"),
                        "acc": entry.get("acc"),
                        "name": entry.get("name"),
                        "gene": gene_name,
                        "gene_names": gene_names,
                        "gene_count": len(gene_names),
                        "organism": entry.get("organism"),
                        "length": entry.get("length"),
                        "disorder_content": entry.get("disorder_content"),
                        "regions_counter": entry.get("regions_counter"),
                        "dataset": entry.get("dataset", []),
                        "matched_on": field,
                    }
                )

        # Gene and name hits are merged into one page_size page; the count the
        # merge pushed past page_size is reported (raise page_size to see them)
        # rather than silently dropped.
        merged_overflow = max(0, len(entries) - page_size)
        # Each filter is paged upstream; with more than one filter queried the
        # totals can overlap, so their sum is only an upper bound.
        total = sum(matches.values())
        total_is_exact = len(matches) == 1
        complete = page == 0 and not has_more and merged_overflow == 0
        return {
            "status": "success",
            "data": entries[:page_size],
            "metadata": {
                "source": "DisProt (disprot.org)",
                "query": query,
                "returned": len(entries[:page_size]),
                "total_matches_by_filter": matches,
                "total_results": total,
                "total_results_is_exact": total_is_exact,
                "page": page,
                "page_size": page_size,
                "page_start": page_start,
                "has_more": has_more,
                "truncated": not complete,
                "result_set_complete": complete,
                "next_page": page + 1 if has_more else None,
                "merged_overflow": merged_overflow,
            },
        }

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed disorder regions for a DisProt entry."""
        accession = arguments.get("accession")
        if not isinstance(accession, str) or not accession.strip():
            return {
                "status": "error",
                "error": "accession must be a non-empty string",
                "parameter": "accession",
            }
        accession = accession.strip()
        region_offset = arguments.get("region_offset", 0)
        if (
            isinstance(region_offset, bool)
            or not isinstance(region_offset, int)
            or region_offset < 0
        ):
            return {
                "status": "error",
                "error": "region_offset must be a non-negative integer",
                "parameter": "region_offset",
            }
        region_limit = arguments.get("region_limit", 30)
        if (
            isinstance(region_limit, bool)
            or not isinstance(region_limit, int)
            or not 1 <= region_limit <= 500
        ):
            return {
                "status": "error",
                "error": "region_limit must be an integer between 1 and 500",
                "parameter": "region_limit",
            }

        # Determine whether it's a DisProt ID (DP*) or UniProt accession
        url = f"{DISPROT_BASE_URL}/search"
        if accession.upper().startswith("DP"):
            params = {"disprot_id": accession.upper(), "page_size": 1}
        else:
            params = {"acc": accession, "page_size": 1}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        search_result = response.json()

        results = search_result.get("data", [])
        if not results:
            return {
                "status": "error",
                "error": f"Entry not found in DisProt for accession '{accession}'.",
            }
        data = results[0]

        # Extract every region first, then expose explicit local pagination.
        # The old hard slice at 30 contradicted regions_counter without any
        # warning or way to fetch the omitted annotations.
        regions = []
        for region in data.get("regions", []):
            cross_refs = []
            for xr in region.get("cross_refs", []):
                cross_refs.append(
                    {
                        "db": xr.get("db"),
                        "id": xr.get("id"),
                    }
                )
            regions.append(
                {
                    "region_id": region.get("region_id"),
                    "start": region.get("start"),
                    "end": region.get("end"),
                    "term_id": region.get("term_id"),
                    "term_name": region.get("term_name"),
                    "term_namespace": region.get("term_namespace"),
                    "term_ontology": region.get("term_ontology"),
                    "evidence_code": region.get("ec_name"),
                    # The ECO identifier, not only its sentence-long name:
                    # ECO:0006165 is what a caller joins or cites.
                    "evidence_code_id": region.get("ec_id"),
                    "evidence_code_go": region.get("ec_go"),
                    # The sentence the annotation rests on.
                    "statements": _statements(region),
                    # What a "protein binding" region binds.
                    "interaction_partners": _partners(region),
                    "reference_id": region.get("reference_id"),
                    "reference_source": region.get("reference_source"),
                    "reference": region.get("reference_html"),
                    "curator_name": region.get("curator_name"),
                    "curator_orcid": region.get("curator_orcid"),
                    "annotation_date": region.get("date"),
                    "disprot_namespace": region.get("disprot_namespace"),
                    "cross_refs": cross_refs,
                }
            )

        genes = data.get("genes", [])
        gene_names = _gene_names(genes)
        gene_name = gene_names[0] if gene_names else ""

        returned_regions = regions[region_offset : region_offset + region_limit]
        has_more_regions = bool(returned_regions) and (
            region_offset + len(returned_regions) < len(regions)
        )
        return {
            "status": "success",
            "data": {
                "disprot_id": data.get("disprot_id"),
                "acc": data.get("acc"),
                "name": data.get("name"),
                "gene": gene_name,
                "gene_names": gene_names,
                "gene_count": len(gene_names),
                "organism": data.get("organism"),
                "length": data.get("length"),
                "disorder_content": data.get("disorder_content"),
                "regions_counter": data.get("regions_counter"),
                "dataset": data.get("dataset", []),
                "regions": returned_regions,
            },
            "metadata": {
                "source": "DisProt (disprot.org)",
                "total_regions": len(regions),
                "reported_regions_counter": data.get("regions_counter"),
                "returned_regions": len(returned_regions),
                "region_offset": region_offset,
                "region_limit": region_limit,
                "has_more_regions": has_more_regions,
                "regions_truncated": len(returned_regions) < len(regions),
                "next_region_offset": (
                    region_offset + len(returned_regions) if has_more_regions else None
                ),
            },
        }
