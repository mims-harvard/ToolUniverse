"""
PDBePISA - Protein Interfaces, Surfaces, and Assemblies Tool

Provides access to the PDBePISA CGI API at EBI for analyzing protein
crystal structures to determine biological assemblies, protein-protein
interfaces, and monomer surface areas.

PISA (Proteins, Interfaces, Structures and Assemblies) is used for the
exploration of macromolecular interfaces, prediction of probable biological
assemblies, database searches of structurally similar interfaces and
assemblies, and identification of protein interfaces in crystal packings.

API base: https://www.ebi.ac.uk/pdbe/pisa/cgi-bin/
Returns XML responses which are parsed into structured JSON.
No authentication required.

Reference: Krissinel & Henrick, J Mol Biol 2007 (PMID: 17681537)
"""

import requests
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


PISA_BASE_URL = "https://www.ebi.ac.uk/pdbe/pisa/cgi-bin"


def _safe_float(text: Optional[str]) -> Optional[float]:
    """Safely convert text to float, returning None on failure."""
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _safe_int(text: Optional[str]) -> Optional[int]:
    """Safely convert text to int, returning None on failure."""
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return int(text)
    except (ValueError, TypeError):
        return None


def _parse_bond(bond_el: ET.Element) -> Dict[str, Any]:
    """Parse a bond (h-bond, salt-bridge, ss-bond, cov-bond) element."""
    return {
        "chain_1": (bond_el.findtext("chain-1") or "").strip(),
        "residue_1": (bond_el.findtext("res-1") or "").strip(),
        "seqnum_1": _safe_int(bond_el.findtext("seqnum-1")),
        "atom_1": (bond_el.findtext("atname-1") or "").strip(),
        "chain_2": (bond_el.findtext("chain-2") or "").strip(),
        "residue_2": (bond_el.findtext("res-2") or "").strip(),
        "seqnum_2": _safe_int(bond_el.findtext("seqnum-2")),
        "atom_2": (bond_el.findtext("atname-2") or "").strip(),
        "distance": _safe_float(bond_el.findtext("dist")),
    }


def _parse_bonds_section(section_el: Optional[ET.Element]) -> Dict[str, Any]:
    """Parse a bonds section (h-bonds, salt-bridges, etc.)."""
    if section_el is None:
        return {"count": 0, "bonds": []}
    n_bonds = _safe_int(section_el.findtext("n_bonds")) or 0
    bonds = [_parse_bond(b) for b in section_el.findall("bond")]
    return {"count": n_bonds, "bonds": bonds}


def _parse_interface(iface_el: ET.Element) -> Dict[str, Any]:
    """Parse a single interface element from PISA XML."""
    result = {
        "id": _safe_int(iface_el.findtext("id")),
        "type": _safe_int(iface_el.findtext("type")),
        "n_occurrences": _safe_int(iface_el.findtext("n_occ")),
        "interface_area": _safe_float(iface_el.findtext("int_area")),
        "solvation_energy": _safe_float(iface_el.findtext("int_solv_en")),
        "p_value": _safe_float(iface_el.findtext("pvalue")),
        "stabilization_energy": _safe_float(iface_el.findtext("stab_en")),
        "css_score": _safe_float(iface_el.findtext("css")),
        "overlap": (iface_el.findtext("overlap") or "").strip(),
        "x_rel": (iface_el.findtext("x-rel") or "").strip(),
        "fixed": (iface_el.findtext("fixed") or "").strip(),
        "h_bonds": _parse_bonds_section(iface_el.find("h-bonds")),
        "salt_bridges": _parse_bonds_section(iface_el.find("salt-bridges")),
        "ss_bonds": _parse_bonds_section(iface_el.find("ss-bonds")),
        "cov_bonds": _parse_bonds_section(iface_el.find("cov-bonds")),
    }

    # Parse molecule info
    molecules = []
    for mol in iface_el.findall("molecule"):
        mol_data = {
            "id": _safe_int(mol.findtext("id")),
            "chain_id": (mol.findtext("chain_id") or "").strip(),
            "mol_class": (mol.findtext("class") or "").strip(),
            "symop": (mol.findtext("symop") or "").strip(),
            "int_nres": _safe_int(mol.findtext("int_nres")),
            "int_area": _safe_float(mol.findtext("int_area")),
            "int_solv_en": _safe_float(mol.findtext("int_solv_en")),
            "pvalue": _safe_float(mol.findtext("pvalue")),
        }
        molecules.append(mol_data)
    result["molecules"] = molecules

    return result


def _parse_assembly(asm_el: ET.Element) -> Dict[str, Any]:
    """Parse a single assembly element from PISA XML."""
    return {
        "id": _safe_int(asm_el.findtext("id")),
        "size": _safe_int(asm_el.findtext("size")),
        "macromolecular_size": _safe_int(asm_el.findtext("mmsize")),
        "stability_score": (asm_el.findtext("score") or "").strip(),
        "dissociation_energy": _safe_float(asm_el.findtext("diss_energy")),
        "accessible_surface_area": _safe_float(asm_el.findtext("asa")),
        "buried_surface_area": _safe_float(asm_el.findtext("bsa")),
        "entropy": _safe_float(asm_el.findtext("entropy")),
        "dissociation_area": _safe_float(asm_el.findtext("diss_area")),
        "interaction_energy": _safe_float(asm_el.findtext("int_energy")),
        "n_unit_cells": _safe_int(asm_el.findtext("n_uc")),
        "n_dissociable": _safe_int(asm_el.findtext("n_diss")),
        "symmetry_number": _safe_int(asm_el.findtext("symNumber")),
        "R350": _safe_int(asm_el.findtext("R350")),
        "formula": (asm_el.findtext("formula") or "").strip(),
        "composition": (asm_el.findtext("composition") or "").strip(),
    }


