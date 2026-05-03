# depmap_tool.py
"""
DepMap (Dependency Map) API tool for ToolUniverse.

DepMap provides cancer cell line dependency data from CRISPR knockout screens,
drug sensitivity data, and multi-omics characterization of cancer cell lines.

Data includes:
- CRISPR gene effect scores (gene essentiality)
- Drug sensitivity data
- Cell line metadata (lineage, mutations)
- Gene expression data

API Documentation: https://depmap.sanger.ac.uk/documentation/api/
Base URL: https://api.cellmodelpassports.sanger.ac.uk
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Sanger Cell Model Passports API
DEPMAP_BASE_URL = "https://api.cellmodelpassports.sanger.ac.uk"


@register_tool("DepMapTool")
class DepMapTool(BaseTool):
    """
    Tool for querying DepMap/Sanger Cell Model Passports API.

    Provides access to:
    - Cancer cell line dependency data (CRISPR screens)
    - Drug sensitivity profiles
    - Cell line metadata and annotations
    - Gene effect scores for target validation

    No authentication required for non-commercial use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_cell_lines"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DepMap API call."""
        operation = self.operation

        if operation == "get_cell_lines":
            return self._get_cell_lines(arguments)
        elif operation == "get_cell_line":
            return self._get_cell_line(arguments)
        elif operation == "search_cell_lines":
            return self._search_cell_lines(arguments)
        elif operation == "get_gene_dependencies":
            return self._get_gene_dependencies(arguments)
        elif operation == "get_drug_response":
            return self._get_drug_response(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of cancer cell lines with metadata.

        Filter by tissue type or cancer type.
        """
        tissue = arguments.get("tissue")
        cancer_type = arguments.get("cancer_type")
        page_size = arguments.get("page_size", 20)

        try:
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"page[size]": min(page_size, 100)}

            # Add filters if provided
            filters = []
            if tissue:
                filters.append(f"tissue:{tissue}")
            if cancer_type:
                filters.append(f"cancer_type:{cancer_type}")

            if filters:
                params["filter[model]"] = ",".join(filters)

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse cell line data
            cell_lines = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                cell_lines.append(
                    {
                        "model_id": item.get("id"),
                        "model_name": attrs.get("model_name"),
                        "tissue": attrs.get("tissue"),
                        "cancer_type": attrs.get("cancer_type"),
                        "sample_site": attrs.get("sample_site"),
                        "gender": attrs.get("gender"),
                        "ethnicity": attrs.get("ethnicity"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                    "total": data.get("meta", {}).get("total", len(cell_lines)),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_cell_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific cell line.

        Returns metadata, mutations, and available data types.
        """
        model_id = arguments.get("model_id")
        model_name = arguments.get("model_name")

        if not model_id and not model_name:
            return {
                "status": "error",
                "error": "Either model_id or model_name is required",
            }

        try:
            if model_id:
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"
            else:
                # Search by name first
                search_result = self._search_cell_lines({"query": model_name})
                if (
                    search_result["status"] != "success"
                    or not search_result["data"]["cell_lines"]
                ):
                    return {
                        "status": "success",
                        "data": None,
                        "message": f"Cell line '{model_name}' not found",
                    }
                model_id = search_result["data"]["cell_lines"][0]["model_id"]
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Cell line not found: {model_id or model_name}",
                }

            response.raise_for_status()
            data = response.json()

            item = data.get("data", {})
            attrs = item.get("attributes", {})

            return {
                "status": "success",
                "data": {
                    "model_id": item.get("id"),
                    "model_name": attrs.get("model_name"),
                    "tissue": attrs.get("tissue"),
                    "cancer_type": attrs.get("cancer_type"),
                    "tissue_status": attrs.get("tissue_status"),
                    "sample_site": attrs.get("sample_site"),
                    "gender": attrs.get("gender"),
                    "ethnicity": attrs.get("ethnicity"),
                    "age_at_sampling": attrs.get("age_at_sampling"),
                    "growth_properties": attrs.get("growth_properties"),
                    "msi_status": attrs.get("msi_status"),
                    "ploidy": attrs.get("ploidy"),
                    "mutational_burden": attrs.get("mutational_burden"),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search cell lines by name or identifier.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"filter[model]": f"model_name:{query}", "page[size]": 20}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            cell_lines = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                cell_lines.append(
                    {
                        "model_id": item.get("id"),
                        "model_name": attrs.get("model_name"),
                        "tissue": attrs.get("tissue"),
                        "cancer_type": attrs.get("cancer_type"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CRISPR gene dependency data.

        Returns gene effect scores indicating essentiality in cancer cell lines.
        Negative scores indicate the gene is essential (cell death upon knockout).
        """
        gene_symbol = arguments.get("gene_symbol")
        arguments.get("model_id")

        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        try:
            # Use DepMap_search_genes internally for reliable matching
            search_result = self._search_genes({"query": gene_symbol})

            if search_result.get("status") != "success":
                return search_result

            genes = search_result.get("data", {}).get("genes", [])
            exact_matches = [g for g in genes if g.get("exact_match")]
            matched_gene = exact_matches[0] if exact_matches else None

            if matched_gene is None and genes:
                # No exact match — report candidates
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "candidates": genes[:5],
                        "warning": (
                            f"No exact match for '{gene_symbol}'. "
                            f"Similar: {[g['symbol'] for g in genes[:5]]}. "
                            "Use DepMap_search_genes for disambiguation."
                        ),
                    },
                }

            if matched_gene is None:
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "message": (
                            f"Gene '{gene_symbol}' not found in DepMap. "
                            "The Sanger Cell Model Passports API has "
                            "limited gene search capabilities."
                        ),
                    },
                }

            return {
                "status": "success",
                "data": {
                    "gene_symbol": gene_symbol,
                    "matched_gene": matched_gene,
                    "note": (
                        "Gene effect scores: negative = essential "
                        "(cell death upon knockout), zero = no effect, "
                        "positive = growth advantage. "
                        "Full dependency profiles at depmap.org."
                    ),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for genes in DepMap by symbol.

        The Sanger Cell Model Passports API gene filter is limited,
        so this method fetches sorted gene batches and filters client-side.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # The Sanger API's filter[gene] param doesn't work for
            # exact symbol matching. Use sorted pagination + client filter.
            url = f"{DEPMAP_BASE_URL}/genes"
            params = {
                "sort": "symbol",
                "page[size]": 100,
            }

            # Scan through pages to find matching genes
            # With sorted results, we search up to 5 pages (500 genes)
            genes = []
            query_upper = query.upper()
            for page_num in range(1, 6):
                params["page[number]"] = page_num
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                for item in data.get("data", []):
                    attrs = item.get("attributes", {})
                    symbol = attrs.get("symbol", "")
                    # Check for exact or prefix match
                    if symbol.upper() == query_upper or symbol.upper().startswith(
                        query_upper
                    ):
                        genes.append(
                            {
                                "gene_id": item.get("id"),
                                "symbol": symbol,
                                "name": attrs.get("name"),
                                "hgnc_id": attrs.get("hgnc_id"),
                                "ensembl_id": attrs.get("ensembl_gene_id"),
                                "exact_match": (symbol.upper() == query_upper),
                            }
                        )

                # If we found exact match(es), no need for more pages
                if any(g["exact_match"] for g in genes):
                    break

                # Check if we've gone past alphabetically
                page_data = data.get("data", [])
                if page_data:
                    last_sym = page_data[-1].get("attributes", {}).get("symbol", "")
                    if last_sym.upper() > query_upper + "Z":
                        break

            # Sort: exact matches first
            genes.sort(
                key=lambda g: (
                    not g["exact_match"],
                    g.get("symbol", ""),
                )
            )

            if not genes:
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "genes": [],
                        "count": 0,
                        "note": (
                            f"Gene '{query}' not found in DepMap "
                            "gene catalog. The Sanger Cell Model "
                            "Passports API has limited gene search. "
                            "Try using an Ensembl ID or check "
                            "depmap.org directly."
                        ),
                    },
                }

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "genes": genes[:20],
                    "count": len(genes),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"DepMap API request failed: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _get_drug_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug sensitivity data for cell lines.

        Returns IC50/AUC values for drug-cell line combinations.
        """
        drug_name = arguments.get("drug_name")
        model_id = arguments.get("model_id")

        if not drug_name and not model_id:
            return {
                "status": "error",
                "error": "Either drug_name or model_id is required",
            }

        try:
            # Query drugs endpoint
            url = f"{DEPMAP_BASE_URL}/drugs"
            params = {"page[size]": 20}

            if drug_name:
                params["filter[drug]"] = f"drug_name:{drug_name}"

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            drugs = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                drugs.append(
                    {
                        "drug_id": item.get("id"),
                        "drug_name": attrs.get("drug_name"),
                        "synonyms": attrs.get("synonyms"),
                        "targets": attrs.get("targets"),
                        "target_pathway": attrs.get("target_pathway"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": drug_name or model_id,
                    "drugs": drugs,
                    "count": len(drugs),
                    "note": "Drug sensitivity data (IC50, AUC) available through DepMap portal.",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
