# bold_systems_tool.py
"""
BOLD Systems tools for ToolUniverse -- DNA barcode records and BINs.

BOLD (Barcode of Life Data System, portal.boldsystems.org) is the primary
global repository of DNA barcode sequences (mostly COI-5P) for species
identification, run by the Centre for Biodiversity Genomics. Its signature
concept is the BIN (Barcode Index Number): an algorithmically-clustered,
sequence-similarity-based operational taxonomic unit that often resolves
species-level identity where morphology or existing taxonomy cannot -- a
capability nothing else in ToolUniverse provides. ToolUniverse's existing
iDigBioSearchTool covers Darwin Core specimen/occurrence records but has no
genetic barcode data or BIN clustering.

The public query API (https://portal.boldsystems.org/api) is a two-step
flow: GET /api/query builds a query from semicolon-delimited "triplet"
tokens ([scope]:[subscope]:[value]) and returns a query_id; GET
/api/documents/{query_id} then pages through the actual records. Confirmed
working triplet scopes/subscopes (live-tested): tax:genus, tax:family,
tax:order, geo:country, ids:processid, bin:uri. tax:species was tested
extensively (several subscope-name guesses, e.g. "species", "epithet",
"binomial") and is silently ignored by the server rather than filtering --
so species-level search here is done by querying at the genus level and
filtering client-side on the returned "species" field, the same workaround
pattern used elsewhere in ToolUniverse for APIs with non-functional
server-side filters.

No authentication required.
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BOLD_BASE_URL = "https://portal.boldsystems.org/api"

_RANK_SCOPES = {
    "genus": "tax:genus",
    "family": "tax:family",
    "order": "tax:order",
    "species": "tax:genus",  # BOLD ignores tax:species; filter client-side.
}

_RECORD_FIELDS = (
    "processid",
    "sampleid",
    "bin_uri",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "subfamily",
    "genus",
    "species",
    "identification",
    "identification_rank",
    "country/ocean",
    "province/state",
    "collectors",
    "collection_date_start",
    "collection_date_end",
    "inst",
    "marker_code",
    "nuc_basecount",
    "insdc_acs",
)


def _summarize(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {field: rec.get(field) for field in _RECORD_FIELDS}


def _bold_get(url: str, params: Dict[str, Any], timeout: int):
    """GET a BOLD endpoint, returning (payload, error_envelope).

    Exactly one of the two is non-None; the error envelope is the standard
    {"status": "error", ...} dict so callers never raise.
    """
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code >= 500:
            return None, {
                "status": "error",
                "error": f"BOLD Systems rejected the query (HTTP {resp.status_code}): "
                f"{resp.text[:200]}",
            }
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, {
            "status": "error",
            "error": f"BOLD Systems request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"BOLD Systems request failed: {e}"}
    except ValueError:
        return None, {
            "status": "error",
            "error": "BOLD Systems returned a non-JSON response",
        }


def _run_query(
    query: str, length: int, timeout: int
) -> "tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]":
    """Run the query -> query_id -> documents two-step flow."""
    query_payload, err = _bold_get(
        f"{BOLD_BASE_URL}/query",
        {"query": query, "extent": "limited"},
        timeout,
    )
    if err is not None:
        return None, err
    query_id = (query_payload or {}).get("query_id")
    if not query_id:
        return None, {
            "status": "error",
            "error": f"BOLD Systems returned no query_id for query '{query}'.",
        }
    doc_payload, err = _bold_get(
        f"{BOLD_BASE_URL}/documents/{query_id}",
        {"start": 0, "length": length},
        timeout,
    )
    if err is not None:
        return None, err
    return doc_payload, None


@register_tool("BOLDSystemsTool")
class BOLDSystemsTool(BaseTool):
    """
    Tool for querying BOLD Systems (Barcode of Life Data System) DNA barcode
    records, dispatched by fields.operation:
      - "search_by_taxon" : records for a genus/family/order/species, optionally
                            narrowed by country
      - "search_by_bin"   : records sharing a BIN (Barcode Index Number) cluster
      - "get_record"      : a single record by its BOLD process ID

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_by_taxon"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.operation == "search_by_taxon":
                return self._search_by_taxon(arguments)
            if self.operation == "search_by_bin":
                return self._search_by_bin(arguments)
            if self.operation == "get_record":
                return self._get_record(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying BOLD Systems: {str(e)}",
            }

    def _limit(self, arguments: Dict[str, Any], default: int = 30) -> int:
        try:
            return max(1, min(int(arguments.get("limit") or default), 200))
        except (TypeError, ValueError):
            return default

    def _search_by_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        taxon_name = (arguments.get("taxon_name") or "").strip()
        if not taxon_name:
            return {
                "status": "error",
                "error": "taxon_name is required, e.g. 'Panthera' (genus) or "
                "'Panthera leo' (species).",
            }

        rank = (arguments.get("rank") or "genus").strip().lower()
        if rank not in _RANK_SCOPES:
            return {
                "status": "error",
                "error": f"rank must be one of {sorted(_RANK_SCOPES)}, got '{rank}'.",
            }

        # BOLD's tax:species triplet is silently ignored server-side, so
        # species search runs at genus level and filters client-side below.
        query_taxon = taxon_name.split()[0] if rank == "species" else taxon_name
        triplets = [f"{_RANK_SCOPES[rank]}:{query_taxon}"]

        country = (arguments.get("country") or "").strip()
        if country:
            triplets.append(f"geo:country:{country}")

        limit = self._limit(arguments)
        # Fetch extra raw rows when species-filtering client-side, since most
        # of a genus's records won't match one target species.
        fetch_length = min(limit * 10, 1000) if rank == "species" else limit

        payload, err = _run_query(";".join(triplets), fetch_length, self.timeout)
        if err is not None:
            return err

        rows = payload.get("data") or []
        if rank == "species":
            target = taxon_name.strip().lower()
            rows = [r for r in rows if (r.get("species") or "").strip().lower() == target]
        rows = rows[:limit]

        return {
            "status": "success",
            "data": [_summarize(r) for r in rows],
            "metadata": {
                "query": ";".join(triplets),
                "rank": rank,
                "returned": len(rows),
                "records_total": payload.get("recordsTotal"),
                "note": (
                    "records_total is the genus-level count before "
                    "client-side species filtering; BOLD does not support "
                    "server-side species-level filtering."
                    if rank == "species"
                    else None
                ),
                "source": "BOLD Systems (portal.boldsystems.org)",
            },
        }

    def _search_by_bin(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        bin_id = (arguments.get("bin_id") or "").strip()
        if not bin_id:
            return {
                "status": "error",
                "error": "bin_id is required, e.g. 'BOLD:AAD6819'.",
            }
        if not bin_id.upper().startswith("BOLD:"):
            bin_id = f"BOLD:{bin_id}"

        limit = self._limit(arguments)
        payload, err = _run_query(f"bin:uri:{bin_id}", limit, self.timeout)
        if err is not None:
            return err

        rows = (payload.get("data") or [])[:limit]
        return {
            "status": "success",
            "data": [_summarize(r) for r in rows],
            "metadata": {
                "bin_id": bin_id,
                "returned": len(rows),
                "records_total": payload.get("recordsTotal"),
                "source": "BOLD Systems (portal.boldsystems.org)",
            },
        }

    def _get_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        process_id = (arguments.get("process_id") or "").strip()
        if not process_id:
            return {
                "status": "error",
                "error": "process_id is required, e.g. 'ABRMM002-06'.",
            }

        payload, err = _run_query(f"ids:processid:{process_id}", 1, self.timeout)
        if err is not None:
            return err

        rows = payload.get("data") or []
        if not rows:
            return {
                "status": "error",
                "error": f"No BOLD record found for process ID '{process_id}'.",
            }

        return {
            "status": "success",
            "data": _summarize(rows[0]),
            "metadata": {
                "process_id": process_id,
                "source": "BOLD Systems (portal.boldsystems.org)",
            },
        }
