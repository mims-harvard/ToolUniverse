"""
Bioregistry API tool for ToolUniverse.

Bioregistry is a community-curated meta-registry of biological databases,
ontologies, and other resources. It provides a unified way to resolve
identifiers across 2600+ databases.

API: https://bioregistry.io/apidocs/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOREGISTRY_API_URL = "https://bioregistry.io/api"


@register_tool("BioregistryTool")
class BioregistryTool(BaseTool):
    """
    Tool for querying the Bioregistry meta-registry.

    Provides:
    - Identifier resolution across 2600+ databases
    - Registry metadata (prefix, name, pattern, providers)
    - Search across all registered resources
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Bioregistry API call based on operation type."""
        operation = arguments.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "resolve_reference":
            return self._resolve_reference(arguments)
        elif operation == "get_registry":
            return self._get_registry(arguments)
        elif operation == "search_registries":
            return self._search_registries(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: resolve_reference, get_registry, search_registries",
            }

    def _resolve_reference(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a compact identifier (prefix:id) to provider URLs."""
        prefix = arguments.get("prefix", "")
        identifier = arguments.get("identifier", "")
        if not prefix or not identifier:
            return {
                "status": "error",
                "error": "Both 'prefix' and 'identifier' are required (e.g., prefix='uniprot', identifier='P04637')",
            }
        try:
            url = f"{BIOREGISTRY_API_URL}/reference/{prefix}:{identifier}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code}: Could not resolve {prefix}:{identifier}",
                }
            data = resp.json()
            providers = data.get("providers", {})
            return {
                "status": "success",
                "data": {
                    "prefix": prefix,
                    "identifier": identifier,
                    "providers": providers,
                    "provider_count": len(providers),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_registry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific registry/database by prefix."""
        prefix = arguments.get("prefix", "")
        if not prefix:
            return {
                "status": "error",
                "error": "Parameter 'prefix' is required (e.g., 'uniprot', 'chebi', 'go')",
            }
        try:
            url = f"{BIOREGISTRY_API_URL}/registry/{prefix}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Registry prefix '{prefix}' not found. Try search_registries to find the correct prefix.",
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code} from Bioregistry",
                }
            data = resp.json()
            result = {
                "prefix": data.get("prefix", prefix),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "homepage": data.get("homepage", ""),
                "pattern": data.get("pattern", ""),
                "uri_format": data.get("uri_format", ""),
                "example": data.get("example", ""),
                "keywords": data.get("keywords", []),
            }
            if data.get("synonyms"):
                result["synonyms"] = data["synonyms"]
            if data.get("publications"):
                result["publications"] = data["publications"][:5]
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_registries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search across all registered resources."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "Parameter 'query' is required (e.g., 'protein', 'gene ontology')",
            }
        limit = arguments.get("limit", 10)
        try:
            url = f"{BIOREGISTRY_API_URL}/search"
            resp = requests.get(url, params={"q": query}, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code} from Bioregistry search",
                }
            results = resp.json()
            if not isinstance(results, list):
                results = []
            trimmed = []
            for item in results[:limit]:
                if isinstance(item, list) and len(item) >= 1:
                    trimmed.append(
                        {
                            "prefix": item[0],
                            "name": item[1] if len(item) > 1 else "",
                            "description": "",
                        }
                    )
                elif isinstance(item, dict):
                    trimmed.append(
                        {
                            "prefix": item.get("prefix", ""),
                            "name": item.get("name", ""),
                            "description": item.get("description", "")[:200]
                            if item.get("description")
                            else "",
                        }
                    )
                elif isinstance(item, str):
                    trimmed.append({"prefix": item, "name": "", "description": ""})
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "results": trimmed,
                    "total": len(results),
                },
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
