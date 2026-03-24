# mgnify_expanded_tool.py
"""
MGnify Expanded REST API tool for ToolUniverse.

MGnify (formerly EBI Metagenomics) provides analysis and archiving of
metagenomics data. This expanded tool covers genomes, taxonomy, biomes,
and samples - complementing the existing study/analysis search tools.

API: https://www.ebi.ac.uk/metagenomics/api/v1
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MGNIFY_BASE_URL = "https://www.ebi.ac.uk/metagenomics/api/v1"


@register_tool("MGnifyExpandedTool")
class MGnifyExpandedTool(BaseTool):
    """
    Expanded tool for querying MGnify metagenomics database.

    Covers genome catalog, taxonomic profiling, biome browsing,
    and sample metadata - extending existing study/analysis tools.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "genome"
        )
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "detail")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MGnify API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MGnify API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to MGnify API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"MGnify API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying MGnify: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "genome" and self.query_mode == "detail":
            return self._genome_detail(arguments)
        elif self.endpoint_type == "genome" and self.query_mode == "search":
            return self._genome_search(arguments)
        elif self.endpoint_type == "biome" and self.query_mode == "list":
            return self._biome_list(arguments)
        elif self.endpoint_type == "study" and self.query_mode == "detail":
            return self._study_detail(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {self.endpoint_type}/{self.query_mode}",
            }

    def _genome_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a MGnify genome."""
        genome_id = arguments.get("genome_id", "")
        if not genome_id:
            return {
                "status": "error",
                "error": "genome_id parameter is required (e.g., MGYG000000001)",
            }

        url = f"{MGNIFY_BASE_URL}/genomes/{genome_id}"
        response = requests.get(url, params={"format": "json"}, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        data = raw.get("data", {})
        attrs = data.get("attributes", {})

        result = {
            "genome_id": data.get("id"),
            "accession": attrs.get("accession"),
            "type": attrs.get("type"),
            "taxonomy": attrs.get("taxon-lineage"),
            "length": attrs.get("length"),
            "num_contigs": attrs.get("num-contigs"),
            "n50": attrs.get("n-50"),
            "gc_content": attrs.get("gc-content"),
            "completeness": attrs.get("completeness"),
            "contamination": attrs.get("contamination"),
            "num_proteins": attrs.get("num-proteins"),
            "rna_16s": attrs.get("rna-16s"),
            "rna_23s": attrs.get("rna-23s"),
            "trnas": attrs.get("trnas"),
            "geographic_origin": attrs.get("geographic-origin"),
            "geographic_range": attrs.get("geographic-range"),
            "ena_genome_accession": attrs.get("ena-genome-accession"),
            "ena_sample_accession": attrs.get("ena-sample-accession"),
            "pangenome_size": attrs.get("pangenome-size"),
            "pangenome_core_size": attrs.get("pangenome-core-size"),
            "pangenome_accessory_size": attrs.get("pangenome-accessory-size"),
            "eggnog_coverage": attrs.get("eggnog-coverage"),
            "ipr_coverage": attrs.get("ipr-coverage"),
        }

        return {
            "data": result,
            "metadata": {
                "source": "MGnify",
                "query": genome_id,
                "endpoint": "genomes/detail",
            },
        }

    def _genome_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search/list MGnify genomes with optional filters."""
        params = {"format": "json"}

        page = arguments.get("page", 1)
        page_size = min(arguments.get("page_size", 25), 100)
        params["page"] = page
        params["page_size"] = page_size

        if "taxonomy" in arguments:
            params["lineage"] = arguments["taxonomy"]

        if "genome_type" in arguments:
            params["genome_type"] = arguments["genome_type"]

        url = f"{MGNIFY_BASE_URL}/genomes"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        results = []
        for item in raw.get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "genome_id": item.get("id"),
                    "type": attrs.get("type"),
                    "taxonomy": attrs.get("taxon-lineage"),
                    "completeness": attrs.get("completeness"),
                    "contamination": attrs.get("contamination"),
                    "length": attrs.get("length"),
                    "num_proteins": attrs.get("num-proteins"),
                    "gc_content": attrs.get("gc-content"),
                }
            )

        pagination = raw.get("meta", {}).get("pagination", {})

        return {
            "data": results,
            "metadata": {
                "total_results": pagination.get("count", len(results)),
                "page": pagination.get("page", page),
                "pages": pagination.get("pages"),
                "source": "MGnify",
                "endpoint": "genomes/search",
            },
        }

    def _biome_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Browse/search MGnify biome hierarchy."""
        params = {"format": "json"}

        page_size = min(arguments.get("page_size", 25), 100)
        params["page_size"] = page_size
        if "page" in arguments:
            params["page"] = arguments["page"]

        if "depth" in arguments:
            params["depth"] = arguments["depth"]

        url = f"{MGNIFY_BASE_URL}/biomes"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        results = []
        for item in raw.get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "biome_id": item.get("id"),
                    "biome_name": attrs.get("biome-name"),
                    "samples_count": attrs.get("samples-count"),
                }
            )

        pagination = raw.get("meta", {}).get("pagination", {})

        return {
            "data": results,
            "metadata": {
                "total_results": pagination.get("count", len(results)),
                "page": pagination.get("page", 1),
                "pages": pagination.get("pages"),
                "source": "MGnify",
                "endpoint": "biomes",
            },
        }

    def _study_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific MGnify study."""
        study_accession = arguments.get("study_accession", "")
        if not study_accession:
            return {
                "status": "error",
                "error": "study_accession parameter is required (e.g., MGYS00002008)",
            }

        url = f"{MGNIFY_BASE_URL}/studies/{study_accession}"
        response = requests.get(url, params={"format": "json"}, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        data = raw.get("data", {})
        attrs = data.get("attributes", {})
        rels = data.get("relationships", {})

        result = {
            "study_id": data.get("id"),
            "study_name": attrs.get("study-name"),
            "study_abstract": attrs.get("study-abstract"),
            "bioproject": attrs.get("bioproject"),
            "centre_name": attrs.get("centre-name"),
            "is_public": attrs.get("is-public"),
            "last_update": attrs.get("last-update"),
            "analyses_count": rels.get("analyses", {}).get("meta", {}).get("count"),
            "downloads_count": rels.get("downloads", {}).get("meta", {}).get("count"),
            "biomes": [b.get("id") for b in rels.get("biomes", {}).get("data", [])],
        }

        return {
            "data": result,
            "metadata": {
                "source": "MGnify",
                "query": study_accession,
                "endpoint": "studies/detail",
            },
        }
