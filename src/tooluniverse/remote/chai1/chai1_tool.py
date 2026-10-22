"""Chai-1 cofolding — MCP server.

Chai-1 (Chai Discovery, `chai_lab` 0.6.1) folds a complex given its chains as a
FASTA: proteins, ligands as SMILES, nucleic acids. This server is the thin,
CPU-only half of the provider; the model runs in its own environment and is
held resident between requests, because `chai_lab` reloads all six TorchScript
modules -- 5.4 GB of traced ESM among them -- inside every fold otherwise.

Unlike Boltz-2's server there is no subprocess fallback, and that is deliberate
rather than an omission. A per-request Chai-1 process spends most of its wall
clock re-reading weights (67.6 s against 25.7 s held, measured), so a silent
fall back to one would look like the provider working while quietly costing
three times as much. When the resident worker cannot start, this says so and
names the reason.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_FASTA_BYTES = 256 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _fold(
    fasta: str, seed: int, options: Dict[str, Any], return_structures: bool
) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="chai1-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": fasta,
                "out_dir": work,
                "name": "fold",
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            "model": "Chai-1",
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
        }
        for key in ("aggregate_score", "ptm", "iptm"):
            if key in result:
                out[key] = result[key]

        cifs = [p for p in (result.get("files") or []) if p.endswith(".cif")]
        out["n_structures"] = len(cifs)
        if not cifs:
            return {
                "error": "Chai-1 produced no structure for this input.",
                "timing": out["timing"],
            }

        # Off by default, as Boltz-2's tool does it. Five sampled structures of
        # a real complex are megabytes of mmCIF, and an agent that wanted the
        # ranking scores would pay for all of it -- and a reply that large is
        # what a transport truncates, producing a broken answer rather than a
        # refused one.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; "
                "the ranking scores above are returned either way"
            )
            return out

        structures = []
        for path in cifs:
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    structures.append(
                        {
                            "name": os.path.basename(path),
                            "error": "exceeds the public output limit",
                        }
                    )
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    structures.append({"name": os.path.basename(path), "cif": f.read()})
            except (OSError, UnicodeError) as exc:
                structures.append(
                    {"name": os.path.basename(path), "error": type(exc).__name__}
                )
        out["structures"] = structures
        return out


@register_mcp_tool(
    tool_type_name="chai1_fold",
    config={
        "description": (
            "Fold a biomolecular complex with Chai-1 and return the predicted "
            "structures in CIF format with their ranking scores. Input is a "
            "chai-lab FASTA: one record per chain, headers of the form "
            "'>protein|name=A', '>ligand|name=LIG' (sequence line is SMILES), "
            "'>rna|name=R' or '>dna|name=D'. No MSA server is used."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "fasta": {
                    "type": "string",
                    "description": (
                        "chai-lab FASTA. Example:\n"
                        ">protein|name=A\nMKTAYIAKQRQ...\n"
                        ">ligand|name=LIG\nCC(=O)Oc1ccccc1C(=O)O"
                    ),
                    "minLength": 10,
                    "maxLength": MAX_FASTA_BYTES,
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed; the same seed reproduces the fold.",
                    "default": 0,
                    "minimum": 0,
                },
                "num_trunk_recycles": {
                    "type": "integer",
                    "description": "Trunk recycles (default 3). More is slower and usually better.",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                },
                "num_diffn_timesteps": {
                    "type": "integer",
                    "description": "Diffusion steps (default 200).",
                    "default": 200,
                    "minimum": 10,
                    "maximum": 500,
                },
                "num_diffn_samples": {
                    "type": "integer",
                    "description": "Structures to sample and rank (default 5).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text of every sampled structure "
                        "(default false: megabytes). The ranking scores come "
                        "back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["fasta"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "structures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "cif": {"type": "string"},
                        },
                    },
                },
                "n_structures": {"type": "integer"},
                "structures_note": {"type": "string"},
                "aggregate_score": {"type": "array", "items": {"type": "number"}},
                "ptm": {"type": "array", "items": {"type": "number"}},
                "iptm": {"type": "array", "items": {"type": "number"}},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "Chai-1 MCP Server",
        "host": "127.0.0.1",
        "port": 8033,
        "transport": "http",
    },
)
class Chai1FoldTool:
    """Fold one complex. Requests queue: the worker serves one at a time."""

    _BOUNDS = {
        "num_trunk_recycles": (1, 10, 3),
        "num_diffn_timesteps": (10, 500, 200),
        "num_diffn_samples": (1, 10, 5),
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        fasta = arguments.get("fasta")
        if not isinstance(fasta, str) or not fasta.strip().startswith(">"):
            return {"error": "'fasta' must be a chai-lab FASTA beginning with '>'."}
        if len(fasta.encode("utf-8")) > MAX_FASTA_BYTES:
            return {"error": f"'fasta' exceeds {MAX_FASTA_BYTES} bytes."}

        options = {}
        for name, (low, high, default) in self._BOUNDS.items():
            value = arguments.get(name, default)
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{name}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{name}' must be between {low} and {high}."}
            options[name] = value

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        try:
            return _fold(fasta, seed, options, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"Chai-1's resident worker is not available ({reason}). "
                    f"Run `tu remote setup chai1` and read its named refusal; "
                    f"this provider has no subprocess fallback on purpose."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
