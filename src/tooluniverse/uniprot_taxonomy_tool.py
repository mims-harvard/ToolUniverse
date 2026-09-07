# uniprot_taxonomy_tool.py
"""
UniProt Taxonomy tool for ToolUniverse.

Provides taxonomy information from UniProt including species details,
lineage, protein statistics, and taxonomy search.

API: https://rest.uniprot.org/taxonomy/
No authentication required.
"""

import requests
import urllib.parse
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPROT_BASE_URL = "https://rest.uniprot.org/taxonomy"


def _as_taxon_int(taxon_id: Any) -> Optional[int]:
    """The caller's taxon id as an int, or None when it isn't one.

    Callers pass taxon ids as either 9606 or "9606", and both must compare
    equal to UniProt's integer ``taxonId`` -- otherwise every string-typed
    lookup would be reported as a merge.
    """
    try:
        return int(str(taxon_id).strip())
    except (TypeError, ValueError):
        return None


def _redirected_from(response: Any) -> Optional[int]:
    """The taxon id UniProt says it redirected away from, if it says so.

    UniProt answers a retired taxon with ``303 -> /taxonomy/<new>?from=<old>``,
    so the ``from`` param on the final URL is UniProt stating the substitution
    outright. Preferred over inferring a merge from an id mismatch, so the
    disclosure can assert only what the API actually reported.

    The isinstance check is load-bearing: a stubbed response's ``url`` may be
    a Mock rather than a string, and urlparse raises TypeError on it.
    """
    url = getattr(response, "url", None)
    if not isinstance(url, str):
        return None
    values = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("from")
    return _as_taxon_int(values[0]) if values else None


@register_tool("UniProtTaxonomyTool")
class UniProtTaxonomyTool(BaseTool):
    """
    Tool for querying UniProt taxonomy data.

    Supports:
    - Get taxonomy details by NCBI taxon ID
    - Search taxonomy by name

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_taxon")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniProt Taxonomy API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UniProt API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to UniProt REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"UniProt API HTTP {status}: taxon may not exist",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_taxon":
            return self._get_taxon(arguments)
        elif self.endpoint == "search":
            return self._search(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomy details by NCBI taxon ID."""
        taxon_id = arguments.get("taxon_id")
        if not taxon_id:
            return {
                "status": "error",
                "error": "taxon_id is required (e.g., 9606 for human).",
            }

        url = f"{UNIPROT_BASE_URL}/{taxon_id}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Process lineage
        lineage = []
        for item in data.get("lineage", []):
            lineage.append(
                {
                    "taxon_id": item.get("taxonId"),
                    "scientific_name": item.get("scientificName"),
                    "rank": item.get("rank"),
                    "hidden": item.get("hidden", False),
                }
            )

        stats = data.get("statistics", {})

        # Fix-R60-2: UniProt answers a merged (retired) taxon with a 303 to the
        # node it was merged into, so `requests` follows the redirect and
        # `data` describes a DIFFERENT taxon than the caller asked for, with
        # the requested id appearing nowhere in the response. See
        # tests/unit/test_uniprot_taxonomy_merged_taxon_disclosed.py for the
        # live transcripts. Answer with the current record, as before, but say
        # that is what happened -- the same obsolete-identifier disclosure
        # already shipped for Mondo, Monarch and HPO.
        returned_id = data.get("taxonId")
        requested_id = _as_taxon_int(taxon_id)
        payload: Dict[str, Any] = {
            # Echo the normalized id so a caller can compare it against
            # `taxon_id` directly; "9606" and 9606 are one taxon, and a raw
            # echo would make every string-typed lookup look like a merge.
            "query_taxon_id": requested_id if requested_id is not None else taxon_id,
            "taxon_id": returned_id,
            "scientific_name": data.get("scientificName"),
            "common_name": data.get("commonName"),
            "mnemonic": data.get("mnemonic"),
            "rank": data.get("rank"),
            "lineage": lineage,
            "statistics": {
                "reviewed_protein_count": stats.get("reviewedProteinCount", 0),
                "unreviewed_protein_count": stats.get("unreviewedProteinCount", 0),
            },
        }
        metadata: Dict[str, Any] = {"source": "UniProt Taxonomy (rest.uniprot.org)"}

        # Prefer what UniProt states over what an id mismatch implies. The
        # `?from=` param on the redirected URL, and `inactiveReason` when the
        # inactive stub itself comes back, are UniProt reporting the
        # substitution; an id mismatch alone is only evidence that one
        # happened, so that case is worded more cautiously. All three are read
        # from the response already in hand -- no extra request.
        inactive = data.get("inactiveReason") or {}
        stated_from = _redirected_from(response)
        merged_to = inactive.get("mergedTo") if isinstance(inactive, dict) else None
        reason = (
            inactive.get("inactiveReasonType") if isinstance(inactive, dict) else None
        )
        obsolete_id = stated_from or (requested_id if merged_to else None)
        if obsolete_id is None and requested_id is not None and returned_id != requested_id:
            obsolete_id = requested_id

        if obsolete_id is not None and obsolete_id != returned_id:
            payload["merged_from"] = obsolete_id
            if stated_from is not None or merged_to is not None:
                how = (
                    f"UniProt reports it as {str(reason).lower()} into "
                    if reason
                    else "UniProt has merged it into "
                )
                lead = (
                    f"NCBI taxon {obsolete_id} is no longer an active node in "
                    f"UniProt's taxonomy: {how}{returned_id} "
                    f"({data.get('scientificName')}), and redirected this "
                    "lookup there."
                )
            else:
                lead = (
                    f"UniProt answered the lookup for NCBI taxon {obsolete_id} "
                    f"with taxon {returned_id} ({data.get('scientificName')}). "
                    "UniProt did not state why, but this is what it does for "
                    "an identifier that has been retired or merged."
                )
            metadata["note"] = (
                f"{lead} Everything below describes {returned_id}, not "
                f"{obsolete_id} -- in particular the protein counts are for "
                "the returned node, which may sit at a higher rank than the "
                "identifier you supplied."
            )

        return {
            "status": "success",
            "data": payload,
            "metadata": metadata,
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search taxonomy by name."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query is required (e.g., 'arabidopsis').",
            }

        size = arguments.get("size", 10)

        url = f"{UNIPROT_BASE_URL}/search"
        response = requests.get(
            url,
            params={"query": query, "size": size},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("results", []):
            stats = item.get("statistics", {})
            results.append(
                {
                    "taxon_id": item.get("taxonId"),
                    "scientific_name": item.get("scientificName"),
                    "common_name": item.get("commonName"),
                    "mnemonic": item.get("mnemonic"),
                    "rank": item.get("rank"),
                    "reviewed_protein_count": stats.get("reviewedProteinCount", 0),
                    "unreviewed_protein_count": stats.get("unreviewedProteinCount", 0),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "UniProt Taxonomy (rest.uniprot.org)",
                "total_results": len(results),
                "query": query,
            },
        }
