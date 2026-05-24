"""
Structure Annotation Tool

Per-residue structural annotation from a PDB structure:
binding interface, ligand pocket, core/surface, secondary structure.

Methodology adapted from an upstream research workflow — Requires:
  pip install biopython freesasa

For secondary structure, an optional companion PDBe SS lookup is supported via
the `include_secondary_structure` flag — uses PDBe REST and does NOT need DSSP
binary.
"""

import os
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool


_RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
_PDBE_SS_URL = "https://www.ebi.ac.uk/pdbe/api/pdb/entry/secondary_structure/{pdb_id}"
_BACKBONE_ATOMS: Set[str] = {"N", "CA", "C", "O", "OXT"}

# Three-letter to one-letter mapping for the 20 standard AAs
_THREE_TO_ONE: Dict[str, str] = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def _fetch_pdb(pdb_id: str) -> str:
    """Fetch raw PDB text from RCSB."""
    url = _RCSB_PDB_URL.format(pdb_id=pdb_id.lower())
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _sidechain_heavy_coords(residue) -> "Any":
    """Side-chain heavy-atom coords; glycine (no side chain) -> Ca.

    Matches the paper's scHA (side-chain heavy-atom) selection.
    """
    import numpy as np

    sc = [
        a for a in residue if a.element != "H" and a.get_name() not in _BACKBONE_ATOMS
    ]
    if not sc:
        sc = [a for a in residue if a.get_name() == "CA"]
    if not sc:
        return np.empty((0, 3))
    return np.array([a.coord for a in sc])


def _all_heavy_coords(residue) -> "Any":
    """All heavy atoms (ligands have no canonical 'side chain')."""
    import numpy as np

    atoms = [a for a in residue if a.element != "H"]
    if not atoms:
        return np.empty((0, 3))
    return np.array([a.coord for a in atoms])


def _min_distance(coords_a, coords_b) -> float:
    """Minimum pairwise distance between two coord arrays."""
    import numpy as np

    if len(coords_a) == 0 or len(coords_b) == 0:
        return float("inf")
    diffs = coords_a[:, None, :] - coords_b[None, :, :]
    return float(np.min(np.linalg.norm(diffs, axis=-1)))


def _compute_rsa(
    structure,
    target_chain: str,
    keep_residue,
) -> Dict[int, float]:
    """Compute relative SASA per target-chain residue on the isolated chain.

    Critical: SASA must come from the ISOLATED target chain — partner chains
    bury interface residues and bias the result.
    Critical: RSA must be self-consistent — let freesasa compute both the SASA
    and the fully-exposed reference (residueAreas().relativeTotal does this
    internally).
    """
    try:
        from Bio.PDB import PDBIO, Select
        import freesasa
    except ImportError as exc:
        raise ImportError(
            "biopython and freesasa are required for RSA computation. "
            "Install with: pip install biopython freesasa"
        ) from exc

    class _ChainOnly(Select):
        def accept_chain(self, c):  # noqa: D401
            return c.id == target_chain

        def accept_residue(self, r):  # noqa: D401
            return keep_residue(r)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdb", delete=False)
    tmp.close()
    try:
        io = PDBIO()
        io.set_structure(structure)
        io.save(tmp.name, _ChainOnly())
        fs_struct = freesasa.Structure(tmp.name)
        fs_result = freesasa.calc(fs_struct)
        areas = fs_result.residueAreas().get(target_chain, {})
        return {int(k): float(v.relativeTotal) for k, v in areas.items()}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def _fetch_pdbe_secondary_structure(pdb_id: str, target_chain: str) -> Dict[int, str]:
    """Lookup per-residue SS for a chain via PDBe REST.

    Returns {residue_number: ss_element} where ss_element is one of
    {"helix", "strand", "coil"}. Residues not annotated default to "coil"
    when read by the caller.
    """
    url = _PDBE_SS_URL.format(pdb_id=pdb_id.lower())
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError):
        return {}

    entry = payload.get(pdb_id.lower(), {})
    molecules = entry.get("molecules", [])
    ss_by_pos: Dict[int, str] = {}
    for molecule in molecules:
        for chain in molecule.get("chains", []):
            if chain.get("chain_id") != target_chain:
                continue
            ss_data = chain.get("secondary_structure", {})
            for kind, ranges in ss_data.items():
                # kind is "helices" or "strands"
                label = (
                    "helix"
                    if "helic" in kind
                    else "strand"
                    if "strand" in kind
                    else kind
                )
                for rng in ranges:
                    start = rng.get("start", {}).get("residue_number")
                    end = rng.get("end", {}).get("residue_number")
                    if start is None or end is None:
                        continue
                    for pos in range(int(start), int(end) + 1):
                        ss_by_pos[pos] = label
    return ss_by_pos


