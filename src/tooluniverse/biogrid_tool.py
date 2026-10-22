"""BioGRID Database REST API Tool for protein and genetic interaction data."""

import os

import requests
from typing import Any, Dict, List, Union
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOGRID_BASE_URL = "https://webservice.thebiogrid.org"


def _join_pipe_delimited(value: Union[str, list]) -> str:
    """Convert a string or list to a pipe-delimited string for BioGRID parameters."""
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


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

    # Maps argument keys to their BioGRID API parameter names (pipe-delimited).
    _LIST_PARAM_MAP = {
        "gene_names": "geneList",
        "chemical_names": "chemicalList",
        "pubmed_ids": "pubmedList",
        "ptm_type": "ptmType",
        "evidence_types": "evidenceList",
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

        # Map list-or-string arguments to pipe-delimited BioGRID parameters
        for arg_key, api_key_name in self._LIST_PARAM_MAP.items():
            if arg_key in arguments and arguments[arg_key]:
                params[api_key_name] = _join_pipe_delimited(arguments[arg_key])

        if "organism" in arguments:
            organism = arguments["organism"]
            params["taxId"] = self._ORGANISM_MAP.get(organism.lower(), organism)
        else:
            # Feature-120B-002: default to human (9606) to avoid returning multi-species results
            params["taxId"] = 9606

        # Note: BioGRID API does not support filtering by "physical"/"genetic" via evidenceList.
        # The interaction_type parameter is informational only; filtering must be done client-side
        # using the EXPERIMENTAL_SYSTEM_TYPE field in the results.

        # Handle residue filtering for PTMs
        if arguments.get("residue"):
            params["residue"] = arguments["residue"]

        # Handle throughput filtering
        if arguments.get("throughput"):
            params["throughputTag"] = arguments["throughput"]

        # Handle interaction action for chemical interactions
        if arguments.get("interaction_action"):
            params["action"] = arguments["interaction_action"]

        # Boolean flags
        if "include_evidence" in arguments:
            params["includeEvidence"] = (
                "true" if arguments["include_evidence"] else "false"
            )

        if "include_enzymes" in arguments:
            params["includeInteractors"] = (
                "true" if arguments["include_enzymes"] else "false"
            )

        if "limit" in arguments:
            params["max"] = arguments["limit"]
        if "offset" in arguments:
            params["start"] = arguments["offset"]

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
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        # Normalize singular aliases to expected list parameters
        if not arguments.get("chemical_names") and arguments.get("chemical_name"):
            arguments = dict(arguments, chemical_names=[arguments["chemical_name"]])
        if not arguments.get("gene_names") and arguments.get("gene_name"):
            arguments = dict(arguments, gene_names=[arguments["gene_name"]])
        for param in self.required:
            if param not in arguments:
                error_msg = f"Missing required parameter: {param}"
                return {
                    "status": "error",
                    "data": {"error": error_msg},
                    "error": error_msg,
                }

        properties = self.tool_config.get("parameter", {}).get("properties", {})
        default_limit = properties.get("limit", {}).get("default", 100)
        limit = arguments.get("limit", default_limit)
        offset = arguments.get("offset", 0)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 9999:
            error_msg = "limit must be an integer between 1 and 9999"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            error_msg = "offset must be a non-negative integer"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        # BioGRID REST API v4.x /interactions/ silently ignores chemicalList —
        # it always returns protein-protein interactions regardless.  Warn the
        # user early so they don't get misleading PPI results.
        tool_name = self.tool_config.get("name", "")
        if tool_name == "BioGRID_get_chemical_interactions":
            has_genes = bool(arguments.get("gene_names"))
            has_chemicals = bool(arguments.get("chemical_names"))
            if not has_genes:
                if has_chemicals:
                    error_msg = (
                        "BioGRID REST API does not support chemical-only searches — "
                        "the chemicalList parameter is silently ignored and returns "
                        "unrelated protein interactions. Please provide gene_names to "
                        "query interactions for specific proteins, or use "
                        "ChEMBL_search_mechanisms / DGIdb_search_interactions for "
                        "drug-protein interaction data."
                    )
                else:
                    error_msg = (
                        "Please provide gene_names (e.g., ['EGFR', 'ABL1']) to query "
                        "BioGRID interactions. Chemical-only search is not supported "
                        "by the BioGRID REST API."
                    )
                return {
                    "status": "error",
                    "error": error_msg,
                    "data": {"error": error_msg},
                }

        url = self._build_url()

        try:
            # BioGRID supports start/max but does not return a total in JSON.
            # Fetch one lookahead record so a full page cannot masquerade as a
            # complete result set. The public API caps max at 10,000.
            request_arguments = dict(arguments, limit=limit + 1, offset=offset)
            params = self._build_params(request_arguments)
        except ValueError as e:
            error_msg = f"Authentication failed: {e}"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        api_response = self._make_request(url, params)

        if "error" in api_response:
            return {
                "status": "error",
                "data": api_response,
                "error": api_response.get("error"),
            }

        upstream_count = len(api_response) if isinstance(api_response, dict) else 0
        has_more = upstream_count > limit
        if isinstance(api_response, dict) and has_more:
            api_response = dict(list(api_response.items())[:limit])
        upstream_returned = len(api_response) if isinstance(api_response, dict) else 0

        # interaction_type is declared as a physical/genetic/both filter, but
        # BioGRID's REST API can't filter on it server-side -- it must be applied
        # client-side on each record's EXPERIMENTAL_SYSTEM_TYPE field (confirmed
        # present in this tool's return_schema, values "physical"/"genetic").
        # Without this it was silently ignored: every call returned all
        # interaction types regardless of the one requested, so a PPI-only query
        # could be polluted with genetic interactions.
        interaction_type = str(arguments.get("interaction_type") or "both").lower()
        interaction_type_note = None
        if interaction_type in ("physical", "genetic") and isinstance(
            api_response, dict
        ):
            total = len(api_response)
            kept = {
                k: v
                for k, v in api_response.items()
                if isinstance(v, dict)
                and str(v.get("EXPERIMENTAL_SYSTEM_TYPE", "")).lower()
                == interaction_type
            }
            api_response = kept
            interaction_type_note = (
                f"Filtered client-side to interaction_type='{interaction_type}' on the "
                f"EXPERIMENTAL_SYSTEM_TYPE field ({len(kept)} of {total} interactions kept); "
                "BioGRID's REST API does not filter by interaction type server-side."
            )

        gene_names = arguments.get("gene_names", [])
        metadata = {
            "source": "BioGRID",
            "gene_names": gene_names,
            "interaction_count": len(api_response)
            if isinstance(api_response, dict)
            else 0,
            "upstream_returned": upstream_returned,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": offset + upstream_returned if has_more else None,
            "upstream_total_lower_bound": (
                offset + upstream_returned + 1 if has_more else offset + upstream_returned
            ),
            "result_set_complete": offset == 0 and not has_more,
            "note": (
                "BioGRID chemicalList filter is not supported by the REST API; "
                "results reflect all protein interactions for the queried gene(s), "
                "not filtered by chemical. Use ChEMBL_search_mechanisms or "
                "DGIdb_search_interactions for drug-protein interaction data."
            ),
        }
        if not has_more:
            metadata["upstream_total"] = offset + upstream_returned
        else:
            metadata["pagination_warning"] = (
                f"Returned the upstream records at offset {offset}; continue with "
                "metadata.next_offset while metadata.has_more is true."
            )
        if interaction_type_note:
            metadata["interaction_type_filter"] = interaction_type_note
        return {
            "status": "success",
            "data": api_response,
            "metadata": metadata,
        }
