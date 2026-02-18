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
            return {"error": f"PDBe Compound API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to PDBe Compound API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "error": "Compound not found in PDBe. Check the 3-letter compound code (e.g., ATP, HEM, NAG)."
                }
            return {"error": f"PDBe Compound API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_summary":
            return self._get_summary(arguments)
        elif self.endpoint == "get_structures":
            return self._get_structures(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound summary from PDBe."""
        comp_id = arguments.get("comp_id", "")
        if not comp_id:
            return {
                "error": "comp_id is required (PDB chemical component ID, e.g., 'ATP', 'HEM', 'NAG', 'CFF')."
            }

        comp_id = comp_id.upper()
        url = f"{PDBE_COMPOUND_BASE_URL}/summary/{comp_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if comp_id not in data:
            return {"error": f"Compound '{comp_id}' not found in PDBe."}

        compound_list = data[comp_id]
        if not compound_list:
            return {"error": f"No data for compound '{comp_id}'."}

        compound = compound_list[0]

        # Extract SMILES
        smiles = []
        for s in compound.get("smiles", []):
            smiles.append(
                {
                    "program": s.get("program"),
                    "value": s.get("name"),
                }
            )

        # Extract cross-references
        cross_links = []
        for cl in compound.get("cross_links", []):
            cross_links.append(
                {
                    "resource": cl.get("resource"),
                    "resource_id": cl.get("resource_id"),
                }
            )

        # Extract systematic names
        sys_names = []
        for sn in compound.get("systematic_names", []):
            sys_names.append(
                {
                    "program": sn.get("program"),
                    "name": sn.get("name"),
                }
            )

        return {
            "data": {
                "comp_id": comp_id,
                "name": compound.get("name"),
                "formula": compound.get("formula"),
                "weight": compound.get("weight"),
                "formal_charge": compound.get("formal_charge"),
                "compound_type": compound.get("compound_type"),
                "inchi": compound.get("inchi"),
                "inchi_key": compound.get("inchi_key"),
                "smiles": smiles[:3],
                "systematic_names": sys_names[:3],
                "cross_references": cross_links[:15],
                "first_observed_in": compound.get("first_observed_in", []),
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
                "error": "comp_id is required (PDB chemical component ID, e.g., 'ATP', 'HEM', 'NAG')."
            }

        comp_id = comp_id.upper()
        # Use PDBe API for compound summary - it provides the same info
        url = f"{PDBE_COMPOUND_BASE_URL}/summary/{comp_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if comp_id not in data:
            return {"error": f"Compound '{comp_id}' not found in PDBe."}

        compound_list = data[comp_id]
        if not compound_list:
            return {"error": f"No data for compound '{comp_id}'."}

        compound = compound_list[0]
        first_seen = compound.get("first_observed_in", [])

        # Also get compound in_pdb data from the regular PDBe API
        pdb_url = f"https://www.ebi.ac.uk/pdbe/api/pdb/compound/summary/{comp_id}"
        try:
            pdb_response = requests.get(pdb_url, timeout=self.timeout)
            pdb_response.raise_for_status()
            pdb_data = pdb_response.json()
            pdb_entries = pdb_data.get(comp_id, [{}])
            if pdb_entries:
                pdb_entry = pdb_entries[0]
                pdb_ids = pdb_entry.get("pdb_entries", [])
            else:
                pdb_ids = []
        except Exception:
            pdb_ids = []

        return {
            "data": {
                "comp_id": comp_id,
                "name": compound.get("name"),
                "formula": compound.get("formula"),
                "weight": compound.get("weight"),
                "first_observed_in": first_seen,
                "pdb_entries": pdb_ids[:50] if pdb_ids else first_seen,
            },
            "metadata": {
                "source": "PDBe Graph API (ebi.ac.uk/pdbe)",
                "total_structures": len(pdb_ids) if pdb_ids else len(first_seen),
            },
        }
