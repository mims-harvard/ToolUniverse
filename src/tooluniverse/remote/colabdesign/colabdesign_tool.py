"""ColabDesign binder design (BindCraft's hallucination step) -- MCP server.

BindCraft's design step on stock ColabDesign 1.1.3 and the public
AlphaFold-Multimer v3 parameters (DeepMind's 2022-12-06 release, CC BY 4.0), held
resident between requests. This server is the thin, CPU-only half of the provider;
the model runs in its own environment (CPython 3.10, jax 0.6.0 with the CUDA 12
plugin, a stack ToolUniverse's cannot import).

THREE THINGS AN OPERATOR NEEDS AND WILL NOT GUESS
-------------------------------------------------
* **There is no alignment and no external service.** Binder hallucination runs
  AlphaFold-Multimer backwards from a loss, with the target's backbone as the
  template and a single sequence for the binder. Nothing is searched, nothing is
  fetched, and no MSA server exists on any route of this provider.
* **One request is one trajectory, and the first of each SHAPE is slow.** Every
  distinct (target residues, binder length, recycles) triple is a different set of
  XLA programs; the first request of one pays the compile, which is minutes. The
  reply says ``first_of_engine_key``. A trajectory that fails BindCraft's own
  pLDDT gates is still a completed request: it returns its best sequence with
  ``accepted_by_stage_gates`` false and the gate named. Judge the design, not the
  reply.
* **Only the design step runs.** BindCraft's redesign (MPNN), reprediction, PyRosetta
  relaxation and filtering stages are not part of this provider, so the sequences
  returned are a hallucination's output, not filtered final designs.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason -- separately from a request the model itself refused.
"""

