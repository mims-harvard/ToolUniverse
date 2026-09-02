# gxa_tool.py
"""
EBI Gene Expression Atlas (GxA) API tool for ToolUniverse.

Provides access to the Expression Atlas API, which hosts baseline and
differential gene expression data across species, tissues, and experimental
conditions. Contains 4,500+ experiments covering hundreds of species.

API: https://www.ebi.ac.uk/gxa/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


GXA_BASE_URL = "https://www.ebi.ac.uk/gxa/json"


class GxATool(BaseTool):
    """
    Tool for EBI Gene Expression Atlas API providing access to baseline
    and differential gene expression experiments across tissues and conditions.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "list_experiments")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GxA API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Expression Atlas API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Expression Atlas API",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"Experiment not found: {arguments.get('experiment_accession', '')}",
                }
            return {
                "status": "error",
                "error": f"Expression Atlas API HTTP error: {code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Expression Atlas: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "list_experiments":
            return self._list_experiments(arguments)
        elif self.endpoint == "get_experiment_expression":
            return self._get_experiment_expression(arguments)
        elif self.endpoint == "get_experiment_info":
            return self._get_experiment_info(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _list_experiments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List/search gene expression experiments."""
        species = arguments.get("species", "")
        experiment_type = arguments.get("experiment_type", "")
        limit = min(arguments.get("limit", 20), 100)

        url = f"{GXA_BASE_URL}/experiments"
        params = {}
        if species:
            params["species"] = species

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        experiments = data.get("experiments", [])

        # Filter by species (API param may not work, so filter client-side)
        if species:
            species_lower = species.lower()
            experiments = [
                e
                for e in experiments
                if species_lower in str(e.get("species", "")).lower()
            ]

        # Filter by type if specified
        if experiment_type:
            et_lower = experiment_type.lower()
            experiments = [
                e
                for e in experiments
                if et_lower in e.get("rawExperimentType", "").lower()
            ]

        # Limit results
        total = len(experiments)
        experiments = experiments[:limit]

        results = []
        for exp in experiments:
            results.append(
                {
                    "accession": exp.get("experimentAccession"),
                    "description": exp.get("experimentDescription"),
                    "species": exp.get("species"),
                    "experiment_type": exp.get("rawExperimentType"),
                    "technology_type": exp.get("technologyType"),
                    "number_of_assays": exp.get("numberOfAssays"),
                    "experimental_factors": exp.get("experimentalFactors"),
                    "load_date": exp.get("loadDate"),
                    "last_update": exp.get("lastUpdate"),
                }
            )

        return {
            "status": "success",
            "data": {
                "total_experiments": total,
                "returned": len(results),
                "experiments": results,
            },
            "metadata": {
                "source": "EBI Gene Expression Atlas",
                "species_filter": species or "all",
                "type_filter": experiment_type or "all",
            },
        }

    def _get_experiment_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene expression data for a specific experiment."""
        accession = arguments.get("experiment_accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "experiment_accession is required (e.g., 'E-MTAB-2836')",
            }

        gene_id = arguments.get("gene_id", "")

        url = f"{GXA_BASE_URL}/experiments/{accession}"
        # Feature-69A-003: the GxA /experiments/{accession} endpoint does NOT support
        # geneId filtering — the parameter is silently ignored. Apply client-side filter.
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Extract experiment metadata
        exp_info = data.get("experiment", {})

        # Extract column headers (tissues/conditions)
        column_headers = data.get("columnHeaders", [])
        columns = []
        for col in column_headers:
            columns.append(
                {
                    "assay_group_id": col.get("assayGroupId"),
                    "factor_value": col.get("factorValue"),
                    "ontology_term_id": col.get("factorValueOntologyTermId"),
                    "replicates": col.get("assayGroupSummary", {}).get("replicates"),
                }
            )

        # Build tissue name lookup by position
        tissue_names = [
            col.get("factorValue", f"condition_{i}")
            for i, col in enumerate(column_headers)
        ]

        # Extract gene expression profiles (apply gene_id filter client-side)
        profiles = data.get("profiles", {})
        raw_rows = profiles.get("rows", [])

        # Feature-69A-004: the upstream endpoint only ever returns a small,
        # arbitrary default sample of the experiment's genes (confirmed live:
        # E-MTAB-2836 has searchResultTotal=9570 but only ~29 rows are ever
        # returned, regardless of any geneQuery/geneId parameter we send).
        # Disclose that sample size vs. the true total so `total_gene_profiles`
        # (which reflects only what we searched) is never mistaken for the
        # experiment's actual gene count.
        profiles_returned_by_upstream = len(raw_rows)
        try:
            # Upstream sometimes serializes this as a numeric string.
            profiles_available_upstream = int(
                profiles.get("searchResultTotal", profiles_returned_by_upstream)
            )
        except (TypeError, ValueError):
            profiles_available_upstream = profiles_returned_by_upstream

        # Apply client-side gene_id filter (API ignores geneId parameter)
        rows = raw_rows
        coverage_warning = None
        if gene_id:
            gene_id_upper = gene_id.upper()
            rows = [r for r in raw_rows if self._gene_id_matches(r, gene_id_upper)]
            if not rows:
                coverage_warning = (
                    "The upstream Expression Atlas endpoint returned only a default "
                    f"sample of {profiles_returned_by_upstream} of "
                    f"{profiles_available_upstream} genes in this experiment, and it "
                    "ignores every gene-filter parameter we can send it (verified "
                    f"directly against the API). The requested gene '{gene_id}' was "
                    "not present in that sample. An empty result here is NOT evidence "
                    "that the gene is unexpressed or absent from the experiment -- it "
                    "only means the requested gene fell outside the small sample the "
                    "upstream API happened to return."
                )

        gene_profiles = []
        for row in rows[:50]:  # Limit to first 50 genes
            expressions = []
            row_exprs = row.get("expressions", [])
            for i, expr in enumerate(row_exprs):
                val = expr.get("value")
                if val is not None and val != "N/A":
                    tissue = (
                        tissue_names[i] if i < len(tissue_names) else f"condition_{i}"
                    )
                    expressions.append(
                        {
                            "tissue": tissue,
                            "value": val,
                        }
                    )
            if expressions:
                gene_profiles.append(
                    {
                        "gene_id": row.get("id"),
                        "gene_name": row.get("name"),
                        "expressions": expressions,
                    }
                )

        return {
            "status": "success",
            "data": {
                "experiment_accession": accession,
                "experiment_description": exp_info.get("description", ""),
                "columns": columns,
                "total_gene_profiles": len(rows),
                "gene_profiles": gene_profiles,
                "profiles_returned_by_upstream": profiles_returned_by_upstream,
                "profiles_available_upstream": profiles_available_upstream,
                "coverage_warning": coverage_warning,
            },
            "metadata": {
                "source": "EBI Gene Expression Atlas",
                "experiment": accession,
                "gene_filter": gene_id or "all",
            },
        }

    def _get_experiment_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get experiment metadata and factor information."""
        accession = arguments.get("experiment_accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "experiment_accession is required (e.g., 'E-MTAB-2836')",
            }

        url = f"{GXA_BASE_URL}/experiments/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        exp = data.get("experiment", {})
        config = data.get("config", {})

        # Get column groupings for understanding experimental design
        groupings = data.get("columnGroupings", [])

        # Get anatomogram info if available
        anatomogram = data.get("anatomogram", {})

        return {
            "status": "success",
            "data": {
                "accession": exp.get("accession", accession),
                "description": exp.get("description"),
                "species": anatomogram.get("species") if anatomogram else None,
                "total_genes": len(data.get("profiles", {}).get("rows", [])),
                "total_conditions": len(data.get("columnHeaders", [])),
                "column_groupings": groupings,
                "config": {
                    "disclaimer": config.get("disclaimer"),
                    "resources": config.get("resources"),
                },
            },
            "metadata": {
                "source": "EBI Gene Expression Atlas",
                "experiment": accession,
            },
        }

    @staticmethod
    def _gene_id_matches(row: dict, gene_id_upper: str) -> bool:
        """Check if a row matches the gene_id, handling versioned Ensembl IDs."""
        row_id = str(row.get("id", "")).upper()
        row_name = str(row.get("name", "")).upper()
        if row_id == gene_id_upper or row_name == gene_id_upper:
            return True
        # Handle versioned Ensembl IDs: ENSG00000142192.15 matches ENSG00000142192
        if gene_id_upper.startswith("ENS") and "." in row_id:
            return row_id.split(".")[0] == gene_id_upper
        if row_id.startswith("ENS") and "." not in gene_id_upper:
            return row_id.split(".")[0] == gene_id_upper
        return False