@register_tool("PDBePISATool")
class PDBePISATool(BaseTool):
    """
    Tool for querying PDBePISA (Protein Interfaces, Surfaces and Assemblies).

    PISA analyzes crystal structures to identify biological assemblies,
    protein-protein interfaces, and surface properties.

    Supported operations:
    - get_interfaces: Get interface analysis for a PDB entry
    - get_assemblies: Get biological assembly predictions
    - get_monomer_analysis: Get monomer surface area analysis
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBePISA API tool with given arguments."""
        # Feature-68B-006: operation is now an internal config value, not a user parameter.
        # Fall back to arguments for backward compatibility.
        operation = self.tool_config.get("fields", {}).get(
            "operation", arguments.get("operation")
        )
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "get_interfaces": self._get_interfaces,
            "get_assemblies": self._get_assemblies,
            "get_monomer_analysis": self._get_monomer_analysis,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "PDBePISA API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PDBePISA API"}
        except ET.ParseError as e:
            return {
                "status": "error",
                "error": f"Failed to parse XML response: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"PDBePISA operation failed: {str(e)}"}

    def _fetch_xml(self, endpoint: str, pdb_id: str) -> Dict[str, Any]:
        """Fetch and parse XML from a PISA CGI endpoint."""
        url = f"{PISA_BASE_URL}/{endpoint}?{pdb_id.lower()}"
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"PDBePISA returned status {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            return {"ok": False, "error": f"Failed to parse XML: {str(e)}"}

        # Check PISA status
        status = (root.findtext("status") or "").strip()
        if status != "Ok":
            return {"ok": False, "error": f"PDBePISA status: {status}"}

        entry = root.find("pdb_entry")
        if entry is None:
            return {"ok": False, "error": "No pdb_entry element in response"}

        entry_status = (entry.findtext("status") or "").strip()
        if entry_status != "Ok":
            return {"ok": False, "error": f"PDB entry status: {entry_status}"}

        return {"ok": True, "entry": entry}

    def _get_interfaces(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get interface analysis for a PDB entry."""
        pdb_id = arguments.get("pdb_id")
        if not pdb_id:
            return {"status": "error", "error": "pdb_id parameter is required"}

        result = self._fetch_xml("interfaces.pisa", pdb_id)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        entry = result["entry"]
        n_interfaces = _safe_int(entry.findtext("n_interfaces")) or 0
        interfaces = [_parse_interface(iface) for iface in entry.findall("interface")]

        return {
            "status": "success",
            "data": {
                "pdb_code": (entry.findtext("pdb_code") or "").strip(),
                "n_interfaces": n_interfaces,
                "interfaces": interfaces,
            },
        }

    def _get_assemblies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get biological assembly predictions for a PDB entry."""
        pdb_id = arguments.get("pdb_id")
        if not pdb_id:
            return {"status": "error", "error": "pdb_id parameter is required"}

        result = self._fetch_xml("multimers.pisa", pdb_id)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        entry = result["entry"]
        total_asm = _safe_int(entry.findtext("total_asm")) or 0

        assembly_sets = []
        for asm_set in entry.findall("asm_set"):
            ser_no = _safe_int(asm_set.findtext("ser_no"))
            assemblies = [_parse_assembly(asm) for asm in asm_set.findall("assembly")]
            assembly_sets.append(
                {
                    "set_number": ser_no,
                    "assemblies": assemblies,
                }
            )

        return {
            "status": "success",
            "data": {
                "pdb_code": (entry.findtext("pdb_code") or "").strip(),
                "total_assemblies": total_asm,
                "assembly_sets": assembly_sets,
            },
        }

    def _get_monomer_analysis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get monomer (individual chain) surface area analysis.

        Uses the interfaces endpoint and extracts per-molecule data
        from interface analyses, providing surface area information
        for each chain in the structure.
        """
        pdb_id = arguments.get("pdb_id")
        if not pdb_id:
            return {"status": "error", "error": "pdb_id parameter is required"}

        # Use interfaces endpoint to extract molecule-level data
        result = self._fetch_xml("interfaces.pisa", pdb_id)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        entry = result["entry"]

        # Collect unique chains and their interface participations
        chain_data = {}
        interfaces = entry.findall("interface")
        for iface in interfaces:
            iface_id = _safe_int(iface.findtext("id"))
            for mol in iface.findall("molecule"):
                chain_id = (mol.findtext("chain_id") or "").strip()
                mol_class = (mol.findtext("class") or "").strip()
                int_area = _safe_float(mol.findtext("int_area"))
                int_solv_en = _safe_float(mol.findtext("int_solv_en"))
                int_nres = _safe_int(mol.findtext("int_nres"))

                if chain_id not in chain_data:
                    chain_data[chain_id] = {
                        "chain_id": chain_id,
                        "mol_class": mol_class,
                        "total_interface_area": 0.0,
                        "interface_count": 0,
                        "interface_participations": [],
                    }

                if int_area is not None:
                    chain_data[chain_id]["total_interface_area"] += int_area
                chain_data[chain_id]["interface_count"] += 1
                chain_data[chain_id]["interface_participations"].append(
                    {
                        "interface_id": iface_id,
                        "interface_area": int_area,
                        "solvation_energy": int_solv_en,
                        "interface_residues": int_nres,
                    }
                )

        chains = list(chain_data.values())

        return {
            "status": "success",
            "data": {
                "pdb_code": (entry.findtext("pdb_code") or "").strip(),
                "n_interfaces": _safe_int(entry.findtext("n_interfaces")) or 0,
                "chains": chains,
            },
        }
