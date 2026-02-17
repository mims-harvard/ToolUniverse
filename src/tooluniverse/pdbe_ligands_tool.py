# pdbe_ligands_tool.py
"""
PDBe Ligands and Residues tool for ToolUniverse.

The PDBe REST API provides information about ligands bound to PDB structures
and detailed per-residue information for protein chains. These complement the
existing PDBe compound tools (which look up compounds by ID) by providing
structure-centric queries.

API: https://www.ebi.ac.uk/pdbe/api/pdb/entry/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_API_BASE_URL = "https://www.ebi.ac.uk/pdbe/api/pdb/entry"


@register_tool("PDBeLigandsTool")
class PDBeLigandsTool(BaseTool):
    """
    Tool for querying PDBe structure-bound ligands and residue details.

    Supports:
    - Get all ligands bound in a PDB structure (drug-like, cofactors, ions)
    - Get per-residue listing with observed ratio for a PDB chain

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "ligand_monomers")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"PDBe API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to PDBe API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                pdb_id = arguments.get("pdb_id", "unknown")
                return {
                    "error": f"PDB entry '{pdb_id}' not found. Provide a valid 4-character PDB ID (e.g., '4hhb', '3ert')."
                }
            return {"error": f"PDBe API HTTP {status}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "ligand_monomers":
            return self._get_ligand_monomers(arguments)
        elif self.endpoint == "residue_listing":
            return self._get_residue_listing(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_ligand_monomers(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all ligand monomers bound in a PDB structure."""
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {
                "error": "pdb_id is required (4-character PDB ID, e.g., '4hhb', '3ert', '1m17')."
            }

        pdb_id = pdb_id.lower().strip()
        url = f"{PDBE_API_BASE_URL}/ligand_monomers/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if pdb_id not in data:
            return {"error": f"No ligand data for PDB '{pdb_id}'."}

        ligands_raw = data[pdb_id]
        ligands = []
        for lig in ligands_raw[:50]:
            annotations = lig.get("annotations", [])
            annotation_info = []
            for ann in annotations[:5]:
                interacting = ann.get("interacting_entity", {})
                annotation_info.append(
                    {
                        "type": ann.get("type"),
                        "interacting_entity_id": interacting.get("entity_id"),
                        "interacting_chain": interacting.get("auth_asym_id"),
                        "interacting_uniprot": interacting.get("best_unp_accession"),
                    }
                )

            ligands.append(
                {
                    "chem_comp_id": lig.get("chem_comp_id"),
                    "chem_comp_name": lig.get("chem_comp_name"),
                    "weight": lig.get("weight"),
                    "chain_id": lig.get("chain_id"),
                    "entity_id": lig.get("entity_id"),
                    "author_residue_number": lig.get("author_residue_number"),
                    "carbohydrate_polymer": lig.get("carbohydrate_polymer", False),
                    "annotations": annotation_info,
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "ligands": ligands,
                "total_ligands": len(ligands_raw),
            },
            "metadata": {
                "source": "PDBe REST API (ebi.ac.uk/pdbe)",
            },
        }

    def _get_residue_listing(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get per-residue listing for a PDB structure chain."""
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {
                "error": "pdb_id is required (4-character PDB ID, e.g., '4hhb', '3ert')."
            }

        chain_id = arguments.get("chain_id", None)
        pdb_id = pdb_id.lower().strip()

        if chain_id:
            url = f"{PDBE_API_BASE_URL}/residue_listing/{pdb_id}/chain/{chain_id}"
        else:
            url = f"{PDBE_API_BASE_URL}/residue_listing/{pdb_id}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if pdb_id not in data:
            return {"error": f"No residue data for PDB '{pdb_id}'."}

        entry_data = data[pdb_id]
        molecules = entry_data.get("molecules", [])

        result_molecules = []
        for mol in molecules[:10]:
            chains = mol.get("chains", [])
            chain_results = []
            for chain in chains[:5]:
                residues = chain.get("residues", [])
                # Summarize residues - show first/last and count
                residue_summary = []
                for res in residues[:30]:
                    residue_summary.append(
                        {
                            "residue_number": res.get("residue_number"),
                            "residue_name": res.get("residue_name"),
                            "author_residue_number": res.get("author_residue_number"),
                            "observed_ratio": res.get("observed_ratio"),
                        }
                    )

                chain_results.append(
                    {
                        "chain_id": chain.get("chain_id"),
                        "struct_asym_id": chain.get("struct_asym_id"),
                        "total_residues": len(residues),
                        "residues": residue_summary,
                    }
                )

            result_molecules.append(
                {
                    "entity_id": mol.get("entity_id"),
                    "chains": chain_results,
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "molecules": result_molecules,
                "total_molecules": len(molecules),
            },
            "metadata": {
                "source": "PDBe REST API (ebi.ac.uk/pdbe)",
            },
        }
