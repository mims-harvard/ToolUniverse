"""
eMolecules tool for ToolUniverse.

eMolecules is a chemical vendor aggregator that provides access to
millions of compounds from hundreds of suppliers.

Website: https://www.emolecules.com/
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# eMolecules base URL
EMOLECULES_BASE_URL = "https://www.emolecules.com"
EMOLECULES_API_URL = "https://api.emolecules.com/v1"


@register_tool("EMoleculesTool")
class EMoleculesTool(BaseTool):
    """
    Tool for searching eMolecules vendor aggregator.

    eMolecules provides:
    - Multi-vendor compound search
    - Pricing and availability
    - Structure search
    - Building block sourcing

    Note: Full API access may require registration.
    Basic search functionality available without API key.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute eMolecules query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search":
            return self._search(arguments)
        elif operation == "search_smiles":
            return self._search_smiles(arguments)
        elif operation == "get_vendors":
            return self._get_vendors(arguments)
        elif operation == "get_compound":
            return self._get_compound(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search, search_smiles, get_vendors, get_compound",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search eMolecules by keyword or compound name.

        Note: eMolecules does not provide a public API. This tool returns
        search URLs for the eMolecules web interface.

        Args:
            arguments: Dict containing:
                - query: Search query
                - max_results: Maximum results (default 20)
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        import urllib.parse

        encoded_query = urllib.parse.quote(query)

        return {
            "status": "success",
            "data": {
                "query": query,
                "search_url": f"{EMOLECULES_BASE_URL}/search/?q={encoded_query}",
                "note": "eMolecules aggregates compounds from 200+ suppliers including Sigma-Aldrich, TCI, Enamine, ChemBridge, and more.",
            },
            "metadata": {
                "source": "eMolecules",
                "note": "eMolecules does not provide a public API. Visit search_url for results.",
            },
        }

    def _search_smiles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search eMolecules by SMILES structure.

        Note: eMolecules does not provide a public API. This tool returns
        search URLs for the eMolecules web interface.

        Args:
            arguments: Dict containing:
                - smiles: SMILES string
                - search_type: exact, substructure, similarity (default: similarity)
        """
        smiles = arguments.get("smiles", "")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        search_type = arguments.get("search_type", "similarity")

        import urllib.parse

        encoded_smiles = urllib.parse.quote(smiles)
        search_type_param = {"exact": "1", "substructure": "2", "similarity": "3"}.get(
            search_type, "3"
        )

        return {
            "status": "success",
            "data": {
                "query_smiles": smiles,
                "search_type": search_type,
                "search_url": f"{EMOLECULES_BASE_URL}/search/?q={encoded_smiles}&t={search_type_param}",
                "note": "Visit search_url to perform structure search on eMolecules",
            },
            "metadata": {
                "source": "eMolecules",
                "note": "eMolecules does not provide a public API.",
            },
        }

    def _get_vendors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of vendors for a compound.

        Note: eMolecules does not provide a public API. This tool returns
        search URLs for vendor lookup on the eMolecules web interface.

        Args:
            arguments: Dict containing:
                - smiles: SMILES string
        """
        smiles = arguments.get("smiles", "")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        import urllib.parse

        encoded_smiles = urllib.parse.quote(smiles)

        return {
            "status": "success",
            "data": {
                "query_smiles": smiles,
                "search_url": f"{EMOLECULES_BASE_URL}/search/?q={encoded_smiles}&t=1",
                "vendor_info": "eMolecules aggregates from 200+ suppliers including Sigma-Aldrich, TCI, Enamine, ChemBridge, Combi-Blocks, and more.",
            },
            "metadata": {
                "source": "eMolecules",
                "note": "eMolecules does not provide a public API. Visit search_url for vendor information.",
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compound details by eMolecules ID.

        Note: eMolecules does not provide a public API. This tool returns
        URLs for viewing compound details on the eMolecules web interface.

        Args:
            arguments: Dict containing:
                - emol_id: eMolecules compound ID
        """
        emol_id = arguments.get("emol_id", "")
        if not emol_id:
            return {"status": "error", "error": "Missing required parameter: emol_id"}

        return {
            "status": "success",
            "data": {
                "emol_id": emol_id,
                "url": f"{EMOLECULES_BASE_URL}/cgi-bin/more?vid={emol_id}",
                "note": "Visit url to view compound details and vendor pricing",
            },
            "metadata": {
                "source": "eMolecules",
                "emol_id": emol_id,
                "note": "eMolecules does not provide a public API.",
            },
        }
