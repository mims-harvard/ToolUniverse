"""BioGRID Database REST API Tool for protein and genetic interaction data."""

import os

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOGRID_BASE_URL = "https://webservice.thebiogrid.org"


@register_tool("BioGRIDRESTTool")
class BioGRIDRESTTool(BaseTool):
    """BioGRID Database REST API tool.
    Generic wrapper for BioGRID API endpoints defined in ppi_tools.json.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        self.endpoint_template: str = fields.get("endpoint", "/interactions/")
        self.required: List[str] = parameter.get("required", [])
        self.output_format: str = fields.get("return_format", "JSON")

    def _build_url(self) -> str:
        """Build URL for BioGRID API request."""
        return BIOGRID_BASE_URL + self.endpoint_template

    _ORGANISM_MAP = {
        "homo sapiens": 9606,
        "mus musculus": 10090,
        "saccharomyces cerevisiae": 559292,
    }

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for BioGRID API request."""
        params = {"format": "json", "interSpeciesExcluded": "false"}

        api_key = (
            arguments.get("api_key")
            or arguments.get("accesskey")
            or arguments.get("access_key")
            or os.getenv("BIOGRID_API_KEY")
            or os.getenv("BIOGRID_ACCESS_KEY")
        )

        if not api_key:
            raise ValueError(
                "BioGRID API key is required. Please provide 'api_key' parameter "
                "or set BIOGRID_ACCESS_KEY environment variable. "
                "Register at: https://webservice.thebiogrid.org/"
            )

        params["accesskey"] = api_key

        # Map gene names to BioGRID format
        if "gene_names" in arguments:
            gene_names = arguments["gene_names"]
            if isinstance(gene_names, list):
                params["geneList"] = "|".join(gene_names)
            else:
                params["geneList"] = str(gene_names)

        # Map chemical names for chemical interaction queries
        if "chemical_names" in arguments:
            chemical_names = arguments["chemical_names"]
            if isinstance(chemical_names, list):
                params["chemicalList"] = "|".join(chemical_names)
            else:
                params["chemicalList"] = str(chemical_names)

        # Map PubMed IDs for publication-based queries
        if "pubmed_ids" in arguments:
            pubmed_ids = arguments["pubmed_ids"]
            if isinstance(pubmed_ids, list):
                params["pubmedList"] = "|".join([str(pid) for pid in pubmed_ids])
            else:
                params["pubmedList"] = str(pubmed_ids)

        if "organism" in arguments:
            organism = arguments["organism"]
            params["taxId"] = self._ORGANISM_MAP.get(organism.lower(), organism)

        # Handle interaction type filtering
        if "interaction_type" in arguments:
            interaction_type = arguments["interaction_type"]
            if interaction_type == "physical":
                params["evidenceList"] = "physical"
            elif interaction_type == "genetic":
                params["evidenceList"] = "genetic"
            # "both" means no evidence filter

        # Handle PTM type filtering
        if "ptm_type" in arguments:
            ptm_type = arguments["ptm_type"]
            if isinstance(ptm_type, list):
                params["ptmType"] = "|".join(ptm_type)
            else:
                params["ptmType"] = str(ptm_type)

        # Handle residue filtering for PTMs
        if "residue" in arguments and arguments["residue"]:
            params["residue"] = arguments["residue"]

        # Handle evidence types filtering
        if "evidence_types" in arguments and arguments["evidence_types"]:
            evidence_types = arguments["evidence_types"]
            if isinstance(evidence_types, list):
                params["evidenceList"] = "|".join(evidence_types)
            else:
                params["evidenceList"] = str(evidence_types)

        # Handle throughput filtering
        if "throughput" in arguments and arguments["throughput"]:
            params["throughputTag"] = arguments["throughput"]

        # Handle interaction action for chemical interactions
        if "interaction_action" in arguments and arguments["interaction_action"]:
            params["action"] = arguments["interaction_action"]

        # Include evidence details
        if "include_evidence" in arguments:
            params["includeEvidence"] = (
                "true" if arguments["include_evidence"] else "false"
            )

        # Include enzyme/interactor details
        if "include_enzymes" in arguments:
            params["includeInteractors"] = (
                "true" if arguments["include_enzymes"] else "false"
            )

        # Set limit
        if "limit" in arguments:
            params["max"] = arguments["limit"]

        # Default search by official gene symbols
        params["searchNames"] = "true"

        return params

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a GET request and handle common errors."""
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            if self.output_format == "JSON":
                return response.json()
            else:
                return {"data": response.text}

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        for param in self.required:
            if param not in arguments:
                error_msg = f"Missing required parameter: {param}"
                return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        url = self._build_url()

        try:
            params = self._build_params(arguments)
        except ValueError as e:
            error_msg = f"Authentication failed: {e}"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        api_response = self._make_request(url, params)

        if "error" in api_response:
            return {"status": "error", "data": api_response, "error": api_response.get("error")}

        return {"status": "success", "data": api_response}
