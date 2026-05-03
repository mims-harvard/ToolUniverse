"""STRING Database REST API Tool for protein-protein interaction data."""

import requests
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool

STRING_BASE_URL = "https://string-db.org/api"


@register_tool("STRINGRESTTool")
class STRINGRESTTool(BaseTool):
    """STRING Database REST API tool.
    Generic wrapper for STRING API endpoints defined in ppi_tools.json.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        self.endpoint_template: str = fields.get("endpoint", "/tsv/network")
        self.required: List[str] = parameter.get("required", [])
        self.output_format: str = fields.get("return_format", "TSV")

    def _build_url(self) -> str:
        """Build URL for STRING API request."""
        return STRING_BASE_URL + self.endpoint_template

    def _build_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for STRING API request."""
        params = {}

        # Map protein IDs to STRING format
        if "protein_ids" in arguments:
            protein_ids = arguments["protein_ids"]
            if isinstance(protein_ids, list):
                params["identifiers"] = "\r".join(protein_ids)
            else:
                params["identifiers"] = str(protein_ids)

        # Add other parameters
        if "species" in arguments:
            params["species"] = arguments["species"]
        if "confidence_score" in arguments:
            params["required_score"] = int(arguments["confidence_score"] * 1000)
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "network_type" in arguments:
            params["network_type"] = arguments["network_type"]

        # Additional parameters for other endpoints
        if "caller_identity" in arguments:
            params["caller_identity"] = arguments["caller_identity"]
        if "echo_query" in arguments:
            params["echo_query"] = arguments["echo_query"]
        if "add_nodes" in arguments:
            params["add_nodes"] = arguments["add_nodes"]
        if "category" in arguments:
            params["category"] = arguments["category"]

        return params

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a GET request and handle common errors."""
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            if self.output_format == "TSV":
                return self._parse_tsv_response(response.text)
            if self.output_format == "JSON":
                return response.json()

            try:
                return response.json()
            except (ValueError, KeyError):
                return self._parse_tsv_response(response.text)

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _parse_tsv_response(self, text: str) -> Dict[str, Any]:
        """Parse TSV response from STRING API."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return {"data": [], "error": "No data returned"}

        header = lines[0].split("\t")
        data = [
            dict(zip(header, line.split("\t"))) for line in lines[1:] if line.strip()
        ]

        return {"data": data, "header": header}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        for param in self.required:
            if param not in arguments:
                error_msg = f"Missing required parameter: {param}"
                return {
                    "status": "error",
                    "data": {"error": error_msg},
                    "error": error_msg,
                }

        url = self._build_url()
        params = self._build_params(arguments)
        api_response = self._make_request(url, params)

        if "error" in api_response:
            return {
                "status": "error",
                "data": api_response,
                "error": api_response.get("error"),
            }

        # Feature-79B: STRING /json/enrichment ignores `category` param server-side.
        # Apply client-side filter when category is specified.
        category_filter = arguments.get("category")
        if category_filter:
            if isinstance(api_response, list):
                api_response = [
                    r for r in api_response if r.get("category") == category_filter
                ]
            elif isinstance(api_response, dict):
                data_list = api_response.get("data", [])
                if isinstance(data_list, list):
                    api_response["data"] = [
                        r for r in data_list if r.get("category") == category_filter
                    ]

        # Unwrap TSV parsed responses to avoid double-nesting
        # _parse_tsv_response returns {"data": [...], "header": [...]}
        # Without unwrapping, result would be {"data": {"data": [...], "header": [...]}}
        if (
            isinstance(api_response, dict)
            and "data" in api_response
            and "header" in api_response
        ):
            return {
                "status": "success",
                "data": api_response["data"],
                "metadata": {"columns": api_response["header"]},
            }
        return {"status": "success", "data": api_response}
