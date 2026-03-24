# bgee_tool.py
"""
Bgee (dataBase for Gene Expression Evolution) API tool for ToolUniverse.

Bgee provides curated gene expression data across multiple animal species,
enabling comparisons of expression patterns across tissues, organs, and
developmental stages. Covers 29+ species with RNA-Seq, Affymetrix, EST,
and in situ hybridization data.

API: https://www.bgee.org/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BGEE_BASE_URL = "https://www.bgee.org/api"


@register_tool("BgeeTool")
class BgeeTool(BaseTool):
    """
    Tool for querying the Bgee gene expression database.

    Bgee integrates expression data from multiple data types (RNA-Seq,
    Affymetrix, EST, in situ hybridization) and provides curated
    present/absent expression calls across tissues and developmental stages.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "gene_search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Bgee API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Bgee API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Bgee API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Bgee API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Bgee: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Bgee endpoint."""
        if self.endpoint == "gene_search":
            return self._gene_search(arguments)
        elif self.endpoint == "gene_expression":
            return self._gene_expression(arguments)
        elif self.endpoint == "species_list":
            return self._species_list(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _gene_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes by name or symbol across species."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        params = {
            "page": "gene",
            "action": "search",
            "query": query,
            "display_type": "json",
        }

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        result_data = data.get("data", {})
        gene_matches = result_data.get("result", {}).get("geneMatches", [])

        results = []
        for match in gene_matches[:20]:  # Limit to 20 results
            gene = match.get("gene", {})
            species = gene.get("species", {})
            results.append(
                {
                    "gene_id": gene.get("geneId"),
                    "name": gene.get("name"),
                    "description": gene.get("description"),
                    "species_id": species.get("id"),
                    "species_name": f"{species.get('genus', '')} {species.get('speciesName', '')}".strip(),
                    "common_name": species.get("name"),
                    "gene_biotype": gene.get("geneBioType", {}).get("name"),
                    "match_source": match.get("matchSource"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "query": query,
                "total_matches": result_data.get("result", {}).get(
                    "totalMatchCount", 0
                ),
                "returned": len(results),
            },
        }

    def _gene_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expression data for a gene across tissues/organs."""
        gene_id = arguments.get("gene_id", "")
        species_id = arguments.get("species_id", "")
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (Ensembl gene ID, e.g., ENSG00000141510)",
            }
        if not species_id:
            return {
                "status": "error",
                "error": "species_id parameter is required (NCBI taxon ID, e.g., 9606 for human)",
            }

        params = {
            "page": "gene",
            "action": "expression",
            "gene_id": gene_id,
            "species_id": species_id,
            "display_type": "json",
        }

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        expr_data = data.get("data", {})
        calls = expr_data.get("calls", [])

        results = []
        for call in calls[:50]:  # Limit to 50 expression calls
            condition = call.get("condition", {})
            anat_entity = condition.get("anatEntity", {})
            cell_type = condition.get("cellType", {})
            score_info = call.get("expressionScore", {})

            entry = {
                "tissue_id": anat_entity.get("id"),
                "tissue_name": anat_entity.get("name"),
                "expression_score": score_info.get("expressionScore"),
                "score_confidence": score_info.get("expressionScoreConfidence"),
                "expression_state": call.get("expressionState"),
                "quality": call.get("expressionQuality"),
                "data_types": call.get("dataTypesWithData", []),
            }
            if cell_type.get("id"):
                entry["cell_type_id"] = cell_type.get("id")
                entry["cell_type_name"] = cell_type.get("name")

            results.append(entry)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "gene_id": gene_id,
                "species_id": str(species_id),
                "total_calls": len(calls),
                "returned": len(results),
                "data_types": expr_data.get("requestedDataTypes", []),
            },
        }

    def _species_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all species available in Bgee."""
        params = {
            "page": "species",
            "display_type": "json",
        }

        response = requests.get(BGEE_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 200:
            return {
                "status": "error",
                "error": f"Bgee API error: {data.get('message', 'Unknown error')}",
            }

        species_data = data.get("data", {}).get("species", [])

        results = []
        for sp in species_data:
            results.append(
                {
                    "species_id": sp.get("id"),
                    "genus": sp.get("genus"),
                    "species_name": sp.get("speciesName"),
                    "common_name": sp.get("name"),
                    "genome_version": sp.get("genomeVersion"),
                    "full_name": f"{sp.get('genus', '')} {sp.get('speciesName', '')}".strip(),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Bgee",
                "total_species": len(results),
            },
        }
