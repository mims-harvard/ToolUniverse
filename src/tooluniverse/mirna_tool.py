# mirna_tool.py
"""
miRNA/lncRNA tools for ToolUniverse via RNAcentral and EBI Search APIs.

Provides miRNA and lncRNA search, sequence retrieval, cross-references, and
publication data by leveraging RNAcentral (the comprehensive ncRNA aggregator)
and EBI Search (for text-based queries with faceted filtering).

miRBase and LNCipedia data is aggregated through RNAcentral, which provides
a unified REST API for accessing ncRNA data from 50+ databases.

APIs used:
  - RNAcentral REST API: https://rnacentral.org/api/v1/
  - EBI Search: https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral

No authentication required. Free public access.
"""

import re

import requests
from typing import Dict, Any
from .base_tool import BaseTool


RNACENTRAL_BASE = "https://rnacentral.org/api/v1"
EBI_SEARCH_BASE = "https://www.ebi.ac.uk/ebisearch/ws/rest/rnacentral"

# Standard EBI search fields
EBI_FIELDS = "description,rna_type,length,expert_db,has_secondary_structure,has_genomic_coordinates"

# Common species name to NCBI Taxonomy ID mapping
SPECIES_TAXID = {
    "homo sapiens": "9606",
    "human": "9606",
    "mus musculus": "10090",
    "mouse": "10090",
    "rattus norvegicus": "10116",
    "rat": "10116",
    "drosophila melanogaster": "7227",
    "fruit fly": "7227",
    "caenorhabditis elegans": "6239",
    "danio rerio": "7955",
    "zebrafish": "7955",
    "arabidopsis thaliana": "3702",
    "saccharomyces cerevisiae": "4932",
    "gallus gallus": "9031",
    "chicken": "9031",
    "bos taurus": "9913",
    "sus scrofa": "9823",
    "xenopus tropicalis": "8364",
}

_RNACENTRAL_ID_RE = re.compile(r"^(URS[0-9A-F]{10})(?:_([1-9][0-9]*))?$")


