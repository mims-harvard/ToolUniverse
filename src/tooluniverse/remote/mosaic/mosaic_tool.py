"""mosaic binder design (Boltz-2 hallucination) -- MCP server.

``mosaic`` (escalante-bio) DESIGNS a protein binder by gradient descent through a
differentiable structure predictor. It is not a folder you hand a sequence to:
you give it a TARGET protein sequence and a binder LENGTH, and it invents the
binder. The predictor is Boltz-2, converted to a JAX module; the loss is
``2*BinderTargetContact + WithinBinderContact + 5*InverseFoldingSequenceRecovery``
(ProteinMPNN); the optimiser is 75 + 50 steps of simplex accelerated projected
gradient on a position-weight matrix over the 20 amino acids; and the result is
refolded once to score it. **Every optimiser step is a full Boltz-2 forward and
backward pass**, which is why one request is minutes, not seconds.

This server is the thin, CPU-only half of the provider. The model runs in its own
environment (CPython 3.12.1, jax 0.10.2 with the CUDA 12 plugin, a stack
ToolUniverse's cannot import) and is held resident between requests.

ONE REQUEST IS ONE DESIGN. One target, one binder length, one seed, one binder
sequence plus the predicted complex and its confidence. A campaign is many
requests, which is exactly the shape residency is for: the first request into a
new SHAPE (target residues x copies + binder length) pays an XLA compilation of
minutes, and every later request of that shape does not.

THINGS A CALLER WILL NOT GUESS
------------------------------
* **No alignment is built or fetched.** The target is run single-sequence and no
  MSA server is contacted. That is upstream's ``use_msa=False``.
* **Designs are stochastic in the seed and not bit-reproducible across requests.**
  Boltz's featuriser re-draws reference coordinates every time, so the same
  request twice gives the same design to roughly three figures, not byte for
  byte. Vary ``seed`` to get different designs.
* **``iptm`` is the number to read, and it is the model's opinion of its own
  design.** The binder was optimised against this same predictor, so a high ipTM
  is not evidence the binder binds. It ranks designs against each other.
* **Cost is set by the token count** (target residues x copies + binder length),
  bounded here at ``MAX_TOKENS``; ``steps1``/``steps2`` change time linearly and
  memory not at all.

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

# These mirror the worker's module constants exactly. Restated here because this
# process must not import anything from the model's environment, and checked
# here as well because a ceiling only the worker knows is one a caller finds by
# having a request fail minutes in.
#
# MAX_TOKENS is the envelope the declared [gpu] vram_budget_gb was measured at
# (see provider.toml), not a convenient number. The three per-field ceilings are
# individually sane and their product is not unbounded only because of this one:
# 200-residue binder + 4 copies of a 376-residue target would be 1704 tokens.
# 512 tokens was MEASURED and is outside the ceiling on purpose: about 120 s per
# optimiser step on an otherwise quiet card, so one 125-step design is ~4 hours.
MAX_TOKENS = 384
MIN_BINDER = 8
MAX_BINDER = 200
MAX_COPIES = 4
MAX_TARGET = 376
MAX_STEPS = 400
MAX_STRUCTURE_BYTES = 4 * 1024 * 1024
_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """The worker's input document, or ValueError naming what is wrong."""
    seq = arguments.get("target_sequence")
    if not isinstance(seq, str) or not seq.strip():
        raise ValueError("'target_sequence' must be a non-empty protein sequence.")
    seq = re.sub(r"\s+", "", seq).upper()
    bad = sorted(set(seq) - _AA)
    if bad:
        raise ValueError(
            f"'target_sequence' has letters outside the 20 standard amino acids: {bad}."
        )
    if len(seq) > MAX_TARGET:
        raise ValueError(
            f"'target_sequence' is {len(seq)} residues; the limit is {MAX_TARGET}."
        )
    spec: Dict[str, Any] = {"target_sequence": seq}
    for name, default, low, high in (
        ("binder_length", 80, MIN_BINDER, MAX_BINDER),
        ("target_copies", 1, 1, MAX_COPIES),
        ("steps1", 75, 1, MAX_STEPS),
        ("steps2", 50, 1, MAX_STEPS),
    ):
        value = arguments.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"'{name}' must be an integer.")
        if not low <= value <= high:
            raise ValueError(f"'{name}' must be between {low} and {high}.")
        spec[name] = value
    epitope = arguments.get("epitope")
    if epitope is not None:
        if not isinstance(epitope, str) or not re.fullmatch(
            r"\s*\d+(\s*-\s*\d+)?(\s*,\s*\d+(\s*-\s*\d+)?)*\s*", epitope
        ):
            raise ValueError(
                "'epitope' must look like '12,15,40-48': 1-based residue positions "
                "along 'target_sequence', comma-separated, ranges inclusive."
            )
        spec["epitope"] = epitope.replace(" ", "")
    tokens = len(seq) * spec["target_copies"] + spec["binder_length"]
    if tokens > MAX_TOKENS:
        raise ValueError(
            f"{tokens} tokens (target {len(seq)} x {spec['target_copies']} + binder "
            f"{spec['binder_length']}) exceeds this server's {MAX_TOKENS}-token "
            f"limit, the envelope the provider's VRAM budget was measured at. The "
            f"pair track scales as N^2, so a larger request needs the budget "
            f"re-measured rather than the limit raised."
        )
    return spec


