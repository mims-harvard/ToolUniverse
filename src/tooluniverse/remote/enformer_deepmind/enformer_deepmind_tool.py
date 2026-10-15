"""Official DeepMind Enformer track prediction, served from a held worker.

This tool runs in ToolUniverse's own interpreter and never imports TensorFlow.
Its job is to check a request, hand it to the resident worker over a Unix
socket, and shape the reply.

WHY A SECOND ENFORMER. ToolUniverse already serves Enformer at port 8011
through `enformer-pytorch`, a community port of the network whose weights were
converted from the authors' release. This one serves the authors' own artifact:
the TF-Hub SavedModel `deepmind/enformer/1`, byte-pinned in the kit's
stock/PINS.json and verified before the worker starts. The two are not
interchangeable -- a converted checkpoint and a different framework's kernels do
not agree to the last float -- so published Enformer numbers reproduce against
this one. Both answer with a `centre` key over the same 5,313 human tracks, and
both providers ship the same smoke sequence, so the two can be compared
directly.

The ceilings below mirror the worker's module constants. They are restated
rather than imported -- the two processes share no dependency set -- and checked
in both places: a ceiling only the worker knows is a ceiling a caller discovers
by having a request fail after three minutes of work.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds
# (resident/enformer_deepmind_resident_worker.py), themselves read from the
# kit's stock/PINS.json rather than assumed.
INPUT_LENGTH = 393_216
RECEPTIVE_LENGTH = 196_608
N_BINS = 896
ORGANISM_TRACKS = {"human": 5_313, "mouse": 1_643}
# Twice the model's input length. Anything longer is centre-cropped anyway, so
# accepting more would only move megabytes through the MCP transport to be
# thrown away: chai1 once returned enough text that the transport truncated the
# reply at exactly 100,000 characters and produced invalid JSON rather than a
# refusal.
MAX_INPUT_LENGTH = INPUT_LENGTH * 2
MAX_TRACKS = 32


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _check(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Every bound, checked here as well as in the worker.

    Returns ``{"error": ...}`` rather than raising, which is this layer's
    convention.
    """
    if not isinstance(arguments, dict):
        return {"error": "Arguments must be an object."}

    sequence = arguments.get("sequence") or arguments.get("input")
    if not isinstance(sequence, str) or not sequence.strip():
        return {
            "error": (
                "'sequence' must be a DNA string. It is centre-cropped or "
                f"N-padded to {INPUT_LENGTH:,} bases, of which the model reads "
                f"the central {RECEPTIVE_LENGTH:,}."
            )
        }
    seq = sequence.strip()
    if len(seq) > MAX_INPUT_LENGTH:
        return {
            "error": (
                f"'sequence' is {len(seq):,} bases; the ceiling is "
                f"{MAX_INPUT_LENGTH:,}. Anything past {INPUT_LENGTH:,} is "
                f"centre-cropped, so send the window you mean."
            )
        }
    bad = set(seq.upper()) - set("ACGTN")
    if bad:
        return {
            "error": (
                f"'sequence' holds {sorted(bad)!r}, which are not DNA letters. "
                f"A, C, G, T and N are accepted; N becomes an all-zero column, "
                f"as in upstream's own usage notebook."
            )
        }

    organism = str(arguments.get("organism", "human")).strip().lower()
    if organism not in ORGANISM_TRACKS:
        return {
            "error": (
                f"'organism' must be one of {sorted(ORGANISM_TRACKS)}; got "
                f"{organism!r}."
            )
        }

    tracks = arguments.get("tracks") or []
    if not isinstance(tracks, list):
        return {"error": "'tracks' must be a list of track indices."}
    if len(tracks) > MAX_TRACKS:
        return {
            "error": (
                f"'tracks' asks for {len(tracks)} profiles; the ceiling is "
                f"{MAX_TRACKS}. Each is {N_BINS} floats and the reply travels "
                f"as JSON."
            )
        }
    n_tracks = ORGANISM_TRACKS[organism]
    for t in tracks:
        if not isinstance(t, int) or isinstance(t, bool):
            return {"error": f"track indices must be integers; got {t!r}."}
        if not 0 <= t < n_tracks:
            return {
                "error": (
                    f"track index {t} is outside the {organism} head's "
                    f"0..{n_tracks - 1}."
                )
            }

    return {"input": seq, "organism": organism, "tracks": [int(t) for t in tracks]}


def _predict(doc: Dict[str, Any]) -> Dict[str, Any]:
    from tooluniverse.remote_resident.supervisor import (
        WorkerRequestError,
        WorkerStartError,
    )

    worker = _worker()
    try:
        reply = worker.request({"op": "predict", **doc})
    except WorkerStartError as exc:
        return {"error": f"the Enformer (DeepMind) worker could not be started: {exc}"}
    except WorkerRequestError as exc:
        return {"error": f"Enformer (DeepMind) refused the request: {exc}"}
    result = reply.get("result") or {}
    return {
        "implementation": "deepmind/enformer/1 (official TF-Hub SavedModel)",
        "organism": result.get("organism"),
        "n_bins": result.get("n_bins"),
        "n_tracks": result.get("n_tracks"),
        "input_length": result.get("input_length"),
        "receptive_length": result.get("receptive_length"),
        "centre": result.get("centre"),
        "profiles": result.get("profiles"),
        "timing": result.get("timing"),
    }


@register_mcp_tool(
    tool_type_name="run_enformer_deepmind_predict",
    config={
        "name": "run_enformer_deepmind_predict",
        "description": (
            "Predict genomic tracks from DNA sequence with the OFFICIAL "
            "DeepMind Enformer release (the TF-Hub SavedModel "
            "deepmind/enformer/1), byte-pinned and verified. Returns the "
            "centre-bin value across every track, plus the full 896-bin "
            "profile of any track named. Use this when published Enformer "
            "numbers must reproduce; use run_enformer_predict (the "
            "enformer-pytorch port, GPU) when throughput matters more than "
            "matching the authors' artifact. One window costs about three "
            "minutes: this release has no GPU-capable build for this machine's "
            "architecture and runs on the CPU."
        ),
        # Structurally identical to the published catalogue entry in
        # src/tooluniverse/data/remote_tools/enformer_deepmind_tools.json --
        # every bound here is one `_check` already enforces, so the schema the
        # server advertises and the schema a caller reads are the same contract.
        "parameter": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": (
                        "DNA sequence (A, C, G, T, N). Centre-cropped or "
                        "N-padded to 393,216 bases, of which the model reads "
                        "the central 196,608. The cost does not depend on the "
                        "length you send."
                    ),
                    "minLength": 1,
                    "maxLength": MAX_INPUT_LENGTH,
                    "pattern": "^[ACGTNacgtn]+$",
                },
                "organism": {
                    "type": "string",
                    "enum": ["human", "mouse"],
                    "description": (
                        "Which head to read: 'human' has 5,313 tracks, 'mouse' "
                        "1,643."
                    ),
                    "default": "human",
                },
                "tracks": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                    "maxItems": MAX_TRACKS,
                    "description": (
                        "Track indices whose full 896-bin profile to return, at "
                        "most 32. The centre bin of every track is returned "
                        "regardless."
                    ),
                },
            },
            "required": ["sequence"],
        },
        "server_name": "Enformer (official DeepMind release) MCP Server",
        "host": "127.0.0.1",
        "port": 8060,
        "transport": "http",
    },
)
class EnformerDeepMindPredictTool:
    """One window through the official SavedModel. Requests queue: one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        doc = _check(arguments)
        if "error" in doc:
            return doc
        return _predict(doc)


if __name__ == "__main__":
    start_mcp_server(__file__)
