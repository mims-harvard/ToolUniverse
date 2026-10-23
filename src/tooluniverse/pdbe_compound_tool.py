# pdbe_compound_tool.py
"""
PDBe Compound tool for ToolUniverse.

PDBe Graph API provides detailed chemical compound information from the Protein
Data Bank, including molecular formula, weight, SMILES, InChI identifiers,
systematic names, cross-references to PubChem/DrugBank/ClinicalTrials, and
the PDB structures containing each compound.

API: https://www.ebi.ac.uk/pdbe/graph-api/compound/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_COMPOUND_BASE_URL = "https://www.ebi.ac.uk/pdbe/graph-api/compound"


@register_tool("PDBECompoundTool")
class PDBECompoundTool(BaseTool):
    """
    Tool for querying PDBe compound (ligand/small molecule) information.

    Supports:
    - Get compound summary (formula, weight, SMILES, InChI, cross-references)
    - Get all PDB structures containing a specific compound

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_summary")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe Compound API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PDBe Compound API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PDBe Compound API",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Compound not found in PDBe. Check the 3-letter compound code (e.g., ATP, HEM, NAG).",
                }
            return {"status": "error", "error": f"PDBe Compound API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_summary":
            return self._get_summary(arguments)
        elif self.endpoint == "get_structures":
            return self._get_structures(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound summary from PDBe."""
        comp_id = arguments.get("comp_id", "")
        if not comp_id:
            return {
                "status": "error",
                "error": "comp_id is required (PDB chemical component ID, e.g., 'ATP', 'HEM', 'NAG', 'CFF').",
            }

        comp_id = comp_id.upper()
        url = f"{PDBE_COMPOUND_BASE_URL}/summary/{comp_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if comp_id not in data:
            return {
                "status": "error",
                "error": f"Compound '{comp_id}' not found in PDBe.",
            }

        compound_list = data[comp_id]
        if not compound_list:
            return {"status": "error", "error": f"No data for compound '{comp_id}'."}

        compound = compound_list[0]

        # Extract SMILES
        smiles = []
        # PDBe returns these fields as JSON null (not absent) for some
        # compounds (e.g. HEM has cross_links: null), so `.get(key, [])`
        # doesn't apply its default -- it returns None, and iterating that
        # raises TypeError. `.get(key) or []` catches both cases.
        for s in compound.get("smiles") or []:
            smiles.append(
                {
                    "program": s.get("program"),
                    "value": s.get("name"),
                }
            )

        # Extract cross-references
        cross_links = []
        for cl in compound.get("cross_links") or []:
            cross_links.append(
                {
                    "resource": cl.get("resource"),
                    "resource_id": cl.get("resource_id"),
                }
            )

        # Extract systematic names
        sys_names = []
        for sn in compound.get("systematic_names") or []:
            sys_names.append(
                {
                    "program": sn.get("program"),
                    "name": sn.get("name"),
                }
            )

        return {
            "status": "success",
            "data": {
                "comp_id": comp_id,
                "name": compound.get("name"),
                "formula": compound.get("formula"),
                "weight": compound.get("weight"),
                "formal_charge": compound.get("formal_charge"),
                "compound_type": compound.get("compound_type"),
                "inchi": compound.get("inchi"),
                "inchi_key": compound.get("inchi_key"),
                "smiles": smiles,
                "smiles_count": len(smiles),
                "systematic_names": sys_names,
                "systematic_name_count": len(sys_names),
                "cross_references": cross_links,
                "cross_reference_count": len(cross_links),
                "first_observed_in": compound.get("first_observed_in") or [],
                "release_status": compound.get("release_status"),
                "creation_date": compound.get("creation_date"),
            },
            "metadata": {
                "source": "PDBe Graph API (ebi.ac.uk/pdbe)",
            },
        }

    def _get_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PDB structures containing a specific compound via PDBe API."""
        comp_id = arguments.get("comp_id", "")
        if not comp_id:
            return {
                "status": "error",
                "error": "comp_id is required (PDB chemical component ID, e.g., 'ATP', 'HEM', 'NAG').",
            }

        comp_id = comp_id.upper()
        try:
            limit = max(1, min(int(arguments.get("limit", 100)), 500))
            offset = max(0, int(arguments.get("offset", 0)))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "limit and offset must be integers",
            }

        # Use PDBe API for compound summary - it provides the same info
        url = f"{PDBE_COMPOUND_BASE_URL}/summary/{comp_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if comp_id not in data:
            return {
                "status": "error",
                "error": f"Compound '{comp_id}' not found in PDBe.",
            }

        compound_list = data[comp_id]
        if not compound_list:
            return {"status": "error", "error": f"No data for compound '{comp_id}'."}

        compound = compound_list[0]
        first_seen = compound.get("first_observed_in") or []

        # The summary endpoint has no pdb_entries field. The official
        # compound/in_pdb endpoint returns every containing PDB entry plus
        # occurrence qualifiers (bound/subcomponent type and copy counts).
        pdb_url = f"https://www.ebi.ac.uk/pdbe/api/pdb/compound/in_pdb/{comp_id}"
        pdb_response = requests.get(pdb_url, timeout=self.timeout)
        pdb_response.raise_for_status()
        occurrences = pdb_response.json().get(comp_id, []) or []
        page = occurrences[offset : offset + limit]
        pdb_ids = [row.get("pdb_id") for row in page if row.get("pdb_id")]
        total = len(occurrences)
        next_offset = offset + len(page)
        has_more = next_offset < total

        return {
            "status": "success",
            "data": {
                "comp_id": comp_id,
                "name": compound.get("name"),
                "formula": compound.get("formula"),
                "weight": compound.get("weight"),
                "first_observed_in": first_seen,
                "pdb_entries": pdb_ids,
                "occurrences": page,
                "total_structures": total,
                "returned": len(page),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
            },
            "metadata": {
                "source": "PDBe Graph API (ebi.ac.uk/pdbe)",
                "total_structures": total,
                "returned": len(page),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
            },
        }
