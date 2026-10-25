"""The MCP surface for RFD4-Proteina's resident worker.

Runs in ToolUniverse's environment and imports nothing of the model's: the
design crosses a Unix socket as JSON, per STANDARD section 2.

ONE TOOL, NOT SEVEN. Upstream serves seven tasks -- generation,
motif_scaffolding, enzyme_design, small_molecule_binder, antibody_design,
partial_diffusion, inverse_folding -- and it would be easy to read that as
seven tools. It is not, and upstream says why: "`task` selects how the sampler
runs the trajectory, not which design problem is being solved". The design
problem is expressed by what the *input* holds fixed. A binder against a
target is `generation` with the target's coordinates and sequence conditioned
and its epitope marked as hotspots; a scaffolded motif is the same call with
different annotations. Splitting the tool by task would invent a distinction
the model does not have and would push callers towards picking a task name
instead of annotating their structure.

So the annotated mmCIF is the argument, and this tool refuses an input that
cannot be one rather than letting a design run for half a minute and come back
empty.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_REPLICATES = 8
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024

RECYCLE_STRATEGIES = ("thinking_low", "thinking_medium", "thinking_high")
BACKENDS = ("native", "bioir")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _check_input_cif(value: Any) -> str:
    """Refuse here what would otherwise cost a request to discover."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("'input_cif' must be the text of an annotated mmCIF.")
    size = len(value.encode("utf-8"))
    if size > MAX_INPUT_BYTES:
        raise ValueError(
            f"'input_cif' is {size} bytes, above this provider's "
            f"{MAX_INPUT_BYTES}; upstream's own published examples run 3 KB "
            f"to 725 KB."
        )
    head = value.lstrip()
    if not head.startswith("data_"):
        raise ValueError(
            "'input_cif' does not begin with a mmCIF 'data_' block. A PDB file "
            "is not accepted: the design conditions travel in mmCIF "
            "annotations that PDB format has nowhere to put."
        )
    if "_atom_site." not in value:
        raise ValueError(
            "'input_cif' has no _atom_site loop, so there is nothing for the "
            "model to read as a specification."
        )
    return value


def _design(payload: Dict[str, Any], return_structures: bool) -> Dict[str, Any]:
    """One design request on the resident worker, or a named reason why not."""
    reply = _worker().request({"op": "predict", **payload})
    result = reply["result"]
    designs = result.get("designs") or []

    out: Dict[str, Any] = {
        "model": result.get("model"),
        "n_designs": result.get("n_designs", len(designs)),
        "recycle_strategy": result.get("recycle_strategy"),
        "inference_backend": result.get("inference_backend"),
        "seed": result.get("seed"),
        "timing": result.get("timing"),
        "weights_held_by": result.get("weights_held_by"),
        "peak_reserved_gib": result.get("peak_reserved_gib"),
    }

    summary = []
    for d in designs:
        entry = {
            "design_id": d.get("design_id"),
            "chains": d.get("chains"),
            "n_atoms": d.get("n_atoms"),
        }
        if return_structures and d.get("cif"):
            text = d["cif"]
            if len(text.encode("utf-8")) > MAX_STRUCTURE_BYTES:
                entry["error"] = "exceeds the public output limit"
            else:
                entry["cif"] = text
        summary.append(entry)
    out["designs"] = summary

    if not designs:
        return {
            "error": "RFD4-Proteina produced no design for this input.",
            "timing": out["timing"],
        }
    if not return_structures:
        out["structures_note"] = (
            "pass return_structures=true to receive the mmCIF text; the "
            "per-chain sequences above come back either way"
        )
    return out


