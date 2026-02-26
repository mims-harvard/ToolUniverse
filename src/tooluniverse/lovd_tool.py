"""
LOVD (Leiden Open Variation Database) API tool for ToolUniverse.

LOVD is the world's largest open-source database system for DNA variants,
used by over 23,000 gene databases. The shared installation at
databases.lovd.nl/shared hosts curated variant data from gene-specific
databases including BRCA, TP53, and many other clinically relevant genes.

API: https://databases.lovd.nl/shared/api/rest.php/
Format: Atom XML by default, JSON with ?format=application/json
No authentication required.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool

LOVD_BASE_URL = "https://databases.lovd.nl/shared/api/rest.php"


@register_tool("LOVDTool")
class LOVDTool(BaseTool):
    """
    Tool for querying LOVD (Leiden Open Variation Database) REST API.

    LOVD provides curated variant data including:
    - Gene information (symbol, chromosomal location, RefSeq, curators)
    - Variant details (DNA/RNA/protein notation, genomic position)
    - Variant search by DBID or HGVS DNA notation

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "get_gene")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LOVD API call."""
        operation = self.operation

        if operation == "get_gene":
            return self._get_gene(arguments)
        elif operation == "get_variants":
            return self._get_variants(arguments)
        elif operation == "search_variants":
            return self._search_variants(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _make_request(self, url: str, params: dict = None) -> requests.Response:
        """Make a GET request with JSON format parameter."""
        if params is None:
            params = {}
        params["format"] = "application/json"
        response = requests.get(url, params=params, timeout=self.timeout)
        return response

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene information from LOVD by gene symbol.

        Returns gene details including HGNC ID, Entrez ID, chromosome location,
        RefSeq transcripts, and curation information.
        """
        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        gene_symbol = gene_symbol.strip().upper()
        url = f"{LOVD_BASE_URL}/genes/{gene_symbol}"

        try:
            response = self._make_request(url)

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found in LOVD",
                }

            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": data,
            }
        except requests.RequestException as e:
            return {"status": "error", "error": f"LOVD API request failed: {str(e)}"}

    def _get_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get variants for a gene from LOVD.

        Returns all curated variants including DNA/RNA/protein notation,
        genomic positions, and reporting counts. Use search_variants for
        filtered queries.
        """
        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        gene_symbol = gene_symbol.strip().upper()
        url = f"{LOVD_BASE_URL}/variants/{gene_symbol}"

        try:
            response = self._make_request(url)

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found in LOVD",
                }

            response.raise_for_status()
            data = response.json()

            # Warn if large result set
            result = {
                "status": "success",
                "data": data,
            }
            if isinstance(data, list):
                result["total_variants"] = len(data)

            return result
        except requests.RequestException as e:
            return {"status": "error", "error": f"LOVD API request failed: {str(e)}"}

    def _search_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search variants in LOVD by DBID or DNA notation.

        Supports searching by:
        - Variant DBID (e.g., TP53_010464)
        - DNA notation without RefSeq prefix (e.g., c.*2609C>A)
        """
        gene_symbol = arguments.get("gene_symbol")
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol is required"}

        gene_symbol = gene_symbol.strip().upper()
        dbid = arguments.get("variant_dbid")
        dna_notation = arguments.get("dna_notation")

        if not dbid and not dna_notation:
            return {
                "status": "error",
                "error": "Either variant_dbid or dna_notation is required",
            }

        url = f"{LOVD_BASE_URL}/variants/{gene_symbol}"

        # Build search parameters
        search_params = {}
        if dbid:
            search_params["search_Variant/DBID"] = dbid
        elif dna_notation:
            # LOVD expects notation without RefSeq prefix (e.g., c.742C>T)
            search_params["search_Variant/DNA"] = dna_notation

        try:
            response = self._make_request(url, params=search_params)

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found in LOVD",
                }

            response.raise_for_status()
            data = response.json()

            result = {
                "status": "success",
                "data": data,
            }
            if isinstance(data, list):
                result["matches"] = len(data)

            return result
        except requests.RequestException as e:
            return {"status": "error", "error": f"LOVD API request failed: {str(e)}"}
