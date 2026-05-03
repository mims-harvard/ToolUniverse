"""
PharmGKB API tool for ToolUniverse.

PharmGKB is a comprehensive resource that curates knowledge about the impact
of genetic variation on drug response for clinicians and researchers.

API Documentation: https://api.pharmgkb.org/v1/
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry

# Base URL for PharmGKB/ClinPGx REST API
PHARMGKB_BASE_URL = "https://api.clinpgx.org/v1"


@register_tool("PharmGKBTool")
class PharmGKBTool(BaseTool):
    """
    Tool for querying PharmGKB REST API.

    PharmGKB provides pharmacogenomics data:
    - Drug-gene-variant clinical annotations
    - CPIC dosing guidelines
    - Drug and gene details
    - Pharmacogenetic pathways

    No authentication required for most endpoints.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "search_drugs")
        self.session = requests.Session()

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PharmGKB API call."""
        operation = self.operation

        if operation == "search_drugs":
            return self._search_entity("Chemical", arguments)
        elif operation == "drug_details":
            return self._get_entity_details("Chemical", arguments)
        elif operation == "search_genes":
            return self._search_entity("Gene", arguments)
        elif operation == "gene_details":
            return self._get_entity_details("Gene", arguments)
        elif operation == "clinical_annotations":
            return self._get_clinical_annotations(arguments)
        elif operation == "search_variants":
            return self._search_entity("Variant", arguments)
        elif operation == "dosing_guidelines":
            return self._get_dosing_guidelines(arguments)
        else:
            return self._error(f"Unknown operation: {operation}")

    def _error(self, message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message}

    def _request_json(
        self, url: str, params: Dict[str, Any]
    ) -> tuple[int, Dict[str, Any], str]:
        try:
            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                max_attempts=4,
                backoff_seconds=0.75,
            )
        except requests.RequestException as e:
            return 0, {}, f"PharmGKB API request failed: {str(e)}"

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            detail = (
                payload.get("error")
                if isinstance(payload, dict)
                else response.text[:200]
            )
            return (
                response.status_code,
                payload,
                f"PharmGKB API error {response.status_code}: {detail}",
            )

        if not payload:
            return (
                response.status_code,
                payload,
                "PharmGKB API returned non-JSON or empty response",
            )

        return response.status_code, payload, ""

    def _search_entity(
        self, entity_type: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search for drugs, genes, or variants."""
        query = (
            arguments.get("query")
            or arguments.get("drug_name")
            or arguments.get("name")
            or arguments.get("drug")
            or ""
        )
        if not query:
            return self._error("query parameter is required")

        params = {"view": "base"}
        if entity_type == "Gene":
            params["symbol"] = query
        else:
            params["name"] = query

        status_code, api_response, error = self._request_json(
            f"{PHARMGKB_BASE_URL}/data/{entity_type.lower()}",
            params,
        )
        if status_code == 404 and entity_type == "Variant":
            # Gene name passed to variant search — try gene lookup as fallback
            _, gene_resp, gene_err = self._request_json(
                f"{PHARMGKB_BASE_URL}/data/gene",
                {"symbol": query, "view": "base"},
            )
            if not gene_err:
                gene_data = gene_resp.get("data", [])
                if gene_data:
                    gene_id = gene_data[0].get("id", "")
                    return {
                        "status": "success",
                        "data": [],
                        "note": (
                            f"'{query}' is a gene symbol, not a variant rsID. "
                            f"PharmGKB gene found: {gene_id}. "
                            f"Use PharmGKB_get_gene_details with gene_id='{gene_id}' "
                            f"for gene-level pharmacogenomics data, or search with an rsID "
                            f"(e.g., 'rs1065852') for a specific variant."
                        ),
                    }
            return {
                "status": "success",
                "data": [],
                "note": f"No variants found matching '{query}'. Use an rsID (e.g., 'rs1065852') to search for a specific variant.",
            }
        if status_code == 404:
            return {"status": "success", "data": []}

        if error:
            return self._error(error)

        results = api_response.get("data", api_response)
        return {"status": "success", "data": results}

    def _get_entity_details(
        self, entity_type: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get details for a specific entity by PharmGKB ID."""
        # Handle both chemical_id and drug_id interchangeably
        if entity_type == "Chemical":
            entity_id = (
                arguments.get("chemical_id")
                or arguments.get("drug_id")
                or arguments.get("id")
            )
        else:
            entity_id = arguments.get(f"{entity_type.lower()}_id") or arguments.get(
                "id"
            )

        if not entity_id:
            return self._error(f"{entity_type.lower()}_id parameter is required")

        _, api_response, error = self._request_json(
            f"{PHARMGKB_BASE_URL}/data/{entity_type.lower()}/{entity_id}",
            {"view": "base"},
        )
        if error:
            return self._error(error)

        result = api_response.get("data", api_response)
        return {"status": "success", "data": result}

    def _get_clinical_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get clinical annotations. Best retrieved by specific ID or filtered."""
        annotation_id = arguments.get("annotation_id")
        if annotation_id:
            _, api_response, error = self._request_json(
                f"{PHARMGKB_BASE_URL}/data/clinicalAnnotation/{annotation_id}",
                {"view": "base"},
            )
            if error:
                return self._error(error)
            result = api_response.get("data", api_response)
            return {"status": "success", "data": result}

        # Feature-121A-001: auto-resolve gene symbol to PharmGKB PA ID for a targeted URL.
        # The API rejects relatedGenes.id filter (HTTP 400); provide a direct page URL instead.
        gene_symbol = arguments.get("gene") or arguments.get("gene_symbol")
        gene_id = arguments.get("gene_id")

        if gene_symbol and not gene_id:
            _, gene_resp, err = self._request_json(
                f"{PHARMGKB_BASE_URL}/data/gene",
                {"symbol": gene_symbol, "view": "min"},
            )
            if not err:
                genes = (
                    gene_resp.get("data", [])
                    if isinstance(gene_resp.get("data"), list)
                    else []
                )
                if genes:
                    gene_id = genes[0].get("id", "")

        if gene_symbol or gene_id:
            target_id = gene_id or gene_symbol
            url = (
                f"https://www.pharmgkb.org/gene/{target_id}/clinicalAnnotation"
                if gene_id
                else f"https://www.pharmgkb.org/gene?symbol={gene_symbol}"
            )
            return self._error(
                f"PharmGKB API does not support listing annotations by gene symbol. "
                f"Browse {url} to find annotation IDs, then call with annotation_id=<id>. "
                f"For drug-gene dosing guidelines, use CPIC_list_guidelines instead."
            )

        return self._error(
            "annotation_id is required (e.g., '1447954390'). "
            "Browse https://www.pharmgkb.org/clinicalAnnotation to find annotation IDs, "
            "or use CPIC_get_guidelines for drug-gene dosing recommendations."
        )

    def _get_dosing_guidelines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get CPIC/DPWG dosing guidelines."""
        guideline_id = arguments.get("guideline_id")
        if guideline_id:
            _, api_response, error = self._request_json(
                f"{PHARMGKB_BASE_URL}/data/guideline/{guideline_id}",
                {"view": "base"},
            )
            if error:
                return self._error(error)
            result = api_response.get("data", api_response)
            return {"status": "success", "data": result}

        # Feature-67A-003: relatedGenes.symbol filter returns HTTP 400 from PharmGKB API.
        # Return an error directing users to look up the guideline_id first.
        gene_symbol = arguments.get("gene") or arguments.get("gene_id")
        if gene_symbol:
            return self._error(
                f"PharmGKB does not support gene-based guideline lookup. "
                f"Use PharmGKB_search_genes to find gene '{gene_symbol}', then use the "
                f"returned guideline IDs with guideline_id parameter."
            )

        return self._error(
            "guideline_id is required. Use PharmGKB_search_genes or PharmGKB_search_drugs "
            "to find relevant guideline IDs."
        )
