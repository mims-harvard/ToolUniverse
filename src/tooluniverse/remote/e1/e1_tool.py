"""Profluent E1 protein language model — MCP server.

E1 1.0.0 (``E1ForMaskedLM`` -> ``E1Scorer`` / ``E1Predictor``) is a masked
protein language model whose distinguishing feature is that it can condition on
*retrieved context* sequences — homologues supplied alongside the query — rather
than on the query alone. Two things are worth serving from one forward pass:

``run_e1_score_variants``
    upstream's own entry point (``python -m E1.tools.score``): one parent
    sequence and its equal-length point mutants, scored by masked-marginal or
    wildtype-marginal log-probability ratio, optionally against context
    sequences. This is zero-shot variant effect prediction.

``run_e1_embed``
    one sequence's mean-pooled hidden state, for comparing, clustering or
    searching proteins by learned representation.

This is the thin, CPU-only half of the provider. The model runs in its own
environment — torch 2.8.0 on Python 3.12.10, with a CUDA stack ToolUniverse's
other 600+ tools cannot be installed beside — and is held resident, because
every fresh ``score`` process spends about 15 s on interpreter start and
checkpoint read before the first forward (the kit's README says so), and the
forward itself is a fraction of that for a small assay.

**Why the embedding default is a single vector.** E1-600m's hidden size is 1280,
so one residue's embedding is already ~12 kB of JSON and a 300-residue matrix is
384,000 numbers. The MCP transport truncated Chai-1's oversized reply at exactly
100,000 characters, which produced invalid JSON rather than an honest refusal.
So ``run_e1_embed`` returns the mean-pooled vector by default; a bounded window
of residue vectors is opt-in and is refused *by number of floats* rather than
silently clipped; and the whole matrix comes back as a path to a ``.npy`` file,
never inline. Enformer's ``track_indices`` and ESM C's ``residue_range`` are the
precedent for the bounded form.

Every bound below is also enforced in ``resident/e1_resident_worker.py``. Here
so a bad call is answered without ever occupying the GPU; there so a request
that did not come through this server cannot build a reply nothing can
transport.
"""

import os
import tempfile
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds.
MAX_RESIDUES = 2_048
MAX_MUTANTS = 256
MAX_CONTEXTS = 4
MAX_CONTEXT_RESIDUES = 1_024
MAX_INLINE_VALUES = 20_000
# Upstream's E1Scorer asserts uppercase A-Z with X excluded, so this is
# upstream's set and not a superset of it.
AMINO_ACIDS = set("ABCDEFGHIJKLMNOPQRSTUVWYZ")
SCORING_METHODS = ("masked_marginal", "wildtype_marginal")
CONTEXT_REDUCTIONS = ("mean", "none")

# The hidden width of the size this provider serves, used only to put a residue
# count in the refusal message beside the float count.
_HIDDEN = 1280

