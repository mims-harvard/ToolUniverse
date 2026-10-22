"""AtlasFold all-atom structure prediction — MCP server.

AtlasFold v1.0.0 folds protein sequences into all-atom structures: one chain
through its monomer head, or several chains of one complex through its
AtlasFold-M head. This server is the thin, CPU-only half of the provider; the
model runs in its own environment (torch 2.7.1+cu128 with cuEquivariance 0.10.0,
a stack this one cannot import) and is held resident between requests.

Measured on an NVIDIA GB10, upstream's default five diffusion samples, one held
worker: 2.9-3.6 s at 35 residues, 12.5 s at 100, 33.0 at 200, 122.3 at 400 and
609.6 at 800, with peak reserved 12.06 GiB up to 200 residues, 13.84 at 400 and
38.63 at 800. That reserve RATCHETS -- a worker that has served one 800-residue
chain holds 38.63 GiB until it retires -- so a deployment that caps requests
well below 800 gets a far smaller provider.

What residency buys here is the model load, not a CUDA graph. Upstream loads
6.1 GiB of AtlasLM-3B plus an 860 MB folding head inside every invocation of its
CLI, and the optimization kit's own README prices the per-run overhead at
"≈11 s start-up and model load: ≈15 s per Run example". The held worker pays
that once. `weights_held_by` on every reply says `worker`, because nothing in
the kit replaces that loader and so the worker is what memoises it.

Three things an operator needs and will not guess:

* **Monomer and multimer are two models, and only one is held.** Each head
  carries its own copy of the 6.1 GiB language model, so holding both would
  nearly double the footprint. A request for the other type drops the held one
  and loads it, which costs one model load and is reported as
  `timing.model_switch`. Sending a mixed batch is refused rather than guessed.
* **On this card the kit runs with thirteen of its thirty levers switched
  off, and the triangle kernels are upstream's torch ones.** `triton==3.3.1`,
  which the kit's lock pins, cannot emit code for compute capability 12.1 at
  all: it aborts the process with `LLVM ERROR: Cannot select: intrinsic
  %llvm.nvvm.shfl.sync.bfly.i32`. So every Triton-backed lever is ablated
  through the kit's own door, and `--kernel torch` replaces upstream's default
  `auto` -- which on this stack would abort even with the kit switched off
  entirely, because cuEquivariance 0.10.0's fused LayerNorm is itself a Triton
  kernel. The worker decides this at start-up with a child-process probe and
  reports it: `kernel_backend` and `triton_usable` are on every reply. What
  survives is the kit's memory half, which is 4.6 GiB (19%) better than stock at
  600 residues. `kit_gates_ok` reports the kit's own verdict per request rather
  than hiding it in an exit code.
* **Confidence always comes back; the structure text does not.** With upstream's
  default of five diffusion samples per seed, ranking them is the one thing a
  caller must do, and `scores` (avg_plddt, ptm per sample) plus `ranked` is how.
  The mmCIF text is opt-in because an all-atom file of a few hundred residues is
  megabytes, and a reply that large is what a transport truncates -- producing a
  broken answer rather than a refused one.

A request-level failure and a worker-launch failure are reported separately and
deliberately. Flattening both into "the worker is not available, re-run setup"
throws away upstream's own account of what went wrong, which is the only thing
that diagnoses a fold that did not happen.
"""

