# metabolomics_workbench_tool.py
"""
Metabolomics Workbench API tool for ToolUniverse.

Metabolomics Workbench is a comprehensive data repository for metabolomics
data, providing access to metabolite structures, study metadata, and
experimental results.

API Documentation: https://www.metabolomicsworkbench.org/tools/mw_rest.php
"""

import requests
from typing import Dict, Any
from urllib.parse import quote
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Metabolomics Workbench REST API
MWBENCH_BASE_URL = "https://www.metabolomicsworkbench.org/rest"


@register_tool("MetabolomicsWorkbenchTool")
class MetabolomicsWorkbenchTool(BaseTool):
    """
    Tool for querying Metabolomics Workbench REST API.

    Metabolomics Workbench provides metabolomics data including:
    - Study metadata and experimental results
    - Compound/metabolite information and structures
    - RefMet standardized nomenclature
    - Mass spectrometry data searches

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get the context type from config (study, compound, refmet, gene, protein, moverz, exactmass)
        self.context = tool_config.get("fields", {}).get("context", "compound")
        self.output_format = tool_config.get("fields", {}).get("output_format", "json")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Metabolomics Workbench API call."""
        # Resolve compound_name/name aliases to input_value
        if "input_value" not in arguments:
            for alias in ("compound_name", "name"):
                if alias in arguments:
                    arguments["input_value"] = arguments.pop(alias)
                    break

        context = self.context

        try:
            if context == "study":
                return self._query_study(arguments)
            elif context == "compound":
                return self._query_compound(arguments)
            elif context == "refmet":
                return self._query_refmet(arguments)
            elif context == "moverz":
                return self._search_moverz(arguments)
            elif context == "exactmass":
                return self._search_exactmass(arguments)
            else:
                return {"status": "error", "error": f"Unknown context: {context}"}
        except Exception as e:
            raise self.handle_error(e)

    def _make_request(self, sub_path: str) -> Dict[str, Any]:
        """Central method to handle API requests and response validation."""
        # Ensure /json is appended to the URL
        if not sub_path.endswith("/json"):
            url = f"{MWBENCH_BASE_URL}/{sub_path.strip('/')}/json"
        else:
            url = f"{MWBENCH_BASE_URL}/{sub_path.strip('/')}"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # The API sometimes returns "null" as a string or an empty string with 200 OK
            raw_text = response.text.strip()
            if not raw_text or raw_text.lower() == "null" or raw_text == '""':
                return {
                    "status": "success",
                    "data": [],
                    "message": "No results found. RefMet requires exact metabolite names "
                    "(e.g., 'Cholic acid' not 'bile acid', 'Cer(d18:1/16:0)' not 'ceramide'). "
                    "Try a specific compound name or use ChEBI_search for class-level terms.",
                }

            try:
                data = response.json()
                # Check for API-level error status
                if isinstance(data, dict) and data.get("status") == "error":
                    return {
                        "status": "error",
                        "error": data.get("message", "API returned an error status"),
                    }

                # Convert exactmass from string to number if present
                data = self._normalize_numeric_fields(data)

                # Feature-79A-001: Add guidance when RefMet returns empty array
                if isinstance(data, list) and len(data) == 0:
                    return {
                        "status": "success",
                        "data": [],
                        "message": "No results found. RefMet requires exact metabolite names "
                        "(e.g., 'Cholic acid' not 'bile acid', 'Cer(d18:1/16:0)' not 'ceramide'). "
                        "Try a specific compound name or use ChEBI_search for class-level terms.",
                    }

                return {"status": "success", "data": data}
            except ValueError:
                # Return as text if not JSON (though we requested JSON)
                return {"status": "success", "data": response.text}

        except requests.RequestException as e:
            raise self.handle_error(e)

    def _normalize_numeric_fields(self, data: Any) -> Any:
        """Convert numeric string fields to actual numbers."""
        if isinstance(data, dict):
            # Convert exactmass from string to float
            if "exactmass" in data and isinstance(data["exactmass"], str):
                try:
                    data["exactmass"] = float(data["exactmass"])
                except (ValueError, TypeError):
                    pass
            # Recursively process nested dicts
            return {k: self._normalize_numeric_fields(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._normalize_numeric_fields(item) for item in data]
        return data

    def _query_study(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query study metadata."""
        study_id = arguments.get("study_id", "")
        output_item = arguments.get("output_item", "summary")
        if not study_id:
            return {"status": "error", "error": "study_id parameter is required"}
        return self._make_request(f"study/study_id/{study_id}/{output_item}")

    def _query_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query compound information."""
        input_item = self.tool_config.get("fields", {}).get("input_item", "formula")
        input_value = arguments.get("input_value", "")
        output_item = arguments.get("output_item", "all")
        if not input_value:
            return {"status": "error", "error": "input_value parameter is required"}
        return self._make_request(f"compound/{input_item}/{input_value}/{output_item}")

    def _query_refmet(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Query RefMet nomenclature."""
        input_item = self.tool_config.get("fields", {}).get("input_item", "name")
        input_value = arguments.get("input_value", "")
        output_item = arguments.get("output_item", "all")
        if not input_value:
            return {"status": "error", "error": "input_value parameter is required"}
        return self._make_request(f"refmet/{input_item}/{input_value}/{output_item}")

    def _search_moverz(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search by m/z value. Requires database as first URL path segment."""
        mz_value = arguments.get("mz_value")
        adduct = arguments.get("adduct", "M+H")
        tolerance = arguments.get("tolerance", 0.1)
        database = arguments.get("database", "MB")  # MB, LIPIDS, or REFMET
        if mz_value is None:
            return {"status": "error", "error": "mz_value parameter is required"}
        # URL-encode adduct: '+' in 'M+H' must be %2B or the server drops the connection
        encoded_adduct = quote(str(adduct), safe="")
        return self._make_request(
            f"moverz/{database}/{mz_value}/{encoded_adduct}/{tolerance}"
        )

    def _search_exactmass(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search by exact mass using moverz endpoint with neutral adduct."""
        mass_value = arguments.get("mass_value")
        tolerance = arguments.get("tolerance", 0.1)
        if mass_value is None:
            return {"status": "error", "error": "mass_value parameter is required"}
        # exactmass endpoint is non-functional; use moverz/REFMET with neutral adduct M
        return self._make_request(f"moverz/REFMET/{mass_value}/M/{tolerance}")
