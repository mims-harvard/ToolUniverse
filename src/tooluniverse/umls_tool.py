import os
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

UMLS_BASE_URL = "https://uts-ws.nlm.nih.gov/rest"


@register_tool("UMLSRESTTool")
class UMLSRESTTool(BaseTool):
    """Base class for UMLS REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint_template = fields.get("endpoint", "")
        self.base_url = fields.get("base_url", UMLS_BASE_URL)
        self.default_sabs = fields.get("sabs")

    def _get_api_key(self) -> Optional[str]:
        """Get UMLS API key from environment variable."""
        api_key = os.getenv("UMLS_API_KEY")
        if not api_key:
            return None
        return api_key

    def _build_url(self, arguments: Dict[str, Any]) -> str:
        """Build the full URL from endpoint template and arguments."""
        endpoint = self.endpoint_template

        # Replace {cui} placeholder
        if "{cui}" in endpoint:
            cui = arguments.get("cui", "")
            endpoint = endpoint.replace("{cui}", cui)

        return f"{self.base_url}{endpoint}"

    def _make_request(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to UMLS API."""
        api_key = self._get_api_key()
        if not api_key:
            return {
                "status": "error",
                "error": (
                    "UMLS API key required. "
                    "Please set UMLS_API_KEY environment variable. "
                    "Register for a free API key at: "
                    "https://uts.nlm.nih.gov/uts/"
                ),
            }

        url = self._build_url(arguments)

        # Build query parameters
        params = {"apiKey": api_key}

        # Handle search query
        if "query" in arguments:
            params["string"] = arguments["query"]

        # Handle source abbreviations
        if "sabs" in arguments and arguments["sabs"]:
            params["sabs"] = arguments["sabs"]
        elif "version" in arguments:
            # For ICD tools, use version parameter
            params["sabs"] = arguments["version"]
        elif self.default_sabs:
            params["sabs"] = self.default_sabs

        # Handle pagination
        if "pageNumber" in arguments:
            params["pageNumber"] = arguments["pageNumber"]
        if "pageSize" in arguments:
            params["pageSize"] = min(arguments["pageSize"], 25)  # Cap at 25

        # Handle CUI for content endpoint
        if "cui" in arguments:
            # CUI is already in URL path, but may need additional params
            pass

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "UMLS (Unified Medical Language System)",
                    "endpoint": url,
                    "query": {k: v for k, v in params.items() if k != "apiKey"},
                    "note": (
                        "UMLS provides access to multiple medical terminologies. "
                        "Register for free API key at: https://uts.nlm.nih.gov/uts/"
                    ),
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except ValueError as e:
            return {"status": "error", "error": f"Failed to parse JSON: {str(e)}"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(arguments)
