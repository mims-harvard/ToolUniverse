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

    @staticmethod
    def _page(records, arguments):
        """Slice a result list to the caller's window and describe the slice.

        Fix-R4A-10: these lists were cut to a hard-coded [:50] with no limit or
        offset parameter declared, so the tail was unreachable -- confirmed
        live that condition="cancer" reports total_count 241 and returns 50.
        The lists are ranked (by assay count, or gene-mention then assay
        count), so the truncated tail is the weakest end, but 191 of 241
        experiments simply could not be retrieved.
        """
        raw_limit = arguments.get("limit")
        limit = 50 if raw_limit in (None, "") else int(raw_limit)
        limit = max(1, min(limit, 500))
        offset = max(0, int(arguments.get("offset") or 0))

        page = records[offset : offset + limit]
        note = None
        if page and offset + len(page) < len(records):
            note = (
                f"Showing {offset + 1}-{offset + len(page)} of {len(records)}. "
                f"Re-run with offset={offset + len(page)} for the next page, or "
                "raise 'limit' (max 500)."
            )
        return page, offset, note

    def _get_baseline_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        List baseline expression experiments for a species.

        Fetches the Expression Atlas experiment catalog and returns its
        baseline experiments for the requested species. The list is not
        filtered by gene -- the underlying API has no reliable way to do so
        (see the inline note below), so ``gene`` only labels the request and
        drives the follow-up suggestion.
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

            # NOTE: this used to also tag each experiment with a
            # "gene_mentioned" flag by full-text-searching EBI Search's
            # experiment *description* field for the gene symbol. Confirmed
            # live that this never works as intended: descriptions are
            # one-line study summaries that essentially never contain a bare
            # gene symbol, so gene_mentioned was false for every real gene
            # (and could false-positive on short symbols that happen to
            # substring-match unrelated words). The GXA API itself also
            # silently ignores a geneQuery filter on /json/experiments
            # (confirmed live: identical result count with and without it),
            # so there's no cheap way to filter this list by gene. Listing
            # species-level baseline experiments honestly, without a broken
            # per-gene relevance signal. Do NOT recommend
            # GxA_get_experiment_expression + gene_id as a way to check
            # whether a specific experiment has data for a gene: confirmed
            # live (Fix round 32) that its gene filter is silently ignored
            # too -- e.g. E-MTAB-2836 reports searchResultTotal="9570" but
            # every geneQuery variant tried (plain symbol, JSON-wrapped
            # symbol, Ensembl ID, with/without specific=true) returns the
            # same 29-row default sample, so an empty/no-match result from
            # it is not evidence the gene is absent. For actual per-gene
            # expression, point callers at tools confirmed to work, e.g.
            # GTEx_get_expression_summary.
            results = [
                {
                    "experiment_accession": exp.get("experimentAccession", ""),
                    "experiment_type": exp.get("rawExperimentType"),
                    "experiment_description": exp.get("experimentDescription"),
                    "species": exp.get("species"),
                    "num_assays": exp.get("numberOfAssays"),
                    "last_update": exp.get("lastUpdate"),
                }
                for exp in baseline_exps
            ]
            results.sort(key=lambda x: -(x.get("num_assays") or 0))
            _page, _offset, _note = self._page(results, arguments)

            return {
                "status": "success",
                "data": {
                    "gene": gene,
                    "species": species,
                    "baseline_experiments": _page,
                    "total_baseline": len(baseline_exps),
                    "returned_baseline": len(_page),
                    "offset": _offset,
                    **({"page_note": _note} if _note else {}),
                },
                "note": (
                    f"This lists baseline experiments for '{species}'; it does "
                    "not filter by gene (the underlying API has no reliable way "
                    f"to do so). This list does not tell you whether '{gene}' "
                    "was measured in any of these experiments. Do not use "
                    "GxA_get_experiment_expression with gene_id to check for a "
                    "gene's presence in an experiment -- its gene filter is "
                    "silently ignored by the upstream API, so it returns only "
                    "a small default sample of an experiment's genes and an "
                    "empty/no-match result is not evidence the gene is absent. "
                    "For actual per-gene expression data, use a tool confirmed "
                    "to filter correctly, such as GTEx_get_expression_summary "
                    f"(gene_symbol='{gene}') for human tissue expression, or "
                    "HPA_get_rna_expression_in_specific_tissues."
                ),
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

            _page, _offset, _note = self._page(experiments, arguments)
            result_data = {
                "gene": gene,
                "condition": condition,
                "species": species,
                "experiments": _page,
                "experiment_count": len(experiments),
                "returned_experiments": len(_page),
                "offset": _offset,
                **({"page_note": _note} if _note else {}),
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

            _page, _offset, _note = self._page(experiments, arguments)
            result_data = {
                "gene": gene,
                "condition": condition,
                "species": species,
                "experiments": _page,
                "total_count": len(experiments),
                "returned_experiments": len(_page),
                "offset": _offset,
                "gene_specific_count": len(gene_exp_ids),
                **({"page_note": _note} if _note else {}),
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
