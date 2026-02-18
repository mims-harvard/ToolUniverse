# ensembl_phenotype_tool.py
"""
Ensembl REST API Phenotype association tool for ToolUniverse.

Provides access to phenotype/disease associations for:
- Genes (phenotype/gene endpoint)
- Genomic regions (phenotype/region endpoint)
- Variants (variation endpoint with phenotypes=1)

Returns disease/trait associations from multiple sources including
Cancer Gene Census, OMIM, ClinVar, NHGRI-EBI GWAS catalog, and Orphanet.

API: https://rest.ensembl.org/
No authentication required. Rate limit: 15 requests/second.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


@register_tool("EnsemblPhenotypeTool")
class EnsemblPhenotypeTool(BaseTool):
    """
    Tool for querying phenotype/disease associations from Ensembl REST API.

    Provides gene-phenotype, region-phenotype, and variant-phenotype lookups.
    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.endpoint_type = tool_config.get("fields", {}).get("endpoint_type", "gene")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Phenotype API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Ensembl REST API request timed out after {self.timeout}s. "
                "Try a smaller region or a less-studied gene."
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            if status == 400:
                return {
                    "error": "Bad request: check gene name, region format, or variant ID"
                }
            if status == 404:
                return {
                    "error": "Not found: the gene, region, or variant was not found in Ensembl"
                }
            return {"error": f"Ensembl REST API HTTP error: {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint_type == "gene":
            return self._phenotype_gene(arguments)
        elif self.endpoint_type == "region":
            return self._phenotype_region(arguments)
        elif self.endpoint_type == "variant":
            return self._phenotype_variant(arguments)
        return {"error": f"Unknown endpoint_type: {self.endpoint_type}"}

    def _phenotype_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype associations for a gene."""
        species = arguments.get("species", "homo_sapiens")
        gene = arguments.get("gene", "")

        if not gene:
            return {"error": "gene parameter is required (e.g., 'BRCA1')"}

        url = f"{ENSEMBL_BASE_URL}/phenotype/gene/{species}/{gene}"
        params = {"content-type": "application/json"}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        phenotypes = []
        for entry in raw:
            attrs = entry.get("attributes", {})
            phenotypes.append(
                {
                    "description": entry.get("description", ""),
                    "source": entry.get("source", ""),
                    "location": entry.get("location"),
                    "gene_ensembl_id": entry.get("Gene"),
                    "ontology_accessions": entry.get("ontology_accessions", []),
                    "external_references": attrs.get("external_reference"),
                }
            )

        # Deduplicate by description+source
        seen = set()
        unique_phenos = []
        for p in phenotypes:
            key = (p["description"], p["source"])
            if key not in seen:
                seen.add(key)
                unique_phenos.append(p)

        return {
            "data": {
                "gene": gene,
                "species": species,
                "phenotype_count": len(unique_phenos),
                "phenotypes": unique_phenos[:200],
            },
            "metadata": {
                "source": "Ensembl REST API",
                "endpoint": f"phenotype/gene/{species}/{gene}",
            },
        }

    def _phenotype_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype associations for a genomic region."""
        species = arguments.get("species", "homo_sapiens")
        region = arguments.get("region", "")
        feature_type = arguments.get("feature_type")

        if not region:
            return {"error": "region is required (e.g., '17:7661779-7687538')"}

        url = f"{ENSEMBL_BASE_URL}/phenotype/region/{species}/{region}"
        params = {"content-type": "application/json"}
        if feature_type:
            params["feature_type"] = feature_type

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        if not isinstance(raw, list):
            raw = []

        # The region endpoint returns entries with nested phenotype_associations
        phenotypes = []
        seen = set()
        for entry in raw:
            variant_id = entry.get("id", "")
            # Each entry has a list of phenotype_associations
            for assoc in entry.get("phenotype_associations", []):
                desc = assoc.get("description", "")
                source = assoc.get("source", "")
                key = (desc, source, variant_id)
                if key not in seen and desc:
                    seen.add(key)
                    phenotypes.append(
                        {
                            "description": desc,
                            "source": source,
                            "id": variant_id,
                            "location": assoc.get("location"),
                            "ontology_accessions": assoc.get("ontology_accessions", []),
                        }
                    )

        return {
            "data": {
                "region": region,
                "species": species,
                "phenotype_count": len(phenotypes),
                "phenotypes": phenotypes[:200],
            },
            "metadata": {
                "source": "Ensembl REST API",
                "endpoint": f"phenotype/region/{species}/{region}",
            },
        }

    def _phenotype_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype associations for a variant via the variation endpoint."""
        species = arguments.get("species", "homo_sapiens")
        variant_id = arguments.get("variant_id", "")

        if not variant_id:
            return {"error": "variant_id is required (e.g., 'rs429358')"}

        # Use the variation endpoint with phenotypes=1
        url = f"{ENSEMBL_BASE_URL}/variation/{species}/{variant_id}"
        params = {"content-type": "application/json", "phenotypes": 1}

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        pheno_list = raw.get("phenotypes", [])
        if not isinstance(pheno_list, list):
            pheno_list = []

        phenotypes = []
        for entry in pheno_list:
            phenotypes.append(
                {
                    "trait": entry.get("trait", ""),
                    "source": entry.get("source", ""),
                    "risk_allele": entry.get("risk_allele"),
                    "pvalue": entry.get("pvalue"),
                    "beta_coefficient": entry.get("beta_coefficient"),
                    "study": entry.get("study"),
                    "genes": entry.get("genes"),
                    "ontology_accessions": entry.get("ontology_accessions", []),
                }
            )

        # Limit to top 200 (can be very large for well-studied variants)
        return {
            "data": {
                "variant_id": variant_id,
                "species": species,
                "phenotype_count": len(phenotypes),
                "phenotypes": phenotypes[:200],
            },
            "metadata": {
                "source": "Ensembl REST API",
                "endpoint": f"variation/{species}/{variant_id}?phenotypes=1",
            },
        }
