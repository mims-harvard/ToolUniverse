"""Offline CPU side-chain pKa predictions with explicit incomplete coverage."""

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .base_tool import BaseTool
from .protein_pka_tool import PROTEIN_RESIDUES, _backbone_geometry, _read_pdb
from .tool_registry import register_tool

SUPPORTED = {"ASP", "GLU", "HIS", "LYS", "CYS", "TYR"}
STANDARD = PROTEIN_RESIDUES - set("ASH GLH CYM CYX HID HIE HIP LYN".split())
REQUIRED = {
    "ASP": {"OD1", "OD2"},
    "GLU": {"OE1", "OE2"},
    "HIS": {"ND1", "NE2"},
    "LYS": {"NZ"},
    "CYS": {"SG"},
    "TYR": {"OH"},
}
LIMITATIONS = [
    "pKAI and pKAI+ are correlated variants of one learned model family, not experiments.",
    "ARG, N-termini and C-termini are not predicted by the supported backend; "
    "this is never a complete protein ionization inventory or a full pH binding cycle.",
    "Close SG pairs are flagged as potentially disulfide-bonded; their CYS predictions "
    "are not eligible for acid-base interpretation without chemistry review.",
    "Only observed backbone bonds and required ionizing atoms are checked; no full "
    "side-chain, peptide, stereochemical, collision, glycan or conformational validation.",
    "HETATM records are ignored by the backend. Protein-only conditional predictions, "
    "not measured pKa, affinity, coupled populations or pH selectivity.",
    "The upstream API rounds pKa values to two decimal places.",
]


def _inventory(content):
    residues, segments = {}, {}
    segment = 0
    hetero = 0
    for line in content.splitlines():
        if line.startswith("TER"):
            segment += 1
        if line.startswith("HETATM"):
            hetero += 1
        if not line.startswith("ATOM  "):
            continue
        chain, number, insertion, name = (
            line[21],
            int(line[22:26]),
            line[26],
            line[17:20].strip(),
        )
        if insertion.strip():
            raise ValueError(
                "pKAI ignores insertion codes; provide an explicitly renumbered structure"
            )
        if name not in STANDARD:
            raise ValueError(
                "pKAI requires standard amino-acid residue names; no silent alias conversion"
            )
        if chain in segments and segments[chain] != segment:
            raise ValueError(
                "A chain ID is reused across TER segments; provide distinct chain IDs"
            )
        segments[chain] = segment
        key = (chain, number)
        residue = residues.setdefault(key, {"name": name, "atoms": {}})
        if residue["name"] != name:
            raise ValueError(
                "Conflicting residue identities at one chain/residue number"
            )
        atom = line[12:16].strip()
        if atom in residue["atoms"]:
            raise ValueError("Duplicate atom names in a protein residue")
        residue["atoms"][atom] = tuple(float(line[i : i + 8]) for i in (30, 38, 46))
    expected = []
    for (chain, number), residue in residues.items():
        name = residue["name"]
        if name in SUPPORTED:
            if not REQUIRED[name] <= residue["atoms"].keys():
                raise ValueError("Missing required ionizing side-chain atom(s)")
            expected.append((chain, number, name))
    if not expected:
        raise ValueError("No supported ionizable side chains in the input")
    cysteines = [
        (key, r["atoms"]["SG"]) for key, r in residues.items() if r["name"] == "CYS"
    ]
    close = set()
    for i, (first, a) in enumerate(cysteines):
        for second, b in cysteines[i + 1 :]:
            if math.dist(a, b) <= 2.3:
                close.update([first, second])
    return sorted(expected), close, hetero


@register_tool("ProteinPKAITool")
class ProteinPKAITool(BaseTool):
    def supports_caching(self):
        # Paths and installed model files can change while arguments stay equal.
        return False

    def run(self, arguments):
        try:
            variant = arguments.get("model_variant")
            variant = "pKAI+" if variant is None else variant
            if variant not in ("pKAI", "pKAI+"):
                raise ValueError("model_variant must be pKAI or pKAI+")
            threads = arguments.get("threads")
            threads = 1 if threads is None else threads
            timeout = arguments.get("timeout_seconds")
            timeout = 180 if timeout is None else timeout
            for value, maximum, label in [
                (threads, 16, "threads"),
                (timeout, 600, "timeout_seconds"),
            ]:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not 1 <= value <= maximum
                ):
                    raise ValueError(f"{label} must be an integer from 1 to {maximum}")
            executable = arguments.get("python_executable")
            executable = sys.executable if executable is None else executable
            if not isinstance(executable, str) or not executable.strip():
                raise ValueError(
                    "python_executable must be a nonempty interpreter path"
                )
            resolved = shutil.which(executable)
            if resolved is None:
                raise ValueError("python_executable was not found")
            content, kind, digest = _read_pdb(arguments)
            expected, close, hetero = _inventory(content)
            geometry = _backbone_geometry(content)
            if geometry["missing_N_CA_C_O_atoms"]:
                raise ValueError("Complete observed N, CA, C and O atoms are required")
            with tempfile.TemporaryDirectory(prefix="tu-pkai-") as folder:
                directory = Path(folder)
                pdb, request, output = [
                    directory / n
                    for n in ["protein.pdb", "request.json", "result.json"]
                ]
                pdb.write_text(content)
                request.write_text(
                    json.dumps(
                        {
                            "pdb_path": str(pdb),
                            "model_variant": variant,
                            "threads": threads,
                        }
                    )
                )
                worker = Path(__file__).with_name("protein_pkai_worker.py")
                run = subprocess.run(
                    [resolved, str(worker), str(request), str(output)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=directory,
                )
                if run.returncode or not output.exists():
                    return {
                        "status": "error",
                        "error": "pKAI worker failed; check the selected interpreter and optional pKAI installation",
                    }
                result = json.loads(output.read_text())
            if result.get("status") != "success":
                return result
            data = result["data"]
            actual = []
            for group in data["groups"]:
                key = (group["chain"], group["residue_number"], group["residue_name"])
                if not math.isfinite(group["pka"]):
                    raise ValueError("Nonfinite pKAI prediction")
                actual.append(key)
                group["close_SG_pair"] = key[:2] in close
                group["eligible_for_acid_base_interpretation"] = not group[
                    "close_SG_pair"
                ]
            if len(actual) != len(set(actual)) or sorted(actual) != expected:
                raise ValueError(
                    "pKAI returned duplicate, missing or unexpected side-chain groups"
                )
            data.update(
                input_kind=kind,
                input_sha256=digest,
                input_backbone_geometry=geometry,
                supported_sidechain_inventory_complete=True,
                expected_sidechain_groups=len(expected),
                complete_protein_ionization_inventory=False,
                unsupported_groups=["ARG", "N+", "C-"],
                close_SG_cysteines=[
                    {"chain": c, "residue_number": n} for c, n in sorted(close)
                ],
                ignored_HETATM_records=hetero,
                limitations=LIMITATIONS,
                binding_verified=False,
                pH_selectivity_verified=False,
            )
            return result
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "pKAI calculation exceeded timeout_seconds",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
