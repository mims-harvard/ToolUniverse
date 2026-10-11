"""Local empirical protein pKa diagnostics with matched-coordinate comparisons."""

import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MAX_BYTES = 2 * 1024 * 1024
PROTEIN_RESIDUES = set(
    "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL "
    "ASH GLH CYM CYX HID HIE HIP LYN".split()
)
LIMITATIONS = [
    "Empirical PROPKA predictions, not measured pKa, affinity or pH selectivity.",
    "Fractions use independent-site Henderson-Hasselbalch; coupled-site populations are not simulated.",
    "Only a gross observed intraresidue backbone-bond sanity check; no optimization, "
    "sidechain/peptide/stereochemical or structural/glycan collision validation, or atom reconstruction.",
    "Protein ionization groups only; ligand pKa values are not reported.",
]


def _backbone_geometry(content):
    """Reject impossible observed backbone bonds without inferring absent atoms."""
    residues = {}
    segment = 0
    for line in content.splitlines():
        if line.startswith("TER"):
            segment += 1
        if line[:6] not in ("ATOM  ", "HETATM"):
            continue
        residue_name = line[17:20].strip()
        if residue_name not in PROTEIN_RESIDUES:
            continue
        key = (segment, line[21], line[22:27], residue_name)
        atoms = residues.setdefault(key, {})
        name = line[12:16].strip()
        if name not in {"N", "CA", "C", "O", "OXT"}:
            continue
        if name in atoms:
            raise ValueError(
                f"Duplicate protein backbone atom {name}: chain {key[1]!r}, "
                f"residue {key[2].strip()}"
            )
        atoms[name] = tuple(float(line[i : i + 8]) for i in (30, 38, 46))
    checked = 0
    missing = 0
    for key, atoms in residues.items():
        missing += len({"N", "CA", "C", "O"} - atoms.keys())
        for first, second in (("N", "CA"), ("CA", "C"), ("C", "O"), ("C", "OXT")):
            if first not in atoms or second not in atoms:
                continue
            distance = math.dist(atoms[first], atoms[second])
            if not 1.0 <= distance <= 2.2:
                raise ValueError(
                    f"Invalid protein backbone bond {first}-{second}: chain {key[1]!r}, "
                    f"residue {key[2].strip()}, distance {distance:.3f} A "
                    "outside the conservative 1.0-2.2 A input bounds. "
                    "Provide corrected coordinates; this tool does not repair geometry."
                )
            checked += 1
    return {
        "checked_observed_bonds": checked,
        "standard_protein_residues": len(residues),
        "missing_N_CA_C_O_atoms": missing,
        "bond_length_bounds_A": [1.0, 2.2],
        "scope": "Observed standard-protein intraresidue N-CA, CA-C, C-O and C-OXT "
        "only. Does not validate absent atoms, peptide continuity, sidechains, clashes, "
        "glycans or stereochemistry; passing is not complete structural validation.",
    }


