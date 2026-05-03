# scxa_tool.py
"""
Single Cell Expression Atlas (SCXA) REST API tool for ToolUniverse.

EBI's Single Cell Expression Atlas provides curated single-cell RNA-seq
experiments with cell type annotations, marker genes, and expression data
across 380+ experiments from multiple species.

API: https://www.ebi.ac.uk/gxa/sc/json/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

SCXA_BASE_URL = "https://www.ebi.ac.uk/gxa/sc/json"


@register_tool("SCExpressionAtlasTool")
class SCExpressionAtlasTool(BaseTool):
    """
    Tool for querying EBI Single Cell Expression Atlas.

    Supports listing single-cell RNA-seq experiments with metadata
    (species, cell counts, technology, factors) and searching for
    experiments where a gene is expressed at single-cell resolution.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "list_experiments"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SCXA API call."""
        try:
            if self.operation == "list_experiments":
                return self._list_experiments(arguments)
            elif self.operation == "search_gene":
                return self._search_gene(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SCXA API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SCXA API. Check network.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying SCXA: {str(e)}",
            }

    def _list_experiments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all single-cell RNA-seq experiments with optional filtering."""
        url = f"{SCXA_BASE_URL}/experiments"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        experiments = raw.get("experiments", [])

        species_filter = arguments.get("species")
        if species_filter:
            species_lower = species_filter.lower()
            experiments = [
                e for e in experiments if species_lower in e.get("species", "").lower()
            ]

        keyword = arguments.get("keyword")
        if keyword:
            kw_lower = keyword.lower()
            experiments = [
                e
                for e in experiments
                if kw_lower in e.get("experimentDescription", "").lower()
                or kw_lower in " ".join(e.get("experimentalFactors", [])).lower()
            ]

        total = len(experiments)
        limit = min(arguments.get("limit", 20), 100)
        experiments = experiments[:limit]

        results = []
        for exp in experiments:
            results.append(
                {
                    "accession": exp.get("experimentAccession"),
                    "description": exp.get("experimentDescription"),
                    "species": exp.get("species"),
                    "technology": exp.get("technologyType"),
                    "num_cells": exp.get("numberOfAssays"),
                    "experimental_factors": exp.get("experimentalFactors"),
                    "experiment_type": exp.get("rawExperimentType"),
                    "last_updated": exp.get("lastUpdate"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_matching": total,
                "returned": len(results),
                "source": "EBI Single Cell Expression Atlas",
            },
        }

    def _search_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for SC experiments where a gene is expressed."""
        gene = arguments.get("gene", "")
        if not gene:
            return {
                "status": "error",
                "error": "gene parameter is required (symbol like TP53 or Ensembl ID like ENSG00000141510)",
            }

        params = {}
        if gene.startswith("ENSG") or gene.startswith("ENSMUS"):
            params["ensgene"] = gene
        else:
            params["symbol"] = gene

        species = arguments.get("species")
        if species:
            params["species"] = species

        url = f"{SCXA_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        matching_gene_id = raw.get("matchingGeneId", "")

        results = []
        for r in raw.get("results", []):
            elem = r.get("element", {})
            results.append(
                {
                    "accession": elem.get("experimentAccession"),
                    "description": elem.get("experimentDescription"),
                    "species": elem.get("species"),
                    "num_cells": elem.get("numberOfAssays"),
                    "technology": elem.get("technologyType"),
                    "experimental_factors": elem.get("experimentalFactors"),
                    "pubmed_ids": elem.get("pubMedIds"),
                    "dois": elem.get("dois"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "gene_query": gene,
                "matching_gene_id": matching_gene_id,
                "total_experiments": len(results),
                "source": "EBI Single Cell Expression Atlas",
            },
        }
