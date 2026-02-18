# ensembl_variation_ext_tool.py
"""
Ensembl Variation Extended tool for ToolUniverse.

Provides variant population frequency data and detailed variant records
from Ensembl, complementing the existing VEP and basic variation tools.

API: https://rest.ensembl.org
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblVariationExtTool")
class EnsemblVariationExtTool(BaseTool):
    """
    Tool for querying Ensembl variant population frequencies and detailed variant info.

    Supports:
    - Allele frequency data across gnomAD and 1000 Genomes populations
    - Detailed variant records with consequences, synonyms, and evidence

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "population_frequencies")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Variation API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            text = ""
            if e.response is not None:
                try:
                    text = e.response.json().get("error", "")
                except Exception:
                    text = e.response.text[:200]
            return {"error": f"Ensembl API HTTP {status}: {text}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "population_frequencies":
            return self._get_population_frequencies(arguments)
        elif self.endpoint == "variant_detail":
            return self._get_variant_detail(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_population_frequencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get allele frequencies across global populations."""
        variant_id = arguments.get("variant_id", "")
        species = arguments.get("species", "human")

        if not variant_id:
            return {"error": "variant_id is required (e.g., 'rs429358')."}

        url = f"{ENSEMBL_BASE_URL}/variation/{species}/{variant_id}"
        response = requests.get(
            url,
            params={"pops": "1", "content-type": "application/json"},
            headers=ENSEMBL_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Extract location info from mappings
        location = {}
        mappings = data.get("mappings", [])
        if mappings:
            m = mappings[0]
            location = {
                "chromosome": m.get("seq_region_name"),
                "start": m.get("start"),
                "allele_string": m.get("allele_string"),
                "assembly": m.get("assembly_name"),
            }

        # Process population data
        populations = []
        for pop in data.get("populations", []):
            populations.append(
                {
                    "population": pop.get("population"),
                    "allele": pop.get("allele"),
                    "frequency": pop.get("frequency"),
                    "allele_count": pop.get("allele_count"),
                    "count": pop.get("count"),
                }
            )

        # Get unique population names
        unique_pops = set(p.get("population", "") for p in populations)

        return {
            "data": {
                "variant_id": data.get("name"),
                "most_severe_consequence": data.get("most_severe_consequence"),
                "source": data.get("source"),
                "location": location,
                "populations": populations,
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_population_entries": len(populations),
                "unique_populations": len(unique_pops),
            },
        }

    def _get_variant_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed variant information."""
        variant_id = arguments.get("variant_id", "")
        species = arguments.get("species", "human")

        if not variant_id:
            return {"error": "variant_id is required (e.g., 'rs429358')."}

        url = f"{ENSEMBL_BASE_URL}/variation/{species}/{variant_id}"
        response = requests.get(
            url,
            params={"content-type": "application/json"},
            headers=ENSEMBL_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        # Extract mappings
        mappings = []
        for m in data.get("mappings", []):
            mappings.append(
                {
                    "seq_region_name": m.get("seq_region_name"),
                    "start": m.get("start"),
                    "end": m.get("end"),
                    "allele_string": m.get("allele_string"),
                    "strand": m.get("strand"),
                    "assembly_name": m.get("assembly_name"),
                }
            )

        synonyms = data.get("synonyms", [])

        return {
            "data": {
                "name": data.get("name"),
                "source": data.get("source"),
                "most_severe_consequence": data.get("most_severe_consequence"),
                "ancestral_allele": data.get("ancestral_allele"),
                "minor_allele": data.get("minor_allele"),
                "MAF": data.get("MAF"),
                "synonyms": synonyms,
                "mappings": mappings,
                "evidence": data.get("evidence", []),
                "clinical_significance": data.get("clinical_significance", []),
            },
            "metadata": {
                "source": "Ensembl REST API (rest.ensembl.org)",
                "total_synonyms": len(synonyms),
                "total_mappings": len(mappings),
            },
        }