class miRNASearchTool(BaseTool):
    """
    Search for miRNAs/lncRNAs/ncRNAs via EBI Search of RNAcentral.
    Can filter results by RNA type for focused results.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get default RNA type filter from tool config fields
        fields = tool_config.get("fields", {})
        self.default_rna_type = fields.get("rna_type_filter", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            query = arguments.get("query", "")
            if not isinstance(query, str) or not query.strip():
                return {
                    "status": "error",
                    "error": "query must be a non-empty string",
                    "parameter": "query",
                }
            query = query.strip()
            # User-supplied rna_type overrides config default
            rna_type_filter = arguments.get("rna_type", "") or self.default_rna_type
            species = arguments.get("species", "")
            size = arguments.get("size", 10)
            start = arguments.get("start", 0)
            if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 100:
                return {
                    "status": "error",
                    "error": "size must be an integer between 1 and 100",
                    "parameter": "size",
                }
            if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                return {
                    "status": "error",
                    "error": "start must be a non-negative integer",
                    "parameter": "start",
                }

            # Build EBI search query with optional filters
            search_parts = [query]
            if rna_type_filter:
                search_parts.append(f"rna_type:{rna_type_filter}")
            if species:
                # Map species name to taxonomy ID for reliable filtering
                taxid = SPECIES_TAXID.get(species.lower(), "")
                if taxid:
                    search_parts.append(f"TAXONOMY:{taxid}")
                else:
                    # Try using the species name directly (works for exact matches)
                    search_parts.append(f"TAXONOMY:{species.replace(' ', '_')}")
            search_query = " AND ".join(search_parts)

            params = {
                "query": search_query,
                "format": "json",
                "size": size,
                "start": start,
                "fields": EBI_FIELDS,
            }

            resp = requests.get(EBI_SEARCH_BASE, params=params, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()

            entries = []
            for entry in result.get("entries", []):
                fields = entry.get("fields", {})
                entries.append(
                    {
                        "rnacentral_id": entry.get("id", ""),
                        "description": (
                            fields.get("description", [""])[0]
                            if fields.get("description")
                            else ""
                        ),
                        "rna_type": (
                            fields.get("rna_type", [""])[0]
                            if fields.get("rna_type")
                            else ""
                        ),
                        "length": int(fields.get("length", ["0"])[0])
                        if fields.get("length")
                        else 0,
                        "expert_databases": fields.get("expert_db", []),
                        "has_secondary_structure": (
                            fields.get("has_secondary_structure", ["False"])[0]
                            == "True"
                            if fields.get("has_secondary_structure")
                            else False
                        ),
                        "has_genomic_coordinates": (
                            fields.get("has_genomic_coordinates", ["False"])[0]
                            == "True"
                            if fields.get("has_genomic_coordinates")
                            else False
                        ),
                    }
                )

            total_hits = result.get("hitCount", 0)
            returned = len(entries)
            has_more = start + returned < total_hits
            truncated = start > 0 or has_more
            return {
                "status": "success",
                "data": {
                    "total_hits": total_hits,
                    "returned": returned,
                    "start": start,
                    "has_more": has_more,
                    "next_start": start + returned if has_more else None,
                    "truncated": truncated,
                    "result_set_complete": not truncated,
                    "entries": entries,
                },
                "metadata": {
                    "source": "EBI Search / RNAcentral",
                    "query": search_query,
                },
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EBI Search API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to EBI Search API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"EBI Search API HTTP error: {code}"}
        except Exception as e:
            return {"status": "error", "error": f"miRNA search failed: {str(e)}"}


class miRNAGetTool(BaseTool):
    """
    Get detailed miRNA/lncRNA information from RNAcentral by ID.
    Returns sequence, species, RNA type, and database cross-references.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_rna")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            endpoint = self.endpoint

            if endpoint == "get_rna":
                return self._get_rna(arguments)
            elif endpoint == "get_publications":
                return self._get_publications(arguments)
            elif endpoint == "get_xrefs":
                return self._get_xrefs(arguments)
            else:
                return {"status": "error", "error": f"Unknown endpoint: {endpoint}"}

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"RNAcentral API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to RNAcentral API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"RNA entry not found: {arguments.get('rnacentral_id', '')}",
                }
            return {"status": "error", "error": f"RNAcentral API HTTP error: {code}"}
        except Exception as e:
            return {"status": "error", "error": f"RNAcentral query failed: {str(e)}"}

    def _get_rna(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get RNA entry details including sequence."""
        raw_id = arguments.get("rnacentral_id", "")
        if not isinstance(raw_id, str) or not raw_id.strip():
            return {
                "status": "error",
                "error": "rnacentral_id must be a non-empty RNAcentral URS ID",
                "parameter": "rnacentral_id",
            }
        match = _RNACENTRAL_ID_RE.fullmatch(raw_id.strip().upper())
        if match is None:
            return {
                "status": "error",
                "error": (
                    "rnacentral_id must use URSXXXXXXXXXX or "
                    "URSXXXXXXXXXX_TAXID format"
                ),
                "parameter": "rnacentral_id",
            }

        base_id, suffix_taxid_text = match.groups()
        suffix_taxid = int(suffix_taxid_text) if suffix_taxid_text else None
        requested_taxid = arguments.get("taxid")
        if requested_taxid is not None:
            if (
                isinstance(requested_taxid, bool)
                or not isinstance(requested_taxid, int)
                or requested_taxid <= 0
            ):
                return {
                    "status": "error",
                    "error": "taxid must be a positive integer",
                    "parameter": "taxid",
                }
        if (
            suffix_taxid is not None
            and requested_taxid is not None
            and suffix_taxid != requested_taxid
        ):
            return {
                "status": "error",
                "error": (
                    f"Conflicting taxids: rnacentral_id specifies {suffix_taxid} "
                    f"but taxid specifies {requested_taxid}"
                ),
                "parameter": "taxid",
            }

        resolved_taxid = requested_taxid or suffix_taxid
        canonical_id = (
            f"{base_id}_{resolved_taxid}" if resolved_taxid is not None else base_id
        )

        # RNAcentral exposes a canonical species-specific JSON record directly
        # at /rna/{URS}_{taxid}/. Querying the bare URS and then selecting an
        # xref is unsafe: an absent taxid used to fall back to the first xref,
        # silently attaching a different organism to the requested taxid.
        url = f"{RNACENTRAL_BASE}/rna/{canonical_id}/?format=json"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            qualifier = "species-specific " if resolved_taxid is not None else ""
            return {
                "status": "error",
                "error": (
                    f"RNAcentral {qualifier}record not found: {canonical_id}"
                ),
                "requested_rnacentral_id": canonical_id,
            }
        resp.raise_for_status()
        result = resp.json()

        returned_id = str(result.get("rnacentral_id") or "").upper()
        if returned_id != canonical_id:
            return {
                "status": "error",
                "error": (
                    "RNAcentral returned a record whose identity does not match "
                    f"the request: requested {canonical_id}, returned "
                    f"{returned_id or '<missing>'}"
                ),
            }

        returned_taxid = result.get("taxid")
        if resolved_taxid is not None and returned_taxid != resolved_taxid:
            return {
                "status": "error",
                "error": (
                    "RNAcentral returned a record whose taxid does not match "
                    f"the request: requested {resolved_taxid}, returned "
                    f"{returned_taxid!r}"
                ),
            }

        publications = result.get("publications")

        return {
            "status": "success",
            "data": {
                "rnacentral_id": returned_id,
                "description": result.get("description") or "",
                "short_description": result.get("short_description") or "",
                "sequence": result.get("sequence", ""),
                "length": result.get("length", 0),
                "rna_type": result.get("rna_type") or "",
                "species": result.get("species") or "",
                "taxid": returned_taxid,
                "genes": result.get("genes") or [],
                # Bare-URS records expose a publications URL rather than a
                # count. None distinguishes "not supplied" from a true zero.
                "publications_count": publications
                if isinstance(publications, int)
                else None,
                "is_active": result.get("is_active", True),
                "distinct_databases": result.get("distinct_databases", ""),
            },
            "metadata": {
                "source": "RNAcentral",
                "requested_rnacentral_id": raw_id,
                "canonical_rnacentral_id": canonical_id,
                "species_specific": resolved_taxid is not None,
                "identity_verified": True,
                "url": f"https://rnacentral.org/rna/{canonical_id}",
            },
        }

    def _get_publications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get publications associated with an RNA entry."""
        rnacentral_id = arguments.get("rnacentral_id", "")
        controls = self._page_controls(arguments, rnacentral_id)
        if isinstance(controls, dict):
            return controls
        page_size, page = controls

        url = f"{RNACENTRAL_BASE}/rna/{rnacentral_id.strip()}/publications/"
        resp = requests.get(
            url,
            params={"format": "json", "page_size": page_size, "page": page},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()

        publications = []
        for pub in result.get("results", []):
            publications.append(
                {
                    "title": pub.get("title", ""),
                    "authors": pub.get("authors", []),
                    "publication": pub.get("publication", ""),
                    "pubmed_id": pub.get("pubmed_id", ""),
                    "doi": pub.get("doi", ""),
                    "expert_db": pub.get("expert_db", False),
                }
            )

        total = result.get("count", 0)
        returned = len(publications)
        has_more = bool(result.get("next"))
        truncated = page > 1 or has_more
        return {
            "status": "success",
            "data": {
                "total_publications": total,
                "returned": returned,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "previous_page": page - 1 if result.get("previous") else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
                "publications": publications,
            },
            "metadata": {
                "source": "RNAcentral",
                "rnacentral_id": rnacentral_id,
                "upstream_total_is_record_count": True,
                "unique_pmids_not_guaranteed": True,
                "warning": (
                    "RNAcentral can expose multiple source records for the same "
                    "PMID with different citation metadata; total_publications is "
                    "an upstream record count, not a guaranteed unique PMID count."
                ),
            },
        }

    def _get_xrefs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-references for an RNA entry."""
        rnacentral_id = arguments.get("rnacentral_id", "")
        controls = self._page_controls(arguments, rnacentral_id)
        if isinstance(controls, dict):
            return controls
        page_size, page = controls

        url = f"{RNACENTRAL_BASE}/rna/{rnacentral_id.strip()}/xrefs/"
        resp = requests.get(
            url,
            params={"format": "json", "page_size": page_size, "page": page},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        result = resp.json()

        xrefs = []
        for xref in result.get("results", []):
            acc = xref.get("accession", {})
            xrefs.append(
                {
                    "database": xref.get("database", ""),
                    "accession_id": acc.get("id", ""),
                    "external_id": acc.get("external_id", ""),
                    "description": acc.get("description", ""),
                    "species": acc.get("species", ""),
                    "rna_type": acc.get("rna_type", ""),
                    "gene": acc.get("gene", ""),
                    "taxid": xref.get("taxid"),
                    "is_active": xref.get("is_active", True),
                    "expert_db_url": acc.get("expert_db_url", ""),
                    "mirbase_mature_products": xref.get("mirbase_mature_products"),
                    "mirbase_precursor": xref.get("mirbase_precursor"),
                }
            )

        total = result.get("count", 0)
        returned = len(xrefs)
        has_more = bool(result.get("next"))
        truncated = page > 1 or has_more
        return {
            "status": "success",
            "data": {
                "total_xrefs": total,
                "returned": returned,
                "page": page,
                "page_size": page_size,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "previous_page": page - 1 if result.get("previous") else None,
                "truncated": truncated,
                "result_set_complete": not truncated,
                "cross_references": xrefs,
            },
            "metadata": {
                "source": "RNAcentral",
                "rnacentral_id": rnacentral_id,
            },
        }

    @staticmethod
    def _page_controls(arguments: Dict[str, Any], rnacentral_id: Any):
        if not isinstance(rnacentral_id, str) or not rnacentral_id.strip():
            return {
                "status": "error",
                "error": "rnacentral_id must be a non-empty string",
                "parameter": "rnacentral_id",
            }
        page_size = arguments.get("page_size", 10)
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 50
        ):
            return {
                "status": "error",
                "error": "page_size must be an integer between 1 and 50",
                "parameter": "page_size",
            }
        page = arguments.get("page", 1)
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be a positive integer",
                "parameter": "page",
            }
        return page_size, page
