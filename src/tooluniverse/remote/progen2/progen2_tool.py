"""ProGen2 protein language model — MCP server.

ProGen2 (``salesforce/progen`` @ ``c27a419c``) is an autoregressive protein
language model. Upstream ships exactly two commands and this provider serves
exactly those two:

* ``likelihood.py`` — the log-likelihood the model assigns to a sequence,
  averaged over the left-to-right and right-to-left directions, as ``ll_sum``
  and ``ll_mean``. Use it to rank designs, compare variants of one protein, or
  ask how protein-like a sequence is.
* ``sample.py`` — nucleus sampling of new sequences from a prompt, which may be
  the start token alone.

This is the thin, CPU-only half of the provider. The model runs in its own
environment — Python 3.9 with torch 2.8.0+cu129 and transformers 4.16.2, which
is the oldest interpreter of the fifteen providers and which ToolUniverse's
other 600+ tools cannot be installed beside — and is held resident, because the
checkpoint read and the CUDA context are the whole per-process cost (the kit's
own Notes: "the gain arrives with many sequences per process") and nothing here
compiles a kernel to amortise.

**Why both operations refuse rather than clip.** Chai-1's oversized reply was
truncated by the MCP transport at exactly 100,000 characters, which produced
invalid JSON rather than an honest refusal. So: ``per_token_log_prob`` is
refused above a stated position count instead of being cut short, the whole
array comes back as a path to a ``.npy`` file and never inline, and generation
is bounded in BOTH directions — at most 16 sequences of at most 1024 tokens,
which is also what the VRAM budget under ``[gpu]`` is declared at. Every bound
below is checked here AND in the worker, on purpose: here so a caller gets a
useful message without occupying the GPU, and there so a request that did not
come through this server cannot build a reply nothing can transport or a K/V
cache nothing budgeted for.
"""

import os
import tempfile
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds and of [runtime] worker_args.
CHECKPOINT = "progen2-base"
# progen2-base's context window (stock/PINS.json weights.progen2-base.config_fields
# n_positions). It is the only size whose window is 2048 rather than 1024, which is
# why this provider serves it; the stock refuses a longer sequence by name.
N_POSITIONS = 2048
MAX_POSITIONS_INLINE = 2_048
MAX_NUM_SAMPLES = 16
MAX_GENERATE_LENGTH = 1024
# The two bounds above are each individually sane and their PRODUCT is not.
# Measured on one card, fresh worker per point: 8 x 512 tokens costs 5.81 GiB,
# 8 x 1024 costs 29.2, and 16 x 1024 -- which the two ceilings above permit
# together -- costs **116.93 GiB**, essentially the whole device. Peak is
# roughly quadratic in num_samples x max_length because attention runs over the
# full generated context and nothing caps the K/V cache.
#
# So the real bound is on the product, and it has to exist in the tool as well
# as in the budget: a declared input ceiling that admits a request no budget can
# cover is not a bound. 4096 is the largest product measured at a figure a host
# can schedule alongside the other providers (5.81 GiB), and `[gpu]
# vram_budget_gb` is declared there.
MAX_GENERATE_TOKEN_BUDGET = 4096
# The tokenizer's vocabulary minus the three specials and the two terminals: 25
# letters, A..Z without J (stock/PINS.json `tokenizer.ids`).
AMINO_ACIDS = set("ABCDEFGHIKLMNOPQRSTUVWXYZ")
TERMINALS = ("1", "2")

