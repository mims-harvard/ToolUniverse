"""
Mutalyzer API tool for ToolUniverse.

Mutalyzer is a suite of programs for HGVS variant nomenclature checking,
normalization, and coordinate conversion. It validates variant descriptions
against reference sequences and provides protein-level predictions.

API: https://mutalyzer.nl/api
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MUTALYZER_BASE = "https://mutalyzer.nl/api"


@register_tool("MutalyzerTool")
class MutalyzerTool(BaseTool):
    """
    Tool for HGVS variant nomenclature validation and normalization
    using the Mutalyzer API.

    Supports: normalize (validate + predict protein), back_translate
    (protein to DNA variants), description_to_model (parse HGVS to
    structured model).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "normalize"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Mutalyzer API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Mutalyzer API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Mutalyzer API. Check network connectivity.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Mutalyzer: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate Mutalyzer endpoint."""
        if self.endpoint_type == "normalize":
            return self._normalize(arguments)
        elif self.endpoint_type == "back_translate":
            return self._back_translate(arguments)
        elif self.endpoint_type == "description_to_model":
            return self._description_to_model(arguments)
        return {
            "status": "error",
            "error": f"Unknown endpoint type: {self.endpoint_type}",
        }

    def _normalize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize an HGVS variant description."""
        variant = arguments.get("variant", "")
        if not variant:
            return {"status": "error", "error": "variant parameter is required"}

        url = f"{MUTALYZER_BASE}/normalize/{variant}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        result = {
            "input_description": data.get("input_description"),
            "corrected_description": data.get("corrected_description"),
            "normalized_description": data.get("normalized_description"),
            "gene_id": data.get("gene_id"),
        }

        # Extract protein prediction if available
        protein = data.get("protein")
        if protein:
            result["protein"] = {
                "description": protein.get("description"),
                "reference_sequence": protein.get("reference"),
                "predicted_sequence": protein.get("predicted"),
            }

        # Extract RNA description if available
        rna = data.get("rna")
        if rna:
            result["rna_description"] = rna.get("description")

        # Extract errors and infos
        custom = data.get("custom", {})
        errors = custom.get("errors", []) if isinstance(custom, dict) else []
        if errors:
            result["errors"] = [
                {"code": e.get("code"), "details": e.get("details")} for e in errors
            ]

        infos = data.get("infos", [])
        if infos:
            result["infos"] = infos

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "Mutalyzer",
                "api_version": "3",
                "query_variant": variant,
            },
        }

    def _back_translate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a protein variant description to possible DNA-level variants."""
        variant = arguments.get("variant", "")
        if not variant:
            return {"status": "error", "error": "variant parameter is required"}

        url = f"{MUTALYZER_BASE}/back_translate/{variant}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # API returns a list of possible DNA-level descriptions
        descriptions = data if isinstance(data, list) else [data]

        return {
            "status": "success",
            "data": {
                "input_protein_variant": variant,
                "dna_descriptions": descriptions,
                "count": len(descriptions),
            },
            "metadata": {
                "source": "Mutalyzer",
                "api_version": "3",
                "query_variant": variant,
            },
        }

    def _description_to_model(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Parse an HGVS description into a structured model."""
        variant = arguments.get("variant", "")
        if not variant:
            return {"status": "error", "error": "variant parameter is required"}

        url = f"{MUTALYZER_BASE}/description_to_model/{variant}"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        return {
            "status": "success",
            "data": {
                "input_description": variant,
                "model": data,
            },
            "metadata": {
                "source": "Mutalyzer",
                "api_version": "3",
                "query_variant": variant,
            },
        }
