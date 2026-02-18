# ensembl_ld_tool.py
"""
Ensembl REST API Linkage Disequilibrium (LD) tool for ToolUniverse.

Provides linkage disequilibrium data from the Ensembl REST API using
1000 Genomes Phase 3 population data. LD measures the non-random
association of alleles at different genetic loci and is essential
for GWAS interpretation, fine-mapping, and population genetics.

API: https://rest.ensembl.org/
Endpoints: /ld/:species/:id/:population_name
           /ld/:species/pairwise/:id1/:id2
No authentication required. Rate limit: 15 requests/second.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblLDTool")
class EnsemblLDTool(BaseTool):
    """
    Tool for querying linkage disequilibrium data from Ensembl REST API.

    Provides LD statistics (r2, D') between variants using 1000 Genomes
    Phase 3 population data across 26 populations.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "ld_variants"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl LD API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Ensembl LD API request timed out after {self.timeout} seconds"
            }
        except requests.exceptions.ConnectionError:
            return {
                "error": "Failed to connect to Ensembl REST API. Check network connectivity."
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            return {"error": f"Ensembl REST API HTTP error: {status}"}
        except Exception as e:
            return {"error": f"Unexpected error querying Ensembl LD: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "ld_variants":
            return self._ld_variants(arguments)
        elif self.endpoint_type == "ld_pairwise":
            return self._ld_pairwise(arguments)
        else:
            return {"error": f"Unknown endpoint_type: {self.endpoint_type}"}

    def _ld_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all variants in LD with a query variant in a population."""
        variant_id = arguments.get("variant_id", "")
        population = arguments.get("population", "")
        r2_threshold = arguments.get("r2_threshold", None)
        d_prime_threshold = arguments.get("d_prime_threshold", None)

        if not variant_id:
            return {"error": "variant_id parameter is required (e.g., 'rs1042779')"}
        if not population:
            return {
                "error": "population parameter is required (e.g., '1000GENOMES:phase_3:CEU')"
            }

        url = f"{ENSEMBL_BASE_URL}/ld/human/{variant_id}/{population}"
        params = {"content-type": "application/json"}
        if r2_threshold is not None:
            params["r2"] = r2_threshold
        if d_prime_threshold is not None:
            params["d_prime"] = d_prime_threshold

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        # Parse LD entries
        ld_variants = []
        for entry in raw:
            try:
                r2_val = float(entry.get("r2", 0))
                dp_val = float(entry.get("d_prime", 0))
            except (ValueError, TypeError):
                r2_val = 0.0
                dp_val = 0.0

            ld_variants.append(
                {
                    "variant1": entry.get("variation1", ""),
                    "variant2": entry.get("variation2", ""),
                    "r2": r2_val,
                    "d_prime": dp_val,
                    "population_name": entry.get("population_name", population),
                }
            )

        # Sort by r2 descending
        ld_variants.sort(key=lambda x: x["r2"], reverse=True)

        # Limit to top 200
        ld_variants = ld_variants[:200]

        result = {
            "query_variant": variant_id,
            "population": population,
            "ld_count": len(ld_variants),
            "ld_variants": ld_variants,
        }

        return {
            "data": result,
            "metadata": {
                "source": "Ensembl REST API",
                "query": f"{variant_id} in {population}",
                "endpoint": "ld",
            },
        }

    def _ld_pairwise(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get pairwise LD statistics between two variants across populations."""
        variant1 = arguments.get("variant1", "")
        variant2 = arguments.get("variant2", "")

        if not variant1:
            return {"error": "variant1 parameter is required (e.g., 'rs6792369')"}
        if not variant2:
            return {"error": "variant2 parameter is required (e.g., 'rs1042779')"}

        url = f"{ENSEMBL_BASE_URL}/ld/human/pairwise/{variant1}/{variant2}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        # Parse LD by population
        ld_by_pop = []
        for entry in raw:
            try:
                r2_val = float(entry.get("r2", 0))
                dp_val = float(entry.get("d_prime", 0))
            except (ValueError, TypeError):
                r2_val = 0.0
                dp_val = 0.0

            ld_by_pop.append(
                {
                    "population_name": entry.get("population_name", ""),
                    "r2": r2_val,
                    "d_prime": dp_val,
                }
            )

        # Sort by population name
        ld_by_pop.sort(key=lambda x: x["population_name"])

        result = {
            "variant1": variant1,
            "variant2": variant2,
            "population_count": len(ld_by_pop),
            "ld_by_population": ld_by_pop,
        }

        return {
            "data": result,
            "metadata": {
                "source": "Ensembl REST API",
                "query": f"{variant1} vs {variant2}",
                "endpoint": "ld/pairwise",
            },
        }
