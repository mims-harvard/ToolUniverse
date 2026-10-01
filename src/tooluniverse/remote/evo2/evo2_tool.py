"""Evo 2 genomic foundation model — MCP server.

Evo 2 (`evo2` 0.6.0 on `vtx` 1.1.0, ``Evo2.score_sequences`` and
``Evo2.forward``) is a DNA language model: a StripedHyena-2 hybrid trained on
genomes, which assigns a likelihood to a nucleotide sequence and produces a
hidden representation of every position in it. Two things follow that are worth
serving: the mean log-likelihood of a sequence, which is what variant-effect
and constraint work compares between a reference and an alternate allele, and
the per-position hidden states, which are the sequence's embedding.

This is the thin, CPU-only half of the provider. The model runs in its own
environment -- torch 2.7.1+cu128 on Python 3.11.5, which ToolUniverse's other
600+ tools cannot be installed beside -- and is held resident, because the
checkpoint is 13.8 GiB and the kit's own README measures the first score in a
fresh process at "≈220 s, then 15-50 s a run".

**Why the default reply is a single vector.** Evo 2's hidden width is 4096, so
one position's embedding is already ~37 kB of JSON and a 1,024 bp matrix is 4.2
million numbers. The MCP transport truncated Chai-1's oversized reply at
exactly 100,000 characters, which produced invalid JSON rather than an honest
refusal. So ``run_evo2_embed`` returns the mean-pooled vector by default; a
bounded window of position vectors is opt-in and is REFUSED by number of floats
rather than silently clipped; and the whole matrix comes back as a path to a
``.npy`` file, never inline. ESM C and Enformer are the precedents.

**The bounds are enforced twice on purpose** -- here so a bad call never
occupies the GPU, and again in the worker so a request that did not come
through this server cannot build a reply nothing can transport.
"""

import os
import tempfile
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of resident/evo2_resident_worker.py's bounds. MAX_BP is also the
# envelope [gpu] vram_budget_gb is declared at, and this provider is unmeasured:
# raise it in all three places together, after measuring.
MAX_BP = 8_192
MAX_SEQUENCES = 8
MAX_TOTAL_BP = 16_384
MAX_INLINE_VALUES = 20_000
MAX_POSITIONS_INLINE = 4_000
# Evo 2's hidden width, from the checkpoint's own config (evo2-7b-1m.yml
# hidden_size). Used only to put a residue count in the refusal messages; the
# worker reports the real width it measured on the model it holds.
HIDDEN_SIZE = 4096
NUCLEOTIDES = set("ACGTUNRYSWKMBDHV")

