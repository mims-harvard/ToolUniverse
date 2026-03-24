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
        # Normalize aliases → protein
        if not arguments.get("protein"):
            alias = (
                arguments.get("protein_id")
                or arguments.get("receptor_name")
                or arguments.get("protein_name")
            )
            if alias:
                arguments = dict(arguments, protein=alias)

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

    def _normalize_protein(self, protein: str) -> str:
        """Resolve gene symbol (e.g. ADRB2) to GPCRdb entry name (e.g. adrb2_human)."""
        if protein and "_" not in protein:
            return f"{protein.lower()}_human"
        return protein

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
                # Try accession endpoint (for UniProt IDs like P07550)
                try:
                    acc_response = requests.get(
                        f"{GPCRDB_API_URL}/protein/accession/{protein}/",
                        timeout=self.timeout,
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "ToolUniverse/GPCRdb",
                        },
                    )
                    acc_response.raise_for_status()
                    data = acc_response.json()
                    if isinstance(data, dict) and "name" in data:
                        data["name"] = _HTML_TAG_RE.sub("", html.unescape(data["name"]))
                    return {
                        "status": "success",
                        "data": data,
                        "metadata": {"source": "GPCRdb", "protein": protein},
                    }
                except Exception:
                    pass
                # Fallback: try {lowercase_symbol}_human (e.g. CCR5 → ccr5_human)
                if "_" not in protein:
                    human_entry = f"{protein.lower()}_human"
                    try:
                        fb_response = requests.get(
                            f"{GPCRDB_API_URL}/protein/{human_entry}/",
                            timeout=self.timeout,
                            headers={
                                "Accept": "application/json",
                                "User-Agent": "ToolUniverse/GPCRdb",
                            },
                        )
                        fb_response.raise_for_status()
                        data = fb_response.json()
                        if isinstance(data, dict) and "name" in data:
                            data["name"] = _HTML_TAG_RE.sub(
                                "", html.unescape(data["name"])
                            )
                        return {
                            "status": "success",
                            "data": data,
                            "metadata": {
                                "source": "GPCRdb",
                                "protein": human_entry,
                                "resolved_from": protein,
                            },
                        }
                    except Exception:
                        pass
                return {
                    "status": "error",
                    "error": f"Protein not found: {protein}. Use GPCRdb entry name (e.g. adrb2_human) or UniProt accession (e.g. P07550).",
                }
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    # Map human-readable class/family names to GPCRdb numeric slugs (Feature-122A-001)
    _FAMILY_NAME_TO_SLUG = {
        "class a": "001",
        "class a (rhodopsin)": "001",
        "rhodopsin": "001",
        "class b": "002",
        "class b1": "002",
        "secretin": "002",
        "class b2": "003",
        "adhesion": "003",
        "class c": "004",
        "glutamate": "004",
        "class f": "005",
        "frizzled": "005",
        "class t": "006",
        "taste2": "006",
        "aminergic": "001_001",
        "aminergic receptors": "001_001",
        "peptide receptors": "001_003",
        "chemokine receptors": "001_003_002",
        "chemokine": "001_003_002",
        "purine receptors": "001_004",
        "lipid receptors": "001_007",
        "serotonin": "001_001_001",
        "5-hydroxytryptamine": "001_001_001",
        "dopamine": "001_001_004",
        "adrenoceptor": "001_001_003",
        "adrenergic": "001_001_003",
        "adrenergic receptors": "001_001_003",
        "muscarinic": "001_001_002",
        "histamine": "001_001_005",
        "beta-adrenergic": "001_001_003_008",
        "opioid": "001_003_015",
        "endothelin": "001_003_006",
    }

    def _list_proteins(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        List GPCR protein families from GPCRdb.

        Args:
            arguments: Dict containing:
                - family: GPCR family slug (e.g., '001') or human-readable name
                  (e.g., 'Chemokine receptors'). If provided, returns proteins in
                  that family.
                - protein_class: Alias for family; accepts human-readable names.

        Note: GPCRdb API does not support listing all proteins by species alone.
        Without family, returns list of protein families.
        """
        family = arguments.get("family") or arguments.get("protein_class", "")

        # Resolve human-readable class names to numeric slugs (Feature-122A-001)
        if family and not family.replace("_", "").isdigit():
            resolved = self._FAMILY_NAME_TO_SLUG.get(family.lower())
            if resolved:
                family = resolved

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

            # Strip HTML entities and tags from name fields (Feature-123B-002)
            for item in proteins:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    item["name"] = html.unescape(_HTML_TAG_RE.sub("", item["name"]))

            note = None
            if family and len(proteins) == 0:
                note = (
                    f"No proteins found for family slug '{family}'. "
                    "The 'family' parameter requires a numeric GPCRdb slug (e.g., '001_003_002' "
                    "for Chemokine receptors). Use protein_class with a human-readable name "
                    "(e.g., 'Chemokine receptors') or call without 'family' to discover slugs."
                )
            elif not family:
                note = (
                    "To list proteins in a specific family, pass its numeric slug as 'family' "
                    "(e.g., '001_003_002') or use protein_class with a human-readable name "
                    "(e.g., 'Chemokine receptors'). Call without arguments to discover all slugs."
                )

            return {
                "status": "success",
                "data": {
                    "proteins": proteins,
                    "count": len(proteins),
                    "family": family if family else "all families",
                    **({"note": note} if note else {}),
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
                - protein: Protein entry name (e.g., adrb2_human) or gene symbol (e.g., ADRB2) — optional
                - state: Receptor state filter (active, inactive, intermediate)
        """
        protein = self._normalize_protein(arguments.get("protein", ""))
        state = arguments.get("state", "")
        resolution = arguments.get("resolution")

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

            # Filter by max resolution (client-side, GPCRdb API has no resolution param)
            if resolution is not None:
                try:
                    max_res = float(resolution)
                    structures = [
                        s
                        for s in structures
                        if s.get("resolution") is not None
                        and float(s["resolution"]) <= max_res
                    ]
                except (ValueError, TypeError):
                    pass

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
                - protein: Protein entry name (e.g., adrb2_human) or gene symbol (e.g., ADRB2)
        """
        protein = self._normalize_protein(arguments.get("protein", ""))
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

            # Filter by ligand type if specified (e.g., agonist, antagonist, inhibitor)
            # GPCRdb API returns "Ligand type" field (e.g., "small molecule", "peptide")
            ligand_type = (
                arguments.get("type") or arguments.get("ligand_type") or ""
            ).lower()
            if ligand_type:
                ligands = [
                    lig
                    for lig in ligands
                    if ligand_type
                    in (lig.get("Ligand type") or lig.get("type") or "").lower()
                ]

            total_count = len(ligands)

            # Apply limit/max_results client-side (Feature-122A-003)
            limit = arguments.get("limit") or arguments.get("max_results")
            if limit is not None:
                try:
                    ligands = ligands[: int(limit)]
                except (TypeError, ValueError):
                    pass

            # Sanitize HTML entities and fix nan DOIs in each ligand record
            for lig in ligands:
                for field in ("Ligand name", "Protein name"):
                    if isinstance(lig.get(field), str):
                        lig[field] = _HTML_TAG_RE.sub("", html.unescape(lig[field]))
                doi = lig.get("DOI", "")
                if isinstance(doi, str) and doi.lower().endswith("/nan"):
                    lig["DOI"] = None

            result: Dict[str, Any] = {
                "protein": protein,
                "ligands": ligands,
                "count": len(ligands),
                "total_count": total_count,
            }
            if limit is not None and total_count > len(ligands):
                result["note"] = (
                    f"Showing {len(ligands)} of {total_count} ligands. Increase limit to retrieve more."
                )

            return {
                "status": "success",
                "data": result,
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
                - protein: Protein entry name (e.g., adrb2_human) or gene symbol (e.g., ADRB2)
        """
        protein = self._normalize_protein(arguments.get("protein", ""))
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

            result: Dict[str, Any] = {
                "protein": protein,
                "mutations": mutations,
                "count": len(mutations),
            }
            if len(mutations) == 0:
                result["note"] = (
                    "The GPCRdb mutations API (/services/mutants/) currently returns empty results for all receptors. For mutation data, visit https://gpcrdb.org/mutations/."
                )

            return {
                "status": "success",
                "data": result,
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