@register_tool("StructureAnnotationTool")
class StructureAnnotationTool(BaseTool):
    """Per-residue structural annotation from a PDB.

    For each residue of the target chain, classify:
      - binding interface : min scHA distance to partner chain(s) < cutoff
      - ligand pocket     : min scHA distance to ligand heavy atoms < cutoff
      - core vs surface   : relative SASA < core_rsa_cutoff
      - region label      : {interface, ligand, both, other}
      - secondary structure (optional, from PDBe)
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            operation = arguments.get("operation", "annotate_per_residue")
            if operation == "annotate_per_residue":
                return self._annotate_per_residue(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {operation!r}. Valid: annotate_per_residue",
            }
        except ImportError as exc:
            return {"status": "error", "error": str(exc)}
        except requests.RequestException as exc:
            return {"status": "error", "error": f"PDB fetch failed: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------ #
    # annotate_per_residue
    # ------------------------------------------------------------------ #
    def _annotate_per_residue(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pdb_id: Optional[str] = arguments.get("pdb_id")
        pdb_content: Optional[str] = arguments.get("pdb_content")
        if not pdb_id and not pdb_content:
            return {
                "status": "error",
                "error": "Either pdb_id or pdb_content must be provided",
            }

        target_chain: str = arguments.get("target_chain", "A")
        partner_chains: List[str] = list(arguments.get("partner_chains", []) or [])
        ligand_resnames: List[str] = [
            r.strip().upper() for r in arguments.get("ligand_resnames", []) or []
        ]
        distance_cutoff: float = float(arguments.get("distance_cutoff", 5.0))
        core_rsa_cutoff: float = float(arguments.get("core_rsa_cutoff", 0.25))
        include_ss: bool = bool(arguments.get("include_secondary_structure", False))

        try:
            from Bio.PDB import PDBParser
        except ImportError:
            return {
                "status": "error",
                "error": (
                    "biopython is required. Install with: pip install biopython freesasa"
                ),
            }

        # Load structure (download if needed)
        if pdb_content is None:
            pdb_content = _fetch_pdb(pdb_id)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdb", delete=False, mode="w")
        try:
            tmp.write(pdb_content)
            tmp.close()
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure(pdb_id or "input", tmp.name)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        model = next(iter(structure))

        if target_chain not in {c.id for c in model}:
            return {
                "status": "error",
                "error": (
                    f"target_chain {target_chain!r} not in structure. "
                    f"Available: {sorted(c.id for c in model)}"
                ),
            }
        chain_target = model[target_chain]

        # Per-residue side-chain heavy coords for the target chain
        target_residues: Dict[int, Tuple[str, Any]] = {}
        for residue in chain_target:
            hetflag = residue.id[0]
            if hetflag.strip():  # skip HETATM and waters in the target chain
                continue
            resnum = residue.id[1]
            aa = _THREE_TO_ONE.get(residue.resname.strip(), "X")
            target_residues[resnum] = (aa, _sidechain_heavy_coords(residue))

        # Pool partner-chain scHA coords
        partner_coords = self._gather_partner_coords(
            model, partner_chains, target_chain
        )

        # Pool ligand all-heavy coords (scan whole model, not just one chain)
        ligand_coords = self._gather_ligand_coords(model, set(ligand_resnames))

        # Compute RSA on the isolated target chain
        try:
            rsa_map = _compute_rsa(
                structure,
                target_chain,
                keep_residue=lambda r: not r.id[0].strip(),
            )
        except ImportError as exc:
            return {"status": "error", "error": str(exc)}

        # Optional secondary structure from PDBe (only meaningful if pdb_id provided)
        ss_map: Dict[int, str] = {}
        if include_ss and pdb_id:
            ss_map = _fetch_pdbe_secondary_structure(pdb_id, target_chain)

        # Assemble per-residue rows
        rows: List[Dict[str, Any]] = []
        for resnum in sorted(target_residues):
            aa, sc_coords = target_residues[resnum]
            d_partner = _min_distance(sc_coords, partner_coords)
            d_ligand = _min_distance(sc_coords, ligand_coords)
            is_interface = d_partner < distance_cutoff
            is_ligand = d_ligand < distance_cutoff
            if is_interface and is_ligand:
                region = "both"
            elif is_interface:
                region = "interface"
            elif is_ligand:
                region = "ligand"
            else:
                region = "other"
            rsa = rsa_map.get(resnum)
            is_core = rsa is not None and rsa < core_rsa_cutoff

            row: Dict[str, Any] = {
                "position": resnum,
                "aa": aa,
                "dist_partner": (
                    None if d_partner == float("inf") else round(d_partner, 3)
                ),
                "dist_ligand": (
                    None if d_ligand == float("inf") else round(d_ligand, 3)
                ),
                "rsa": (None if rsa is None else round(rsa, 3)),
                "region": region,
                "is_core": is_core,
            }
            if include_ss:
                row["ss_element"] = ss_map.get(resnum, "coil")
            rows.append(row)

        return {
            "status": "success",
            "pdb_id": pdb_id,
            "target_chain": target_chain,
            "partner_chains": partner_chains,
            "ligand_resnames": ligand_resnames,
            "distance_cutoff": distance_cutoff,
            "core_rsa_cutoff": core_rsa_cutoff,
            "n_residues": len(rows),
            "annotations": rows,
            "method": {
                "interface_metric": "sidechain_heavy_atom_min_distance",
                "ligand_metric": "sidechain_to_all_heavy_atom_min_distance",
                "rsa_source": "freesasa.residueAreas.relativeTotal (isolated target chain)",
                "ss_source": ("pdbe_rest" if include_ss else None),
            },
            "provenance": (
                "Methodology adapted from an upstream research workflow — "
                "the original script"
            ),
        }

    @staticmethod
    def _gather_partner_coords(model, partner_chains: Iterable[str], target_chain: str):
        import numpy as np

        partner_chains = [c for c in partner_chains if c != target_chain]
        if not partner_chains:
            return np.empty((0, 3))
        arrays = []
        chain_ids = {c.id for c in model}
        for chain_id in partner_chains:
            if chain_id not in chain_ids:
                continue
            for residue in model[chain_id]:
                if residue.id[0].strip():
                    continue
                arrays.append(_sidechain_heavy_coords(residue))
        if not arrays:
            return np.empty((0, 3))
        return np.vstack(arrays)

    @staticmethod
    def _gather_ligand_coords(model, ligand_resnames: Set[str]):
        import numpy as np

        if not ligand_resnames:
            return np.empty((0, 3))
        arrays = []
        for chain in model:
            for residue in chain:
                if residue.resname.strip().upper() not in ligand_resnames:
                    continue
                arrays.append(_all_heavy_coords(residue))
        if not arrays:
            return np.empty((0, 3))
        return np.vstack(arrays)
