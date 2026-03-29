# ctd_tool.py
"""
CTD (Comparative Toxicogenomics Database) REST API tool for ToolUniverse.

CTD is a curated database that advances understanding about how environmental
exposures affect human health. It provides manually curated interactions between
chemicals, genes, phenotypes, diseases, and exposure data.

API: https://ctdbase.org/tools/batchQuery.go
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CTD_BASE_URL = "https://ctdbase.org/tools/batchQuery.go"


@register_tool("CTDTool")
class CTDTool(BaseTool):
    """
    Tool for querying the Comparative Toxicogenomics Database (CTD).

    CTD curates chemical-gene, chemical-disease, and gene-disease relationships
    from peer-reviewed literature. Supports queries by chemical names, gene
    symbols, disease names, or their standard identifiers.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.input_type = tool_config.get("fields", {}).get("input_type", "chem")
        self.report_type = tool_config.get("fields", {}).get(
            "report_type", "genes_curated"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CTD batch query API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CTD API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to CTD API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"CTD API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying CTD: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a CTD batch query and return structured results."""
        input_terms = (
            arguments.get("input_terms")
            or arguments.get("query")
            or arguments.get("gene_symbol")
            or arguments.get("chemical_name")
            or arguments.get("disease_name")
            or ""
        )
        if not input_terms:
            return {"status": "error", "error": "input_terms parameter is required"}

        # Allow overriding input_type and report_type from arguments
        input_type = arguments.get("input_type", self.input_type)
        report_type = arguments.get("report_type", self.report_type)

        # Feature-31B-03: CTD uses mitochondrial gene names without "MT-" prefix
        # (e.g., "ND5" not "MT-ND5"). Strip prefix for gene queries.
        normalized_terms = input_terms
        if input_type == "gene" and input_terms.upper().startswith("MT-"):
            normalized_terms = input_terms[3:]

        params = {
            "inputType": input_type,
            "inputTerms": normalized_terms,
            "report": report_type,
            "format": "json",
        }

        response = requests.get(CTD_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        raw_text = response.text.strip()

        if not raw_text or raw_text == "[]":
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "total_results": 0,
                    "input_type": input_type,
                    "report_type": report_type,
                    "query": input_terms,
                },
            }

        content_type = response.headers.get("content-type", "")
        try:
            data = response.json()
        except ValueError:
            snippet = raw_text[:200]
            is_html = "text/html" in content_type or raw_text.lstrip().startswith("<")
            return {
                "status": "error",
                "error": "CTD API returned non-JSON response",
                "content_type": content_type,
                "response_snippet": snippet,
                "retryable": is_html,
                "suggestion": (
                    "CTD may be under maintenance or rate-limiting. "
                    "Check https://ctdbase.org for status. "
                    "Retry in a few minutes."
                    if is_html
                    else "Response was truncated or malformed. Retry the request."
                ),
            }

        metadata = {
            "input_type": input_type,
            "report_type": report_type,
            "query": input_terms,
        }
        if normalized_terms != input_terms:
            metadata["normalized_query"] = normalized_terms
            metadata["note"] = (
                f"CTD uses '{normalized_terms}' instead of '{input_terms}' "
                "for mitochondrial genes."
            )

        if isinstance(data, (list, dict)):
            metadata["total_results"] = len(data) if isinstance(data, list) else 1
            return {"status": "success", "data": data, "metadata": metadata}
        return {
            "status": "error",
            "error": f"Unexpected CTD response type: {type(data).__name__}",
        }
