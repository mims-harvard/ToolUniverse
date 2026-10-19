"""ESM C protein language model — MCP server.

ESM Cambrian (`esm` 3.4.0, ``ESMC.from_pretrained`` -> ``encode`` -> ``logits``)
is a masked protein language model. One forward pass over a sequence gives two
things worth serving: the per-residue hidden states, which are the sequence's
embedding, and the 64-way vocabulary logits, from which the likelihood the
model assigns to each observed residue follows.

This is the thin, CPU-only half of the provider. The model runs in its own
environment -- torch 2.11.0+cu130 on Python 3.12.1, which ToolUniverse's other
600+ tools cannot be installed beside -- and is held resident, because the
6-billion-parameter checkpoint is 25.4 GiB and a process that exits after each
request re-reads all of it for a forward pass that takes well under a second.

**Why the default reply is a single vector.** ESMC-6B's hidden size is 2560, so
one residue's embedding is already ~23 kB of JSON and a 300-residue matrix is
768,000 numbers. The MCP transport truncated Chai-1's oversized reply at
exactly 100,000 characters, which produced invalid JSON rather than an honest
refusal. So ``run_esmc_embed`` returns the mean-pooled vector by default; a
bounded window of residue vectors is opt-in and is refused by number of floats
rather than silently clipped; and the whole matrix comes back as a path to a
``.npy`` file, never inline. Enformer's ``top_n`` / ``track_indices`` is the
precedent for the bounded form.
"""

import os
import tempfile
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds. They are checked in both places on
# purpose: here so a caller gets a useful message without occupying the GPU,
# and in the worker so a request that did not come through this server cannot
# build a reply nothing can transport.
MAX_RESIDUES = 4_096
MAX_INLINE_VALUES = 20_000
MAX_POSITIONS_INLINE = 4_000
AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")

