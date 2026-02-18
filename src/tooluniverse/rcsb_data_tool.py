# rcsb_data_tool.py
"""
RCSB PDB Data API tool for ToolUniverse.

Provides access to the RCSB PDB Data API REST endpoints for retrieving
detailed structural metadata, assembly information, and non-polymer entity
(ligand/small molecule) data from PDB structures.

API: https://data.rcsb.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


RCSB_DATA_BASE_URL = "https://data.rcsb.org/rest/v1/core"


class RCSBDataTool(BaseTool):
    """
    Tool for RCSB PDB Data API providing direct REST access to PDB
    structure metadata, biological assembly info, and non-polymer entities.

    Complements existing RCSB GraphQL and Search tools by providing
    simpler, direct access to individual resource endpoints.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "entry")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the RCSB Data API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"RCSB Data API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to RCSB Data API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {"error": f"Entry not found in RCSB PDB: {arguments}"}
            return {"error": f"RCSB Data API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying RCSB Data API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "entry":
            return self._get_entry(arguments)
        elif self.endpoint == "assembly":
            return self._get_assembly(arguments)
        elif self.endpoint == "nonpolymer_entity":
            return self._get_nonpolymer_entity(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive entry details for a PDB structure."""
        pdb_id = arguments.get("pdb_id", "").upper()
        if not pdb_id:
            return {"error": "pdb_id parameter is required (e.g., '4HHB', '1TUP')"}

        url = f"{RCSB_DATA_BASE_URL}/entry/{pdb_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entry_info = data.get("rcsb_entry_info", {})
        struct = data.get("struct", {})
        exptl = data.get("exptl", [])
        accession = data.get("rcsb_accession_info", {})
        cell = data.get("cell", {})
        symmetry = data.get("symmetry", {})

        # Extract experiment details
        experiments = []
        for exp in exptl:
            experiments.append(
                {
                    "method": exp.get("method"),
                    "crystals_number": exp.get("crystals_number"),
                }
            )

        # Extract resolution
        resolution = entry_info.get("resolution_combined", [])

        return {
            "data": {
                "pdb_id": data.get("rcsb_id"),
                "title": struct.get("title"),
                "method": experiments[0].get("method") if experiments else None,
                "resolution": resolution[0] if resolution else None,
                "deposit_date": accession.get("deposit_date"),
                "release_date": accession.get("initial_release_date"),
                "revision_date": accession.get("revision_date"),
                "polymer_entity_count": entry_info.get("polymer_entity_count"),
                "nonpolymer_entity_count": entry_info.get("nonpolymer_entity_count"),
                "deposited_atom_count": entry_info.get("deposited_atom_count"),
                "deposited_model_count": entry_info.get(
                    "deposited_modeled_polymer_monomer_count"
                ),
                "molecular_weight": entry_info.get("molecular_weight"),
                "assembly_count": entry_info.get("assembly_count"),
                "space_group": symmetry.get("space_group_name_H_M"),
                "unit_cell": {
                    "a": cell.get("length_a"),
                    "b": cell.get("length_b"),
                    "c": cell.get("length_c"),
                    "alpha": cell.get("angle_alpha"),
                    "beta": cell.get("angle_beta"),
                    "gamma": cell.get("angle_gamma"),
                }
                if cell
                else None,
            },
            "metadata": {
                "source": "RCSB PDB Data API",
                "pdb_id": pdb_id,
            },
        }

    def _get_assembly(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get biological assembly details for a PDB structure."""
        pdb_id = arguments.get("pdb_id", "").upper()
        assembly_id = arguments.get("assembly_id", "1")
        if not pdb_id:
            return {"error": "pdb_id parameter is required (e.g., '4HHB', '1TUP')"}

        url = f"{RCSB_DATA_BASE_URL}/assembly/{pdb_id}/{assembly_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        assembly_info = data.get("rcsb_assembly_info", {})
        struct_assembly = data.get("pdbx_struct_assembly", {})
        oper_list = data.get("pdbx_struct_oper_list", [])
        auth_evidence = data.get("pdbx_struct_assembly_auth_evidence", [])

        # Extract operations
        operations = []
        for op in oper_list[:10]:
            operations.append(
                {
                    "id": op.get("id"),
                    "type": op.get("type"),
                    "name": op.get("name"),
                }
            )

        # Extract evidence
        evidence = []
        for ev in auth_evidence[:5]:
            evidence.append(
                {
                    "experimental_support": ev.get("experimental_support"),
                    "details": ev.get("details"),
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "assembly_id": data.get("rcsb_id"),
                "oligomeric_details": struct_assembly.get("oligomeric_details"),
                "oligomeric_count": struct_assembly.get("oligomeric_count"),
                "method_details": struct_assembly.get("method_details"),
                "polymer_entity_count": assembly_info.get("polymer_entity_count"),
                "nonpolymer_entity_count": assembly_info.get("nonpolymer_entity_count"),
                "polymer_entity_instance_count": assembly_info.get(
                    "polymer_entity_instance_count"
                ),
                "total_polymer_monomer_count": assembly_info.get(
                    "total_polymer_monomer_count"
                ),
                "operations": operations,
                "evidence": evidence,
            },
            "metadata": {
                "source": "RCSB PDB Data API - Assembly",
                "pdb_id": pdb_id,
                "assembly_id": assembly_id,
            },
        }

    def _get_nonpolymer_entity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get non-polymer entity (ligand/small molecule) details."""
        pdb_id = arguments.get("pdb_id", "").upper()
        entity_id = arguments.get("entity_id", "")
        if not pdb_id or not entity_id:
            return {
                "error": "Both pdb_id and entity_id are required (e.g., pdb_id='4HHB', entity_id='3')"
            }

        url = f"{RCSB_DATA_BASE_URL}/nonpolymer_entity/{pdb_id}/{entity_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entity_nonpoly = data.get("pdbx_entity_nonpoly", {})
        nonpoly_info = data.get("rcsb_nonpolymer_entity", {})
        container_ids = data.get("rcsb_nonpolymer_entity_container_identifiers", {})
        data.get("nonpolymer_comp", {})
        drugbank = data.get("rcsb_nonpolymer_entity_annotation", [])

        # Extract annotations
        annotations = []
        for ann in drugbank[:10]:
            annotations.append(
                {
                    "type": ann.get("type"),
                    "annotation_id": ann.get("annotation_id"),
                    "name": ann.get("name"),
                    "description": ann.get("description"),
                }
            )

        return {
            "data": {
                "pdb_id": pdb_id,
                "entity_id": data.get("rcsb_id"),
                "name": entity_nonpoly.get("name"),
                "comp_id": entity_nonpoly.get("comp_id"),
                "formula_weight": nonpoly_info.get("formula_weight"),
                "details": nonpoly_info.get("details"),
                "auth_asym_ids": container_ids.get("auth_asym_ids", []),
                "annotations": annotations,
            },
            "metadata": {
                "source": "RCSB PDB Data API - Nonpolymer Entity",
                "pdb_id": pdb_id,
                "entity_id": entity_id,
            },
        }
