"""Borzoi variant effect scoring from calico's own release, served from a held worker.

This tool runs in ToolUniverse's own interpreter and never imports TensorFlow.
Its job is to check a request, hand it to the resident worker over a Unix
socket, and shape the reply.

WHY A SECOND BORZOI, AND WHY IT IS NOT THE SAME OPERATION. ToolUniverse already
serves Borzoi at port 8012 through `borzoi-pytorch`, a community port, with
`run_borzoi_variant_effect` -- which takes two SEQUENCES and returns the
ref-vs-alt delta at the central bin. This one runs calico's own
`src/scripts/borzoi_sad.py`: it takes VARIANTS against pinned hg38, scores each
one through the reverse-complement ensemble, untransforms the predictions with
upstream's own targets table, sums strand pairs down to 6,385 tracks, and
returns upstream's four published statistics -- SAD, logSAD, D2, logD2. That is
the method the Borzoi paper reports, not an approximation of it, and the
provider's `sad.h5` is written by stock's own writer.

The two differ in what they need, too: this one reads the genome, so the caller
sends coordinates rather than sequence, and cannot be asked about a sequence
that is not in hg38.

The ceilings below mirror the worker's module constants. They are restated
rather than imported -- the two processes share no dependency set -- and checked
in both places: a ceiling only the worker knows is a ceiling a caller discovers
after twenty minutes of work.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirrors of the worker's own bounds
# (resident/borzoi_calico_resident_worker.py).
MAX_VARIANTS = int(os.environ.get("BORZOI_CALICO_MAX_VARIANTS", "4"))
MAX_TOP_TRACKS = 100
STATS = ("SAD", "logSAD", "D2", "logD2")
N_TRACKS = 6385
# About 255 s per variant on this CPU.
SECONDS_PER_VARIANT = 255


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

    variants = arguments.get("variants")
    if not isinstance(variants, list) or not variants:
        return {
            "error": (
                "'variants' must be a non-empty list of objects with 'chrom', "
                "'pos', 'ref' and 'alt' (and optionally 'id'). Coordinates are "
                "GRCh38/hg38, 1-based, as in a VCF."
            )
        }
    if len(variants) > MAX_VARIANTS:
        return {
            "error": (
                f"'variants' holds {len(variants)}; the ceiling is "
                f"{MAX_VARIANTS}. Each costs about {SECONDS_PER_VARIANT} s on "
                f"this CPU-only deployment, so {MAX_VARIANTS} is already about "
                f"{MAX_VARIANTS * SECONDS_PER_VARIANT // 60} minutes."
            )
        }

    cleaned = []
    for i, v in enumerate(variants):
        if not isinstance(v, dict):
            return {"error": f"variant {i} is not an object."}
        missing = [
            k for k in ("chrom", "pos", "ref", "alt") if not str(v.get(k, "")).strip()
        ]
        if missing:
            return {"error": f"variant {i} is missing {missing}."}
        try:
            pos = int(str(v["pos"]).strip())
        except (TypeError, ValueError):
            return {"error": f"variant {i} 'pos' must be an integer; got {v['pos']!r}."}
        if pos < 1:
            return {"error": f"variant {i} 'pos' must be 1-based and positive."}
        for key in ("ref", "alt"):
            allele = str(v[key]).strip().upper()
            if not allele or set(allele) - set("ACGT"):
                return {
                    "error": (
                        f"variant {i} '{key}' is {allele!r}; only A, C, G and T "
                        f"are accepted. Indels are not scored by this operation."
                    )
                }
        # The `chr` prefix is settled here and again in the worker. baskerville
        # prepends it to a bare name, so `1` and `chr1` reach the same sequence
        # -- but the id written into sad.h5 is whatever the caller sent, and two
        # callers who disagree about the prefix would get rows that look like
        # different variants.
        chrom = str(v["chrom"]).strip()
        if not chrom.startswith("chr"):
            chrom = "chr" + chrom
        cleaned.append(
            {
                "chrom": chrom,
                "pos": pos,
                "ref": str(v["ref"]).strip().upper(),
                "alt": str(v["alt"]).strip().upper(),
                "id": str(v.get("id") or "").strip()
                or f"{chrom}_{pos}_{str(v['ref']).strip().upper()}_{str(v['alt']).strip().upper()}",
            }
        )

    top = arguments.get("top_tracks", 20)
    if not isinstance(top, int) or isinstance(top, bool):
        return {"error": "'top_tracks' must be an integer."}
    if not 1 <= top <= MAX_TOP_TRACKS:
        return {
            "error": (
                f"'top_tracks' must be between 1 and {MAX_TOP_TRACKS}; got "
                f"{top}. The full {N_TRACKS}-track vectors stay in the "
                f"provider's sad.h5, whose path is in the reply."
            )
        }

    return {"variants": cleaned, "top_tracks": top}


def _score(doc: Dict[str, Any]) -> Dict[str, Any]:
    from tooluniverse.remote_resident.supervisor import (
        WorkerRequestError,
        WorkerStartError,
    )

    worker = _worker()
    try:
        reply = worker.request({"op": "predict", **doc})
    except WorkerStartError as exc:
        return {"error": f"the Borzoi (calico) worker could not be started: {exc}"}
    except WorkerRequestError as exc:
        return {"error": f"Borzoi (calico) refused the request: {exc}"}
    result = reply.get("result") or {}
    return {
        "implementation": "calico/borzoi borzoi_sad.py @ 5c93582 (fold 0, --rc)",
        "n_variants": result.get("n_variants"),
        "n_tracks": result.get("n_tracks"),
        "stats": result.get("stats"),
        "variants": result.get("variants"),
        "sad_h5": result.get("sad_h5"),
        "timing_s": result.get("timing_s"),
    }


@register_mcp_tool(
    tool_type_name="run_borzoi_calico_sad",
    config={
        "name": "run_borzoi_calico_sad",
        "description": (
            "Score regulatory variants with CALICO'S OWN Borzoi release "
            "(borzoi_sad.py at commit 5c93582, fold 0, reverse-complement "
            "ensemble) against pinned GRCh38. Returns upstream's four published "
            "statistics -- SAD, logSAD, D2, logD2 -- over 6,385 strand-summed "
            "human RNA tracks, with the strongest tracks per variant named. This "
            "is the paper's method rather than an approximation of it; use "
            "run_borzoi_variant_effect (the borzoi-pytorch port, GPU) for a fast "
            "central-bin delta from two sequences. CPU-only here: about four "
            "minutes per variant, four variants maximum."
        ),
        # Structurally identical to the published catalogue entry in
        # src/tooluniverse/data/remote_tools/borzoi_calico_tools.json -- every
        # bound here is one `_check` already enforces, so the schema the server
        # advertises and the schema a caller reads are the same contract.
        "parameter": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "variants": {
                    "type": "array",
                    "minItems": 1,
                    # The default of MAX_VARIANTS, written as a literal: a
                    # published schema has to be the same for every caller, and
                    # BORZOI_CALICO_MAX_VARIANTS can move the enforced ceiling
                    # on one host. A host that raises it advertises 4 and
                    # accepts more; it never advertises more than it accepts.
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "chrom": {
                                "type": "string",
                                "description": "GRCh38 chromosome, with or without the 'chr' prefix.",
                            },
                            "pos": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "1-based position, as in a VCF.",
                            },
                            "ref": {
                                "type": "string",
                                "pattern": "^[ACGTacgt]+$",
                                "description": "Reference allele (ACGT; SNVs only).",
                            },
                            "alt": {
                                "type": "string",
                                "pattern": "^[ACGTacgt]+$",
                                "description": "Alternate allele (ACGT; SNVs only).",
                            },
                            "id": {
                                "type": "string",
                                "description": "Optional identifier, echoed into the output. Defaults to chrom_pos_ref_alt.",
                            },
                        },
                        "required": ["chrom", "pos", "ref", "alt"],
                    },
                    "description": (
                        "Single-nucleotide variants to score, at most 4. Each "
                        "costs about four minutes."
                    ),
                },
                "top_tracks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_TOP_TRACKS,
                    "description": (
                        "How many tracks to name per variant, ranked by |SAD|, "
                        "between 1 and 100 (default 20). The full 6,385-track "
                        "vectors stay in the provider's sad.h5, whose path the "
                        "reply carries."
                    ),
                    "default": 20,
                },
            },
            "required": ["variants"],
        },
        "server_name": "Borzoi (calico release) Variant Scoring MCP Server",
        "host": "127.0.0.1",
        "port": 8061,
        "transport": "http",
    },
)
class BorzoiCalicoSadTool:
    """Score variants through calico's own pipeline. Requests queue: one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        doc = _check(arguments)
        if "error" in doc:
            return doc
        return _score(doc)


if __name__ == "__main__":
    start_mcp_server(__file__)
