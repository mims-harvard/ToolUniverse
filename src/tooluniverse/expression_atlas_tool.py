# expression_atlas_tool.py
"""
EBI Expression Atlas API tool for ToolUniverse.

Expression Atlas provides gene expression data across species and biological conditions,
including baseline (normal tissue/cell type) and differential (disease vs. normal) expression.

Data includes:
- Baseline tissue/cell-type expression from RNA-seq and proteomics
- Differential expression between conditions (disease, treatment, etc.)
- Experiment metadata and design

API Base URL: https://www.ebi.ac.uk/gxa/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs
GXA_BASE = "https://www.ebi.ac.uk/gxa"
EBI_SEARCH_BASE = "https://www.ebi.ac.uk/ebisearch/ws/rest"


@register_tool("ExpressionAtlasTool")
class ExpressionAtlasTool(BaseTool):
    """
    Tool for querying EBI Expression Atlas gene expression data.

    Provides access to:
    - Baseline gene expression across tissues and cell types
    - Differential expression in disease and treatment contexts
    - Experiment search and metadata
    - Both bulk RNA-seq and single-cell data

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_baseline_expression"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Expression Atlas API call."""
        operation = self.operation

        if operation == "get_baseline_expression":
            return self._get_baseline_expression(arguments)
        elif operation == "search_differential_experiments":
            return self._search_differential_experiments(arguments)
        elif operation == "search_experiments":
            return self._search_experiments(arguments)
        elif operation == "get_experiment":
            return self._get_experiment(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _gene_experiment_ids(self, gene: str) -> set:
        """Look up experiment accessions whose EBI Search description-index
        entry happens to mention `gene`. Confirmed live: baseline-type
        experiment descriptions (e.g. "The Genotype-Tissue Expression
        (GTEx) project v8") almost never contain individual gene symbols
        (0/4561 hits for HK1, 1/4561 for TP53), so this is a best-effort
        text-coincidence tag, not real per-gene filtering -- callers must
        not treat a non-empty result set as "this gene's expression data."
        """
        gene_experiment_ids: set = set()
        search_resp = requests.get(
            f"{EBI_SEARCH_BASE}/atlas-experiments",
            params={"query": gene, "size": 100, "format": "json"},
            timeout=self.timeout,
        )
        if search_resp.status_code == 200:
            for entry in search_resp.json().get("entries", []):
                gene_experiment_ids.add(entry.get("id"))
        return gene_experiment_ids

    @staticmethod
    def _gene_filter_warning(gene: str) -> str:
        return (
            f"'gene_mentioned' only reflects a text-search coincidence "
            f"against experiment descriptions, not real per-gene "
            f"expression values -- this API has no working way to filter "
            f"experiments by whether they actually studied '{gene}'. The "
            f"experiment list below is effectively the full, unfiltered "
            f"catalog for the given species/condition constraints, not a "
            f"gene-specific result set."
        )

    def _get_baseline_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get baseline expression experiments for a gene.

        Uses EBI Search to find experiments mentioning the gene,
        then filters the Expression Atlas experiment catalog for
        baseline experiments in the specified species.
        """
        gene = arguments.get("gene", "")
        species = arguments.get("species", "homo sapiens")

        if not gene:
            return {
                "status": "error",
                "error": "gene parameter is required",
            }

        try:
            # Step 1: Get all experiments from Expression Atlas
            all_url = f"{GXA_BASE}/json/experiments"
            all_resp = requests.get(all_url, timeout=self.timeout)
            all_resp.raise_for_status()
            all_data = all_resp.json()
            all_experiments = all_data.get("experiments", [])

            # Filter for baseline experiments in the species
            species_lower = species.lower()
            baseline_exps = [
                e
                for e in all_experiments
                if "BASELINE" in e.get("rawExperimentType", "")
                and e.get("species", "").lower() == species_lower
            ]

            # Step 2: Search EBI Search for gene-specific experiments
            gene_experiment_ids = self._gene_experiment_ids(gene)

            # Combine: tag baseline experiments that mention the gene
            results = []
            for exp in baseline_exps:
                acc = exp.get("experimentAccession", "")
                results.append(
                    {
                        "experiment_accession": acc,
                        "experiment_type": exp.get("rawExperimentType"),
                        "experiment_description": exp.get("experimentDescription"),
                        "species": exp.get("species"),
                        "num_assays": exp.get("numberOfAssays"),
                        "gene_mentioned": acc in gene_experiment_ids,
                        "last_update": exp.get("lastUpdate"),
                    }
                )

            # Sort: gene-mentioned first, then by assay count
            results.sort(
                key=lambda x: (
                    not x.get("gene_mentioned", False),
                    -(x.get("num_assays") or 0),
                )
            )

            return {
                "status": "success",
                "data": {
                    "gene": gene,
                    "species": species,
                    "baseline_experiments": results[:50],
                    "total_baseline": len(baseline_exps),
                    "gene_specific_count": len(
                        [r for r in results if r["gene_mentioned"]]
                    ),
                    "warning": self._gene_filter_warning(gene),
                },
                "source": ("EBI Expression Atlas - Baseline Expression"),
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (f"Expression Atlas API timeout after {self.timeout}s"),
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": (f"Expression Atlas API HTTP error: {sc}"),
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": (f"Expression Atlas API request failed: {str(e)}"),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _search_differential_experiments(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Search for differential expression experiments by gene
        and/or condition.
        """
        gene = arguments.get("gene", "")
        condition = arguments.get("condition", "")
        species = arguments.get("species", "homo sapiens")

        if not gene and not condition:
            return {
                "status": "error",
                "error": ("Either gene or condition parameter is required"),
            }

        try:
            # Get all experiments
            url = f"{GXA_BASE}/json/experiments"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            all_experiments = data.get("experiments", [])
            species_lower = species.lower()

            # Filter for differential experiments
            diff_exps = [
                e
                for e in all_experiments
                if "DIFFERENTIAL" in e.get("rawExperimentType", "")
                and (not species or e.get("species", "").lower() == species_lower)
            ]

            # If condition specified, filter by description
            if condition:
                cond_lower = condition.lower()
                diff_exps = [
                    e
                    for e in diff_exps
                    if cond_lower in e.get("experimentDescription", "").lower()
                ]

            # If gene specified, cross-reference with
            # EBI Search gene-experiment matches
            gene_exp_ids = self._gene_experiment_ids(gene) if gene else set()

            experiments = []
            for exp in diff_exps:
                acc = exp.get("experimentAccession", "")
                experiments.append(
                    {
                        "experiment_accession": acc,
                        "experiment_type": exp.get("rawExperimentType"),
                        "experiment_description": exp.get("experimentDescription"),
                        "species": exp.get("species"),
                        "num_assays": exp.get("numberOfAssays"),
                        "gene_mentioned": (acc in gene_exp_ids if gene else None),
                        "factors": exp.get("experimentalFactors", []),
                    }
                )

            # Sort: gene-mentioned first
            if gene:
                experiments.sort(
                    key=lambda x: (
                        not x.get("gene_mentioned", False),
                        -(x.get("num_assays") or 0),
                    )
                )

            result_data = {
                "gene": gene,
                "condition": condition,
                "species": species,
                "experiments": experiments[:50],
                "experiment_count": len(experiments),
            }
            if gene:
                result_data["warning"] = self._gene_filter_warning(gene)

            return {
                "status": "success",
                "data": result_data,
                "source": ("EBI Expression Atlas - Differential Expression"),
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (f"Expression Atlas API timeout after {self.timeout}s"),
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": (f"Expression Atlas API HTTP error: {sc}"),
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": (f"Expression Atlas API request failed: {str(e)}"),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _search_experiments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Expression Atlas experiments by gene and/or condition.

        Uses EBI Search for gene-specific queries and filters
        the full experiment catalog by species and condition text.
        """
        gene = arguments.get("gene", "")
        condition = arguments.get("condition", "")
        species = arguments.get("species", "")

        if not gene and not condition:
            return {
                "status": "error",
                "error": ("Either gene or condition parameter is required"),
            }

        try:
            # Get gene-specific experiment IDs from EBI Search
            gene_exp_ids = self._gene_experiment_ids(gene) if gene else set()

            # Get full experiment catalog
            url = f"{GXA_BASE}/json/experiments"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            all_experiments = data.get("experiments", [])

            # Apply filters
            filtered = all_experiments
            if species:
                sp_lower = species.lower()
                filtered = [
                    e for e in filtered if e.get("species", "").lower() == sp_lower
                ]
            if condition:
                cond_lower = condition.lower()
                filtered = [
                    e
                    for e in filtered
                    if cond_lower in e.get("experimentDescription", "").lower()
                ]

            # Build results
            experiments = []
            for exp in filtered:
                acc = exp.get("experimentAccession", "")
                experiments.append(
                    {
                        "experiment_accession": acc,
                        "experiment_type": exp.get("rawExperimentType"),
                        "experiment_description": exp.get("experimentDescription"),
                        "species": exp.get("species"),
                        "num_assays": exp.get("numberOfAssays"),
                        "gene_mentioned": (acc in gene_exp_ids if gene else None),
                    }
                )

            # Sort: gene-mentioned first
            if gene:
                experiments.sort(
                    key=lambda x: (
                        not x.get("gene_mentioned", False),
                        -(x.get("num_assays") or 0),
                    )
                )

            result_data = {
                "gene": gene,
                "condition": condition,
                "species": species,
                "experiments": experiments[:50],
                "total_count": len(experiments),
                "gene_specific_count": len(gene_exp_ids),
            }
            if gene:
                result_data["warning"] = self._gene_filter_warning(gene)

            return {
                "status": "success",
                "data": result_data,
                "source": "EBI Expression Atlas",
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (f"Expression Atlas API timeout after {self.timeout}s"),
            }
        except requests.exceptions.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": (f"Expression Atlas API HTTP error: {sc}"),
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": (f"Expression Atlas API request failed: {str(e)}"),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _get_experiment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific Expression Atlas experiment.

        Returns experiment design, assays, and analysis information.
        """
        accession = arguments.get("accession", "")

        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        try:
            url = f"{GXA_BASE}/json/experiments/{accession}"

            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            experiment = data.get("experiment", data)

            return {
                "status": "success",
                "data": {
                    "accession": experiment.get("accession", accession),
                    "type": experiment.get("type"),
                    "description": experiment.get("description"),
                    "species": experiment.get("species"),
                    "factors": experiment.get("experimentalFactors", []),
                    "technology": experiment.get("technologyType", []),
                    "contrasts": experiment.get("contrasts", []),
                    "assay_count": experiment.get("numberOfAssays"),
                    "last_update": experiment.get("lastUpdate"),
                    "pubmed_ids": experiment.get("pubmedIds", []),
                },
                "source": "EBI Expression Atlas",
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Expression Atlas API timeout after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            status_code = (
                e.response.status_code if e.response is not None else "unknown"
            )
            if status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Experiment not found: {accession}",
                }
            return {
                "status": "error",
                "error": f"Expression Atlas API HTTP error: {status_code}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Expression Atlas API request failed: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
