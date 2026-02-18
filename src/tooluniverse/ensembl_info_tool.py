# ensembl_info_tool.py
"""
Ensembl Info API tool for ToolUniverse.

Provides access to Ensembl REST API info endpoints for retrieving
genome assembly metadata and species information.

API: https://rest.ensembl.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


ENSEMBL_REST_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


class EnsemblInfoTool(BaseTool):
    """
    Tool for Ensembl info endpoints providing genome assembly metadata
    and species catalog.

    These endpoints complement existing Ensembl tools (sequence, variation,
    overlap, xrefs, etc.) by providing assembly-level and species-level
    information needed for genomic coordinate interpretation.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "assembly")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl info API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {"error": f"Species not found: {arguments.get('species', '')}"}
            return {"error": f"Ensembl API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying Ensembl API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "assembly":
            return self._get_assembly_info(arguments)
        elif self.endpoint == "species":
            return self._get_species_info(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_assembly_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genome assembly metadata for a species."""
        species = arguments.get("species", "")
        if not species:
            return {
                "error": "species parameter is required (e.g., 'homo_sapiens', 'mus_musculus')"
            }

        url = f"{ENSEMBL_REST_BASE_URL}/info/assembly/{species}"
        params = {"content-type": "application/json"}
        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract chromosome information
        top_level = data.get("top_level_region", [])
        chromosomes = []
        for region in top_level:
            if region.get("coord_system") == "chromosome":
                chromosomes.append(
                    {
                        "name": region.get("name"),
                        "length": region.get("length"),
                    }
                )

        # Sort chromosomes (numeric then alphabetic)
        def chrom_sort_key(c):
            name = c.get("name", "")
            try:
                return (0, int(name))
            except ValueError:
                return (1, name)

        chromosomes.sort(key=chrom_sort_key)

        return {
            "data": {
                "species": species,
                "assembly_name": data.get("assembly_name"),
                "assembly_accession": data.get("assembly_accession"),
                "assembly_date": data.get("assembly_date"),
                "genebuild_method": data.get("genebuild_method"),
                "genebuild_last_update": data.get("genebuild_last_geneset_update"),
                "golden_path_length": data.get("golden_path"),
                "karyotype": data.get("karyotype", []),
                "coordinate_system_versions": data.get("coord_system_versions", []),
                "total_regions": len(top_level),
                "chromosomes": chromosomes[:30],
            },
            "metadata": {
                "source": "Ensembl REST API - Assembly Info",
                "species": species,
            },
        }

    def _get_species_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of species available in Ensembl with genome info."""
        search = arguments.get("search", "")

        url = f"{ENSEMBL_REST_BASE_URL}/info/species"
        params = {"content-type": "application/json"}
        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        species_list = data.get("species", [])

        # Filter if search term provided
        if search:
            search_lower = search.lower()
            species_list = [
                s
                for s in species_list
                if search_lower in s.get("display_name", "").lower()
                or search_lower in s.get("name", "").lower()
                or search_lower in s.get("common_name", "").lower()
                or str(s.get("taxon_id", "")) == search
            ]

        # Format results
        species_results = []
        for s in species_list[:50]:
            taxon_id_raw = s.get("taxon_id")
            try:
                taxon_id = int(taxon_id_raw) if taxon_id_raw is not None else None
            except (ValueError, TypeError):
                taxon_id = None
            species_results.append(
                {
                    "name": s.get("name"),
                    "display_name": s.get("display_name"),
                    "common_name": s.get("common_name"),
                    "taxon_id": taxon_id,
                    "assembly": s.get("assembly"),
                    "accession": s.get("accession"),
                    "division": s.get("division"),
                    "strain": s.get("strain"),
                    "strain_collection": s.get("strain_collection"),
                }
            )

        return {
            "data": {
                "total_species": len(data.get("species", [])),
                "matched_species": len(species_results),
                "search_term": search if search else None,
                "species": species_results,
            },
            "metadata": {
                "source": "Ensembl REST API - Species Info",
                "search": search if search else "all",
            },
        }
