"""
PDBe (Protein Data Bank in Europe) API Tool

This tool provides access to PDBe API for protein structure metadata,
quality metrics, and structure information.
"""

import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("PDBeAPIRESTTool")
class PDBeAPIRESTTool(BaseTool):
    """
    PDBe API REST tool.
    Generic wrapper for PDBe API endpoints defined in pdbe_api_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/pdbe/api"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            for k, v in args.items():
                # Convert pdb_id to lowercase for PDBe API consistency
                if k == "pdb_id":
                    v = str(v).lower()
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name
        if tool_name == "pdbe_get_entry_summary":
            pdb_id = args.get("pdb_id", "")
            if pdb_id:
                return f"{self.base_url}/pdb/entry/summary/{pdb_id.lower()}"

        elif tool_name == "pdbe_get_entry_quality":
            pdb_id = args.get("pdb_id", "")
            if pdb_id:
                return f"{self.base_url}/validation/summary_quality_scores/entry/{pdb_id.lower()}"

        elif tool_name == "pdbe_get_entry_publications":
            pdb_id = args.get("pdb_id", "")
            if pdb_id:
                return f"{self.base_url}/pdb/entry/publications/{pdb_id.lower()}"

        elif tool_name == "pdbe_get_entry_assemblies":
            pdb_id = args.get("pdb_id", "")
            if pdb_id:
                return f"{self.base_url}/pdb/entry/assemblies/{pdb_id.lower()}"

        elif tool_name == "pdbe_get_entry_secondary_structure":
            pdb_id = args.get("pdb_id", "")
            if pdb_id:
                return f"{self.base_url}/pdb/entry/secondary_structure/{pdb_id.lower()}"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for PDBe API"""
        # PDBe API typically doesn't use query parameters for these endpoints
        return {}

    def _extract_assemblies_from_summary(self, pdb_id: str) -> Optional[Dict[str, Any]]:
        """Extract assemblies data from summary endpoint as fallback"""
        try:
            summary_url = f"{self.base_url}/pdb/entry/summary/{pdb_id.lower()}"
            response = self.session.get(summary_url, timeout=self.timeout)
            response.raise_for_status()
            summary_data = response.json()

            # Extract assemblies from summary
            if pdb_id.lower() in summary_data:
                entry_data = summary_data[pdb_id.lower()]
                if isinstance(entry_data, list) and entry_data:
                    entry = entry_data[0]
                    if isinstance(entry, dict):
                        # Look for assemblies
                        if "assemblies" in entry:
                            assemblies = entry["assemblies"]
                            return {
                                "status": "success",
                                "data": assemblies
                                if isinstance(assemblies, list)
                                else [assemblies],
                                "url": response.url,
                                "count": len(assemblies)
                                if isinstance(assemblies, list)
                                else 1,
                                "note": "Assemblies extracted from summary endpoint (assemblies endpoint not available).",
                                "fallback_used": True,
                            }
                        elif "assembly" in entry:
                            assembly = entry["assembly"]
                            return {
                                "status": "success",
                                "data": [assembly]
                                if isinstance(assembly, dict)
                                else assembly,
                                "url": response.url,
                                "count": 1,
                                "note": "Assembly extracted from summary endpoint (assemblies endpoint not available).",
                                "fallback_used": True,
                            }
        except Exception:
            pass
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe API call"""
        tool_name = self.tool_config.get("name", "")
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)

            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle assemblies endpoint - fallback to summary
            if tool_name == "pdbe_get_entry_assemblies" and response.status_code == 404:
                pdb_id = arguments.get("pdb_id", "")
                if pdb_id:
                    fallback_result = self._extract_assemblies_from_summary(pdb_id)
                    if fallback_result:
                        return fallback_result

            # Handle quality endpoint which may not be available for all entries
            if tool_name == "pdbe_get_entry_quality" and response.status_code == 404:
                pdb_id = arguments.get("pdb_id", "")
                return {
                    "status": "error",
                    "error": f"Validation quality scores not available for PDB entry {pdb_id}.",
                    "url": response.url,
                    "suggestion": "Try pdbe_get_entry_summary or pdbe_get_entry_experiment for experimental quality metrics.",
                }

            response.raise_for_status()
            data = response.json()

            response_data = {
                "status": "success",
                "data": data,
                "url": response.url,
            }

            # Extract count if available
            if isinstance(data, dict):
                pdb_id = arguments.get("pdb_id", "")
                if pdb_id and pdb_id.lower() in data:
                    entry_data = data[pdb_id.lower()]
                    if isinstance(entry_data, list):
                        response_data["count"] = len(entry_data)
                    elif isinstance(entry_data, dict):
                        response_data["count"] = 1

            return response_data

        except requests.exceptions.RequestException as e:
            tool_name = self.tool_config.get("name", "")

            # Handle assemblies endpoint - fallback to summary
            if tool_name == "pdbe_get_entry_assemblies" and "404" in str(e):
                pdb_id = arguments.get("pdb_id", "")
                if pdb_id:
                    fallback_result = self._extract_assemblies_from_summary(pdb_id)
                    if fallback_result:
                        return fallback_result

            return {
                "status": "error",
                "error": f"PDBe API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
