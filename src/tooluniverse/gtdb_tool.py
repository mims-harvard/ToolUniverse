"""
GTDB Tool - Genome Taxonomy Database

GTDB provides a standardized genome-based taxonomy for prokaryotes (Bacteria
and Archaea). The taxonomy is built from phylogenomic analysis of genome
sequences, resolving polyphyletic groups in NCBI taxonomy and providing a
consistent, genome-based classification system.

API base: https://gtdb-api.ecogenomic.org
No authentication required.

GTDB taxon naming convention: prefix__name
  d__ (domain), p__ (phylum), c__ (class), o__ (order),
  f__ (family), g__ (genus), s__ (species)

Reference: Parks et al., Nature Biotechnology 2018, 36:996-1004
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


GTDB_BASE_URL = "https://gtdb-api.ecogenomic.org"


@register_tool("GTDBTool")
class GTDBTool(BaseTool):
    """
    Tool for querying the Genome Taxonomy Database (GTDB).

    GTDB is a genome-based taxonomy for prokaryotes, maintained by the
    Ecogenomics lab at the University of Queensland.

    Supported operations:
    - search_taxon: Search for taxa by partial name
    - get_species: Get species cluster details with genomes
    - get_taxon_info: Get taxon card info (rank, genome count, lineage)
    - search_genomes: Search genomes by organism name
    - get_genome: Get detailed genome metadata
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GTDB API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_taxon": self._search_taxon,
            "get_species": self._get_species,
            "get_taxon_info": self._get_taxon_info,
            "search_genomes": self._search_genomes,
            "get_genome": self._get_genome,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "GTDB API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to GTDB API"}
        except Exception as e:
            return {
                "status": "error",
                "error": "GTDB operation failed: {}".format(str(e)),
            }

    def _make_request(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to GTDB API."""
        url = "{}/{}".format(GTDB_BASE_URL, path)
        response = self.session.get(url, params=params or {}, timeout=self.timeout)
        if response.status_code == 200:
            try:
                data = response.json()
                return {"ok": True, "data": data}
            except ValueError:
                ct = response.headers.get("content-type", "")
                return {
                    "ok": False,
                    "error": "Invalid JSON response from GTDB API",
                    "content_type": ct,
                    "response_snippet": response.text[:200],
                    "retryable": "text/html" in ct
                    or response.text.lstrip().startswith("<"),
                    "suggestion": "GTDB API may be under maintenance. Retry in a few minutes.",
                }
        elif response.status_code == 400:
            try:
                err = response.json()
                return {"ok": False, "error": err.get("detail", "Bad request")}
            except ValueError:
                return {
                    "ok": False,
                    "error": "Bad request",
                    "response_snippet": response.text[:200],
                }
        elif response.status_code == 404:
            return {"ok": False, "error": "Taxon or resource not found in GTDB"}
        else:
            return {
                "ok": False,
                "error": "GTDB API returned status {}".format(response.status_code),
            }

    def _search_taxon(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for taxa by partial name."""
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = arguments.get("limit", 20)
        result = self._make_request(
            "taxon/search/{}".format(query),
            params={"limit": min(limit, 100)},
        )

        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        matches = result["data"].get("matches", [])
        return {
            "status": "success",
            "data": {
                "query": query,
                "matches": matches,
                "count": len(matches),
            },
        }

    def _get_species(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get species cluster details."""
        species = arguments.get("species")
        if not species:
            return {"status": "error", "error": "species parameter is required"}

        result = self._make_request("species/search/{}".format(species))
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        # Limit genomes list to avoid huge responses
        genomes = data.get("genomes", [])
        total_genomes = len(genomes)
        max_genomes = arguments.get("max_genomes", 20)
        if total_genomes > max_genomes:
            genomes = genomes[:max_genomes]

        return {
            "status": "success",
            "data": {
                "species_name": data.get("name", species),
                "total_genomes": total_genomes,
                "genomes_shown": len(genomes),
                "genomes": genomes,
            },
        }

    def _get_taxon_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxon card info (rank, genome count, higher ranks)."""
        taxon = arguments.get("taxon")
        if not taxon:
            return {"status": "error", "error": "taxon parameter is required"}

        # Ensure taxon has a GTDB prefix
        prefixes = ["d__", "p__", "c__", "o__", "f__", "g__", "s__"]
        has_prefix = any(taxon.startswith(p) for p in prefixes)

        # Get card info
        result = self._make_request("taxon/{}/card".format(taxon))
        if not result["ok"]:
            # If the original failed and we don't have a prefix, try with common prefixes
            if not has_prefix:
                for prefix in prefixes:
                    result = self._make_request("taxon/{}{}/card".format(prefix, taxon))
                    if result["ok"]:
                        taxon = prefix + taxon
                        break
            if not result["ok"]:
                return {"status": "error", "error": result["error"]}

        card = result["data"]

        # Also get the full lineage
        lineage_result = self._make_request("taxonomy/partial/{}".format(taxon))
        lineage = lineage_result["data"] if lineage_result["ok"] else None

        return {
            "status": "success",
            "data": {
                "taxon": taxon,
                "rank": card.get("rank"),
                "n_genomes": card.get("nGenomes"),
                "higher_ranks": card.get("higherRanks", []),
                "in_releases": card.get("inReleases", []),
                "lineage": lineage,
            },
        }

    def _search_genomes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search genomes by organism name."""
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        page = arguments.get("page", 1)
        items_per_page = arguments.get("items_per_page", 10)

        result = self._make_request(
            "search/gtdb",
            params={
                "search": query,
                "page": page,
                "itemsPerPage": min(items_per_page, 50),
            },
        )

        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]
        rows = data.get("rows", [])
        total = data.get("totalRows", len(rows))

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_results": total,
                "page": page,
                "results": rows,
                "count": len(rows),
            },
        }

    def _get_genome(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed genome metadata by accession."""
        accession = arguments.get("accession")
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        result = self._make_request("genome/{}/card".format(accession))
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        data = result["data"]

        # Also get taxon history
        history_result = self._make_request("genome/{}/taxon-history".format(accession))
        taxon_history = history_result["data"] if history_result["ok"] else []

        return {
            "status": "success",
            "data": {
                "genome": data.get("genome", {}),
                "metadata_nucleotide": data.get("metadata_nucleotide", {}),
                "metadata_gene": data.get("metadata_gene", {}),
                "metadata_ncbi": data.get("metadata_ncbi", {}),
                "gtdb_taxonomy": data.get("metadata_taxonomy", {}),
                "taxon_history": taxon_history,
            },
        }
