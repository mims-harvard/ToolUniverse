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
        key = f"{self.endpoint_type}/{self.query_mode}"
        dispatch_map = {
            "genome/detail": self._genome_detail,
            "genome/search": self._genome_search,
            "biome/list": self._biome_list,
            "study/detail": self._study_detail,
            "analysis/taxonomy": self._analysis_taxonomy,
            "analysis/go_terms": self._analysis_go_terms,
            "analysis/interpro": self._analysis_interpro,
        }
        handler = dispatch_map.get(key)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {key}",
            }
        return handler(arguments)

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
            "status": "success",
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
            "status": "success",
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
            "status": "success",
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
            "status": "success",
            "data": result,
            "metadata": {
                "source": "MGnify",
                "query": study_accession,
                "endpoint": "studies/detail",
            },
        }

    def _fetch_analysis_annotations(
        self, analysis_id: str, annotation_type: str, page_size: int = 25
    ) -> Dict[str, Any]:
        """Shared helper to fetch paginated annotations from an analysis."""
        url = f"{MGNIFY_BASE_URL}/analyses/{analysis_id}/{annotation_type}"
        params = {"format": "json", "page_size": min(page_size, 100)}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _analysis_taxonomy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get taxonomic composition from a MGnify analysis (SSU or LSU)."""
        analysis_id = arguments.get("analysis_id", "")
        if not analysis_id:
            return {
                "status": "error",
                "error": "analysis_id is required (e.g., MGYA00585482)",
            }

        rna_type = arguments.get("rna_type", "ssu")
        if rna_type not in ("ssu", "lsu"):
            rna_type = "ssu"

        page_size = arguments.get("page_size", 25)
        raw = self._fetch_analysis_annotations(
            analysis_id, f"taxonomy/{rna_type}", page_size
        )

        results = []
        for item in raw.get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "organism_id": item.get("id"),
                    "name": attrs.get("name"),
                    "rank": attrs.get("rank"),
                    "domain": attrs.get("domain"),
                    "count": attrs.get("count"),
                    "lineage": attrs.get("lineage"),
                }
            )

        pagination = raw.get("meta", {}).get("pagination", {})
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "analysis_id": analysis_id,
                "rna_type": rna_type,
                "total_results": pagination.get("count", len(results)),
                "page": pagination.get("page", 1),
                "pages": pagination.get("pages"),
                "source": "MGnify",
            },
        }

    def _analysis_go_terms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GO term functional annotations from a MGnify analysis."""
        analysis_id = arguments.get("analysis_id", "")
        if not analysis_id:
            return {
                "status": "error",
                "error": "analysis_id is required (e.g., MGYA00585482)",
            }

        page_size = arguments.get("page_size", 25)
        raw = self._fetch_analysis_annotations(analysis_id, "go-terms", page_size)

        results = []
        for item in raw.get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "go_id": attrs.get("accession"),
                    "description": attrs.get("description"),
                    "count": attrs.get("count"),
                    "category": attrs.get("lineage"),
                }
            )

        pagination = raw.get("meta", {}).get("pagination", {})
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "analysis_id": analysis_id,
                "total_results": pagination.get("count", len(results)),
                "page": pagination.get("page", 1),
                "pages": pagination.get("pages"),
                "source": "MGnify",
            },
        }

    def _analysis_interpro(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get InterPro protein domain annotations from a MGnify analysis."""
        analysis_id = arguments.get("analysis_id", "")
        if not analysis_id:
            return {
                "status": "error",
                "error": "analysis_id is required (e.g., MGYA00585482)",
            }

        page_size = arguments.get("page_size", 25)
        raw = self._fetch_analysis_annotations(
            analysis_id, "interpro-identifiers", page_size
        )

        results = []
        for item in raw.get("data", []):
            attrs = item.get("attributes", {})
            results.append(
                {
                    "interpro_id": attrs.get("accession"),
                    "description": attrs.get("description"),
                    "count": attrs.get("count"),
                }
            )

        pagination = raw.get("meta", {}).get("pagination", {})
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "analysis_id": analysis_id,
                "total_results": pagination.get("count", len(results)),
                "page": pagination.get("page", 1),
                "pages": pagination.get("pages"),
                "source": "MGnify",
            },
        }