_PORT = 8044
_MCP = {
    "server_name": "Profluent E1 MCP Server",
    "host": "127.0.0.1",
    "port": _PORT,
    "transport": "http",
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _records(value: Any, field: str) -> list:
    """``[(id, sequence)]`` from a FASTA string, or one record from a bare one."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field}' must be a non-empty sequence or FASTA string.")
    lines = [ln.strip() for ln in value.splitlines()]
    lines = [ln for ln in lines if not ln.startswith((";", "#"))]
    if not any(ln.startswith(">") for ln in lines):
        seq = "".join("".join(lines).split()).upper()
        if not seq:
            raise ValueError(f"'{field}' carries no sequence.")
        return [("query", seq)]
    out, name, cur = [], None, []
    for ln in lines:
        if ln.startswith(">"):
            if name is not None:
                out.append((name, "".join(cur)))
            head = ln[1:].strip()
            name, cur = (head.split()[0] if head else ""), []
        elif ln:
            cur.append(ln)
    if name is not None:
        out.append((name, "".join(cur)))
    records = [
        (n or f"seq{i}", "".join(s.split()).upper())
        for i, (n, s) in enumerate(out)
        if s.strip()
    ]
    if not records:
        raise ValueError(f"'{field}' carries no sequence.")
    return records


def _check(seq: str, what: str, limit: int) -> str:
    bad = sorted(set(seq) - AMINO_ACIDS)
    if bad:
        raise ValueError(
            f"{what} holds {bad}, which E1 does not accept: uppercase A-Z, and "
            f"X is excluded by upstream's own assertion."
        )
    if len(seq) > limit:
        raise ValueError(f"{what} is {len(seq)} residues; the limit is {limit}.")
    return seq


def _int(arguments: Dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    value = arguments.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{key}' must be an integer.")
    if not lo <= value <= hi:
        raise ValueError(f"'{key}' must be between {lo} and {hi}.")
    return value


def _bool(arguments: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"'{key}' must be a boolean.")
    return value


def _choice(arguments: Dict[str, Any], key: str, allowed, default: str) -> str:
    value = arguments.get(key, default)
    if not isinstance(value, str) or value.strip().lower() not in allowed:
        raise ValueError(f"'{key}' must be one of {list(allowed)}.")
    return value.strip().lower()


def _context_block(arguments: Dict[str, Any]) -> str:
    """The validated context FASTA, or ``""``."""
    raw = arguments.get("context_sequences")
    if raw is None:
        return ""
    records = _records(raw, "context_sequences")
    if len(records) > MAX_CONTEXTS:
        raise ValueError(
            f"{len(records)} context sequences were given; at most "
            f"{MAX_CONTEXTS} are accepted, because scoring runs once per "
            f"context and the forward work is multiplied by their number."
        )
    for name, seq in records:
        _check(seq, f"context {name!r}", MAX_CONTEXT_RESIDUES)
    return "\n".join(f">{n}\n{s}" for n, s in records)


def _forward(text: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """One forward pass on the resident worker, or a named reason why not."""
    with tempfile.TemporaryDirectory(prefix="e1-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": text,
                "out_dir": work,
                "name": "e1",
                "options": options,
            }
        )
        result = dict(reply["result"])
        # The .npy lives in a directory that is about to be removed, so it is
        # moved somewhere the caller can actually open it. Writing it straight
        # to a persistent path would leave a file behind on every failure that
        # happened after the write.
        info = result.get("per_residue_file")
        if info and os.path.isfile(info.get("path", "")):
            keep = tempfile.mkdtemp(prefix="e1-embeddings-")
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
            f"E1's resident worker is not available ({reason}). Run "
            f"`tu remote setup e1` and read its named refusal; this provider "
            f"has no subprocess fallback, because the checkpoint read and "
            f"interpreter start cost about 15 s per request and would look "
            f"like the provider working while costing far more than it appears "
            f"to."
        )
    }


_SEQUENCE_PROPERTY = {
    "type": "string",
    "description": (
        "One protein sequence in single-letter amino-acid code, or a "
        f"single-record FASTA. At most {MAX_RESIDUES} residues. Upstream "
        f"rejects 'X'."
    ),
    "minLength": 1,
}
_CONTEXT_PROPERTY = {
    "type": "string",
    "description": (
        "Optional FASTA of retrieved context sequences (homologues) to "
        "condition the scores on -- this is what distinguishes E1 from a "
        f"context-free protein language model. At most {MAX_CONTEXTS} records "
        f"of {MAX_CONTEXT_RESIDUES} residues each; they need not be the "
        "parent's length. Omit for an unconditioned score."
    ),
}


@register_mcp_tool(
    tool_type_name="run_e1_score_variants",
    config={
        "description": (
            "Score protein point mutants against their parent sequence with "
            "the Profluent E1 masked protein language model: zero-shot variant "
            "effect prediction. Give one parent sequence and the mutant "
            "sequences, all of the same length (E1 scores substitutions, not "
            "insertions or deletions); each mutant comes back with a score "
            "that is the summed log-probability of its substituted residues "
            "minus that of the parent's, so a higher score means the model "
            "favours the mutant. Optionally condition the scores on retrieved "
            "homologues via 'context_sequences', which is what E1 is built "
            "for. Use it to rank designs, prioritise a mutagenesis library, or "
            "predict which substitutions a protein tolerates."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "parent_sequence": _SEQUENCE_PROPERTY,
                "mutant_sequences": {
                    "type": "string",
                    "description": (
                        "FASTA of the mutants to score, each the same length as "
                        f"the parent. At most {MAX_MUTANTS} records. Record "
                        "names come back as the score ids, so naming them "
                        "'S6R', 'R18V' and so on makes the reply readable."
                    ),
                    "minLength": 1,
                },
                "context_sequences": _CONTEXT_PROPERTY,
                "scoring_method": {
                    "type": "string",
                    "description": (
                        "'masked_marginal' (the default, and upstream's) masks "
                        "each substituted position of the parent in turn, which "
                        "costs one forward per mutated position and is the "
                        "stronger predictor. 'wildtype_marginal' reads every "
                        "position's logits off a single unmasked forward of the "
                        "parent: one forward total, cheaper, less accurate."
                    ),
                    "enum": list(SCORING_METHODS),
                    "default": "masked_marginal",
                },
                "context_reduction": {
                    "type": "string",
                    "description": (
                        "With 'context_sequences': 'mean' (default) averages "
                        "each mutant's score over the contexts and returns one "
                        "row per mutant; 'none' returns one row per (mutant, "
                        "context) pair. Ignored without contexts."
                    ),
                    "enum": list(CONTEXT_REDUCTIONS),
                    "default": "mean",
                },
                "top_n": {
                    "type": "integer",
                    "description": (
                        "How many highest-scoring mutants to repeat under "
                        "'best' (default 10). The full 'scores' list is always "
                        "returned; this is a convenience ordering."
                    ),
                    "default": 10,
                    "minimum": 0,
                    "maximum": 100,
                },
            },
            "required": ["parent_sequence", "mutant_sequences"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "variant": {"type": "string"},
                "parent_id": {"type": "string"},
                "parent_length": {"type": "integer"},
                "n_mutants": {"type": "integer"},
                "n_scored": {"type": "integer"},
                "scoring_method": {"type": "string"},
                "context_reduction": {"type": "string"},
                "context_ids": {"type": "array", "items": {"type": "string"}},
                "score_units": {"type": "string"},
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "context_id": {"type": ["string", "null"]},
                            "score": {"type": "number"},
                        },
                    },
                },
                "best": {"type": "array", "items": {"type": "object"}},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class E1ScoreVariantsTool:
    """Score mutants against a parent. Requests queue: one at a time."""

    _DROP = ("mean_embedding", "mean_embedding_norm", "embedding_dim", "pooling")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            parents = _records(arguments.get("parent_sequence"), "parent_sequence")
            if len(parents) != 1:
                raise ValueError(
                    f"'parent_sequence' holds {len(parents)} records; upstream "
                    f"asserts exactly one parent sequence per call."
                )
            parent_id, parent = parents[0]
            _check(parent, "the parent sequence", MAX_RESIDUES)

            mutants = _records(arguments.get("mutant_sequences"), "mutant_sequences")
            if len(mutants) > MAX_MUTANTS:
                raise ValueError(
                    f"{len(mutants)} mutants were given; at most {MAX_MUTANTS} "
                    f"are accepted."
                )
            wrong = sorted({len(s) for _, s in mutants} - {len(parent)})
            if wrong:
                raise ValueError(
                    f"mutants of length {wrong} were given and the parent is "
                    f"{len(parent)} residues; E1 scores substitutions only, so "
                    f"every mutant must be the parent's length."
                )
            for name, seq in mutants:
                _check(seq, f"mutant {name!r}", MAX_RESIDUES)

            options: Dict[str, Any] = {
                "op": "score",
                "scoring_method": _choice(
                    arguments, "scoring_method", SCORING_METHODS, "masked_marginal"
                ),
                "context_reduction": _choice(
                    arguments, "context_reduction", CONTEXT_REDUCTIONS, "mean"
                ),
                "top_n": _int(arguments, "top_n", 10, 0, 100),
            }
            context = _context_block(arguments)
            if context:
                options["context_sequences"] = context

            text = "\n".join(
                [f">{parent_id}", parent]
                + [line for n, s in mutants for line in (f">{n}", s)]
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            result = _forward(text, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in self._DROP:
            result.pop(key, None)
        return result


@register_mcp_tool(
    tool_type_name="run_e1_embed",
    config={
        "description": (
            "Embed one protein sequence with the Profluent E1 protein language "
            "model and return the mean-pooled embedding vector. Use it to "
            "compare, cluster or search proteins by learned representation. "
            "The full per-residue matrix is NOT returned inline (1280 floats "
            "per residue at the 600m size): ask for 'residue_range' to get a "
            "bounded window of residue vectors, or 'per_residue_file' to get "
            "the whole matrix written as a .npy file whose path comes back."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": _SEQUENCE_PROPERTY,
                "residue_range": {
                    "type": "array",
                    "description": (
                        "Inclusive 1-based [start, end] window of residue "
                        "vectors to return inline. Refused, not clipped, when "
                        f"(end - start + 1) * embedding_dim exceeds "
                        f"{MAX_INLINE_VALUES} floats -- at the 600m size's "
                        f"{_HIDDEN} dimensions that is "
                        f"{MAX_INLINE_VALUES // _HIDDEN} residues."
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
                "sequence_id": {"type": "string"},
                "sequence_length": {"type": "integer"},
                "embedding_dim": {"type": "integer"},
                "pooling": {"type": "string"},
                "mean_embedding": {"type": "array", "items": {"type": "number"}},
                "mean_embedding_norm": {"type": "number"},
                "residue_embeddings": {"type": "object"},
                "per_residue_file": {"type": "object"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class E1EmbedTool:
    """Embed one sequence. Requests queue: the worker serves one at a time."""

    _DROP = (
        "scores",
        "best",
        "score_units",
        "scoring_method",
        "context_reduction",
        "context_ids",
        "levers_applied",
    )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            records = _records(arguments.get("sequence"), "sequence")
            if len(records) != 1:
                raise ValueError(
                    f"'sequence' holds {len(records)} records; this operation "
                    f"embeds one sequence per call."
                )
            name, seq = records[0]
            _check(seq, "the sequence", MAX_RESIDUES)

            options: Dict[str, Any] = {
                "op": "embed",
                "decimals": _int(arguments, "decimals", 5, 1, 8),
                "per_residue_file": _bool(arguments, "per_residue_file"),
            }

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
                if not 1 <= start <= end <= len(seq):
                    raise ValueError(
                        f"'residue_range' {window} is outside 1..{len(seq)} "
                        f"(1-based and inclusive)."
                    )
                count = (end - start + 1) * _HIDDEN
                if count > MAX_INLINE_VALUES:
                    raise ValueError(
                        f"'residue_range' {window} is about {count} floats, "
                        f"over the {MAX_INLINE_VALUES} an inline reply may "
                        f"carry; narrow the range to about "
                        f"{MAX_INLINE_VALUES // _HIDDEN} residues, or ask for "
                        f"'per_residue_file'."
                    )
                options["residue_range"] = [start, end]
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            result = _forward(f">{name}\n{seq}", options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        for key in self._DROP:
            result.pop(key, None)
        return result


if __name__ == "__main__":
    start_mcp_server()