def _design(spec: Dict[str, Any], seed: int, return_structure: bool) -> Dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="mosaic-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(spec),
                "out_dir": work,
                "name": "design",
                "seed": seed,
                "options": {},
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            k: result.get(k)
            for k in (
                "model",
                "binder_sequence",
                "binder_length",
                "target_copies",
                "n_tokens",
                "epitope",
                "seed",
                "steps",
                "scores",
                "sequence_sharpness",
                "loss",
                "shape_compiled_before",
                "shapes_held",
                "requests_served",
                "timing",
                "peak_reserved_gib",
                "peak_in_use_gib",
                "weights_held_by",
                "kit_mode",
            )
        }
        # The PDB is opt-in and returned as TEXT, never as a path: the temporary
        # directory it was written to is removed before this function returns,
        # and a path that was true for a millisecond is worse than an absent field.
        pdbs = [p for p in (result.get("files") or []) if p.endswith("_complex.pdb")]
        if not return_structure:
            out["structure_note"] = (
                "pass return_structure=true to receive the designed complex as PDB "
                "text (binder is chain A, then the target copies); the sequence and "
                "scores come back either way"
            )
            return out
        if not pdbs:
            out["structure_error"] = "the worker reported no complex file"
            return out
        try:
            if os.path.getsize(pdbs[0]) > MAX_STRUCTURE_BYTES:
                out["structure_error"] = "exceeds the public output limit"
            else:
                with open(pdbs[0], "r", encoding="utf-8") as fh:
                    out["complex_pdb"] = fh.read()
        except (OSError, UnicodeError) as exc:
            out["structure_error"] = type(exc).__name__
        return out


@register_mcp_tool(
    tool_type_name="mosaic_design_binder",
    config={
        "description": (
            "Design a protein binder against a target protein by gradient "
            "descent through Boltz-2 (escalante-bio/mosaic). Give the target's "
            "amino-acid sequence and a binder length; it invents the binder: 125 "
            "optimiser steps, each a full Boltz-2 forward+backward pass under a "
            "contact + inverse-folding loss, then one refold to score the result. "
            "Returns the binder sequence, ipTM, pLDDT and binder-to-target PAE, "
            "and (opt-in) the designed complex as PDB text. Single-sequence: no "
            "MSA is built or fetched. A request takes minutes; the first request "
            "of a new size also pays a compilation of minutes."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "target_sequence": {
                    "type": "string",
                    "description": (
                        "The target protein, one chain, standard amino acids only."
                    ),
                    "minLength": 1,
                    "maxLength": MAX_TARGET,
                },
                "binder_length": {
                    "type": "integer",
                    "description": "Residues in the binder to invent.",
                    "default": 80,
                    "minimum": MIN_BINDER,
                    "maximum": MAX_BINDER,
                },
                "target_copies": {
                    "type": "integer",
                    "description": (
                        "Copies of the target chain in the complex (for a "
                        "homo-oligomeric target)."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_COPIES,
                },
                "epitope": {
                    "type": "string",
                    "description": (
                        "Optional target residues the binder must contact, "
                        "1-based along target_sequence, e.g. '12,15,40-48'; "
                        "applied on every copy."
                    ),
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed for the starting sequence and the optimiser. "
                        "Vary it for different designs."
                    ),
                    "default": 0,
                    "minimum": 0,
                },
                "steps1": {
                    "type": "integer",
                    "description": (
                        "Optimiser steps in stage 1 (upstream: 75). Time is "
                        "linear in the total of steps1 + steps2."
                    ),
                    "default": 75,
                    "minimum": 1,
                    "maximum": MAX_STEPS,
                },
                "steps2": {
                    "type": "integer",
                    "description": "Optimiser steps in stage 2 (upstream: 50).",
                    "default": 50,
                    "minimum": 1,
                    "maximum": MAX_STEPS,
                },
                "return_structure": {
                    "type": "boolean",
                    "description": (
                        "Return the designed complex as PDB text (default false)."
                    ),
                    "default": False,
                },
            },
            "required": ["target_sequence"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "binder_sequence": {"type": "string"},
                "binder_length": {"type": "integer"},
                "target_copies": {"type": "integer"},
                "n_tokens": {"type": "integer"},
                "epitope": {"type": ["string", "null"]},
                "seed": {"type": "integer"},
                "steps": {"type": "object"},
                "scores": {"type": "object"},
                "sequence_sharpness": {"type": "number"},
                "loss": {"type": "object"},
                "shape_compiled_before": {"type": "boolean"},
                "shapes_held": {"type": "integer"},
                "requests_served": {"type": "integer"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "peak_in_use_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "complex_pdb": {"type": "string"},
                "structure_note": {"type": "string"},
                "structure_error": {"type": "string"},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "mosaic MCP Server",
        "host": "127.0.0.1",
        "port": 8055,
        "transport": "http",
    },
)
class MosaicDesignBinderTool:
    """Design one binder. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            spec = _validate(arguments)
        except ValueError as exc:
            return {"error": str(exc)}

        seed = arguments.get("seed", 0)
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}
        return_structure = arguments.get("return_structure", False)
        if not isinstance(return_structure, bool):
            return {"error": "'return_structure' must be a boolean."}

        try:
            return _design(spec, seed, return_structure)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"mosaic's resident worker is not available ({reason}). Run "
                    f"`tu remote setup mosaic` and read its named refusal; this "
                    f"provider has no subprocess fallback."
                ),
            }
        except WorkerRequestError as exc:
            # The request, not the provider: the model stays up and this is its
            # own account of why THIS input did not design.
            return {"error": f"mosaic could not design for this input: {exc}"}
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"mosaic failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
