# stitch_tool.py
"""
STITCH (Search Tool for Interacting Chemicals) API tool for ToolUniverse.

STITCH is a database of known and predicted interactions between
chemicals and proteins, combining data from various sources.

API Documentation: http://stitch.embl.de/
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for STITCH REST API (chemical-protein interactions)
# NOTE: stitch.embl.de API endpoints have moved to string-db.org (same API format)
STITCH_BASE_URL = "https://string-db.org/api"


@register_tool("STITCHTool")
class STITCHTool(BaseTool):
    """
    Tool for querying STITCH database.

    STITCH provides chemical-protein interaction data including:
    - Known drug-target interactions
    - Predicted chemical-protein interactions
    - Interaction scores and evidence
    - Network analysis data

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_interactions"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the STITCH API call."""
        operation = self.operation

        if operation == "get_interactions":
            return self._get_interactions(arguments)
        elif operation == "get_interactors":
            return self._get_interactors(arguments)
        elif operation == "resolve":
            return self._resolve_identifiers(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get chemical-protein interactions.

        Endpoint: GET /json/interactions
        """
        # Accept 'chemical' or 'chemicals' as alias for 'identifiers'
        identifiers = (
            arguments.get("identifiers")
            or arguments.get("chemical")
            or arguments.get("chemicals")
            or []
        )

        if not identifiers:
            return {
                "status": "error",
                "error": "identifiers parameter is required (chemical names or IDs)",
            }

        if isinstance(identifiers, str):
            identifiers = [identifiers]

        # Normalize CID format: CID000002244 → CIDm00002244 (STITCH uses 'm' prefix)
        import re

        def _normalize_cid(id_str):
            m = re.match(r"^CID0*(\d+)$", id_str, re.IGNORECASE)
            if m:
                return f"CIDm{int(m.group(1)):08d}"
            return id_str

        identifiers = [_normalize_cid(i) for i in identifiers]

        params = {
            "identifiers": "%0D".join(identifiers),  # URL-encoded newline separator
            "species": arguments.get("species", 9606),  # Default: human
            "limit": arguments.get("limit", 10),
            "required_score": arguments.get("required_score", 400),  # Medium confidence
        }

        try:
            response = requests.get(
                f"{STITCH_BASE_URL}/json/interactions",
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No interactions found for {identifiers} in STITCH. "
                    "Try using CID identifiers (e.g., 'CIDm00002244' for aspirin) "
                    "or check compound names at http://stitch.embl.de/",
                }
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}

    def _get_interactors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get interaction partners for a chemical or protein.

        Endpoint: GET /json/interactors
        """
        identifiers = arguments.get("identifiers", [])

        if not identifiers:
            return {"status": "error", "error": "identifiers parameter is required"}

        if isinstance(identifiers, str):
            identifiers = [identifiers]

        params = {
            "identifiers": "%0D".join(identifiers),
            "species": arguments.get("species", 9606),
            "limit": arguments.get("limit", 10),
        }

        try:
            response = requests.get(
                f"{STITCH_BASE_URL}/json/network",
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"No interactors found for {identifiers} in STITCH. "
                    "Try using CID identifiers or check compound names at http://stitch.embl.de/",
                }
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}

    def _resolve_identifiers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve chemical/protein names to STITCH identifiers.

        Endpoint: GET /json/resolve
        """
        identifier = arguments.get("identifier", "")

        if not identifier:
            return {"status": "error", "error": "identifier parameter is required"}

        params = {"identifier": identifier, "species": arguments.get("species", 9606)}

        try:
            response = requests.get(
                f"{STITCH_BASE_URL}/json/resolve",
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Identifier '{identifier}' not found in STITCH. "
                    "Try using CID identifiers or check at http://stitch.embl.de/",
                }
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"STITCH API request failed: {str(e)}"}