import os
from typing import Any, Dict, List, Tuple

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CHAINS = 16
# Where the provider's VRAM budget was MEASURED (38.63 GiB at 800 residues; the
# ladder is in provider.toml). A longer chain needs it re-measured, not a larger
# constant here -- 800 residues already costs 3.2x what 100 does.
MAX_RESIDUES_TOTAL = 800
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# Upstream's 20 canonical letters plus the ambiguity and non-standard codes its
# tokenizer accepts. A ligand or nucleic acid is NOT in this provider's surface:
# AtlasFold v1.0.0's two CLIs take protein FASTA only.
_PROTEIN = set("ACDEFGHIKLMNPQRSTVWYXBZUO")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate_chains(chains: Any) -> Tuple[str, int]:
    """Return ``(sequence, n_residues)`` for one target, or raise ValueError.

    Several chains become one ':'-joined record, which is upstream's and the
    kit's own convention for the multimer head ("multimer: a record's chains
    joined with ':'").
    """
    if isinstance(chains, str):
        chains = [chains]
    if not isinstance(chains, list) or not chains:
        raise ValueError("'chains' must be a non-empty array of protein sequences.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per complex.")

    out: List[str] = []
    total = 0
    for i, chain in enumerate(chains):
        if not isinstance(chain, str) or not chain.strip():
            raise ValueError(f"chain {i}: must be a non-empty amino-acid string.")
        seq = chain.strip().upper().replace(" ", "")
        if ":" in seq:
            raise ValueError(
                f"chain {i}: ':' separates chains, so give each chain as its own "
                f"array element rather than joining them."
            )
        bad = sorted(set(seq) - _PROTEIN)
        if bad:
            raise ValueError(
                f"chain {i}: not an amino-acid sequence — unexpected letters {bad}. "
                f"AtlasFold v1.0.0 folds protein only; it has no ligand, DNA or "
                f"RNA input."
            )
        out.append(seq)
        total += len(seq)

    if total > MAX_RESIDUES_TOTAL:
        raise ValueError(
            f"{total} residues exceeds this server's {MAX_RESIDUES_TOTAL} limit, "
            f"which is where the provider's VRAM budget was derived (11.5 GiB). "
            f"Most of that budget is a 3-billion-parameter language model that "
            f"does not grow with the input, so the budget rises gently with "
            f"length — but it has not been measured past 800 residues, and a "
            f"longer chain needs it re-measured rather than a larger limit here."
        )
    return ":".join(out), total


def _fold(
    sequence: str,
    name: str,
    seeds: List[int],
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="atlasfold-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                # The worker's native form: FASTA text, which is the only input
                # the stock CLI takes (-i/--input-fasta).
                "input": f">{name}\n{sequence}\n",
                "out_dir": work,
                "name": name,
                "seed": seeds,
                "options": options,
                "include_structure_text": bool(return_structures),
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            "model": result.get("model"),
            "model_type": result.get("model_type"),
            "n_structures": result.get("n_structures"),
            # Per-sample avg_plddt and ptm, and which sample upstream ranked
            # best. With five samples per seed this is what a caller ranks on.
            "scores": result.get("scores"),
            "ranked": result.get("ranked"),
            "seeds": result.get("seeds"),
            "kernel_backend": result.get("kernel_backend"),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
            "kit_levers_off": result.get("kit_levers_off"),
            # Whether this host's Triton can compile for its GPU. False means
            # the kit is running with its kernel levers ablated and the
            # triangle operations on upstream's torch statement -- correct
            # results, a different speed and memory profile. See provider.toml.
            "triton_usable": result.get("triton_usable"),
        }
        # The kit's own per-request verdict. A refused gate means a lever took an
        # UNEXPECTED fallback: the structures are complete, but they were not
        # produced the way the declared mode says, which is a thing an operator
        # must be able to see without reading a worker log.
        if result.get("kit_gates_ok") is False:
            out["kit_gates_refused"] = result.get("kit_gates_refused")
            out["note"] = (
                "the structures are complete, but the optimization kit refused "
                "one or more lever gates on this request: a lever fell back to "
                "the stock statement for a reason its author did not expect. "
                "See kit_gates_refused."
            )

        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; the "
                "confidence scores come back either way"
            )
            return out

        texts = []
        for entry in result.get("structure_text") or []:
            if entry.get("error"):
                texts.append(entry)
                continue
            text = entry.get("text") or ""
            if len(text.encode("utf-8", "ignore")) > MAX_STRUCTURE_BYTES:
                texts.append(
                    {
                        "name": entry.get("name"),
                        "error": "exceeds the public output limit",
                    }
                )
                continue
            texts.append({"name": entry.get("name"), "structure": text})
        out["structures"] = texts
        return out


