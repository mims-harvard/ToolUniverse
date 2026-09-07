"""
Ensembl REST API Tool

This tool provides access to the Ensembl genome browser database for gene
lookup, sequence retrieval, variant information, homology data, and more.
"""

import re
import requests
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry

# Ensembl REST API Base URL
ENSEMBL_BASE_URL = "https://rest.ensembl.org"


@register_tool("EnsemblRESTTool")
class EnsemblRESTTool(BaseTool):
    """
    Generic Ensembl REST API tool.
    Handles all Ensembl endpoints based on endpoint template in JSON config.
    Supports path parameters (e.g., {species}, {id}) and query parameters.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = tool_config.get("endpoint", "")
        self.param_schema = tool_config.get("parameter", {}).get("properties", {})
        self.required_params = tool_config.get("parameter", {}).get("required", [])
        # Allow per-tool timeout override via JSON config
        self.timeout = int(tool_config.get("timeout", 30))

    def _build_url(self, arguments: dict) -> str:
        """
        Combines endpoint_template (containing {xxx}) with path parameters
        from arguments.
        For example endpoint_template="/lookup/id/{id}",
        arguments={"id":"ENSG00000139618"}
        → Returns "https://rest.ensembl.org/lookup/id/ENSG00000139618"
        """
        url_path = self.endpoint_template
        # Find all {xxx} placeholders and replace with values from arguments
        for key in re.findall(r"\{([^{}]+)\}", self.endpoint_template):
            if key not in arguments:
                raise ValueError(f"Missing path parameter '{key}'")
            url_path = url_path.replace(f"{{{key}}}", str(arguments[key]))
        return ENSEMBL_BASE_URL + url_path

    def run(self, arguments: dict):
        # 0. Apply schema defaults and parameter aliases for path params
        schema_props = self.tool_config.get("parameter", {}).get("properties", {})
        # Fix-R15C-4: remember which params the caller actually supplied
        # (before default-injection below) so the stable-ID branch can tell
        # "user explicitly asked for homo_sapiens" apart from "species was
        # silently defaulted to homo_sapiens because it's a path placeholder
        # for the /lookup/symbol/{species}/{gene_id} route". Ensembl stable
        # IDs (ENSG.../ENSBTAG.../etc.) are already species-specific, so
        # /lookup/id/{gene_id} needs no species filter -- but forwarding an
        # auto-defaulted species=homo_sapiens there makes Ensembl reject any
        # non-human stable ID with a misleading "ID not found" (confirmed
        # live for bovine ENSBTAG00000026356: works with no species param or
        # species=cow, HTTP 400 "not found" with species=homo_sapiens).
        explicitly_provided = set(arguments.keys())
        arguments = dict(arguments)
        # Inject schema defaults for any missing path parameters
        for path_key in re.findall(r"\{([^{}]+)\}", self.endpoint_template):
            if path_key not in arguments and path_key in schema_props:
                default_val = schema_props[path_key].get("default")
                if default_val is not None:
                    arguments[path_key] = default_val
        # Accept 'variant_id' as alias for 'id' (variation endpoints)
        if "id" not in arguments and arguments.get("variant_id"):
            arguments["id"] = arguments["variant_id"]

        # 1. Validate required parameters
        for required_param in self.required_params:
            if required_param not in arguments:
                return {
                    "status": "error",
                    "error": f"Parameter '{required_param}' is required.",
                }

        # 2. Build URL, replace {xxx} placeholders
        try:
            url = self._build_url(arguments)
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        # 3. Find remaining arguments besides path parameters
        # as query parameters
        path_keys = re.findall(r"\{([^{}]+)\}", self.endpoint_template)
        query_params = {}
        for k, v in arguments.items():
            if k not in path_keys and v is not None:
                query_params[k] = v

        # Ensembl's /sequence/id endpoint calls its protein-sequence option
        # "protein", not "peptide" -- confirmed live: type=peptide -> HTTP
        # 400 "The type 'peptide' is not understood by this service" for
        # every input, making protein sequence retrieval impossible via this
        # tool. "peptide" is kept as an accepted schema value (it's the
        # intuitive guess) and silently normalized here rather than removed,
        # so existing callers using either name both work.
        if (
            "/sequence/id" in self.endpoint_template
            and query_params.get("type") == "peptide"
        ):
            query_params["type"] = "protein"

        # 4. Special handling for certain endpoints
        # Lookup by symbol needs special routing - handle both stable IDs
        # and symbols.
        if "/lookup/symbol" in self.endpoint_template or "gene_id" in arguments:
            gene_id = arguments.get("gene_id", "")
            if gene_id:
                # Check if it's a stable ID (ENSG, ENST, etc.)
                gene_id_pattern = re.compile(r"^ENS[A-Z]*[0-9]+$", re.IGNORECASE)
                if gene_id_pattern.match(gene_id):
                    # Use lookup/id endpoint for stable IDs (without expand
                    # to avoid timeouts).
                    url = f"{ENSEMBL_BASE_URL}/lookup/id/{gene_id}"
                    # Don't use expand=1 by default to avoid timeouts
                    query_params = {}
                    # Only forward species if the caller explicitly passed
                    # it -- not when it was auto-defaulted for the (unused,
                    # for stable IDs) /lookup/symbol/{species}/... route.
                    if "species" in arguments and "species" in explicitly_provided:
                        query_params["species"] = arguments["species"]
                    if "expand" in arguments:
                        query_params["expand"] = arguments["expand"]
                else:
                    # Use lookup/symbol endpoint for gene symbols
                    species = arguments.get("species", "homo_sapiens")
                    url = f"{ENSEMBL_BASE_URL}/lookup/symbol/{species}/{gene_id}"
                    # Don't use expand=1 by default
                    query_params = {}
                    if "expand" in arguments:
                        query_params["expand"] = arguments["expand"]

        # Handle overlap/region endpoint - ensure feature parameter is passed.
        # Different overlap/region tools mean different things by "default"
        # (e.g. ensembl_get_structural_variants defaults to
        # "structural_variation", ensembl_get_overlap_features defaults to
        # "gene") — use each tool's own schema default instead of hardcoding
        # "variation" for all of them, which silently returned SNP data from
        # tools that promise structural variants or genes.
        if (
            "/overlap/region" in self.endpoint_template
            and "feature" not in query_params
        ):
            schema_default = schema_props.get("feature", {}).get("default")
            query_params["feature"] = schema_default or "variation"

        # 5. Make HTTP request (with small retry for transient failures)
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ToolUniverse/1.0",
            }
            response = request_with_retry(
                requests,
                "GET",
                url,
                params=query_params,
                headers=headers,
                timeout=self.timeout,
                max_attempts=3,
                backoff_seconds=0.5,
            )
            response.raise_for_status()

            data = response.json()
            return {
                "status": "success",
                "data": data,
                "url": url,
                "content_type": response.headers.get(
                    "content-type", "application/json"
                ),
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (f"Ensembl API request timed out after {self.timeout}s"),
                "url": url,
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": (
                    f"Ensembl API returned HTTP {e.response.status_code}: "
                    f"{e.response.text[:200]}"
                ),
                "url": url,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Ensembl API request failed: {str(e)}",
                "url": url,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url,
            }


# Legacy tool classes for backward compatibility
# These are kept for tools that might reference them directly
# New tools should use EnsemblRESTTool with endpoint templates


@register_tool("EnsemblLookupGene")
class EnsemblLookupGene(EnsemblRESTTool):
    """
    Legacy: Lookup gene information by ID or symbol.
    Use EnsemblRESTTool with endpoint='/lookup/id/{id}' instead.
    """

    def __init__(self, tool_config):
        # Convert to generic pattern
        tool_config["endpoint"] = "/lookup/id/{id}"
        super().__init__(tool_config)


@register_tool("EnsemblGetSequence")
class EnsemblGetSequence(EnsemblRESTTool):
    """
    Legacy: Get DNA or protein sequences.
    Use EnsemblRESTTool with endpoint='/sequence/id/{id}' instead.
    """

    def __init__(self, tool_config):
        # Convert to generic pattern
        tool_config["endpoint"] = "/sequence/id/{id}"
        super().__init__(tool_config)


@register_tool("EnsemblGetVariants")
class EnsemblGetVariants(EnsemblRESTTool):
    """
    Legacy: Get variant information.
    Use EnsemblRESTTool with endpoint='/overlap/region/{species}/{region}'
    instead.
    """

    def __init__(self, tool_config):
        # Convert to generic pattern
        tool_config["endpoint"] = "/overlap/region/{species}/{region}"
        super().__init__(tool_config)
