"""
SAbDab (Structural Antibody Database) tool for ToolUniverse.

SAbDab is a database containing all antibody structures from the PDB,
annotated with CDR sequences, chain pairings, and other structural features.

Website: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# SAbDab base URL
SABDAB_BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab"


@register_tool("SAbDabTool")
class SAbDabTool(BaseTool):
    """
    Tool for querying SAbDab structural antibody database.

    SAbDab provides:
    - Antibody structures from PDB
    - CDR (complementarity-determining region) annotations
    - Heavy/light chain pairing information
    - Antigen binding information

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 60)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SAbDab query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search_structures":
            return self._search_structures(arguments)
        elif operation == "get_structure":
            return self._get_structure(arguments)
        elif operation == "get_summary":
            return self._get_summary(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_structures, get_structure, get_summary",
            }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search SAbDab for antibody structures.

        Args:
            arguments: Dict containing:
                - query: Search query (antigen name, species, etc.)
                - limit: Maximum results
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 50)

        try:
            # SAbDab search endpoint
            response = requests.get(
                f"{SABDAB_BASE_URL}/search/",
                params={"q": query, "limit": limit},
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )

            # SAbDab search endpoint returns HTML, not JSON
            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
                structures = data if isinstance(data, list) else data.get("results", [])
            else:
                return {
                    "status": "error",
                    "error": (
                        "SAbDab search does not provide a JSON API. "
                        f"Use SAbDab_get_structure with a known PDB ID instead, "
                        f"or browse https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab/search/?q={query}"
                    ),
                }

            return {
                "status": "success",
                "data": {
                    "structures": structures,
                    "count": len(structures),
                    "query": query,
                },
                "metadata": {
                    "source": "SAbDab",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get antibody structure details by PDB ID.

        Args:
            arguments: Dict containing:
                - pdb_id: 4-character PDB ID
        """
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {"status": "error", "error": "Missing required parameter: pdb_id"}

        # SAbDab API requires lowercase PDB IDs
        pdb_id_lower = pdb_id.lower()

        try:
            # Use direct PDB download endpoint (Chothia numbering)
            pdb_url = f"{SABDAB_BASE_URL}/pdb/{pdb_id_lower}/"
            response = requests.get(
                pdb_url,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/SAbDab"},
            )

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Structure not found: {pdb_id}. Note: SAbDab may not have all PDB structures.",
                }

            response.raise_for_status()

            # Extract metadata from PDB REMARK lines
            pdb_content = response.text
            metadata = {"pdb_id": pdb_id}

            # Parse REMARK 5 lines which contain SAbDab annotations
            remarks = []
            for line in pdb_content.split("\n"):
                if line.startswith("REMARK   5 PAIRED_"):
                    for part in line.split():
                        if "=" in part:
                            key, val = part.split("=")
                            metadata[key.lower()] = val
                elif line.startswith("REMARK   5 "):
                    remark = line[15:].strip()
                    if remark and remark not in str(remarks):
                        remarks.append(remark)
            if remarks:
                metadata["remarks"] = remarks

            return {
                "status": "success",
                "data": {
                    "pdb_id": pdb_id,
                    "download_url": pdb_url,
                    "structure_url": f"{SABDAB_BASE_URL}/structureviewer/?pdb={pdb_id}",
                    "search_url": f"{SABDAB_BASE_URL}/search/?pdb={pdb_id}",
                    "metadata": metadata,
                    "pdb_size_bytes": len(pdb_content),
                    "pdb_preview": pdb_content[:500]
                    if len(pdb_content) > 500
                    else pdb_content,
                },
                "metadata": {
                    "source": "SAbDab",
                    "note": "PDB file with Chothia numbering available at download_url",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get SAbDab database summary statistics.

        Args:
            arguments: Dict (no required parameters)
        """
        try:
            response = requests.get(
                f"{SABDAB_BASE_URL}/stats/",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "application/json",
                },
            )

            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
            else:
                # Return static info about SAbDab
                data = {
                    "description": "SAbDab - Structural Antibody Database",
                    "content": "All antibody structures from PDB with annotations",
                    "features": [
                        "CDR sequence annotations",
                        "Heavy/light chain pairing",
                        "Antigen information",
                        "Species classification",
                    ],
                    "url": SABDAB_BASE_URL,
                }

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "SAbDab",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
