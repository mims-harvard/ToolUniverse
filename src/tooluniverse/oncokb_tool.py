"""
OncoKB API tool for ToolUniverse.

OncoKB is a precision oncology knowledge base that provides information about
the effects and treatment implications of specific cancer gene alterations.

API Documentation: https://api.oncokb.org/
Requires API token: https://www.oncokb.org/apiAccess
"""

import os
import requests
from typing import Dict, Any
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

    @property
    def _api_mode(self) -> str:
        """Return the current API mode label."""
        return "demo" if self.use_demo else "authenticated"

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "ToolUniverse/OncoKB",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _demo_gene_note(self, gene: str) -> str:
        return (
            f"Demo mode: {gene} is not in the demo dataset (limited to BRAF, TP53, ROS1). "
            "Set ONCOKB_API_TOKEN for full coverage. Get a token at https://www.oncokb.org/apiAccess"
        )

    def _apply_demo_gene_warning(
        self, data: Dict[str, Any], metadata: Dict[str, Any], gene: str
    ) -> None:
        """Mutate data and metadata in-place with demo-mode warning when gene is absent."""
        note = self._demo_gene_note(gene)
        metadata["note"] = note
        data["warning"] = note

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GET request to the OncoKB API with standard error handling."""
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401:
                return {
                    "ok": False,
                    "error": "Authentication required. Set ONCOKB_API_TOKEN environment variable.",
                }
            if status == 403:
                return {
                    "ok": False,
                    "error": "Access forbidden. Check your API token permissions.",
                }
            if status == 404:
                return {"ok": False, "error": f"Not found (HTTP 404)"}
            return {"ok": False, "error": f"HTTP error: {status}"}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "Request timed out"}
        except requests.exceptions.RequestException as e:
            return {"ok": False, "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"ok": False, "error": f"Unexpected error: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OncoKB API call based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()
        # Accept gene_symbol as alias for gene (consistent with other tools)
        if not arguments.get("gene") and arguments.get("gene_symbol"):
            arguments = dict(arguments, gene=arguments["gene_symbol"])
        # Accept alteration as alias for variant
        if not arguments.get("variant") and arguments.get("alteration"):
            arguments = dict(arguments, variant=arguments["alteration"])
        # Parse 'query' like "BRAF V600E" or "BRAF" into gene + variant
        if not arguments.get("gene") and arguments.get("query"):
            parts = arguments["query"].strip().split(None, 1)
            arguments = dict(arguments, gene=parts[0])
            if len(parts) > 1 and not arguments.get("variant"):
                arguments = dict(arguments, variant=parts[1])

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
        """Annotate a specific variant for oncogenic potential and treatment implications."""
        gene = arguments.get("gene", "")
        variant = arguments.get("variant", "")

        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}
        if not variant:
            return {"status": "error", "error": "Missing required parameter: variant"}

        # Accept cancer_type as alias for tumor_type (both refer to OncoTree code)
        tumor_type = arguments.get("tumor_type") or arguments.get("cancer_type") or ""

        params: Dict[str, Any] = {"hugoSymbol": gene, "alteration": variant}
        if tumor_type:
            params["tumorType"] = tumor_type

        resp = self._make_request("annotate/mutations/byProteinChange", params)
        if not resp["ok"]:
            return {"status": "error", "error": resp["error"]}

        data = resp["data"]
        metadata: Dict[str, Any] = {
            "source": "OncoKB",
            "api_mode": self._api_mode,
            "gene": gene,
            "variant": variant,
        }
        # Demo API silently returns geneExist=False for genes outside its limited set.
        if self.use_demo and not data.get("geneExist", True):
            self._apply_demo_gene_warning(data, metadata, gene)
        return {"status": "success", "data": data, "metadata": metadata}

    def _get_gene_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene-level oncogenic information."""
        gene = arguments.get("gene", "")
        if not gene:
            return {
                "status": "error",
                "error": "Missing required parameter: gene (or gene_symbol)",
            }

        # Demo API doesn't support /genes/{gene}, use /utils/allCuratedGenes instead
        if self.use_demo:
            resp = self._make_request("utils/allCuratedGenes", {})
            if not resp["ok"]:
                return {"status": "error", "error": resp["error"]}

            gene_data = next(
                (
                    g
                    for g in resp["data"]
                    if g.get("hugoSymbol", "").upper() == gene.upper()
                ),
                None,
            )
            if not gene_data:
                data: Dict[str, Any] = {}
                metadata: Dict[str, Any] = {
                    "source": "OncoKB",
                    "api_mode": "demo",
                    "gene": gene,
                }
                self._apply_demo_gene_warning(data, metadata, gene)
                return {"status": "success", "data": data, "metadata": metadata}
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

        # Full API supports /genes/{gene}
        resp = self._make_request(f"genes/{gene}", {})
        if not resp["ok"]:
            error_msg = resp["error"]
            if "Not found" in error_msg:
                error_msg = f"Gene not found: {gene}"
            return {"status": "error", "error": error_msg}

        return {
            "status": "success",
            "data": resp["data"],
            "metadata": {
                "source": "OncoKB",
                "api_mode": "authenticated",
                "gene": gene,
            },
        }

    def _get_cancer_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of all cancer genes curated in OncoKB."""
        resp = self._make_request("genes", {})
        if not resp["ok"]:
            return {"status": "error", "error": resp["error"]}

        data = resp["data"]

        # Filter to only include cancer genes (oncogene or TSG).
        # Demo API returns geneType:"ONCOGENE"/"TSG" instead of boolean fields.
        def _is_cancer_gene(g: dict) -> bool:
            if g.get("oncogene") or g.get("tsg"):
                return True
            gene_type = (g.get("geneType") or "").upper()
            return "ONCOGENE" in gene_type or "TSG" in gene_type

        cancer_genes = [g for g in data if _is_cancer_gene(g)]

        metadata: Dict[str, Any] = {
            "source": "OncoKB",
            "api_mode": self._api_mode,
        }
        if self.use_demo:
            metadata["note"] = (
                "Demo mode: results are limited. Set ONCOKB_API_TOKEN "
                "environment variable for full cancer gene list (700+ genes). "
                "Get a token at https://www.oncokb.org/apiAccess"
            )
        return {
            "status": "success",
            "data": {
                "total_genes": len(data),
                "cancer_genes_count": len(cancer_genes),
                "genes": cancer_genes,
            },
            "metadata": metadata,
        }

    def _get_levels(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about OncoKB evidence levels."""
        resp = self._make_request("levels", {})
        if not resp["ok"]:
            return {"status": "error", "error": resp["error"]}

        return {
            "status": "success",
            "data": resp["data"],
            "metadata": {
                "source": "OncoKB",
                "api_mode": self._api_mode,
                "description": "OncoKB evidence levels for therapeutic actionability",
            },
        }

    def _annotate_copy_number(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate copy number alterations (amplification/deletion)."""
        gene = arguments.get("gene", "")
        # Feature-120B-004: accept copy_number_alteration as alias for copy_number_type
        cna_type = (
            arguments.get("copy_number_type")
            or arguments.get("copy_number_alteration", "")
        ).upper()

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

        # Accept cancer_type as alias for tumor_type (both refer to OncoTree code)
        tumor_type = arguments.get("tumor_type") or arguments.get("cancer_type") or ""

        params: Dict[str, Any] = {
            "hugoSymbol": gene,
            "copyNameAlterationType": cna_type.upper(),
        }
        if tumor_type:
            params["tumorType"] = tumor_type

        resp = self._make_request("annotate/copyNumberAlterations", params)
        if not resp["ok"]:
            return {"status": "error", "error": resp["error"]}

        data = resp["data"]
        metadata: Dict[str, Any] = {
            "source": "OncoKB",
            "api_mode": self._api_mode,
            "gene": gene,
            "copy_number_type": cna_type,
        }
        if self.use_demo and not data.get("geneExist", True):
            self._apply_demo_gene_warning(data, metadata, gene)
        return {"status": "success", "data": data, "metadata": metadata}
