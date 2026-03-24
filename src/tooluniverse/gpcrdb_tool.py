"""
GPCRdb API tool for ToolUniverse.

GPCRdb is a comprehensive database for G protein-coupled receptors (GPCRs),
which are the targets of ~35% of all approved drugs.

API Documentation: https://docs.gpcrdb.org/web_services.html
No authentication required.
"""

import html
import re
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for GPCRdb API
GPCRDB_API_URL = "https://gpcrdb.org/services"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@register_tool("GPCRdbTool")
class GPCRdbTool(BaseTool):
    """
    Tool for querying GPCRdb GPCR database.

    GPCRdb provides:
    - GPCR protein information and classification
    - Structure data for GPCR crystal/cryo-EM structures
    - Ligand binding data
    - Mutation data and effects
    - Sequence alignments

    No authentication required. Free public access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GPCRdb API call based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "get_protein":
            return self._get_protein(arguments)
        elif operation == "list_proteins":
            return self._list_proteins(arguments)
        elif operation == "get_structures":
            return self._get_structures(arguments)
        elif operation == "get_ligands":
            return self._get_ligands(arguments)
        elif operation == "get_mutations":
            return self._get_mutations(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: get_protein, list_proteins, get_structures, get_ligands, get_mutations",
            }

    def _get_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed protein information for a GPCR.

        Args:
            arguments: Dict containing:
                - protein: Protein entry name (e.g., adrb2_human) or UniProt accession
        """
        protein = arguments.get("protein", "")
        if not protein:
            return {"status": "error", "error": "Missing required parameter: protein"}

        try:
            response = requests.get(
                f"{GPCRDB_API_URL}/protein/{protein}/",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/GPCRdb",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Strip HTML tags/entities from name field (GPCRdb returns e.g. "&beta;<sub>2</sub>-adrenoceptor")
            if isinstance(data, dict) and "name" in data:
                data["name"] = _HTML_TAG_RE.sub("", html.unescape(data["name"]))

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "source": "GPCRdb",
                    "protein": protein,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"status": "error", "error": f"Protein not found: {protein}"}
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _list_proteins(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        List GPCR protein families from GPCRdb.

        Args:
            arguments: Dict containing:
                - family: GPCR family (e.g., "001" for Class A). If provided, returns proteins in that family.
                - species: Species (ignored if no family specified)

        Note: GPCRdb API does not support listing all proteins by species alone.
        Without family, returns list of protein families.
        """
        family = arguments.get("family", "")

        try:
            if family:
                # List proteins in specific family
                url = f"{GPCRDB_API_URL}/proteinfamily/proteins/{family}/"
            else:
                # List protein families (no endpoint for all proteins by species)
                url = f"{GPCRDB_API_URL}/proteinfamily/"

            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/GPCRdb",
                },
            )
            response.raise_for_status()
            data = response.json()

            proteins = data if isinstance(data, list) else [data]

            return {
                "status": "success",
                "data": {
                    "proteins": proteins,
                    "count": len(proteins),
                    "family": family if family else "all families",
                    "note": "Specify 'family' parameter to list proteins in a specific family. Without family, returns list of protein families.",
                },
                "metadata": {
                    "source": "GPCRdb",
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get GPCR structure information.

        Args:
            arguments: Dict containing:
                - protein: Protein entry name (optional - if not provided, returns all structures)
                - state: Receptor state filter (active, inactive, intermediate)
        """
        protein = arguments.get("protein", "")
        state = arguments.get("state", "")

        try:
            if protein:
                url = f"{GPCRDB_API_URL}/structure/protein/{protein}/"
            else:
                url = f"{GPCRDB_API_URL}/structure/"

            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/GPCRdb",
                },
            )
            response.raise_for_status()
            data = response.json()

            structures = data if isinstance(data, list) else [data]

            # Filter by state if specified
            if state:
                structures = [
                    s for s in structures if s.get("state", "").lower() == state.lower()
                ]

            return {
                "status": "success",
                "data": {
                    "structures": structures,
                    "count": len(structures),
                    "protein": protein if protein else "all",
                    "state_filter": state if state else "all",
                },
                "metadata": {
                    "source": "GPCRdb",
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"structures": [], "count": 0},
                    "metadata": {"note": "No structures found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_ligands(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get ligands associated with a GPCR.

        Args:
            arguments: Dict containing:
                - protein: Protein entry name (e.g., adrb2_human)
        """
        protein = arguments.get("protein", "")
        if not protein:
            return {"status": "error", "error": "Missing required parameter: protein"}

        try:
            response = requests.get(
                f"{GPCRDB_API_URL}/ligands/{protein}/",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/GPCRdb",
                },
            )
            response.raise_for_status()
            data = response.json()

            ligands = data if isinstance(data, list) else data.get("ligands", [])

            return {
                "status": "success",
                "data": {
                    "protein": protein,
                    "ligands": ligands,
                    "count": len(ligands),
                },
                "metadata": {
                    "source": "GPCRdb",
                    "protein": protein,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"protein": protein, "ligands": [], "count": 0},
                    "metadata": {"note": "No ligands found for this protein"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_mutations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get mutation data for a GPCR.

        Args:
            arguments: Dict containing:
                - protein: Protein entry name (e.g., adrb2_human)
        """
        protein = arguments.get("protein", "")
        if not protein:
            return {"status": "error", "error": "Missing required parameter: protein"}

        try:
            response = requests.get(
                f"{GPCRDB_API_URL}/mutants/protein/{protein}/",
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/GPCRdb",
                },
            )
            response.raise_for_status()
            data = response.json()

            mutations = data if isinstance(data, list) else data.get("mutations", [])

            return {
                "status": "success",
                "data": {
                    "protein": protein,
                    "mutations": mutations,
                    "count": len(mutations),
                },
                "metadata": {
                    "source": "GPCRdb",
                    "protein": protein,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "success",
                    "data": {"protein": protein, "mutations": [], "count": 0},
                    "metadata": {"note": "No mutation data found"},
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