@register_mcp_tool(
    tool_type_name="rfd4_proteina_design",
    config={
        "description": (
            "Design biomolecules with RFD4-Proteina. The input is an annotated "
            "mmCIF whose annotations ARE the design specification: what to hold "
            "fixed by coordinate and by sequence, which residues are hotspots, "
            "which regions to generate. One call covers every task upstream "
            "serves -- de novo monomers, protein and DNA binders, motif "
            "scaffolding, enzyme active-site scaffolding, small-molecule "
            "binders, antibody and TCR CDR redesign, partial diffusion and "
            "inverse folding -- because which one you get is a property of the "
            "annotations, not of a mode. Returns each design's per-chain "
            "sequence; the mmCIF text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "input_cif": {
                    "type": "string",
                    "description": (
                        "The annotated mmCIF text. An ordinary unannotated "
                        "structure is not a design specification and will be "
                        "refused. Upstream's examples/ directory has one per "
                        "design shape."
                    ),
                },
                "num_replicates": {
                    "type": "integer",
                    "description": (
                        f"Independent designs from the one specification, 1 to "
                        f"{MAX_REPLICATES}. Each holds the GPU for a whole "
                        f"rollout, so this multiplies the wall clock."
                    ),
                    "default": 1,
                },
                "recycle_strategy": {
                    "type": "string",
                    "description": (
                        "Compute preset. The three differ only in how often the "
                        "trunk is recycled over 60 steps: thinking_low 120 "
                        "trunk passes, thinking_medium 180, thinking_high 300."
                    ),
                    "enum": list(RECYCLE_STRATEGIES),
                    "default": "thinking_medium",
                },
                "inference_backend": {
                    "type": "string",
                    "description": (
                        "'native' runs the workflow in torch; 'bioir' runs it "
                        "through NVIDIA's BioNeMo Inference Runtime, which "
                        "captures a CUDA graph. See this provider's README for "
                        "what each measured on the verified card before "
                        "choosing."
                    ),
                    "enum": list(BACKENDS),
                    "default": "native",
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed. Omit for a random one.",
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the designed mmCIF text as well as the "
                        "sequences. Off by default: replicates of mmCIF are "
                        "megabytes, and a transport truncates an oversized "
                        "reply into invalid JSON rather than refusing it."
                    ),
                    "default": False,
                },
            },
            "required": ["input_cif"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_designs": {"type": "integer"},
                "designs": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "recycle_strategy": {"type": "string"},
                "inference_backend": {"type": "string"},
                "seed": {"type": "integer"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "peak_reserved_gib": {"type": "number"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "RFD4-Proteina MCP Server",
        "host": "127.0.0.1",
        "port": 8062,
        "transport": "http",
    },
)
class RFD4ProteinaDesignTool:
    """Design biomolecules. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        try:
            # Sent as "input": the shared field the resident protocol and the
            # setup smoke step both use. The tool's own argument keeps the
            # explicit name because a caller writing it should see what it is.
            payload: Dict[str, Any] = {
                "input": _check_input_cif(arguments.get("input_cif"))
            }
        except ValueError as exc:
            return {"error": str(exc)}

        replicates = arguments.get("num_replicates", 1)
        if not isinstance(replicates, int) or isinstance(replicates, bool):
            return {"error": "'num_replicates' must be an integer."}
        if not 1 <= replicates <= MAX_REPLICATES:
            return {
                "error": f"'num_replicates' must be between 1 and {MAX_REPLICATES}."
            }
        payload["num_replicates"] = replicates

        for name, allowed in (
            ("recycle_strategy", RECYCLE_STRATEGIES),
            ("inference_backend", BACKENDS),
        ):
            value = arguments.get(name)
            if value is not None:
                if not isinstance(value, str) or value not in allowed:
                    return {"error": f"'{name}' must be one of {', '.join(allowed)}."}
                payload[name] = value

        seed = arguments.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or isinstance(seed, bool):
                return {"error": "'seed' must be an integer."}
            payload["seed"] = seed

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}
        payload["return_structures"] = return_structures

        try:
            return _design(payload, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"RFD4-Proteina's resident worker is not available "
                    f"({reason}). Run `tu remote setup rfd4_proteina` and read "
                    f"its named refusal; this provider has no subprocess "
                    f"fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
