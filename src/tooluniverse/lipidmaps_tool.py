# lipidmaps_tool.py
"""
LIPID MAPS Structure Database REST API tool for ToolUniverse.

LIPID MAPS (Lipid Metabolites And Pathways Strategy) is a comprehensive
classification system for lipids that includes lipid structures, genes,
proteins, and mass spectrometry data.

API Documentation: https://lipidmaps.org/resources/rest
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for LIPID MAPS REST API
LIPIDMAPS_BASE_URL = "https://www.lipidmaps.org/rest"


@register_tool("LipidMapsTool")
class LipidMapsTool(BaseTool):
    """
    Tool for querying LIPID MAPS Structure Database REST API.

    LIPID MAPS provides comprehensive lipidomics data including:
    - Lipid structure information (LMSD - LIPID MAPS Structure Database)
    - Lipid-related gene information (LMPD - LIPID MAPS Proteome Database)
    - Lipid-related protein information
    - Mass spectrometry m/z search

    No authentication required. Free for academic/research use.

    URL Pattern: /rest/{context}/{input_item}/{input_value}/{output_item}/{output_format}
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get the context type from config (compound, gene, protein, moverz)
        self.context = tool_config.get("fields", {}).get("context", "compound")
        self.input_item = tool_config.get("fields", {}).get("input_item", "lm_id")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LIPID MAPS API call based on the configured context."""
        context = self.context

        try:
            if context == "compound":
                return self._query_compound(arguments)
            elif context == "gene":
                return self._query_gene(arguments)
            elif context == "protein":
                return self._query_protein(arguments)
            elif context == "moverz":
                return self._search_moverz(arguments)
            else:
                return {"status": "error", "error": f"Unknown context: {context}"}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"LIPID MAPS API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to LIPID MAPS API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"LIPID MAPS API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying LIPID MAPS: {str(e)}",
            }

    def _make_request(self, sub_path: str) -> Dict[str, Any]:
        """Central method to handle API requests and response parsing."""
        url = f"{LIPIDMAPS_BASE_URL}/{sub_path}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        raw_text = response.text.strip()

        # Handle empty or null responses
        if (
            not raw_text
            or raw_text.lower() == "null"
            or raw_text == '""'
            or raw_text == "{}"
        ):
            return {"status": "success", "data": [], "message": "No results found"}

        try:
            data = response.json()

            # LIPID MAPS returns results with Row1, Row2, ... keys for multiple results
            # or a flat dict for single results
            if isinstance(data, dict):
                # Check if it's a multi-row result (Row1, Row2, ...)
                row_keys = [k for k in data.keys() if k.startswith("Row")]
                if row_keys:
                    # Convert Row1, Row2, ... to a list
                    results = [data[k] for k in sorted(row_keys)]
                    return {
                        "status": "success",
                        "data": results,
                        "metadata": {"total_results": len(results)},
                    }
                elif "input" in data or "lm_id" in data or "gene_id" in data:
                    # Single result
                    return {
                        "status": "success",
                        "data": data,
                        "metadata": {"total_results": 1},
                    }
                else:
                    return {"status": "success", "data": data}
            elif isinstance(data, list):
                return {
                    "status": "success",
                    "data": data,
                    "metadata": {"total_results": len(data)},
                }
            else:
                return {"status": "success", "data": data}

        except ValueError:
            # Not JSON - return raw text (some endpoints return TSV)
            return {"status": "success", "data": raw_text}

    def _query_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query compound/lipid information from LMSD."""
        input_value = arguments.get("input_value", "")
        output_item = arguments.get("output_item", "all")
        if not input_value:
            return {"status": "error", "error": "input_value parameter is required"}
        return self._make_request(
            f"compound/{self.input_item}/{input_value}/{output_item}/json"
        )

    def _query_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query lipid-related gene information from LMPD."""
        input_value = arguments.get("input_value", "")
        output_item = arguments.get("output_item", "all")
        if not input_value:
            return {"status": "error", "error": "input_value parameter is required"}
        return self._make_request(
            f"gene/{self.input_item}/{input_value}/{output_item}/json"
        )

    def _query_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query lipid-related protein information from LMPD."""
        input_value = arguments.get("input_value", "")
        output_item = arguments.get("output_item", "all")
        if not input_value:
            return {"status": "error", "error": "input_value parameter is required"}
        return self._make_request(
            f"protein/{self.input_item}/{input_value}/{output_item}/json"
        )

    def _search_moverz(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search lipids by m/z value for mass spectrometry identification."""
        mz_value = arguments.get("mz_value")
        ion_type = arguments.get("ion_type", "M-H")
        tolerance = arguments.get("tolerance", 0.01)
        if mz_value is None:
            return {"status": "error", "error": "mz_value parameter is required"}

        # LIPID MAPS m/z endpoint returns TSV, not JSON
        url = f"{LIPIDMAPS_BASE_URL}/moverz/LIPIDS/{mz_value}/{ion_type}/-/{tolerance}/txt"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        raw_text = response.text.strip()
        if not raw_text:
            return {
                "status": "success",
                "data": [],
                "message": "No lipid matches found",
            }

        # Parse TSV response
        lines = raw_text.split("\n")
        results = []
        headers = None
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t")
            if headers is None:
                headers = parts
            else:
                if len(parts) == len(headers):
                    results.append(dict(zip(headers, parts)))
                else:
                    results.append({"raw": line})

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "query_mz": mz_value,
                "ion_type": ion_type,
                "tolerance": tolerance,
            },
        }
