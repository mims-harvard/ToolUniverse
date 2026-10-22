"""GPN-Star variant-effect scoring — MCP server.

GPN-Star (`gpn` 0.9.0, ``gpn star vep``; songlab-cal/gpn) is a masked language
model over a window of a MULTIPLE-SPECIES ALIGNMENT, not over a bare DNA string.
For each single-nucleotide variant the window around it is read from an
alignment store the host holds (a zarr, one array per chromosome, one column per
species, the human row first), the variant's position is masked in that row, and
the score is the mean over the forward and the reverse-complement window of

    logit(alt) - logit(ref)

at the masked column. Negative means the alternate base is less likely than the
reference given what evolution does at that column across the aligned species.

This is the thin, CPU-only half of the provider. The model runs in its own
environment -- torch 2.13.0+cu130 on Python 3.13, which ToolUniverse's other
600+ tools cannot be installed beside -- and is held resident, so a request pays
the windows and the forward pass and not the interpreter, the imports, the
0.8 GB checkpoint read or the kit's per-shape set-up.

**The alignment store is an input.** The real hg38 100-way store is a 42 GB
download (songlab/multiz100way) that unpacks to ~64 GB, and it is never fetched
here. The kit ships a 0.14 MiB sparse cut that holds only the windows of eight
example variants; a host that has not pointed TOOLUNIVERSE_GPNSTAR_MSA_ROOT at a
full store answers for those and refuses everything else by name.

**The bounds are enforced twice on purpose** -- here so a bad call never
occupies the GPU, and again in the worker so a request that did not come through
this server is held to the same ceilings. Peak memory follows the batch shape,
``batch_size x window_size``, not the variant count; that PRODUCT is bounded.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of resident/gpnstar_resident_worker.py's bounds. MAX_BATCH_TOKENS is the
# envelope [gpu] vram_budget_gb is declared at: raise them in all three places
# together, after measuring.
MAX_VARIANTS = 2048
MIN_WINDOW = 16
MAX_WINDOW = 512
NATIVE_WINDOW = 128
MAX_BATCH = 64
DEFAULT_BATCH = 8
MAX_BATCH_TOKENS = 8192
MAX_REQUEST_TOKENS = 524_288
NUCLEOTIDES = "ACGT"

_PORT = 8057
_MCP = {
    "server_name": "GPN-Star MCP Server",
    "host": "127.0.0.1",
    "port": _PORT,
    "transport": "http",
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _clean(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """The request document the worker takes, or a ValueError naming what is wrong."""
    unknown = sorted(
        set(arguments) - {"variants", "window_size", "batch_size", "decimals"}
    )
    if unknown:
        raise ValueError(f"unknown argument(s) {unknown}.")

    rows = arguments.get("variants")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "'variants' must be a non-empty list of {chrom, pos, ref, alt} objects."
        )
    if len(rows) > MAX_VARIANTS:
        raise ValueError(
            f"{len(rows)} variants; this provider takes {MAX_VARIANTS} at most per "
            f"call. Split the list: calls queue on one held worker."
        )

    def integer(name: str, value: Any, lo: int, hi: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"'{name}' must be an integer.")
        if not lo <= value <= hi:
            raise ValueError(f"'{name}' must be between {lo} and {hi}.")
        return value

    window = integer(
        "window_size",
        arguments.get("window_size", NATIVE_WINDOW),
        MIN_WINDOW,
        MAX_WINDOW,
    )
    if window % 2:
        raise ValueError(
            f"'window_size' {window} is odd; the window must be even (the variant "
            f"sits at index window/2)."
        )
    batch = integer(
        "batch_size", arguments.get("batch_size", DEFAULT_BATCH), 1, MAX_BATCH
    )
    if batch * window > MAX_BATCH_TOKENS:
        raise ValueError(
            f"batch_size {batch} x window_size {window} = {batch * window} tokens "
            f"per forward; the limit is {MAX_BATCH_TOKENS}. Peak GPU memory follows "
            f"that product and the declared budget covers it -- lower either one."
        )

    if len(rows) * window > MAX_REQUEST_TOKENS:
        raise ValueError(
            f"{len(rows)} variants x window_size {window} = {len(rows) * window} "
            f"alignment columns in one call; the limit is {MAX_REQUEST_TOKENS} "
            f"(at window {window}, {MAX_REQUEST_TOKENS // window} variants). It "
            f"bounds how long one call may hold the worker -- split the list."
        )

    cleaned = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"chrom", "pos", "ref", "alt"}:
            raise ValueError(
                f"variant {i} must be an object with exactly chrom, pos, ref and alt."
            )
        chrom = row["chrom"]
        if isinstance(chrom, int) and not isinstance(chrom, bool):
            chrom = str(chrom)
        if not isinstance(chrom, str) or not chrom.strip():
            raise ValueError(
                f"variant {i}: 'chrom' must be a chromosome name, e.g. \"1\"."
            )
        pos = row["pos"]
        if isinstance(pos, bool) or not isinstance(pos, int) or pos < 1:
            raise ValueError(f"variant {i}: 'pos' must be a 1-based integer.")
        for label in ("ref", "alt"):
            v = row[label]
            if not isinstance(v, str) or len(v) != 1 or v.upper() not in NUCLEOTIDES:
                raise ValueError(
                    f"variant {i}: '{label}' must be one of A, C, G, T -- GPN-Star "
                    f"scores single-nucleotide variants, not indels."
                )
        if row["ref"].upper() == row["alt"].upper():
            raise ValueError(f"variant {i}: ref and alt are the same base.")
        cleaned.append(
            {
                "chrom": chrom.strip(),
                "pos": pos,
                "ref": row["ref"].upper(),
                "alt": row["alt"].upper(),
            }
        )

    decimals = arguments.get("decimals", 5)
    if (
        isinstance(decimals, bool)
        or not isinstance(decimals, int)
        or not 1 <= decimals <= 8
    ):
        raise ValueError("'decimals' must be an integer between 1 and 8.")
    return {
        "doc": {"variants": cleaned, "window_size": window, "batch_size": batch},
        "decimals": decimals,
    }


def _unavailable(exc: Exception) -> Dict[str, Any]:
    reason = getattr(exc, "reason", "") or type(exc).__name__
    if reason == "request_failed":
        # The worker answered and said why: a reference base that disagrees with
        # the alignment, a position the store holds nothing at. That text is the
        # answer, and hiding it behind "not available" would send the caller to
        # restart a healthy worker.
        return {"error": str(exc)}
    return {
        "error": (
            f"GPN-Star's resident worker is not available ({reason}). Run "
            f"`tu remote setup gpnstar` and read its named refusal; this provider "
            f"has no subprocess fallback, because a per-request process would "
            f"re-import the stack and re-read the checkpoint every time."
        )
    }


@register_mcp_tool(
    tool_type_name="run_gpnstar_vep",
    config={
        "description": (
            "Score single-nucleotide variants with GPN-Star, a language model "
            "over a multiple-species alignment (human hg38, 100 vertebrates for "
            "the primary model). Each variant gets a log-likelihood ratio "
            "logit(alt) - logit(ref) at its position, averaged over the forward "
            "and reverse-complement windows: negative means the alternate base "
            "is less likely than the reference given the alignment, i.e. more "
            "likely to be deleterious. Coordinates are 1-based; chromosome names "
            "follow the alignment store (1..22, X, Y; a chr prefix is accepted); "
            "the reference base must match the alignment's human base, and a "
            "mismatch is refused rather than scored. Returns one score per "
            "variant in input order. The alignment store is held by the server "
            "operator: unless a full hg38 store has been configured, only the "
            "windows of the kit's eight example variants (chromosomes 1, 2, 3 "
            "and 5) can be scored, and any other position is refused with 'the "
            "alignment holds no data'. SNVs only: no indels."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "variants": {
                    "type": "array",
                    "description": (
                        "The variants to score, in the order the scores come "
                        f"back. At most {MAX_VARIANTS} per call."
                    ),
                    "minItems": 1,
                    "maxItems": 2048,
                    "items": {
                        "type": "object",
                        "properties": {
                            "chrom": {
                                "type": "string",
                                "description": (
                                    "Chromosome as the alignment store names it, "
                                    'e.g. "1" or "X" ("chr1" is accepted).'
                                ),
                                "minLength": 1,
                            },
                            "pos": {
                                "type": "integer",
                                "description": "1-based position on the hg38 chromosome.",
                                "minimum": 1,
                            },
                            "ref": {
                                "type": "string",
                                "description": (
                                    "Reference base, which must equal the "
                                    "alignment's human base at this position."
                                ),
                                "enum": ["A", "C", "G", "T"],
                            },
                            "alt": {
                                "type": "string",
                                "description": "Alternate base; differs from ref.",
                                "enum": ["A", "C", "G", "T"],
                            },
                        },
                        "required": ["chrom", "pos", "ref", "alt"],
                        "additionalProperties": False,
                    },
                },
                "window_size": {
                    "type": "integer",
                    "description": (
                        "Alignment columns read around each variant (even). The "
                        "primary model's native window is 128. Peak GPU memory "
                        "follows batch_size x window_size, which may not exceed "
                        f"{MAX_BATCH_TOKENS}; variants x window_size may not "
                        f"exceed {MAX_REQUEST_TOKENS}."
                    ),
                    "default": 128,
                    "minimum": 16,
                    "maximum": 512,
                    "multipleOf": 2,
                },
                "batch_size": {
                    "type": "integer",
                    "description": (
                        "Variants per forward pass. Does not change the scores' "
                        "meaning; it trades memory for speed. batch_size x "
                        f"window_size may not exceed {MAX_BATCH_TOKENS}."
                    ),
                    "default": 8,
                    "minimum": 1,
                    "maximum": 64,
                },
                "decimals": {
                    "type": "integer",
                    "description": "Decimal places for returned scores (default 5).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 8,
                },
            },
            "required": ["variants"],
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "model_name": {"type": "string"},
                "task": {"type": "string"},
                "n_variants": {"type": "integer"},
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "chrom:pos:ref>alt for each variant, in input order.",
                },
                "scores": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "logit(alt) - logit(ref), mean of both strands.",
                },
                "scores_sha256": {"type": "string"},
                "window_size": {"type": "integer"},
                "batch_size": {"type": "integer"},
                "n_batches": {"type": "integer"},
                "single_variant_sent_twice": {
                    "type": "boolean",
                    "description": (
                        "True when the call held one variant: upstream's own "
                        "command fails on a one-row table, so the variant was "
                        "scored in a batch of two copies and the first score kept."
                    ),
                },
                "levers_declined": {"type": "array", "items": {"type": "string"}},
                "alignment": {"type": "string"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "levers_applied": {"type": "array", "items": {"type": "string"}},
                "kit_kv_routes": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config=_MCP,
)
class GpnstarVepTool:
    """Score SNVs. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import json

        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            request = _clean(arguments)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            reply = _worker().request(
                {
                    "op": "predict",
                    "input": json.dumps(request["doc"]),
                    "name": "gpnstar",
                    "options": {"decimals": request["decimals"]},
                }
            )
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)
        return dict(reply["result"])


if __name__ == "__main__":
    start_mcp_server()