@register_mcp_tool(
    tool_type_name="atlasfold_predict",
    config={
        "description": (
            "Predict an all-atom protein structure with AtlasFold v1.0.0. Give "
            "one sequence in 'chains' for a monomer, or several for one complex "
            "(folded by the AtlasFold-M multimer head). Returns per-sample "
            "confidence scores (avg_plddt, pTM) and which sample ranked best; "
            "the mmCIF text itself is opt-in. Protein only -- this model has no "
            "ligand, DNA or RNA input."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "chains": {
                    "type": "array",
                    "description": (
                        "The amino-acid sequences of one target. One element "
                        "folds through the monomer head; two or more are one "
                        "complex folded through the multimer head."
                    ),
                    "minItems": 1,
                    "maxItems": MAX_CHAINS,
                    "items": {"type": "string", "minLength": 1},
                },
                "name": {
                    "type": "string",
                    "description": "A label for the target; appears in the output names.",
                    "default": "target",
                },
                "seeds": {
                    "type": "array",
                    "description": (
                        "Random seeds. Each seed produces num_samples "
                        "structures, so total structures is seeds x "
                        "num_samples. Upstream's default is the single seed 1."
                    ),
                    "items": {"type": "integer", "minimum": 0},
                    "minItems": 1,
                    "maxItems": 5,
                },
                "num_samples": {
                    "type": "integer",
                    "description": (
                        "Diffusion samples per seed (upstream's default is 5). "
                        "Each is scored separately, so this is how to compare "
                        "conformations; rank them on `scores`."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
                "num_recycles": {
                    "type": "integer",
                    "description": (
                        "Recycling iterations (upstream's default is 4 for a "
                        "monomer, 10 for a multimer). More costs time, not "
                        "memory."
                    ),
                    "minimum": 0,
                    "maximum": 20,
                },
                "num_steps": {
                    "type": "integer",
                    "description": (
                        "Diffusion sampling steps. Omit for upstream's own "
                        "length-dependent default (20 up to 512 tokens, 30 to "
                        "1024, 100 above; 200 for a multimer)."
                    ),
                    "minimum": 1,
                    "maximum": 500,
                },
                "format": {
                    "type": "string",
                    "enum": ["cif", "pdb"],
                    "description": "Structure file format (default cif).",
                    "default": "cif",
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the structure text (default false: an all-atom "
                        "file of a few hundred residues is megabytes). The "
                        "confidence scores come back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["chains"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "model_type": {"type": "string"},
                "n_structures": {"type": "integer"},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "scores": {"type": "object"},
                "ranked": {"type": "object"},
                "seeds": {"type": "array", "items": {"type": "integer"}},
                "kernel_backend": {"type": "string"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "triton_usable": {"type": "boolean"},
                "kit_mode": {"type": "string"},
                "kit_levers_off": {"type": "string"},
                "kit_gates_refused": {"type": "array", "items": {"type": "object"}},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AtlasFold MCP Server",
        "host": "127.0.0.1",
        "port": 8043,
        "transport": "http",
    },
)
class AtlasFoldPredictTool:
    """Fold one target. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequence, _residues = _validate_chains(arguments.get("chains"))
        except ValueError as exc:
            return {"error": str(exc)}

        name = arguments.get("name", "target")
        if not isinstance(name, str) or not name.strip():
            return {"error": "'name' must be a non-empty string."}
        name = name.strip()
        if any(c in name for c in "/\\ \t") or name in {".", ".."}:
            return {
                "error": (
                    "'name' becomes a directory name, so it must not contain "
                    "spaces, slashes or path components."
                )
            }

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        seeds = arguments.get("seeds", [1])
        if not isinstance(seeds, list) or not seeds or len(seeds) > 5:
            return {"error": "'seeds' must be an array of 1 to 5 integers."}
        for value in seeds:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return {"error": "'seeds' must contain non-negative integers."}

        options: Dict[str, Any] = {}
        for key, low, high in (
            ("num_samples", 1, 10),
            ("num_recycles", 0, 20),
            ("num_steps", 1, 500),
        ):
            if key not in arguments:
                continue
            value = arguments[key]
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{key}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{key}' must be between {low} and {high}."}
            options[key] = value

        fmt = arguments.get("format", "cif")
        if fmt not in ("cif", "pdb"):
            return {"error": "'format' must be 'cif' or 'pdb'."}
        options["format"] = fmt

        try:
            return _fold(sequence, name, seeds, options, return_structures)
        except WorkerStartError as exc:
            # The PROVIDER, not the request: nothing was folded because nothing
            # could be started. Named separately from the case below on purpose.
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"AtlasFold's resident worker is not available ({reason}). "
                    f"Run `tu remote setup atlasfold` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }
        except WorkerRequestError as exc:
            # The REQUEST, not the provider. The worker lets upstream's own
            # exception propagate instead of going through the kit's cmd_pred,
            # which would have printed it and returned an exit code -- so the
            # text below is AtlasFold's own account and is passed through
            # rather than flattened.
            return {
                "error": f"AtlasFold could not fold this target: {exc}",
                "note": (
                    "this is a failure of the request, not of the provider: the "
                    "worker is up and holding the model, and the next request "
                    "will be served. The run's own PHASE / LEVER / NOT ACTIVE "
                    "lines are in the worker transcript at "
                    "~/.cache/tooluniverse/remote-logs/atlasfold-resident.log."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"AtlasFold failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
