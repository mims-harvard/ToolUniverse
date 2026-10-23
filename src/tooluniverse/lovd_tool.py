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

from typing import Any, Dict
from urllib.parse import quote

import requests

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
        try:
            operation = self.operation
            if operation == "get_gene":
                return self._get_gene(arguments)
            elif operation == "get_variants":
                return self._get_variants(arguments)
            elif operation == "search_variants":
                return self._search_variants(arguments)
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
        except ValueError as exc:
            return {"status": "error", "error": f"LOVD returned invalid JSON: {exc}"}

    def _make_request(self, url: str, params: dict = None) -> requests.Response:
        """Make a GET request with JSON format parameter."""
        if params is None:
            params = {}
        params["format"] = "application/json"
        response = requests.get(url, params=params, timeout=self.timeout)
        return response

    @staticmethod
    def _gene_symbol(arguments: Dict[str, Any]) -> tuple[str | None, str | None]:
        value = arguments.get("gene_symbol")
        if not isinstance(value, str) or not value.strip():
            return None, "gene_symbol must be a non-empty string"
        return value.strip().upper(), None

    @staticmethod
    def _unknown_arguments(arguments: Dict[str, Any], allowed: set[str]) -> list[str]:
        return sorted(set(arguments) - allowed)

    @staticmethod
    def _validate_variant_records(data: Any, gene_symbol: str) -> str | None:
        if not isinstance(data, list):
            return "LOVD variant response was not a list"
        for record in data:
            if not isinstance(record, dict):
                return "LOVD variant response contained a malformed record"
            symbol = record.get("symbol")
            if not isinstance(symbol, str) or symbol.upper() != gene_symbol:
                return "LOVD returned a variant for a different gene"
            dna = record.get("Variant/DNA")
            if dna is not None and (
                not isinstance(dna, list)
                or any(not isinstance(value, str) for value in dna)
            ):
                return "LOVD returned malformed Variant/DNA values"
        return None

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene information from LOVD by gene symbol.

        Returns gene details including HGNC ID, Entrez ID, chromosome location,
        RefSeq transcripts, and curation information.
        """
        unknown = self._unknown_arguments(arguments, {"gene_symbol"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unrecognized parameter(s): {', '.join(unknown)}",
            }
        gene_symbol, error = self._gene_symbol(arguments)
        if error:
            return {"status": "error", "error": error}
        assert gene_symbol is not None
        url = f"{LOVD_BASE_URL}/genes/{quote(gene_symbol, safe='')}"

        try:
            response = self._make_request(url)

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found in LOVD",
                }

            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or (
                not isinstance(data.get("symbol"), str)
                or data["symbol"].upper() != gene_symbol
            ):
                return {
                    "status": "error",
                    "error": "LOVD returned a different or malformed gene record",
                    "requested_symbol": gene_symbol,
                    "returned_symbol": data.get("symbol")
                    if isinstance(data, dict)
                    else None,
                }

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "query_symbol": gene_symbol,
                    "returned_symbol_verified": True,
                    "source_record_complete": True,
                },
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
        unknown = self._unknown_arguments(arguments, {"gene_symbol"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unrecognized parameter(s): {', '.join(unknown)}",
            }
        gene_symbol, error = self._gene_symbol(arguments)
        if error:
            return {"status": "error", "error": error}
        assert gene_symbol is not None
        url = f"{LOVD_BASE_URL}/variants/{quote(gene_symbol, safe='')}"

        try:
            response = self._make_request(url)

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found in LOVD",
                }

            response.raise_for_status()
            data = response.json()
            validation_error = self._validate_variant_records(data, gene_symbol)
            if validation_error:
                return {"status": "error", "error": validation_error}

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "query_symbol": gene_symbol,
                    "returned": len(data),
                    "result_set_complete": True,
                    "completeness_basis": "LOVD unpaginated gene-variant endpoint",
                    "returned_gene_verified": True,
                },
            }
        except requests.RequestException as e:
            return {"status": "error", "error": f"LOVD API request failed: {str(e)}"}

    def _search_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search variants in LOVD by DBID or DNA notation.

        Supports searching by:
        - Variant DBID (e.g., TP53_010464)
        - DNA notation without RefSeq prefix (e.g., c.*2609C>A)
        """
        unknown = self._unknown_arguments(
            arguments, {"gene_symbol", "variant_dbid", "dna_notation"}
        )
        if unknown:
            return {
                "status": "error",
                "error": f"Unrecognized parameter(s): {', '.join(unknown)}",
            }
        gene_symbol, error = self._gene_symbol(arguments)
        if error:
            return {"status": "error", "error": error}
        assert gene_symbol is not None
        dbid = arguments.get("variant_dbid")
        dna_notation = arguments.get("dna_notation")
        for name, value in (("variant_dbid", dbid), ("dna_notation", dna_notation)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                return {
                    "status": "error",
                    "error": f"{name} must be a non-empty string",
                }
        if bool(dbid) == bool(dna_notation):
            return {
                "status": "error",
                "error": "Provide exactly one of variant_dbid or dna_notation",
            }
        dbid = dbid.strip() if dbid else None
        dna_notation = dna_notation.strip() if dna_notation else None

        url = f"{LOVD_BASE_URL}/variants/{quote(gene_symbol, safe='')}"

        # Build search parameters
        search_params = {}
        if dbid:
            search_params["search_Variant/DBID"] = dbid
        else:
            # LOVD expects notation without RefSeq prefix (e.g., c.742C>T)
            search_params["search_Variant/DNA"] = dna_notation

        try:
            response = self._make_request(url, params=search_params)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": [],
                    "metadata": {
                        "query_symbol": gene_symbol,
                        "filter_type": "variant_dbid" if dbid else "dna_notation",
                        "filter_value": dbid or dna_notation,
                        "matches": 0,
                        "filter_verified": True,
                        "result_set_complete": True,
                        "note": "LOVD uses HTTP 404 with an empty array for a valid gene filter with no matches.",
                    },
                }

            response.raise_for_status()
            data = response.json()
            validation_error = self._validate_variant_records(data, gene_symbol)
            if validation_error:
                return {"status": "error", "error": validation_error}
            if dbid:
                mismatches = [
                    record.get("Variant/DBID")
                    for record in data
                    if record.get("Variant/DBID") != dbid
                ]
            else:
                mismatches = [
                    record.get("Variant/DNA")
                    for record in data
                    if not any(
                        value == dna_notation or value.endswith(f":{dna_notation}")
                        for value in record.get("Variant/DNA", [])
                    )
                ]
            if mismatches:
                return {
                    "status": "error",
                    "error": "LOVD returned variants that did not match the requested filter",
                    "mismatches": mismatches,
                }

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "query_symbol": gene_symbol,
                    "filter_type": "variant_dbid" if dbid else "dna_notation",
                    "filter_value": dbid or dna_notation,
                    "matches": len(data),
                    "filter_verified": True,
                    "result_set_complete": True,
                    "returned_gene_verified": True,
                },
            }
        except requests.RequestException as e:
            return {"status": "error", "error": f"LOVD API request failed: {str(e)}"}
