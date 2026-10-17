"""ProteinMPNN fixed-backbone sequence design, served from a held worker.

This tool runs in ToolUniverse's own interpreter and never imports anything
from the model's environment. Its job is to check a request, hand it to the
resident worker over a Unix socket, and shape the reply.

The ceilings below mirror the worker's module constants. They are restated
rather than imported -- the two processes share no dependency set -- and they
are checked in BOTH places on purpose: a ceiling only the worker knows is a
ceiling a caller discovers by having a request fail after a minute of work.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds (resident/proteinmpnn_resident_worker.py).
MAX_RESIDUES = int(os.environ.get("PROTEINMPNN_MAX_RESIDUES", "3000"))
MAX_SEQS = 128
VARIANTS = ("vanilla", "soluble")
# A backbone, not a structure archive. 8 MB is ~100k atoms, far past
# MAX_RESIDUES, and it keeps a caller from pushing a megabyte through the MCP
# transport by accident -- chai1 once returned enough text that the transport
# truncated the reply at exactly 100,000 characters and produced invalid JSON
# rather than a refusal.
MAX_STRUCTURE_BYTES = 8 * 1024 * 1024


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _check(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Every bound, checked here as well as in the worker.

    Returns ``{"error": ...}`` rather than raising, which is this layer's
    convention -- and worth saying out loud, because a probe written against a
    sibling provider read "nothing raised" as "the request was admitted" and
    reported a ceiling that had never refused anything.
    """
    if not isinstance(arguments, dict):
        return {"error": "Arguments must be an object."}

    structure = arguments.get("structure") or arguments.get("pdb")
    if not isinstance(structure, str) or not structure.strip():
        return {
            "error": (
                "'structure' must be the text of a PDB file holding the "
                "backbone to design sequences for."
            )
        }
    if len(structure.encode("utf-8", "replace")) > MAX_STRUCTURE_BYTES:
        return {
            "error": (
                f"'structure' is larger than "
                f"{MAX_STRUCTURE_BYTES // (1024 * 1024)} MB; send the backbone "
                f"alone (N, CA, C, O of amino-acid residues)."
            )
        }
    if "ATOM" not in structure:
        return {
            "error": (
                "'structure' holds no ATOM record. ProteinMPNN reads ATOM lines "
                "only; a header-only or HETATM-only file has no backbone."
            )
        }

    variant = arguments.get("weight_set", "vanilla")
    if variant not in VARIANTS:
        return {
            "error": (
                f"'weight_set' must be one of {list(VARIANTS)}; got "
                f"{variant!r}. 'vanilla' is upstream's default; 'soluble' is "
                f"SolubleMPNN, trained without membrane proteins."
            )
        }

    num_seq = arguments.get("num_sequences", 8)
    if not isinstance(num_seq, int) or isinstance(num_seq, bool):
        return {"error": "'num_sequences' must be an integer."}
    if not 1 <= num_seq <= MAX_SEQS:
        return {
            "error": (
                f"'num_sequences' must be between 1 and {MAX_SEQS}; got "
                f"{num_seq}."
            )
        }

    batch = arguments.get("batch_size", num_seq)
    if not isinstance(batch, int) or isinstance(batch, bool):
        return {"error": "'batch_size' must be an integer."}
    if not 1 <= batch <= num_seq:
        return {
            "error": (
                f"'batch_size' must be between 1 and 'num_sequences' "
                f"({num_seq}); got {batch}."
            )
        }
    if num_seq % batch:
        return {
            "error": (
                f"'num_sequences' ({num_seq}) must be a whole number of "
                f"batches of 'batch_size' ({batch}). Upstream designs "
                f"num_sequences // batch_size batches per temperature and "
                f"drops the remainder silently, so this is refused instead."
            )
        }

    temperature = arguments.get("temperature", 0.1)
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        return {"error": "'temperature' must be a number."}
    if not 0.0 < float(temperature) <= 1.0:
        return {
            "error": (
                f"'temperature' must be in (0, 1]; got {temperature}. It "
                f"divides the logits, so 0 is a division by zero. Upstream's "
                f"default is 0.1; 0.2-0.3 gives more diverse sequences."
            )
        }

    seed = arguments.get("seed", 37)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 1:
        return {
            "error": (
                "'seed' must be an integer >= 1. The worker will not draw one: "
                "it is held across requests, so a drawn seed could not be "
                "reproduced by the caller."
            )
        }

    return {
        "pdb": structure,
        "variant": variant,
        "num_seq_per_target": num_seq,
        "batch_size": batch,
        "sampling_temp": float(temperature),
        "seed": seed,
    }


