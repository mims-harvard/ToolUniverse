"""
OncoKB API tool for ToolUniverse.

OncoKB is a precision oncology knowledge base that provides information about
the effects and treatment implications of specific cancer gene alterations.

API Documentation: https://api.oncokb.org/
Requires API token: https://www.oncokb.org/apiAccess
"""

import os
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for OncoKB API
ONCOKB_API_URL = "https://www.oncokb.org/api/v1"
ONCOKB_DEMO_URL = "https://demo.oncokb.org/api/v1"


@register_tool("OncoKBTool")
class OncoKBTool(BaseTool):
    """
    Tool for querying OncoKB precision oncology knowledge base.

    OncoKB provides:
    - Actionable cancer variant annotations
    - Evidence levels for clinical actionability
    - FDA-approved and investigational treatments
    - Gene-level oncogenic classifications

    Requires API token via ONCOKB_API_TOKEN environment variable.
    Demo API available for testing (limited to BRAF, TP53, ROS1 genes).
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})
        # Get API token from environment
        self.api_token = os.environ.get("ONCOKB_API_TOKEN", "")
        # Use demo API if no token provided
        self.use_demo = not bool(self.api_token)
        self.base_url = ONCOKB_DEMO_URL if self.use_demo else ONCOKB_API_URL

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "ToolUniverse/OncoKB",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OncoKB API call based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "annotate_variant":
            return self._annotate_variant(arguments)
        elif operation == "get_gene_info":
            return self._get_gene_info(arguments)
        elif operation == "get_cancer_genes":
            return self._get_cancer_genes(arguments)
        elif operation == "get_levels":
            return self._get_levels(arguments)
        elif operation == "annotate_copy_number":
            return self._annotate_copy_number(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: annotate_variant, get_gene_info, get_cancer_genes, get_levels, annotate_copy_number",
            }

    def _annotate_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Annotate a specific variant for oncogenic potential and treatment implications.

        Args:
            arguments: Dict containing:
                - gene: Gene symbol (e.g., BRAF)
                - variant: Variant notation (e.g., V600E)
                - tumor_type: Optional cancer type (OncoTree code)
        """
        gene = arguments.get("gene", "")
        variant = arguments.get("variant", "")

        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}
        if not variant:
            return {"status": "error", "error": "Missing required parameter: variant"}

        tumor_type = arguments.get("tumor_type", "")

        # Build query parameters
        params = {
            "hugoSymbol": gene,
            "alteration": variant,
        }
        if tumor_type:
            params["tumorType"] = tumor_type

        try:
            response = requests.get(
                f"{self.base_url}/annotate/mutations/byProteinChange",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            metadata: Dict[str, Any] = {
                "source": "OncoKB",
                "api_mode": "demo" if self.use_demo else "authenticated",
                "gene": gene,
                "variant": variant,
            }
            # Feature-81A-002: warn when demo mode returns empty data for unsupported gene.
            # Demo API silently returns geneExist=False for genes outside its limited set.
            if self.use_demo and not data.get("geneExist", True):
                metadata["note"] = (
                    f"Demo mode: {gene} is not in the demo dataset (limited to BRAF, TP53, ROS1). "
                    "Set ONCOKB_API_TOKEN for full coverage. Get a token at https://www.oncokb.org/apiAccess"
                )
            return {"status": "success", "data": data, "metadata": metadata}

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication required. Set ONCOKB_API_TOKEN environment variable.",
                }
            elif e.response.status_code == 403:
                return {
                    "status": "error",
                    "error": "Access forbidden. Check your API token permissions.",
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene-level oncogenic information.

        Args:
            arguments: Dict containing:
                - gene: Gene symbol (e.g., BRAF, TP53)
        """
        gene = arguments.get("gene", "")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        try:
            # Demo API doesn't support /genes/{gene} endpoint, use /utils/allCuratedGenes instead
            if self.use_demo:
                response = requests.get(
                    f"{self.base_url}/utils/allCuratedGenes",
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                all_genes = response.json()

                # Find the specific gene
                gene_data = None
                for g in all_genes:
                    if g.get("hugoSymbol", "").upper() == gene.upper():
                        gene_data = g
                        break

                if not gene_data:
                    return {
                        "status": "error",
                        "error": f"Gene not found in demo data: {gene}. Demo limited to curated cancer genes.",
                    }

                return {
                    "status": "success",
                    "data": gene_data,
                    "metadata": {
                        "source": "OncoKB",
                        "api_mode": "demo",
                        "gene": gene,
                        "note": "Demo mode: limited to curated cancer genes",
                    },
                }
            else:
                # Full API supports /genes/{gene}
                response = requests.get(
                    f"{self.base_url}/genes/{gene}",
                    headers=self._get_headers(),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "status": "success",
                    "data": data,
                    "metadata": {
                        "source": "OncoKB",
                        "api_mode": "authenticated",
                        "gene": gene,
                    },
                }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"status": "error", "error": f"Gene not found: {gene}"}
            if e.response.status_code == 401:
                return {
                    "status": "error",
                    "error": "API authentication required. Set ONCOKB_API_TOKEN environment variable.",
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_cancer_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of all cancer genes curated in OncoKB.

        Returns genes classified as oncogenes and/or tumor suppressors.
        """
        try:
            response = requests.get(
                f"{self.base_url}/genes",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Filter to only include cancer genes (oncogene or TSG)
            cancer_genes = [g for g in data if g.get("oncogene") or g.get("tsg")]

            result = {
                "status": "success",
                "data": {
                    "total_genes": len(data),
                    "cancer_genes_count": len(cancer_genes),
                    "genes": cancer_genes,
                },
                "metadata": {
                    "source": "OncoKB",
                    "api_mode": "demo" if self.use_demo else "authenticated",
                },
            }
            if self.use_demo:
                result["metadata"]["note"] = (
                    "Demo mode: results are limited. Set ONCOKB_API_TOKEN "
                    "environment variable for full cancer gene list (700+ genes). "
                    "Get a token at https://www.oncokb.org/apiAccess"
                )
            return result

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_levels(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about OncoKB evidence levels.

        Returns the definitions of all actionability levels (1, 2, 3A, 3B, 4, R1, R2).
        """
        try:
            response = requests.get(
                f"{self.base_url}/levels",
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "OncoKB",
                    "api_mode": "demo" if self.use_demo else "authenticated",
                    "description": "OncoKB evidence levels for therapeutic actionability",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _annotate_copy_number(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Annotate copy number alterations (amplification/deletion).

        Args:
            arguments: Dict containing:
                - gene: Gene symbol
                - copy_number_type: AMPLIFICATION or DELETION
                - tumor_type: Optional cancer type (OncoTree code)
        """
        gene = arguments.get("gene", "")
        cna_type = arguments.get("copy_number_type", "")

        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}
        if not cna_type:
            return {
                "status": "error",
                "error": "Missing required parameter: copy_number_type",
            }

        if cna_type.upper() not in ["AMPLIFICATION", "DELETION"]:
            return {
                "status": "error",
                "error": "copy_number_type must be AMPLIFICATION or DELETION",
            }

        tumor_type = arguments.get("tumor_type", "")

        params = {
            "hugoSymbol": gene,
            "copyNameAlterationType": cna_type.upper(),
        }
        if tumor_type:
            params["tumorType"] = tumor_type

        try:
            response = requests.get(
                f"{self.base_url}/annotate/copyNumberAlterations",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            metadata: Dict[str, Any] = {
                "source": "OncoKB",
                "api_mode": "demo" if self.use_demo else "authenticated",
                "gene": gene,
                "copy_number_type": cna_type,
            }
            if self.use_demo and not data.get("geneExist", True):
                metadata["note"] = (
                    f"Demo mode: {gene} is not in the demo dataset (limited to BRAF, TP53, ROS1). "
                    "Set ONCOKB_API_TOKEN for full coverage. Get a token at https://www.oncokb.org/apiAccess"
                )
            return {"status": "success", "data": data, "metadata": metadata}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
