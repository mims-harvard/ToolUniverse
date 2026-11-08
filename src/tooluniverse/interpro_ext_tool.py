# interpro_ext_tool.py
"""
InterPro Extended API tool for ToolUniverse.

Provides access to InterPro API endpoints for querying proteins by domain,
complementing existing domain-centric search tools.

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse
from .base_tool import BaseTool


INTERPRO_API_BASE_URL = "https://www.ebi.ac.uk/interpro/api"


def _json_or_none(response):
    """Parse a JSON response body, returning None when there is no body.

    The InterPro API reports an empty result set as HTTP 204 No Content with a
    zero-length body instead of a 200 carrying ``{"count": 0, "results": []}``.
    ``raise_for_status()`` treats 204 as success, so calling ``.json()`` on it
    raises a JSONDecodeError that used to escape as an opaque
    "Unexpected error querying InterPro API" message -- callers could not tell
    "nothing matched" from "the tool is broken".
    """
    if response.status_code == 204:
        return None
    body = response.content
    if not body or not body.strip():
        return None
    return response.json()


def _match_locations(protein_rows: list) -> list:
    """Where on a protein an InterPro entry matches.

    `entry_protein_locations` is what "this protein contains this domain"
    actually means: the residue ranges, each possibly in several fragments,
    with the signature model and score behind the call. The twin endpoint in
    the sibling module builds the same shape and the two must agree -- a
    caller joining a domain's proteins to a protein's domains reads both.
    """
    locations = []
    for row in protein_rows or []:
        if not isinstance(row, dict):
            continue
        for location in row.get("entry_protein_locations") or []:
            if not isinstance(location, dict):
                continue
            locations.append(
                {
                    "fragments": [
                        {
                            "start": fragment.get("start"),
                            "end": fragment.get("end"),
                            "status": fragment.get("dc-status"),
                        }
                        for fragment in (location.get("fragments") or [])
                        if isinstance(fragment, dict)
                    ],
                    "model": location.get("model"),
                    "score": location.get("score"),
                    "representative": location.get("representative"),
                }
            )
    return locations


class InterProExtTool(BaseTool):
    """
    Extended InterPro API tool for protein-by-domain queries.

    Complements existing InterPro tools (get_protein_domains, search_domains,
    get_domain_details) by providing reverse lookup: find all proteins
    containing a specific domain.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "proteins_by_domain")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterPro API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"InterPro API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to InterPro API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"Domain not found in InterPro: {arguments.get('domain_id', '')}",
                }
            return {"status": "error", "error": f"InterPro API HTTP error: {code}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying InterPro API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "proteins_by_domain":
            return self._get_proteins_by_domain(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_proteins_by_domain(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteins containing a specific InterPro domain."""
        domain_id = arguments.get("domain_id", "")
        if not domain_id:
            return {
                "status": "error",
                "error": "domain_id parameter is required (InterPro accession, e.g., IPR011615)",
            }

        page_size = max(1, min(int(arguments.get("page_size") or 20), 50))
        reviewed_only = arguments.get("reviewed_only", False)

        # Build URL for protein search by domain
        db = "reviewed" if reviewed_only else "uniprot"
        url = f"{INTERPRO_API_BASE_URL}/protein/{db}/entry/interpro/{domain_id}"
        params = {"page_size": page_size}
        cursor = arguments.get("cursor")
        if cursor:
            params["cursor"] = cursor

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        # HTTP 204 / empty body == "no protein carries this domain".
        data = _json_or_none(response) or {}

        total_count = data.get("count", 0)
        results = data.get("results", [])
        next_url = data.get("next")
        next_cursor = None
        if next_url:
            cursor_values = parse_qs(urlparse(next_url).query).get("cursor", [])
            next_cursor = cursor_values[0] if cursor_values else None

        proteins = []
        for r in results:
            meta = r.get("metadata", {})
            # The `entries` block of each hit says where on this protein the
            # requested domain sits and what kind of entry it is. For a tool
            # whose question is which proteins CONTAIN a domain, that is the
            # answer's substance, and the row carried none of it: IPR011615
            # on A0A016WYN1 runs 106-281 of 439 residues.
            entry_rows = [e for e in (r.get("entries") or []) if isinstance(e, dict)]
            matched = next(
                (
                    e
                    for e in entry_rows
                    if str(e.get("accession") or "").upper() == domain_id.upper()
                ),
                entry_rows[0] if entry_rows else {},
            )
            locations = _match_locations(entry_rows)
            organism = meta.get("source_organism") or {}
            proteins.append(
                {
                    "accession": meta.get("accession"),
                    "name": meta.get("name"),
                    "source_database": meta.get("source_database"),
                    "length": meta.get("length"),
                    "source_organism": organism.get("scientificName"),
                    "tax_id": organism.get("taxId"),
                    "gene": meta.get("gene"),
                    "in_alphafold": meta.get("in_alphafold"),
                    "match_locations": locations,
                    "match_count": len(locations),
                    "entry_type": matched.get("entry_type"),
                    "entry_source_database": matched.get("source_database"),
                    "entry_integrated_interpro": matched.get("entry_integrated"),
                    "entries_matched": sorted(
                        {e.get("accession") for e in entry_rows if e.get("accession")}
                    ),
                }
            )

        return {
            "status": "success",
            "data": {
                "domain_id": domain_id,
                "total_proteins": total_count,
                "returned": len(proteins),
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "proteins": proteins,
                "page_size": page_size,
                "reviewed_only": reviewed_only,
            },
            "metadata": {
                "source": "InterPro API - Proteins by Domain",
                "domain_id": domain_id,
            },
        }
