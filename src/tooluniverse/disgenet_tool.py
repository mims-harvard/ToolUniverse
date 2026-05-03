"""
DisGeNET API tool for ToolUniverse.

DisGeNET is one of the largest public collections of genes and variants
associated with human diseases, aggregating data from multiple sources.

API Documentation: https://www.disgenet.org/api/
Requires API key: Register at https://www.disgenet.org/
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for DisGeNET API
DISGENET_API_URL = "https://api.disgenet.com/api/v1"


@register_tool("DisGeNETTool")
class DisGeNETTool(BaseTool):
    """
    Tool for querying DisGeNET gene-disease association database.

    DisGeNET provides:
    - Gene-disease associations (GDAs)
    - Variant-disease associations (VDAs)
    - Disease-disease associations
    - Aggregated evidence scores

    Requires API key via DISGENET_API_KEY environment variable.
    Register for free at https://www.disgenet.org/
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})
        self.api_key = os.environ.get("DISGENET_API_KEY", "")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "ToolUniverse/DisGeNET",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DisGeNET API call based on operation type."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "DisGeNET API key required. Set DISGENET_API_KEY environment variable. Register at https://www.disgenet.org/",
            }

        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search_gene":
            return self._search_gene(arguments)
        elif operation == "search_disease":
            return self._search_disease(arguments)
        elif operation == "get_gda":
            return self._get_gene_disease_associations(arguments)
        elif operation == "get_vda":
            return self._get_variant_disease_associations(arguments)
        elif operation == "get_disease_genes":
            return self._get_disease_genes(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_gene, search_disease, get_gda, get_vda, get_disease_genes",
            }

    def _search_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for gene-disease associations by gene symbol.

        Args:
            arguments: Dict containing:
                - gene: Gene symbol (e.g., BRCA1, TP53)
                - limit: Maximum results (default 10)
        """
        gene = arguments.get("gene", "")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        limit = arguments.get("limit", 10)

        try:
            response = requests.get(
                f"{DISGENET_API_URL}/gda/gene/{gene}",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": {
                    "gene": gene,
                    "associations": data
                    if isinstance(data, list)
                    else data.get("results", []),
                    "count": len(data)
                    if isinstance(data, list)
                    else data.get("count", 0),
                },
                "metadata": {
                    "source": "DisGeNET",
                    "gene": gene,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return {"status": "error", "error": "Invalid or expired API key"}
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"gene": gene, "associations": [], "count": 0},
                    "metadata": {"note": "No associations found for gene"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for disease information and associated genes.

        Args:
            arguments: Dict containing:
                - disease: Disease name or ID (UMLS CUI, e.g., C0006142 for breast cancer)
                - limit: Maximum results (default 10)
        """
        disease = arguments.get("disease", "")
        if not disease:
            return {"status": "error", "error": "Missing required parameter: disease"}

        limit = arguments.get("limit", 10)

        try:
            # Try as UMLS CUI first
            if disease.startswith("C") and disease[1:].isdigit():
                endpoint = f"/gda/disease/{disease}"
            else:
                endpoint = f"/gda/disease/{disease}"

            response = requests.get(
                f"{DISGENET_API_URL}{endpoint}",
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": {
                    "disease": disease,
                    "associations": data
                    if isinstance(data, list)
                    else data.get("results", []),
                    "count": len(data)
                    if isinstance(data, list)
                    else data.get("count", 0),
                },
                "metadata": {
                    "source": "DisGeNET",
                    "disease": disease,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"disease": disease, "associations": [], "count": 0},
                    "metadata": {"note": "No associations found for disease"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_disease_associations(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get gene-disease associations with filtering options.

        Args:
            arguments: Dict containing:
                - gene: Gene symbol (optional if disease provided)
                - disease: Disease ID (optional if gene provided)
                - source: Data source filter (CURATED, ANIMAL_MODELS, LITERATURE, etc.)
                - min_score: Minimum GDA score (0-1)
                - limit: Maximum results
        """
        gene = arguments.get("gene", "")
        disease = arguments.get("disease", "")

        if not gene and not disease:
            return {"status": "error", "error": "Either gene or disease required"}

        params = {"limit": arguments.get("limit", 25)}

        if arguments.get("source"):
            params["source"] = arguments["source"]
        if arguments.get("min_score"):
            params["min_score"] = arguments["min_score"]

        try:
            if gene:
                endpoint = f"/gda/gene/{gene}"
            else:
                endpoint = f"/gda/disease/{disease}"

            response = requests.get(
                f"{DISGENET_API_URL}{endpoint}",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            associations = data if isinstance(data, list) else data.get("results", [])

            return {
                "status": "success",
                "data": {
                    "gene": gene if gene else None,
                    "disease": disease if disease else None,
                    "associations": associations,
                    "count": len(associations),
                },
                "metadata": {
                    "source": "DisGeNET GDA",
                    "filters": params,
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_variant_disease_associations(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get variant-disease associations.

        Args:
            arguments: Dict containing:
                - variant: Variant ID (rsID, e.g., rs1234)
                - gene: Gene symbol to get all variants
                - limit: Maximum results
        """
        variant = arguments.get("variant", "")
        gene = arguments.get("gene", "")

        if not variant and not gene:
            return {"status": "error", "error": "Either variant or gene required"}

        params = {"limit": arguments.get("limit", 25)}

        try:
            if variant:
                endpoint = f"/vda/variant/{variant}"
            else:
                endpoint = f"/vda/gene/{gene}"

            response = requests.get(
                f"{DISGENET_API_URL}{endpoint}",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            associations = data if isinstance(data, list) else data.get("results", [])

            return {
                "status": "success",
                "data": {
                    "variant": variant if variant else None,
                    "gene": gene if gene else None,
                    "associations": associations,
                    "count": len(associations),
                },
                "metadata": {
                    "source": "DisGeNET VDA",
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"associations": [], "count": 0},
                    "metadata": {"note": "No variant associations found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all genes associated with a disease.

        Args:
            arguments: Dict containing:
                - disease: Disease ID (UMLS CUI) or disease name
                - min_score: Minimum association score (0-1)
                - limit: Maximum results
        """
        disease = arguments.get("disease", "")
        if not disease:
            return {"status": "error", "error": "Missing required parameter: disease"}

        params = {
            "limit": arguments.get("limit", 50),
        }
        if arguments.get("min_score"):
            params["min_score"] = arguments["min_score"]

        try:
            response = requests.get(
                f"{DISGENET_API_URL}/gda/disease/{disease}",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            associations = data if isinstance(data, list) else data.get("results", [])

            # Extract unique genes
            genes = []
            seen = set()
            for assoc in associations:
                gene_symbol = assoc.get("gene_symbol", assoc.get("geneSymbol"))
                if gene_symbol and gene_symbol not in seen:
                    seen.add(gene_symbol)
                    genes.append(
                        {
                            "symbol": gene_symbol,
                            "score": assoc.get("score", assoc.get("gda_score")),
                            "evidence_count": assoc.get(
                                "evidence_count", assoc.get("nPublications")
                            ),
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "disease": disease,
                    "genes": genes,
                    "gene_count": len(genes),
                },
                "metadata": {
                    "source": "DisGeNET",
                    "disease": disease,
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