_PORT = 8037
_MCP = {
    "server_name": "ESM C MCP Server",
    "host": "127.0.0.1",
    "port": _PORT,
    "transport": "http",
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _clean_sequence(value: Any) -> str:
    """One protein sequence out of a raw string or a single-record FASTA."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("'sequence' must be a non-empty protein sequence or FASTA.")
    lines = [ln.strip() for ln in value.splitlines()]
    if any(ln.startswith(">") for ln in lines):
        records, current = [], []
        for ln in lines:
            if ln.startswith(">"):
                if current:
                    records.append("".join(current))
                current = []
            elif ln:
                current.append(ln)
        if current:
            records.append("".join(current))
        if len(records) != 1:
            raise ValueError(
                f"the input FASTA holds {len(records)} records; these operations "
                f"take one sequence per call."
            )
        seq = records[0]
    else:
        seq = "".join(lines)
    seq = "".join(seq.split()).upper()
    if not seq:
        raise ValueError("the input carries no sequence.")
    bad = sorted(set(seq) - AMINO_ACIDS)
    if bad:
        raise ValueError(f"the sequence holds {bad}, which are not amino-acid letters.")
    if len(seq) > MAX_RESIDUES:
        raise ValueError(
            f"the sequence is {len(seq)} residues; this provider accepts "
            f"{MAX_RESIDUES} at most."
        )
    return seq


def _forward(sequence: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """One forward pass on the resident worker, or a named reason why not."""
    with tempfile.TemporaryDirectory(prefix="esmc-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": sequence,
                "out_dir": work,
                "name": "esmc",
                "options": options,
            }
        )
        result = dict(reply["result"])
        # The .npy lives in a directory that is about to be removed, so it is
        # moved somewhere the caller can actually open. Writing it straight to
        # a persistent path would leave a 25 MB file behind on every failure
        # that happened after the write.
        info = result.get("per_residue_file")
        if info and os.path.isfile(info.get("path", "")):
            keep = tempfile.mkdtemp(prefix="esmc-embeddings-")
            final = os.path.join(keep, os.path.basename(info["path"]))
            os.replace(info["path"], final)
            info["path"] = final
            info["note"] = (
                "read with numpy.load(path); the file is not cleaned up "
                "automatically -- remove it when you are done with it"
            )
        return result


def _unavailable(exc: Exception) -> Dict[str, Any]:
    reason = getattr(exc, "reason", "") or type(exc).__name__
    return {
        "error": (
            f"ESM C's resident worker is not available ({reason}). Run "
            f"`tu remote setup esmc` and read its named refusal; this provider "
            f"has no subprocess fallback, because a 25.4 GiB checkpoint read "
            f"per request would look like the provider working while costing "
            f"far more than it appears to."
        )
    }


_SEQUENCE_PROPERTY = {
    "type": "string",
    "description": (
        "One protein sequence in single-letter amino-acid code, or a "
        f"single-record FASTA. At most {MAX_RESIDUES} residues."
    ),
    "minLength": 1,
}


@register_mcp_tool(
    tool_type_name="run_esmc_embed",
    config={
        "description": (
            "Embed one protein sequence with the ESM Cambrian (ESM C) protein "
            "language model and return the mean-pooled embedding vector. Use "
            "it to compare, cluster or search proteins by learned "
            "representation. The full per-residue matrix is NOT returned "
            "inline (2560 floats per residue): ask for 'residue_range' to get "
            "a bounded window of residue vectors, or 'per_residue_file' to get "
            "the whole matrix written as a .npy file whose path comes back."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": _SEQUENCE_PROPERTY,
                "include_cls_embedding": {
                    "type": "boolean",
                    "description": (
                        "Also return the BOS (sequence-level) vector, which is "
                        "another whole embedding of the same width."
                    ),
                    "default": False,
                },
                "residue_range": {
                    "type": "array",
                    "description": (
                        "Inclusive 1-based [start, end] window of residue "
                        "vectors to return inline. Refused, not clipped, when "
                        f"(end - start + 1) * embedding_dim exceeds "
                        f"{MAX_INLINE_VALUES} floats -- at the 6B model's 2560 "
                        f"dimensions that is {MAX_INLINE_VALUES // 2560} residues."
                    ),
                    "items": {"type": "integer", "minimum": 1},
                    "minItems": 2,
                    "maxItems": 2,
                },
                "per_residue_file": {
                    "type": "boolean",
                    "description": (
                        "Write the whole (length x embedding_dim) float32 "
                        "matrix to a .npy file on the provider host and return "
                        "its path, shape and size instead of its contents."
                    ),
                    "default": False,
                },
                "decimals": {
                    "type": "integer",
                    "description": "Decimal places for returned floats (default 5).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 8,
                },
            },
            "required": ["sequence"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "variant": {"type": "string"},
                "sequence_length": {"type": "integer"},
                "embedding_dim": {"type": "integer"},
                "pooling": {"type": "string"},
                "mean_embedding": {"type": "array", "items": {"type": "number"}},
                "mean_embedding_norm": {"type": "number"},
                "cls_embedding": {"type": "array", "items": {"type": "number"}},
                "residue_embeddings": {"type": "object"},
                "per_residue_file": {"type": "object"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class EsmcEmbedTool:
    """Embed one sequence. Requests queue: the worker serves one at a time."""

    _DROP = (
        "mean_log_likelihood",
        "pseudo_perplexity",
        "least_likely_residues",
        "levers_applied",
    )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequence = _clean_sequence(arguments.get("sequence"))
            options: Dict[str, Any] = {"top_n": 0}

            decimals = arguments.get("decimals", 5)
            if not isinstance(decimals, int) or isinstance(decimals, bool):
                raise ValueError("'decimals' must be an integer.")
            if not 1 <= decimals <= 8:
                raise ValueError("'decimals' must be between 1 and 8.")
            options["decimals"] = decimals

            for flag in ("include_cls_embedding", "per_residue_file"):
                value = arguments.get(flag, False)
                if not isinstance(value, bool):
                    raise ValueError(f"'{flag}' must be a boolean.")
                options[flag] = value

            window = arguments.get("residue_range")
            if window is not None:
                if (
                    not isinstance(window, list)
                    or len(window) != 2
                    or not all(
                        isinstance(v, int) and not isinstance(v, bool) for v in window
                    )
                ):
                    raise ValueError(
                        "'residue_range' must be two integers, [start, end]."
                    )
                start, end = window
                if not 1 <= start <= end <= len(sequence):
                    raise ValueError(
                        f"'residue_range' {window} is outside 1..{len(sequence)} "
                        f"(1-based and inclusive)."
                    )
                options["residue_range"] = [start, end]
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            result = _forward(sequence, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in self._DROP:
            result.pop(key, None)
        return result


@register_mcp_tool(
    tool_type_name="run_esmc_logits",
    config={
        "description": (
            "Score one protein sequence with the ESM Cambrian (ESM C) masked "
            "language model: the model's mean log-likelihood and "
            "pseudo-perplexity for the sequence, plus the residues it finds "
            "least likely. Use it to rank designs, flag unusual positions, or "
            "compare variants of one protein. Per-position log-probabilities "
            "are opt-in and bounded, because a long sequence is a long array."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": _SEQUENCE_PROPERTY,
                "top_n": {
                    "type": "integer",
                    "description": (
                        "How many least-likely residues to name (default 10)."
                    ),
                    "default": 10,
                    "minimum": 0,
                    "maximum": 200,
                },
                "per_residue_log_prob": {
                    "type": "boolean",
                    "description": (
                        "Return the log-probability of every observed residue, "
                        "one number per position. Refused for sequences longer "
                        f"than {MAX_POSITIONS_INLINE} residues."
                    ),
                    "default": False,
                },
                "decimals": {
                    "type": "integer",
                    "description": "Decimal places for returned floats (default 5).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 8,
                },
            },
            "required": ["sequence"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "variant": {"type": "string"},
                "sequence_length": {"type": "integer"},
                "mean_log_likelihood": {"type": "number"},
                "pseudo_perplexity": {"type": "number"},
                "least_likely_residues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "integer"},
                            "residue": {"type": "string"},
                            "log_prob": {"type": "number"},
                        },
                    },
                },
                "per_residue_log_prob": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class EsmcLogitsTool:
    """Score one sequence under the masked language model."""

    _DROP = ("mean_embedding", "mean_embedding_norm", "pooling", "embedding_dim")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequence = _clean_sequence(arguments.get("sequence"))

            top_n = arguments.get("top_n", 10)
            if not isinstance(top_n, int) or isinstance(top_n, bool):
                raise ValueError("'top_n' must be an integer.")
            if not 0 <= top_n <= 200:
                raise ValueError("'top_n' must be between 0 and 200.")

            decimals = arguments.get("decimals", 5)
            if not isinstance(decimals, int) or isinstance(decimals, bool):
                raise ValueError("'decimals' must be an integer.")
            if not 1 <= decimals <= 8:
                raise ValueError("'decimals' must be between 1 and 8.")

            per_residue = arguments.get("per_residue_log_prob", False)
            if not isinstance(per_residue, bool):
                raise ValueError("'per_residue_log_prob' must be a boolean.")
            if per_residue and len(sequence) > MAX_POSITIONS_INLINE:
                raise ValueError(
                    f"'per_residue_log_prob' was asked for a {len(sequence)}-"
                    f"residue sequence; the inline limit is "
                    f"{MAX_POSITIONS_INLINE} positions."
                )
        except ValueError as exc:
            return {"error": str(exc)}

        options = {
            "top_n": top_n,
            "decimals": decimals,
            "per_residue_log_prob": per_residue,
        }
        try:
            result = _forward(sequence, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in self._DROP:
            result.pop(key, None)
        return result


if __name__ == "__main__":
    start_mcp_server()
