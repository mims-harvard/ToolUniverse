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
LIMITATIONS = [
    "Empirical PROPKA predictions, not measured pKa, affinity or pH selectivity.",
    "Fractions use independent-site Henderson-Hasselbalch; coupled-site populations are not simulated.",
    "No optimization, structural/glycan collision checks, or missing-atom reconstruction.",
    "Protein ionization groups only; ligand pKa values are not reported.",
]


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
            chain = arguments.get("partner_chain")
            comparing = (
                self.tool_config.get("fields", {}).get("operation") == "compare_partner"
            )
            if comparing:
                if not isinstance(chain, str) or len(chain) != 1:
                    raise ValueError(
                        "partner_chain must be one PDB chain character (space for blank)"
                    )
                lines = [
                    line
                    for line in content.splitlines()
                    if line[:6] in ("ATOM  ", "HETATM") and line[21] == chain
                ]
                if not any(line.startswith("ATOM  ") for line in lines):
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
                ph_values=ph_values,
                limitations=LIMITATIONS,
                binding_verified=False,
                pH_selectivity_verified=False,
            )
            if comparing:
                result["data"].update(
                    partner_chain=chain,
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