def _read_pdb(arguments):
    supplied = [
        key
        for key in ("pdb_id", "pdb_path", "pdb_content")
        if arguments.get(key) is not None
    ]
    if len(supplied) != 1:
        raise ValueError("Provide exactly one of pdb_id, pdb_path or pdb_content")
    key = supplied[0]
    value = arguments[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    if key == "pdb_id":
        if not re.fullmatch(r"[1-9][A-Za-z0-9]{3}", value):
            raise ValueError(
                "pdb_id must be a four-character legacy RCSB PDB identifier"
            )
        with requests.get(
            f"https://files.rcsb.org/download/{value.upper()}.pdb",
            stream=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            chunks, count = [], 0
            for chunk in response.iter_content(65536):
                count += len(chunk)
                if count > MAX_BYTES:
                    raise ValueError("PDB exceeds the 2 MiB input limit")
                chunks.append(chunk)
            raw = b"".join(chunks)
    elif key == "pdb_path":
        with Path(value).expanduser().open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    else:
        raw = value.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("PDB exceeds the 2 MiB input limit")
    content = raw.decode("utf-8")
    lines = content.splitlines()
    if sum(line.startswith("MODEL ") for line in lines) > 1:
        raise ValueError("Multiple PDB models: provide one model explicitly")
    atoms = [line for line in lines if line[:6] in ("ATOM  ", "HETATM")]
    if not any(line.startswith("ATOM  ") for line in atoms):
        raise ValueError("Expected PDB ATOM records; FASTA and mmCIF are unsupported")
    for line in atoms:
        if len(line) < 54:
            raise ValueError("Truncated PDB atom record")
        if line[16].strip():
            raise ValueError("Alternate atom locations: provide one altloc explicitly")
        if not all(math.isfinite(float(line[i : i + 8])) for i in (30, 38, 46)):
            raise ValueError("Nonfinite PDB atom coordinates")
    return content, key, hashlib.sha256(raw).hexdigest()


@register_tool("ProteinPKATool")
class ProteinPKATool(BaseTool):
    def run(self, arguments):
        try:
            ph_values = arguments.get("ph_values")
            if ph_values is None:
                ph_values = [6.5, 7.4]
            if not isinstance(ph_values, list) or not 1 <= len(ph_values) <= 20:
                raise ValueError("ph_values must contain 1 to 20 numbers")
            if any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or not 0 <= v <= 14
                for v in ph_values
            ):
                raise ValueError("pH values must be finite numbers between 0 and 14")
            timeout = arguments.get("timeout_seconds")
            timeout = 180 if timeout is None else timeout
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, int)
                or not 1 <= timeout <= 600
            ):
                raise ValueError("timeout_seconds must be an integer from 1 to 600")
            content, kind, digest = _read_pdb(arguments)
            backbone_geometry = _backbone_geometry(content)
            chain = arguments.get("partner_chain")
            comparing = (
                self.tool_config.get("fields", {}).get("operation") == "compare_partner"
            )
            if comparing:
                if not isinstance(chain, str) or len(chain) != 1:
                    raise ValueError(
                        "partner_chain must be one PDB chain character (space for blank)"
                    )
                keep = arguments.get("free_keep_chains")
                keep = [] if keep is None else keep
                if (
                    not isinstance(keep, list)
                    or len(keep) > 62
                    or any(not isinstance(c, str) or len(c) != 1 for c in keep)
                    or len(set(keep)) != len(keep)
                    or chain in keep
                ):
                    raise ValueError(
                        "free_keep_chains must contain distinct additional one-character chain IDs"
                    )
                records = [
                    line
                    for line in content.splitlines()
                    if line[:6] in ("ATOM  ", "HETATM")
                ]
                present = {line[21] for line in records}
                if any(c not in present for c in keep):
                    raise ValueError(
                        "Requested free_keep_chains contain absent coordinate chains"
                    )
                selected = {chain, *keep}
                lines = [line for line in records if line[21] in selected]
                if not any(
                    line.startswith("ATOM  ") and line[21] == chain for line in lines
                ):
                    raise ValueError(
                        "Requested partner_chain has no protein ATOM records"
                    )
                free_content = "\n".join(lines) + "\nTER\nEND\n"
            if importlib.util.find_spec("propka") is None:
                return {
                    "status": "error",
                    "error": "Optional dependency missing: pip install 'tooluniverse[protein-pka]'",
                }
            with tempfile.TemporaryDirectory(prefix="tu-propka-") as folder:
                directory = Path(folder)
                pdb = directory / "bound.pdb"
                pdb.write_text(content)
                request = {"pdb_path": str(pdb), "ph_values": ph_values}
                if comparing:
                    free = directory / "free.pdb"
                    free.write_text(free_content)
                    request.update(free_path=str(free), partner_chain=chain)
                inp, out = directory / "request.json", directory / "result.json"
                inp.write_text(json.dumps(request))
                worker = Path(__file__).with_name("protein_pka_worker.py")
                run = subprocess.run(
                    [sys.executable, str(worker), str(inp), str(out)],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if run.returncode or not out.exists():
                    return {
                        "status": "error",
                        "error": "PROPKA worker failed",
                        "detail": run.stderr[-2000:],
                    }
                result = json.loads(out.read_text())
            if result["status"] != "success":
                return result
            result["data"].update(
                input_sha256=digest,
                input_kind=kind,
                input_backbone_geometry=backbone_geometry,
                ph_values=ph_values,
                limitations=LIMITATIONS,
                binding_verified=False,
                pH_selectivity_verified=False,
            )
            if comparing:
                result["data"].update(
                    partner_chain=chain,
                    free_partner_chains=[chain, *keep],
                    free_partner_coordinate_records=len(lines),
                    comparison_geometry="Partner extracted from identical bound coordinates; no free-state relaxation",
                    free_partner_sha256=hashlib.sha256(
                        free_content.encode()
                    ).hexdigest(),
                )
            return result
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "PROPKA calculation exceeded timeout_seconds",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