def _design(doc: Dict[str, Any]) -> Dict[str, Any]:
    from tooluniverse.remote_resident.supervisor import (
        WorkerRequestError,
        WorkerStartError,
    )

    worker = _worker()
    try:
        reply = worker.request({"op": "predict", **doc})
    except WorkerStartError as exc:
        return {"error": f"the ProteinMPNN worker could not be started: {exc}"}
    except WorkerRequestError as exc:
        return {"error": f"ProteinMPNN refused the request: {exc}"}
    result = reply.get("result") or {}
    structures = result.get("structures") or []
    first = structures[0] if structures else {}
    return {
        "model": result.get("model"),
        "device": result.get("device"),
        "weight_set": result.get("variant"),
        "seed": result.get("seed"),
        "temperature": (result.get("sampling_temp") or [None])[0],
        "n_residues": first.get("n_residues"),
        "designed_chains": first.get("designed_chains"),
        "native_sequence": first.get("native_sequence"),
        "native_score": first.get("native_score"),
        "sequences": [d.get("sequence") for d in first.get("designs", [])],
        "designs": first.get("designs"),
        "n_designs": result.get("n_designs"),
        "timing_s": result.get("timing_s"),
        "peak_rss_gib": result.get("peak_rss_gib"),
    }


@register_mcp_tool(
    tool_type_name="proteinmpnn_design",
    config={
        "description": (
            "Design protein SEQUENCES for a fixed backbone with ProteinMPNN "
            "(inverse folding). Give the backbone as PDB text; returns "
            "num_sequences designed sequences with each one's score and its "
            "sequence recovery against the structure's own sequence. Raise "
            "'temperature' for diversity. 'weight_set' selects ProteinMPNN "
            "(vanilla) or SolubleMPNN. Reproduces upstream's released "
            "protein_mpnn_run.py field for field at the same seed, which is "
            "checked by byte-comparison in this provider's acceptance suite. "
            "Runs on the CPU and holds no GPU memory, so it can share a host "
            "with any folding model: expect ~20 s for 8 sequences of a "
            "106-residue backbone on a quiet 20-core box, roughly linear in "
            "both length and sequence count."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "structure": {
                    "type": "string",
                    "description": (
                        "The backbone, as the text of a PDB file. ATOM lines of "
                        "amino-acid residues are read (N, CA, C, O); waters, "
                        "ligands and side chains are ignored. Every chain in "
                        "the file is designed. Up to "
                        f"{MAX_STRUCTURE_BYTES // (1024 * 1024)} MB and "
                        f"{MAX_RESIDUES} residues."
                    ),
                },
                "num_sequences": {
                    "type": "integer",
                    "description": (
                        f"How many sequences to design (default 8, max "
                        f"{MAX_SEQS}). Must be a whole number of batches of "
                        f"'batch_size'."
                    ),
                    "default": 8,
                },
                "batch_size": {
                    "type": "integer",
                    "description": (
                        "How many sequences are decoded per forward pass "
                        "(default: all of them). Upstream's own option; lower "
                        "it only to hold memory down on a long backbone."
                    ),
                },
                "temperature": {
                    "type": "number",
                    "description": (
                        "Sampling temperature, in (0, 1]. Upstream's default is "
                        "0.1, which is close to greedy; 0.2-0.3 trades score "
                        "for diversity."
                    ),
                    "default": 0.1,
                },
                "weight_set": {
                    "type": "string",
                    "enum": list(VARIANTS),
                    "description": (
                        "'vanilla' is ProteinMPNN as released and upstream's "
                        "default. 'soluble' is SolubleMPNN, the same "
                        "architecture trained without membrane proteins; use it "
                        "for soluble designs."
                    ),
                    "default": "vanilla",
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed, >= 1 (default 37). The same seed and the "
                        "same backbone give the same sequences; the worker will "
                        "not draw one for you."
                    ),
                    "default": 37,
                },
            },
            "required": ["structure"],
        },
        "server_name": "ProteinMPNN Sequence Design MCP Server",
        "host": "127.0.0.1",
        "port": 8049,
        "transport": "http",
    },
)
class ProteinMPNNDesignTool:
    """Design sequences for a fixed backbone. Requests queue: one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        doc = _check(arguments)
        if "error" in doc:
            return doc
        return _design(doc)


if __name__ == "__main__":
    start_mcp_server(__file__)
