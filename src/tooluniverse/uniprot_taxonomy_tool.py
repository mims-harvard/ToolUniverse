# uniprot_taxonomy_tool.py
"""
UniProt Taxonomy tool for ToolUniverse.

Provides taxonomy information from UniProt including species details,
lineage, protein statistics, and taxonomy search.

API: https://rest.uniprot.org/taxonomy/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPROT_BASE_URL = "https://rest.uniprot.org/taxonomy"


def _as_taxon_int(taxon_id: Any) -> Any:
    """The caller's taxon id as an int, or None when it isn't one.

    Callers pass taxon ids as either 9606 or "9606", and both must compare
    equal to UniProt's integer ``taxonId`` -- otherwise every string-typed
    lookup would be reported as a merge.
    """
    try:
        return int(str(taxon_id).strip())
    except (TypeError, ValueError):
        return None


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

        # Fix-R60-2: UniProt answers a merged (retired) taxon with an HTTP 303
        # to the node it was merged into, so `requests` follows the redirect
        # and `data` describes a DIFFERENT taxon than the caller asked for.
        # Nothing here recorded that. Confirmed live: taxon 46170 is
        # Staphylococcus aureus subsp. aureus -- the subspecies node most
        # older BioSample/BioProject MRSA records are filed under -- and
        # {"taxon_id": "46170"} returned taxon_id 1280 / "Staphylococcus
        # aureus" (the species node, with a larger protein-count denominator)
        # with the requested id appearing nowhere in the response, so the
        # substitution was undetectable. UniProt publishes the merge plainly:
        #   curl -sD- -o/dev/null https://rest.uniprot.org/taxonomy/46170
        #     HTTP/2 303 ... location: /taxonomy/1280?from=46170
        #   curl -s --max-redirs 0 https://rest.uniprot.org/taxonomy/46170
        #     {"taxonId":46170,"inactiveReason":{"inactiveReasonType":
        #      "MERGED","mergedTo":1280}}
        # Answer with the current record, as before, but say that is what
        # happened -- the same obsolete-identifier disclosure already shipped
        # for Mondo, Monarch and HPO. Comparing the two ids needs no extra
        # request, so this costs nothing.
        returned_id = data.get("taxonId")
        payload: Dict[str, Any] = {
            "query_taxon_id": taxon_id,
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

        requested_id = _as_taxon_int(taxon_id)
        if requested_id is not None and returned_id != requested_id:
            payload["merged_from"] = requested_id
            metadata["note"] = (
                f"NCBI taxon {requested_id} is no longer an active node in "
                f"UniProt's taxonomy: UniProt has merged it into {returned_id} "
                f"({data.get('scientificName')}), and redirected this lookup "
                f"there. Everything below describes {returned_id}, not "
                f"{requested_id} -- in particular the protein counts are for "
                "the merged node, which may sit at a higher rank than the "
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
