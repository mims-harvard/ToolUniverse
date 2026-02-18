# pdbe_sifts_tool.py
"""
PDBe SIFTS Mapping tool for ToolUniverse.

SIFTS (Structure Integration with Function, Taxonomy and Sequences) provides
cross-referencing between PDB structures and UniProt proteins, enabling
structure-based discovery of best available crystal/EM structures for a protein.

API: https://www.ebi.ac.uk/pdbe/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PDBE_API_BASE_URL = "https://www.ebi.ac.uk/pdbe/api"


@register_tool("PDBeSIFTSTool")
class PDBeSIFTSTool(BaseTool):
    """
    PDBe SIFTS Mapping tool for UniProt-PDB cross-referencing.

    Provides ranked best structures for a protein, PDB-to-UniProt chain
    mapping, and comprehensive structure coverage analysis.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "best_structures")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBe SIFTS API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"PDBe SIFTS API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to PDBe SIFTS API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"PDBe SIFTS API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying PDBe SIFTS API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "best_structures":
            return self._get_best_structures(arguments)
        elif self.endpoint == "pdb_to_uniprot":
            return self._get_pdb_to_uniprot(arguments)
        elif self.endpoint == "uniprot_to_pdb":
            return self._get_uniprot_to_pdb(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_best_structures(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get best PDB structures for a UniProt protein, ranked by coverage and resolution."""
        accession = arguments.get("uniprot_accession", "")
        if not accession:
            return {"error": "uniprot_accession parameter is required (e.g., P04637)"}

        url = f"{PDBE_API_BASE_URL}/mappings/best_structures/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = data.get(accession, [])

        structures = []
        for e in entries[:50]:
            structures.append(
                {
                    "pdb_id": e.get("pdb_id"),
                    "chain_id": e.get("chain_id"),
                    "uniprot_start": e.get("start"),
                    "uniprot_end": e.get("end"),
                    "resolution": e.get("resolution"),
                    "experimental_method": e.get("experimental_method"),
                    "coverage": e.get("coverage"),
                    "tax_id": e.get("tax_id"),
                }
            )

        return {
            "data": {
                "uniprot_accession": accession,
                "structures": structures,
                "total_structures": len(entries),
            },
            "metadata": {
                "source": "PDBe SIFTS - Best Structures",
                "accession": accession,
            },
        }

    def _get_pdb_to_uniprot(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Map PDB entry chains to UniProt accessions."""
        pdb_id = arguments.get("pdb_id", "")
        if not pdb_id:
            return {"error": "pdb_id parameter is required (e.g., 1tup)"}

        pdb_id = pdb_id.lower()
        url = f"{PDBE_API_BASE_URL}/mappings/uniprot/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entry_data = data.get(pdb_id, {})
        uniprot_data = entry_data.get("UniProt", {})

        proteins = []
        for acc, info in uniprot_data.items():
            chain_mappings = []
            for m in info.get("mappings", [])[:20]:
                chain_mappings.append(
                    {
                        "chain_id": m.get("chain_id"),
                        "pdb_start": m.get("start", {}).get("residue_number"),
                        "pdb_end": m.get("end", {}).get("residue_number"),
                        "uniprot_start": m.get("unp_start"),
                        "uniprot_end": m.get("unp_end"),
                    }
                )

            proteins.append(
                {
                    "uniprot_accession": acc,
                    "name": info.get("identifier"),
                    "chain_mappings": chain_mappings,
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "proteins": proteins,
                "total_proteins": len(proteins),
            },
            "metadata": {
                "source": "PDBe SIFTS - PDB to UniProt Mapping",
                "pdb_id": pdb_id,
            },
        }

    def _get_uniprot_to_pdb(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all PDB entries covering a UniProt protein."""
        accession = arguments.get("uniprot_accession", "")
        if not accession:
            return {"error": "uniprot_accession parameter is required (e.g., P04637)"}

        # Use best_structures endpoint which returns all PDB structures
        url = f"{PDBE_API_BASE_URL}/mappings/best_structures/{accession}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = data.get(accession, [])

        # Group by PDB ID to show unique structures
        pdb_entries = {}
        for e in entries:
            pdb_id = e.get("pdb_id", "")
            if pdb_id not in pdb_entries:
                pdb_entries[pdb_id] = {
                    "pdb_id": pdb_id,
                    "resolution": e.get("resolution"),
                    "experimental_method": e.get("experimental_method"),
                    "chains": [],
                }
            pdb_entries[pdb_id]["chains"].append(
                {
                    "chain_id": e.get("chain_id"),
                    "uniprot_start": e.get("start"),
                    "uniprot_end": e.get("end"),
                    "coverage": e.get("coverage"),
                }
            )

        # Sort by resolution (best first)
        sorted_entries = sorted(
            pdb_entries.values(),
            key=lambda x: x.get("resolution") or 999,
        )

        return {
            "data": {
                "uniprot_accession": accession,
                "pdb_entries": sorted_entries[:50],
                "total_pdb_entries": len(pdb_entries),
                "total_chain_mappings": len(entries),
            },
            "metadata": {
                "source": "PDBe SIFTS - UniProt to PDB Mapping",
                "accession": accession,
            },
        }