import json
import os
import re
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
# The row the VRAM budget was measured at (provider.toml [gpu]): target residues
# plus binder length. Peak memory and time both track it, so the ceiling is the
# budget's envelope and not a separate number.
MAX_TOKENS = 400
MIN_BINDER, MAX_BINDER = 8, 250
MAX_PDB_BYTES = 8 * 1024 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
MAX_CHAINS_REQUESTED = 4
ITERATION_BOUNDS = {
    "soft_iterations": (50, 200),
    "temporary_iterations": (0, 100),
    "hard_iterations": (0, 50),
    "greedy_iterations": (0, 50),
}
RECYCLE_BOUNDS = (1, 3)
_ALLOWED_FIELDS = {
    "target_pdb", "chain", "binder_len", "hotspot", "seed", "name",
    "num_recycles_design", "return_structures", *ITERATION_BOUNDS,
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _target_residues(pdb_text: str, chains: list) -> Dict[str, int]:
    """Residues with a CA atom per requested chain, as the kit counts them."""
    seen = {c: set() for c in chains}
    for line in pdb_text.splitlines():
        if len(line) < 27 or not line.startswith("ATOM"):
            continue
        if line[12:16].strip() != "CA" or line[16] not in (" ", "A"):
            continue
        c = line[21]
        if c in seen:
            seen[c].add(line[22:27])
    return {c: len(v) for c, v in seen.items()}


def _check(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the request; return the document the worker takes, or {'error': ...}."""
    pdb = arguments.get("target_pdb")
    if not isinstance(pdb, str) or "ATOM" not in pdb:
        return {"error": "'target_pdb' must be PDB text with ATOM records."}
    if len(pdb.encode("utf-8", "ignore")) > MAX_PDB_BYTES:
        return {"error": f"'target_pdb' exceeds {MAX_PDB_BYTES // (1024 * 1024)} MB."}

    chain = arguments.get("chain", "A")
    if not isinstance(chain, str):
        return {"error": "'chain' must be a string such as 'A' or 'A,B'."}
    chains = [c.strip() for c in chain.replace("+", ",").split(",") if c.strip()]
    if not chains or any(len(c) != 1 or not c.isalnum() for c in chains):
        return {
            "error": "'chain' is one or more single-character chain ids, e.g. 'A' or 'A,B'."
        }
    if len(chains) > MAX_CHAINS_REQUESTED:
        return {"error": f"at most {MAX_CHAINS_REQUESTED} target chains."}
    counts = _target_residues(pdb, chains)
    empty = [c for c, n in counts.items() if n == 0]
    if empty:
        return {"error": f"chain(s) {','.join(empty)} have no CA atom in 'target_pdb'."}

    binder_len = arguments.get("binder_len")
    if not isinstance(binder_len, int) or isinstance(binder_len, bool):
        return {"error": "'binder_len' must be an integer."}
    if not MIN_BINDER <= binder_len <= MAX_BINDER:
        return {"error": f"'binder_len' must be between {MIN_BINDER} and {MAX_BINDER}."}
    target_res = sum(counts.values())
    tokens = target_res + binder_len
    if tokens > MAX_TOKENS:
        return {
            "error": (
                f"{tokens} tokens ({target_res} target residues + a binder of "
                f"{binder_len}) exceeds this server's {MAX_TOKENS}, the row the "
                f"provider's VRAM budget was measured at. Peak memory and time both "
                f"grow with the token count, so a larger request needs the budget "
                f"re-measured, not the limit raised. Crop the target to the region "
                f"around the site you want to bind -- BindCraft's own advice."
            )
        }

    doc: Dict[str, Any] = {
        "target_pdb": pdb,
        "chain": ",".join(chains),
        "binder_len": binder_len,
    }

    hotspot = arguments.get("hotspot")
    if hotspot is not None:
        if not isinstance(hotspot, str) or not re.fullmatch(r"[A-Za-z0-9,\-\s]*", hotspot):
            return {
                "error": (
                    "'hotspot' is BindCraft's target_hotspot_residues grammar, e.g. "
                    "'56', '31,33,57', 'A31,A33' or 'A1-10'."
                )
            }
        if hotspot.strip():
            doc["hotspot"] = hotspot.strip()

    seed = arguments.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        return {"error": "'seed' must be a non-negative integer."}
    doc["seed"] = seed

    name = arguments.get("name", "design")
    if not isinstance(name, str) or not name.strip():
        return {"error": "'name' must be a non-empty string."}
    doc["name"] = name.strip()

    recycles = arguments.get("num_recycles_design")
    if recycles is not None:
        if not isinstance(recycles, int) or isinstance(recycles, bool):
            return {"error": "'num_recycles_design' must be an integer."}
        if not RECYCLE_BOUNDS[0] <= recycles <= RECYCLE_BOUNDS[1]:
            return {
                "error": (
                    f"'num_recycles_design' must be between {RECYCLE_BOUNDS[0]} and "
                    f"{RECYCLE_BOUNDS[1]}."
                )
            }
        doc["num_recycles_design"] = recycles

    for key, (lo, hi) in ITERATION_BOUNDS.items():
        if key not in arguments:
            continue
        v = arguments[key]
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            return {"error": f"'{key}' must be an integer between {lo} and {hi}."}
        doc[key] = v
    return {"doc": doc, "tokens": tokens}


def _design(doc: Dict[str, Any], return_structures: bool) -> Dict[str, Any]:
    """One trajectory on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="colabdesign-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(doc),
                "out_dir": work,
                "name": doc.get("name", "design"),
                "seed": doc.get("seed", 0),
                "options": {},
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            "model": result.get("model"),
            "sequences": result.get("sequences"),
            "accepted_by_stage_gates": result.get("accepted_by_stage_gates"),
            "terminate": result.get("terminate"),
            "gate_fired": result.get("gate_fired"),
            "final": result.get("final"),
            "best_metric": result.get("best_metric"),
            "best_metric_name": result.get("best_metric_name"),
            "n_steps": result.get("n_steps"),
            "phases_run": result.get("phases_run"),
            "tokens": result.get("tokens"),
            "target_residues": result.get("target_residues"),
            "binder_len": result.get("binder_len"),
            "hotspot": result.get("hotspot"),
            "seed": result.get("seed"),
            "num_recycles_design": result.get("num_recycles_design"),
            "iterations": result.get("iterations"),
            "optimise_beta": result.get("optimise_beta"),
            "engine_key": result.get("engine_key"),
            "first_of_engine_key": result.get("first_of_engine_key"),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
            "output_sha256": result.get("output_sha256"),
        }
        if not return_structures:
            out["structure_note"] = (
                "pass return_structures=true to receive design.pdb and "
                "trajectory.jsonl; the sequences and scores come back either way"
            )
            return out

        texts = {}
        for path in result.get("files") or []:
            name = os.path.basename(str(path))
            if name not in ("design.pdb", "trajectory.jsonl"):
                continue
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    texts[name] = {"error": "exceeds the public output limit"}
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    texts[name] = f.read()
            except (OSError, UnicodeError) as exc:
                texts[name] = {"error": type(exc).__name__}
        out["design_pdb"] = texts.get("design.pdb")
        out["trajectory_jsonl"] = texts.get("trajectory.jsonl")
        return out


@register_mcp_tool(
    tool_type_name="colabdesign_design",
    config={
        "description": (
            "Design a protein BINDER against a target structure with BindCraft's "
            "binder-hallucination step on ColabDesign 1.1.3 and AlphaFold-Multimer "
            "v3. Give the target as PDB text, its chain, the binder length and "
            "optionally hotspot residues. No alignment is needed and no external "
            "service is contacted. One call is one trajectory (gradient-based "
            "sequence optimisation through the structure predictor): it returns the "
            "best binder sequence, whether the trajectory passed BindCraft's own "
            "pLDDT gates, and the final confidence terms. Only the design step runs "
            "-- no MPNN redesign, reprediction, relaxation or filtering. The first "
            "request of each (target residues, binder length, recycles) shape "
            "compiles for minutes."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "target_pdb": {
                    "type": "string",
                    "description": (
                        "The target structure as PDB text (ATOM records). Crop it to "
                        "the region around the binding site: target residues plus "
                        f"binder length may not exceed {MAX_TOKENS}."
                    ),
                },
                "chain": {
                    "type": "string",
                    "description": (
                        "Target chain id(s) in the PDB, e.g. 'A' or 'A,B'."
                    ),
                    "default": "A",
                },
                "binder_len": {
                    "type": "integer",
                    "description": "Length of the binder to design, in residues.",
                    "minimum": MIN_BINDER,
                    "maximum": MAX_BINDER,
                },
                "hotspot": {
                    "type": "string",
                    "description": (
                        "Target residues the binder should contact, in BindCraft's "
                        "grammar: '56', '31,33,57', 'A31,A33' or 'A1-10'. Omit for no "
                        "hotspot."
                    ),
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed for the trajectory.",
                    "default": 0,
                    "minimum": 0,
                },
                "name": {
                    "type": "string",
                    "description": "A job name; it prefixes the design's name.",
                    "default": "design",
                },
                "num_recycles_design": {
                    "type": "integer",
                    "description": (
                        "AlphaFold recycles per design step (BindCraft's default is "
                        "1). Part of the compiled program, so changing it recompiles."
                    ),
                    "minimum": RECYCLE_BOUNDS[0],
                    "maximum": RECYCLE_BOUNDS[1],
                },
                "soft_iterations": {
                    "type": "integer",
                    "description": (
                        "Stage-1 logit iterations (BindCraft default 75). Upstream "
                        "hard-codes the first 50, so values below 50 are not accepted."
                    ),
                    "minimum": ITERATION_BOUNDS["soft_iterations"][0],
                    "maximum": ITERATION_BOUNDS["soft_iterations"][1],
                },
                "temporary_iterations": {
                    "type": "integer",
                    "description": "Stage-2 softmax iterations (BindCraft default 45).",
                    "minimum": ITERATION_BOUNDS["temporary_iterations"][0],
                    "maximum": ITERATION_BOUNDS["temporary_iterations"][1],
                },
                "hard_iterations": {
                    "type": "integer",
                    "description": "Stage-3 one-hot iterations (BindCraft default 5).",
                    "minimum": ITERATION_BOUNDS["hard_iterations"][0],
                    "maximum": ITERATION_BOUNDS["hard_iterations"][1],
                },
                "greedy_iterations": {
                    "type": "integer",
                    "description": (
                        "Stage-4 PSSM semi-greedy iterations (BindCraft default 15)."
                    ),
                    "minimum": ITERATION_BOUNDS["greedy_iterations"][0],
                    "maximum": ITERATION_BOUNDS["greedy_iterations"][1],
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the design PDB text and the per-step trajectory "
                        "(default false). Sequences and scores come back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["target_pdb", "binder_len"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "sequences": {"type": "array", "items": {"type": "string"}},
                "accepted_by_stage_gates": {"type": "boolean"},
                "terminate": {"type": ["string", "null"]},
                "gate_fired": {"type": ["string", "null"]},
                "final": {"type": "object"},
                "best_metric": {"type": "number"},
                "best_metric_name": {"type": "string"},
                "n_steps": {"type": "integer"},
                "phases_run": {"type": ["array", "object", "string", "integer"]},
                "tokens": {"type": "integer"},
                "target_residues": {"type": "integer"},
                "binder_len": {"type": "integer"},
                "hotspot": {"type": ["string", "null"]},
                "seed": {"type": "integer"},
                "num_recycles_design": {"type": "integer"},
                "iterations": {"type": "object"},
                "optimise_beta": {"type": "boolean"},
                "engine_key": {"type": "array", "items": {"type": "integer"}},
                "first_of_engine_key": {"type": "boolean"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "output_sha256": {"type": "object"},
                "design_pdb": {"type": ["string", "null"]},
                "trajectory_jsonl": {"type": ["string", "null"]},
                "structure_note": {"type": "string"},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "ColabDesign MCP Server",
        "host": "127.0.0.1",
        "port": 8054,
        "transport": "http",
    },
)
class ColabDesignDesignTool:
    """Design one binder. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        unknown = sorted(set(arguments) - _ALLOWED_FIELDS)
        if unknown:
            return {
                "error": (
                    f"unknown field(s) {unknown}; this tool accepts "
                    f"{sorted(_ALLOWED_FIELDS)}. BindCraft's other advanced settings "
                    f"are not exposed: each would change the work or the shapes the "
                    f"VRAM budget was measured at."
                )
            }

        checked = _check(arguments)
        if "error" in checked:
            return checked

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        try:
            return _design(checked["doc"], return_structures)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"ColabDesign's resident worker is not available ({reason}). "
                    f"Run `tu remote setup colabdesign` and read its named refusal; "
                    f"this provider has no subprocess fallback."
                ),
                "note": (
                    "two causes are specific to this provider: the AlphaFold-Multimer "
                    "v3 parameters absent or off their pins under "
                    "COLABDESIGN_PARAMS_DIR, and the kit not installed into the "
                    "interpreter TOOLUNIVERSE_COLABDESIGN_PYTHON names."
                ),
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The model stays up; this text is
            # the worker's own account of why THIS input did not design.
            return {
                "error": f"ColabDesign could not design against this target: {exc}",
                "note": (
                    "BindCraft's design step needs backbone coordinates for the "
                    "target chain(s) named in 'chain'; a hotspot must name residues "
                    "that exist in the PDB's own numbering."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"ColabDesign failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