_PORT = 8041
_MCP = {
    "server_name": "Evo 2 MCP Server",
    "host": "127.0.0.1",
    "port": _PORT,
    "transport": "http",
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _clean_records(value: Any) -> List[tuple]:
    """[(id, sequence)] out of a FASTA, or one unnamed record out of raw text."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("'sequence' must be a non-empty DNA sequence or FASTA.")
    lines = [ln.strip() for ln in value.splitlines()]
    out: List[tuple] = []
    if any(ln.startswith(">") for ln in lines):
        name, chunks = None, []
        for ln in lines:
            if ln.startswith(">"):
                if name is not None:
                    out.append((name, "".join(chunks)))
                parts = ln[1:].split()
                name, chunks = (parts[0] if parts else ""), []
            elif ln:
                chunks.append(ln)
        if name is not None:
            out.append((name, "".join(chunks)))
    else:
        joined = "".join(lines)
        if joined:
            out.append(("sequence_1", joined))
    if not out:
        raise ValueError("the input carries no sequence.")
    if len(out) > MAX_SEQUENCES:
        raise ValueError(
            f"the input holds {len(out)} records; this provider takes "
            f"{MAX_SEQUENCES} at most per call."
        )

    cleaned, total = [], 0
    for i, (name, seq) in enumerate(out):
        seq = "".join(seq.split()).upper()
        label = name or f"record {i + 1}"
        if not seq:
            raise ValueError(f"{label} carries no sequence.")
        bad = sorted(set(seq) - NUCLEOTIDES)
        if bad:
            raise ValueError(
                f"{label} holds {bad}, which are not IUPAC nucleotide codes -- "
                f"Evo 2 is a DNA model, not a protein one."
            )
        if len(seq) > MAX_BP:
            raise ValueError(
                f"{label} is {len(seq)} bp; this provider accepts {MAX_BP} at "
                f"most. That is a memory decision, not a model limit: Evo 2's "
                f"own max_seqlen is 1,048,576, and {MAX_BP} bp is the envelope "
                f"its declared VRAM budget was derived at."
            )
        total += len(seq)
        cleaned.append((name or f"sequence_{i + 1}", seq))
    if total > MAX_TOTAL_BP:
        raise ValueError(
            f"the call totals {total} bp over {len(cleaned)} records; the limit "
            f"is {MAX_TOTAL_BP} bp per call."
        )
    return cleaned


def _as_fasta(records: List[tuple]) -> str:
    return "".join(f">{name}\n{seq}\n" for name, seq in records)


def _forward(records: List[tuple], options: Dict[str, Any]) -> Dict[str, Any]:
    """One forward pass on the resident worker, or a named reason why not."""
    with tempfile.TemporaryDirectory(prefix="evo2-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": _as_fasta(records),
                "out_dir": work,
                "name": "evo2",
                "options": options,
            }
        )
        result = dict(reply["result"])
        # The .npy lives in a directory that is about to be removed, so it is
        # moved somewhere the caller can actually open. Writing it straight to
        # a persistent path would leave a 17 MB file behind on every failure
        # that happened after the write.
        info = result.get("per_position_file")
        if info and os.path.isfile(info.get("path", "")):
            keep = tempfile.mkdtemp(prefix="evo2-embeddings-")
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
            f"Evo 2's resident worker is not available ({reason}). Run "
            f"`tu remote setup evo2` and read its named refusal; this provider "
            f"has no subprocess fallback, because a 13.8 GiB checkpoint read "
            f"per request would look like the provider working while costing "
            f"far more than it appears to."
        )
    }


def _decimals(arguments: Dict[str, Any]) -> int:
    decimals = arguments.get("decimals", 5)
    if not isinstance(decimals, int) or isinstance(decimals, bool):
        raise ValueError("'decimals' must be an integer.")
    if not 1 <= decimals <= 8:
        raise ValueError("'decimals' must be between 1 and 8.")
    return decimals


_SEQUENCE_PROPERTY = {
    "type": "string",
    "description": (
        "DNA in IUPAC nucleotide codes: one sequence, or a FASTA of up to "
        f"{MAX_SEQUENCES} records. At most {MAX_BP} bp per record and "
        f"{MAX_TOTAL_BP} bp in total."
    ),
    "minLength": 1,
}


@register_mcp_tool(
    tool_type_name="run_evo2_score",
    config={
        "description": (
            "Score DNA sequences with the Evo 2 genomic foundation model: the "
            "mean log-likelihood the model assigns each sequence, and its "
            "perplexity. Use it to compare a reference allele against an "
            "alternate one (score both windows and take the difference), to "
            "rank designed or synthetic sequences by how genome-like they are, "
            "or to flag unusual regions. Returns one score per FASTA record, in "
            "input order."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": _SEQUENCE_PROPERTY,
                "reduce": {
                    "type": "string",
                    "description": (
                        "'mean' for the mean per-base log-likelihood (the "
                        "default, and comparable between sequences of different "
                        "length), or 'sum' for the pseudo-log-likelihood of the "
                        "whole sequence (which grows with length)."
                    ),
                    "enum": ["mean", "sum"],
                    "default": "mean",
                },
                "average_reverse_complement": {
                    "type": "boolean",
                    "description": (
                        "Score each sequence on both strands and average. "
                        "Doubles the work; use it when the strand of the input "
                        "is arbitrary."
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
                "model_name": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "string"}},
                "sequence_lengths": {"type": "array", "items": {"type": "integer"}},
                "scores": {"type": "array", "items": {"type": "number"}},
                "scores_hex": {"type": "array", "items": {"type": "string"}},
                "perplexity": {"type": "array", "items": {"type": "number"}},
                "reduce": {"type": "string"},
                "average_reverse_complement": {"type": "boolean"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "kit_route": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class Evo2ScoreTool:
    """Score DNA. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            records = _clean_records(arguments.get("sequence"))
            options: Dict[str, Any] = {
                "task": "score",
                "decimals": _decimals(arguments),
                "batch_size": 1,
            }

            reduce = arguments.get("reduce", "mean")
            if reduce not in ("mean", "sum"):
                raise ValueError("'reduce' must be 'mean' or 'sum'.")
            options["reduce"] = reduce

            rc = arguments.get("average_reverse_complement", False)
            if not isinstance(rc, bool):
                raise ValueError("'average_reverse_complement' must be a boolean.")
            options["average_reverse_complement"] = rc
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            result = _forward(records, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in ("mean_embedding", "mean_embedding_norm", "pooling", "layer_name"):
            result.pop(key, None)
        return result


@register_mcp_tool(
    tool_type_name="run_evo2_embed",
    config={
        "description": (
            "Embed one DNA sequence with the Evo 2 genomic foundation model and "
            "return the mean-pooled embedding vector of one hidden layer, plus "
            "the sequence's log-likelihood. Use it to compare, cluster or "
            "search genomic regions by learned representation. The full "
            "per-position matrix is NOT returned inline (4096 floats per base): "
            "ask for 'position_range' to get a bounded window of position "
            "vectors, or 'per_position_file' to get the whole matrix written as "
            "a .npy file whose path comes back."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": (
                        "ONE DNA sequence in IUPAC nucleotide codes, or a "
                        f"single-record FASTA. At most {MAX_BP} bp."
                    ),
                    "minLength": 1,
                },
                "layer_name": {
                    "type": "string",
                    "description": (
                        "Which hidden layer to take the embedding from, as "
                        "'blocks.<i>.mlp.l3'. Defaults to the last block's. "
                        "Only these are offered: the optimization kit folds the "
                        "input-projection weights, so a hook on a projection "
                        "layer would return that folded layout."
                    ),
                },
                "position_range": {
                    "type": "array",
                    "description": (
                        "Inclusive 1-based [start, end] window of position "
                        "vectors to return inline. Refused, not clipped, when "
                        f"(end - start + 1) * embedding_dim exceeds "
                        f"{MAX_INLINE_VALUES} floats -- at Evo 2's "
                        f"{HIDDEN_SIZE} dimensions that is "
                        f"{MAX_INLINE_VALUES // HIDDEN_SIZE} positions."
                    ),
                    "items": {"type": "integer", "minimum": 1},
                    "minItems": 2,
                    "maxItems": 2,
                },
                "per_position_file": {
                    "type": "boolean",
                    "description": (
                        "Write the whole (length x embedding_dim) float32 "
                        "matrix to a .npy file on the provider host and return "
                        "its path, shape and size instead of its contents."
                    ),
                    "default": False,
                },
                "per_position_log_prob": {
                    "type": "boolean",
                    "description": (
                        "Also return the log-probability of every observed base, "
                        "one number per position -- L-1 of them, for 1-based "
                        "positions 2..L, since the first base has no preceding "
                        "context. Refused for sequences longer "
                        f"than {MAX_POSITIONS_INLINE} bp."
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
                "model_name": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "string"}},
                "sequence_lengths": {"type": "array", "items": {"type": "integer"}},
                "layer_name": {"type": "string"},
                "embedding_dim": {"type": "integer"},
                "pooling": {"type": "string"},
                "mean_embedding": {"type": "array", "items": {"type": "number"}},
                "mean_embedding_norm": {"type": "number"},
                "position_embeddings": {"type": "object"},
                "per_position_file": {"type": "object"},
                "per_position_log_prob": {"type": "array", "items": {"type": "number"}},
                "per_position_log_prob_positions": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
                "scores": {"type": "array", "items": {"type": "number"}},
                "perplexity": {"type": "array", "items": {"type": "number"}},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "kit_route": {"type": "string"},
                "kit_path": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class Evo2EmbedTool:
    """Embed one DNA sequence. Requests queue: one at a time on the card."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            records = _clean_records(arguments.get("sequence"))
            if len(records) != 1:
                raise ValueError(
                    f"embedding takes one sequence per call; the input holds "
                    f"{len(records)} records."
                )
            sequence = records[0][1]
            options: Dict[str, Any] = {
                "task": "embed",
                "decimals": _decimals(arguments),
            }

            layer = arguments.get("layer_name")
            if layer is not None:
                if not isinstance(layer, str) or not layer.strip():
                    raise ValueError("'layer_name' must be a non-empty string.")
                options["layer_name"] = layer.strip()

            for flag in ("per_position_file", "per_position_log_prob"):
                value = arguments.get(flag, False)
                if not isinstance(value, bool):
                    raise ValueError(f"'{flag}' must be a boolean.")
                options[flag] = value
            if (
                options["per_position_log_prob"]
                and len(sequence) > MAX_POSITIONS_INLINE
            ):
                raise ValueError(
                    f"'per_position_log_prob' was asked for a {len(sequence)} bp "
                    f"sequence; the inline limit is {MAX_POSITIONS_INLINE} "
                    f"positions."
                )

            window = arguments.get("position_range")
            if window is not None:
                if (
                    not isinstance(window, list)
                    or len(window) != 2
                    or not all(
                        isinstance(v, int) and not isinstance(v, bool) for v in window
                    )
                ):
                    raise ValueError(
                        "'position_range' must be two integers, [start, end]."
                    )
                start, end = window
                if not 1 <= start <= end <= len(sequence):
                    raise ValueError(
                        f"'position_range' {window} is outside 1..{len(sequence)} "
                        f"(1-based and inclusive)."
                    )
                count = (end - start + 1) * HIDDEN_SIZE
                if count > MAX_INLINE_VALUES:
                    raise ValueError(
                        f"'position_range' {window} is {count} floats, over the "
                        f"{MAX_INLINE_VALUES} an inline reply may carry; narrow "
                        f"it to {MAX_INLINE_VALUES // HIDDEN_SIZE} positions or "
                        f"ask for 'per_position_file'."
                    )
                options["position_range"] = [start, end]
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            result = _forward(records, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in ("scores_hex", "average_reverse_complement", "batch_size"):
            result.pop(key, None)
        return result


if __name__ == "__main__":
    start_mcp_server()
