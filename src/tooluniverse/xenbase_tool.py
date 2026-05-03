"""
Xenbase Tool - Xenopus (Frog) Model Organism Database

Provides access to Xenopus gene data through the Alliance of Genome Resources
API. Xenbase is the primary database for Xenopus tropicalis and Xenopus laevis
genetics, genomics, and developmental biology.

Note: Xenbase does not have a public REST/JSON API. Data is accessed through
the Alliance of Genome Resources (alliancegenome.org) which aggregates Xenbase
data alongside other model organism databases.

Supported species:
- Xenopus tropicalis (NCBITaxon:8364) - Western clawed frog
- Xenopus laevis (NCBITaxon:8355) - African clawed frog

API: https://www.alliancegenome.org/api
No authentication required.

Reference: Fisher et al., Nucl. Acids Res. 2023 (Xenbase)
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


ALLIANCE_BASE = "https://www.alliancegenome.org/api"
XENOPUS_TAXON_IDS = ["NCBITaxon:8364", "NCBITaxon:8355"]


@register_tool("XenbaseTool")
class XenbaseTool(BaseTool):
    """
    Tool for querying Xenopus gene data via the Alliance of Genome Resources.

    Supported operations:
    - search_genes: Search Xenopus genes by name/symbol
    - get_gene: Get detailed gene information by Xenbase gene ID
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_genes"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Xenbase/Alliance API call."""
        try:
            if self.endpoint_type == "search_genes":
                return self._search_genes(arguments)
            elif self.endpoint_type == "get_gene":
                return self._get_gene(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint type: {self.endpoint_type}",
                }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Xenbase API request timed out"}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Alliance API for Xenbase data",
            }
        except Exception as e:
            return {"status": "error", "error": f"Xenbase API error: {str(e)}"}

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for Xenopus genes by name or symbol."""
        query = arguments.get("query") or arguments.get("gene_name", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        limit = arguments.get("limit", 10)
        species = arguments.get("species", "")

        # Map species names to taxon IDs
        taxon_filter = None
        if species:
            species_lower = species.lower()
            if "tropicalis" in species_lower or "8364" in species_lower:
                taxon_filter = "NCBITaxon:8364"
            elif "laevis" in species_lower or "8355" in species_lower:
                taxon_filter = "NCBITaxon:8355"

        url = f"{ALLIANCE_BASE}/search"
        params = {"q": query, "category": "gene", "limit": limit}

        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            pk = r.get("primaryKey", "")
            sp = r.get("species", "")
            if not pk.startswith("Xenbase:"):
                continue
            if taxon_filter and taxon_filter not in str(r.get("taxonId", "")):
                # Filter by species name in text if taxonId not present
                if taxon_filter == "NCBITaxon:8364" and "tropicalis" not in sp.lower():
                    continue
                if taxon_filter == "NCBITaxon:8355" and "laevis" not in sp.lower():
                    continue

            results.append(
                {
                    "gene_id": pk,
                    "symbol": r.get("symbol"),
                    "name": r.get("name"),
                    "species": sp,
                    "synonyms": r.get("synonyms", [])[:5],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "total_alliance_results": data.get("total", 0),
                "xenbase_results": len(results),
            },
        }

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed gene information by Xenbase gene ID."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "Missing required parameter: gene_id"}

        # Ensure Xenbase: prefix
        if not gene_id.startswith("Xenbase:"):
            gene_id = f"Xenbase:{gene_id}"

        url = f"{ALLIANCE_BASE}/gene/{gene_id}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code == 404:
            return {"status": "error", "error": f"Gene not found: {gene_id}"}
        resp.raise_for_status()
        data = resp.json()

        species_info = data.get("species", {})
        genome_locations = data.get("genomeLocations", [])
        location = None
        if genome_locations:
            loc = genome_locations[0]
            location = {
                "chromosome": loc.get("chromosome"),
                "start": loc.get("start"),
                "end": loc.get("end"),
                "strand": loc.get("strand"),
                "assembly": loc.get("assembly"),
            }

        result = {
            "gene_id": data.get("id"),
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "species": {
                "name": species_info.get("name"),
                "short_name": species_info.get("shortName"),
                "taxon_id": species_info.get("taxonId"),
                "data_provider": species_info.get("dataProviderShortName"),
            },
            "synonyms": data.get("synonyms", []),
            "gene_synopsis": data.get("geneSynopsis"),
            "automated_gene_synopsis": data.get("automatedGeneSynopsis"),
            "so_term": data.get("soTerm", {}).get("name")
            if data.get("soTerm")
            else None,
            "genomic_location": location,
            "xenbase_url": data.get("modCrossRefCompleteUrl"),
            "cross_references": {
                k: v for k, v in (data.get("crossReferenceMap") or {}).items() if v
            },
        }

        return {"status": "success", "data": result}
