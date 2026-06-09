"""
SAbDab (Structural Antibody Database) tool for ToolUniverse.

SAbDab is a database containing all antibody structures from the PDB,
annotated with CDR sequences, chain pairings, and other structural features.

Website: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab
"""

import csv
import io
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
        elif operation == "get_structure_summary":
            return self._get_structure_summary(arguments)
        elif operation == "get_summary":
            return self._get_summary(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_structures, get_structure, get_structure_summary, get_summary",
            }

    def _search_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search SAbDab for antibody structures.

        Args:
            arguments: Dict containing:
                - query: Search query (antigen name, species, etc.)
                - limit: Maximum results
        """
        query = arguments.get("query") or arguments.get("antigen", "")
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

            # SAbDab search endpoint returns HTML, not JSON — return browse URL
            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
                structures = data if isinstance(data, list) else data.get("results", [])
                return {
                    "status": "success",
                    "data": {
                        "structures": structures,
                        "count": len(structures),
                        "query": query,
                    },
                    "metadata": {"source": "SAbDab"},
                }

            browse_url = f"https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab/search/?q={query}"
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "browse_url": browse_url,
                    "note": (
                        "SAbDab search does not expose a JSON API. "
                        "Open browse_url to view matching antibody structures, "
                        "or use SAbDab_get_structure with a known PDB ID for structured data."
                    ),
                },
                "metadata": {"source": "SAbDab"},
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
        pdb_id = arguments.get("pdb_id") or arguments.get("pdb_code") or ""
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

    @staticmethod
    def _coerce(value: str):
        """Convert SAbDab TSV string cells to typed values.

        SAbDab writes the literal strings 'None'/'NA'/'' for missing fields and
        'True'/'False' for boolean flags. Numeric fields (resolution, r_free)
        come back as decimal strings.
        """
        if value is None:
            return None
        stripped = value.strip()
        if stripped in ("", "None", "NA", "na", "N/A"):
            return None
        if stripped == "True":
            return True
        if stripped == "False":
            return False
        # Try numeric conversion (resolution, r_free, r_factor, delta_g, ...)
        try:
            if "." in stripped or "e" in stripped.lower():
                return float(stripped)
            return int(stripped)
        except ValueError:
            return stripped

    def _get_structure_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get per-structure curated antibody annotations for a PDB ID.

        Returns the SAbDab summary TSV row(s) for the structure: antigen
        name/type/species, heavy/light chain species and subclass, resolution,
        experimental method, R-free / R-factor, scFv and engineered flags, and
        (when curated) binding affinity Kd, delta_G, affinity method,
        temperature and PMID.

        Args:
            arguments: Dict containing:
                - pdb_id: 4-character PDB ID (alias: pdb_code, pdb)
        """
        pdb_id = (
            arguments.get("pdb_id")
            or arguments.get("pdb_code")
            or arguments.get("pdb")
            or ""
        )
        if not pdb_id:
            return {
                "status": "error",
                "error": "Missing required parameter: pdb_id",
            }

        pdb_id_lower = pdb_id.strip().lower()

        try:
            response = requests.get(
                f"{SABDAB_BASE_URL}/summary/{pdb_id_lower}/",
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/SAbDab",
                    "Accept": "text/tab-separated-values",
                },
            )

            if response.status_code == 404:
                return {
                    "status": "error",
                    "error": (
                        f"Structure not found in SAbDab: {pdb_id}. "
                        "SAbDab only annotates PDB entries containing antibody structures."
                    ),
                }

            response.raise_for_status()

            text = response.text
            content_type = response.headers.get("Content-Type", "")

            # Expect a TSV with a header row + one row per antibody chain pairing.
            if "tab-separated" not in content_type and "\t" not in text:
                return {
                    "status": "error",
                    "error": (
                        f"SAbDab did not return tabular data for {pdb_id} "
                        "(structure may not be an antibody complex)."
                    ),
                }

            reader = csv.DictReader(io.StringIO(text.strip()), delimiter="\t")
            rows = []
            for raw in reader:
                rows.append({k: self._coerce(v) for k, v in raw.items()})

            if not rows:
                return {
                    "status": "error",
                    "error": f"No SAbDab annotation rows found for {pdb_id}.",
                }

            first = rows[0]
            return {
                "status": "success",
                "data": {
                    "pdb_id": pdb_id_lower,
                    "antigen_name": first.get("antigen_name"),
                    "antigen_type": first.get("antigen_type"),
                    "antigen_species": first.get("antigen_species"),
                    "heavy_species": first.get("heavy_species"),
                    "light_species": first.get("light_species"),
                    "resolution": first.get("resolution"),
                    "method": first.get("method"),
                    "r_free": first.get("r_free"),
                    "r_factor": first.get("r_factor"),
                    "heavy_subclass": first.get("heavy_subclass"),
                    "light_subclass": first.get("light_subclass"),
                    "light_ctype": first.get("light_ctype"),
                    "scfv": first.get("scfv"),
                    "engineered": first.get("engineered"),
                    "affinity": first.get("affinity"),
                    "delta_g": first.get("delta_g"),
                    "affinity_method": first.get("affinity_method"),
                    "temperature": first.get("temperature"),
                    "pmid": first.get("pmid"),
                    "chains": rows,
                    "count": len(rows),
                },
                "metadata": {
                    "source": "SAbDab",
                    "summary_url": f"{SABDAB_BASE_URL}/summary/{pdb_id_lower}/",
                    "note": (
                        "'chains' lists one row per antibody chain pairing in the "
                        "structure; top-level fields are taken from the first pairing."
                    ),
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
        # Redirect hint if user passed a PDB ID (Feature-125B-003)
        pdb = arguments.get("pdb") or arguments.get("pdb_id")
        if pdb:
            return {
                "status": "error",
                "error": (
                    f"SAbDab_get_summary returns database-wide statistics, not per-structure data. "
                    f"To retrieve structure '{pdb}', use SAbDab_get_structure instead."
                ),
            }
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