_PORT = 8047
_MCP = {
    "server_name": "ProGen2 MCP Server",
    "host": "127.0.0.1",
    "port": _PORT,
    "transport": "http",
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _content_lines(value: str) -> list:
    return [
        line.strip()
        for line in value.splitlines()
        if line.strip() and not line.strip().startswith(("#", ";"))
    ]


def _clean_sequence(value: Any, *, closed: bool) -> str:
    """One ProGen2 context out of a raw string or a single-record FASTA.

    ``closed`` is True for scoring, where the sequence is a complete protein and is
    wrapped ``1<seq>2`` if the caller did not wrap it, and False for generation,
    where the input is a PREFIX and must not be closed with a C-terminus marker --
    closing it would ask the model to continue past the end of a protein.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("'sequence' must be a non-empty protein sequence or FASTA.")
    lines = _content_lines(value)
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
        raw = records[0]
    else:
        raw = "".join(lines)
    raw = "".join(raw.split()).upper()
    if not raw:
        raise ValueError("the input carries no sequence.")

    if closed:
        if raw[0] in TERMINALS or raw[-1] in TERMINALS:
            if raw[0] not in TERMINALS or raw[-1] not in TERMINALS:
                raise ValueError(
                    f"the sequence carries a terminal marker at one end only "
                    f"({raw[0]!r} ... {raw[-1]!r}). A ProGen2 context is "
                    f"'1<seq>2' (N to C) or '2<seq>1' (C to N); or give the amino "
                    f"acids alone and they will be wrapped."
                )
            body, ctx = raw[1:-1], raw
        else:
            body, ctx = raw, TERMINALS[0] + raw + TERMINALS[1]
    else:
        if raw[-1] in TERMINALS and len(raw) > 1:
            raise ValueError(
                f"the prompt ends with the terminus marker {raw[-1]!r}, which "
                f"closes the protein; generation continues a prompt, so give the "
                f"N-terminal fragment without a closing marker (or score it with "
                f"run_progen2_score instead)."
            )
        ctx = raw if raw[0] in TERMINALS else TERMINALS[0] + raw
        body = ctx[1:]

    bad = sorted(set(body) - AMINO_ACIDS)
    if bad:
        raise ValueError(
            f"the sequence holds {bad}, which are neither amino-acid letters nor "
            f"ProGen2 terminal markers at the ends."
        )
    if len(ctx) > N_POSITIONS:
        raise ValueError(
            f"the context is {len(ctx)} tokens and {CHECKPOINT}'s context window "
            f"is {N_POSITIONS}; ProGen2 refuses a longer sequence by name."
        )
    return ctx


def _run(sequence: str, options: Dict[str, Any], seed=None) -> Dict[str, Any]:
    """One request on the resident worker, or a named reason why not."""
    with tempfile.TemporaryDirectory(prefix="progen2-") as work:
        request = {
            "op": "predict",
            "input": sequence,
            "out_dir": work,
            "name": "progen2",
            "options": options,
        }
        if seed is not None:
            request["seed"] = seed
        reply = _worker().request(request)
        result = dict(reply["result"])
        # The .npy lives in a directory that is about to be removed, so it is moved
        # somewhere the caller can actually open. Writing it straight to a
        # persistent path would leave a file behind on every failure after the
        # write.
        info = result.get("per_token_file")
        if info and os.path.isfile(info.get("path", "")):
            keep = tempfile.mkdtemp(prefix="progen2-logprobs-")
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
            f"ProGen2's resident worker is not available ({reason}). Run "
            f"`tu remote setup progen2` and read its named refusal; this provider "
            f"has no subprocess fallback, because a per-request checkpoint read "
            f"would look like the provider working while costing far more than it "
            f"appears to."
        )
    }


def _int(arguments: Dict[str, Any], name: str, default: int, lo: int, hi: int) -> int:
    value = arguments.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{name}' must be an integer.")
    if not lo <= value <= hi:
        raise ValueError(f"'{name}' must be between {lo} and {hi}.")
    return value


def _float(
    arguments: Dict[str, Any], name: str, default: float, lo: float, hi: float
) -> float:
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{name}' must be a number.")
    value = float(value)
    if not lo < value <= hi:
        raise ValueError(f"'{name}' must be greater than {lo} and at most {hi}.")
    return value


def _bool(arguments: Dict[str, Any], name: str, default: bool = False) -> bool:
    value = arguments.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"'{name}' must be a boolean.")
    return value


_SEQUENCE_PROPERTY = {
    "type": "string",
    "description": (
        "One protein sequence in single-letter amino-acid code, or a "
        "single-record FASTA. ProGen2's own terminal markers are accepted: "
        "'1<seq>2' reads N to C and '2<seq>1' reads C to N. Given amino acids "
        f"alone the sequence is wrapped '1<seq>2'. At most {N_POSITIONS - 2} "
        f"residues ({CHECKPOINT}'s context window is {N_POSITIONS} tokens)."
    ),
    "minLength": 1,
}


@register_mcp_tool(
    tool_type_name="run_progen2_score",
    config={
        "description": (
            "Score one protein sequence with the ProGen2 protein language model: "
            "the log-likelihood it assigns to the sequence, as a sum over "
            "residues (ll_sum), a per-residue mean (ll_mean) and the "
            "corresponding perplexity. Both are the average of the "
            "left-to-right and right-to-left readings, which is what ProGen2's "
            "own likelihood.py reports. Use it to rank designed sequences, "
            "compare variants of one protein, or judge how protein-like a "
            "sequence is. Higher (less negative) ll_mean means the model finds "
            "the sequence more likely. Per-residue log-probabilities are opt-in "
            "and bounded, because a long sequence is a long array; the whole "
            "array can be written to a .npy file instead."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": _SEQUENCE_PROPERTY,
                "per_token_log_prob": {
                    "type": "boolean",
                    "description": (
                        "Return the log-probability of every scored token, left "
                        "to right, one number per position. Refused, not "
                        f"clipped, above {MAX_POSITIONS_INLINE} positions -- ask "
                        "for 'per_token_file' instead."
                    ),
                    "default": False,
                },
                "per_token_file": {
                    "type": "boolean",
                    "description": (
                        "Write the per-token log-probabilities to a float32 .npy "
                        "file on the provider host and return its path, shape "
                        "and size instead of its contents."
                    ),
                    "default": False,
                },
                "decimals": {
                    "type": "integer",
                    "description": "Decimal places for returned floats (default 6).",
                    "default": 6,
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
                "checkpoint": {"type": "string"},
                "sequence_length": {"type": "integer"},
                "context_tokens": {"type": "integer"},
                "ll_sum": {"type": "number"},
                "ll_mean": {"type": "number"},
                "ll_left_to_right_sum": {"type": "number"},
                "ll_right_to_left_sum": {"type": "number"},
                "ll_left_to_right_mean": {"type": "number"},
                "ll_right_to_left_mean": {"type": "number"},
                "perplexity": {"type": "number"},
                "per_token_log_prob": {"type": "array", "items": {"type": "number"}},
                "per_token_file": {"type": "object"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class Progen2ScoreTool:
    """Score one sequence. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequence = _clean_sequence(arguments.get("sequence"), closed=True)
            options: Dict[str, Any] = {
                "task": "score",
                "decimals": _int(arguments, "decimals", 6, 1, 8),
                "per_token_log_prob": _bool(arguments, "per_token_log_prob"),
                "per_token_file": _bool(arguments, "per_token_file"),
            }
            if options["per_token_log_prob"] and len(sequence) > MAX_POSITIONS_INLINE:
                raise ValueError(
                    f"'per_token_log_prob' was asked for a {len(sequence)}-token "
                    f"context; the inline limit is {MAX_POSITIONS_INLINE} "
                    f"positions. Use 'per_token_file' instead."
                )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            return _run(sequence, options)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


@register_mcp_tool(
    tool_type_name="run_progen2_generate",
    config={
        "description": (
            "Generate new protein sequences with the ProGen2 protein language "
            "model by nucleus sampling, optionally continuing a prompt. Use it "
            "to propose candidate sequences, extend a partial design, or sample "
            "a family's neighbourhood. Give 'prompt' an N-terminal fragment to "
            "condition on, or leave it out for an unconditioned sample. Output "
            "is bounded on purpose: at most "
            f"{MAX_NUM_SAMPLES} sequences of at most {MAX_GENERATE_LENGTH} "
            "tokens each, which is what the provider's VRAM budget is declared "
            "at. Results are reproducible for a given 'seed'."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "An N-terminal fragment to continue, in single-letter "
                        "amino-acid code, or a single-record FASTA. Omit it (or "
                        "give '1') to sample without conditioning. The prompt is "
                        "NOT closed with a C-terminus marker, because generation "
                        "continues it."
                    ),
                },
                "num_samples": {
                    "type": "integer",
                    "description": (
                        f"How many sequences to sample (1-{MAX_NUM_SAMPLES}). "
                        "Peak GPU memory is roughly linear in num_samples x "
                        "max_length."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_NUM_SAMPLES,
                },
                "max_length": {
                    "type": "integer",
                    "description": (
                        "Total token budget per sequence INCLUDING the prompt "
                        f"(ProGen2's own --max-length). At most "
                        f"{MAX_GENERATE_LENGTH}. Sampling stops early at a "
                        "terminus marker."
                    ),
                    "default": 256,
                    "minimum": 2,
                    "maximum": MAX_GENERATE_LENGTH,
                },
                "temperature": {
                    "type": "number",
                    "description": (
                        "Sampling temperature (ProGen2's --t; its default is "
                        "0.2, which samples conservatively). Higher is more "
                        "diverse and less protein-like."
                    ),
                    "default": 0.2,
                    "minimum": 0.01,
                    "maximum": 2.0,
                },
                "top_p": {
                    "type": "number",
                    "description": (
                        "Nucleus sampling threshold (ProGen2's --p, default 0.95)."
                    ),
                    "default": 0.95,
                    "minimum": 0.01,
                    "maximum": 1.0,
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed (ProGen2's --rng-seed, default 42). The "
                        "same seed and the same arguments give the same "
                        "sequences."
                    ),
                    "default": 42,
                    "minimum": 0,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "checkpoint": {"type": "string"},
                "prompt": {"type": "string"},
                "num_samples": {"type": "integer"},
                "max_length": {"type": "integer"},
                "temperature": {"type": "number"},
                "top_p": {"type": "number"},
                "seed": {"type": "integer"},
                "sequences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "sequence": {"type": "string"},
                            "context_and_completion": {"type": "string"},
                            "length": {"type": "integer"},
                            "terminated": {"type": "boolean"},
                        },
                    },
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
class Progen2GenerateTool:
    """Sample sequences. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            prompt = arguments.get("prompt")
            context = (
                TERMINALS[0]
                if prompt in (None, "", TERMINALS[0])
                else _clean_sequence(prompt, closed=False)
            )
            num_samples = _int(arguments, "num_samples", 1, 1, MAX_NUM_SAMPLES)
            max_length = _int(arguments, "max_length", 256, 2, MAX_GENERATE_LENGTH)
            if num_samples * max_length > MAX_GENERATE_TOKEN_BUDGET:
                raise ValueError(
                    f"num_samples x max_length is "
                    f"{num_samples * max_length}, over this provider's "
                    f"{MAX_GENERATE_TOKEN_BUDGET}-token generation budget. "
                    f"Peak VRAM is roughly quadratic in that product: 4096 "
                    f"tokens costs 5.81 GiB and 16384 costs 116.93, measured. "
                    f"Ask for fewer or shorter sequences, or run them as "
                    f"separate requests -- a held worker makes that cheap."
                )
            if max_length <= len(context):
                raise ValueError(
                    f"'max_length' is {max_length} and the prompt is already "
                    f"{len(context)} tokens; it must be larger, because "
                    f"max_length is the total budget including the prompt."
                )
            options = {
                "task": "generate",
                "num_samples": num_samples,
                "max_length": max_length,
                "temperature": _float(arguments, "temperature", 0.2, 0.0, 2.0),
                "top_p": _float(arguments, "top_p", 0.95, 0.0, 1.0),
            }
            seed = _int(arguments, "seed", 42, 0, 2**31 - 1)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            return _run(context, options, seed=seed)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


if __name__ == "__main__":
    start_mcp_server()
