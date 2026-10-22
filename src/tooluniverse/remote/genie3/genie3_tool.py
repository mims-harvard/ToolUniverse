"""Genie 3 de novo protein backbone design — MCP server.

Genie 3 designs protein backbones by reverse diffusion: given a request it
samples N backbones, either unconditionally at a chosen length or as binders
against one of the targets its checkout ships. This server is the thin,
CPU-only half of the provider; the model runs in its own environment and is
held resident between requests.

**What residency buys here, and what it does not.** The kit's README puts
process start-up and model set-up at "≈10-15 s per process in every mode",
against sampling that scales with designs x denoiser steps. A held worker pays
the imports and the CUDA context once for the life of the worker, and -- where
a request repeats -- the 331 MiB checkpoint read and the network construction
once per distinct request rather than once per call.

Measured, four identical requests in one held worker: **9.8 s, 0.8 s, 0.8 s,
0.8 s -- 12x**, which ties RFdiffusion3 for the largest gain on this standard.
That was not the prediction. The estimate written here before measuring was "the
Boltz-2 and BoltzGen end of the range", reasoned from the absence of a
torch.compile trace to amortise on this card, and it was wrong by 6x: what
dominates is that a 20-step 50-residue sampling pass is SHORTER than the
per-process set-up it was being compared against, so removing the set-up removes
almost all of the wall clock. Residency's payoff tracks the ratio of fixed cost
to work, not the kind of fixed cost.

And -- the part that makes the 12x worth having -- the PDB files are
byte-identical across all four requests. See provider.toml [provider]
verified_on.

**This card runs the kit's `exact` line, not its default `fast` one.** `exact`
is tier 1 -- PDB files byte-identical to eager deterministic stock at the same
batch size and seed -- and keeps nine of the kit's thirteen levers. `fast`
would abort the process on this Triton band. The manifest carries the whole
measurement; the reply carries `kit_mode` and `tier` so a caller never has to
guess which line produced a structure.

The PDB text is opt-in: a backbone is small, but eight of them with a 670-token
target is not, and a transport truncates an oversized reply into invalid JSON
rather than refusing it. The per-design record comes back either way.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason.
"""

import os
import re
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# Caps, and what each one is a cap ON.
#
# MAX_LENGTH and MAX_BATCH together ARE the measured VRAM envelope: the top rung
# of [gpu]'s ladder is 670 padded tokens at batch 2, which reserved 4.84 GiB,
# and that is the figure vram_budget_gb declares. Neither cap is a round number
# chosen for comfort -- each is the largest value anyone has run. A host that
# wants more re-measures the ladder and raises both together, because the two
# interact: peak tracks token count roughly quadratically and batch roughly
# linearly.
MAX_LENGTH = 670
MIN_LENGTH = 10
# n_sample is NOT a memory cap, and this is a real property of this provider
# rather than an optimistic reading. Designs beyond `batch_size` arrive as
# further sequential batches of the same feature shape -- the kit's L9 replays
# the captured graph for each one and the allocator reuses the same pool -- so
# asking for more designs costs wall clock and not VRAM. 8 is a politeness
# limit on how long one request may hold the worker.
MAX_DESIGNS = 8
# batch_size multiplies the resident activation footprint directly, and the kit
# refuses a batch that does not fit BY NAME before it runs (its guard projects
# need = resident + 2.0 x B x probe). 2 is the measured top of the ladder; a
# larger batch is the throughput configuration the kit's README recommends and
# this provider has not measured it.
MAX_BATCH = 2
# Upstream's own default is 100 (ddim.py:15). Fewer is faster and lower
# quality; more is neither forbidden nor measured.
DEFAULT_STEPS = 100
MAX_STEPS = 200
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# The binder-design problems the pinned checkout ships
# (data/design/binder_design/binderbench/problems/*.json). The archive excludes
# the FASTA and MSA trees, which the structure path does not read.
BINDER_DATASET = "data/design/binder_design/binderbench"
BINDER_TARGETS = (
    "01_bhrf1",
    "02_sc2rbd",
    "03_il7ra",
    "04_pdl1",
    "05_trka",
    "06_insulinr",
    "07_h1",
    "08_vegfa",
    "09_il17a",
    "10_tnfa",
)
# Upstream's own direction_scale per request kind: 0.8 unconditional,
# 0.0 binder (examples/*/experiment.yaml, recorded in stock/PINS.json
# cli_defaults). The sampler has no default for it, so one must be stated.
DIRECTION_SCALE = {"unconditional": 0.8, "target": 0.0}
_LENGTH_RE = re.compile(r"^\d+(-\d+)?$")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _lengths(value: Any) -> tuple:
    """(min, max) from '60' or '60-100', raising ValueError by name."""
    text = str(value).strip()
    if not _LENGTH_RE.match(text):
        raise ValueError("'length' must be a number like 100 or a range like 100-200.")
    bounds = [int(p) for p in text.split("-")]
    lo, hi = bounds[0], bounds[-1]
    if lo < MIN_LENGTH:
        raise ValueError(f"'length' below {MIN_LENGTH} is not a protein.")
    if hi > MAX_LENGTH:
        raise ValueError(
            f"'length' above {MAX_LENGTH} is outside this provider's measured "
            f"VRAM envelope ({MAX_LENGTH} tokens at batch {MAX_BATCH} reserved "
            f"4.84 GiB, the declared budget). Genie 3 was also trained on "
            f"chains of at most 512 residues (the checkpoint's own data "
            f"directory is afdbreps_l-512), so longer is outside the model's "
            f"distribution as well as the budget. Re-measure the ladder in "
            f"provider.toml before raising it."
        )
    if lo > hi:
        raise ValueError("'length' range must be increasing.")
    return lo, hi


def _request_yaml(
    kind: str, n_designs: int, n_steps: int, extra: Dict[str, Any]
) -> str:
    """Upstream's experiment YAML for this request.

    Composed here rather than in the worker because it is upstream's own file
    format and the worker's job is to run one, not to invent one -- and because
    the kit's `design.compose_request` is what fills in the weight paths, the
    seed and the output directory on the other side. Only the keys a caller
    actually chose appear.
    """
    import yaml

    doc: Dict[str, Any] = {
        "experiment": {"name": f"genie3_{kind}"},
        # Required by upstream's loader (loader.py:254-259) and overwritten by
        # the kit's compose_request with this pass's real output directory.
        "paths": {"rootdir": "out/genie3"},
        "generation": {
            "dataset": {"source": kind, "n_sample": int(n_designs)},
            "sampler": {
                "sampler": {
                    "direction_scale": DIRECTION_SCALE[kind],
                    "n_sample_step": int(n_steps),
                }
            },
        },
    }
    doc["generation"]["dataset"].update(extra.get("dataset") or {})
    if extra.get("paths"):
        doc["paths"].update(extra["paths"])
    return yaml.safe_dump(doc, sort_keys=False)


def _design(
    request_text: str, batch_size: int, seed: int, return_structures: bool
) -> Dict[str, Any]:
    """One design request on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="genie3-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": request_text,
                "out_dir": work,
                "name": "design",
                "seed": seed,
                "options": {"batch_size": int(batch_size)},
            }
        )
        result = reply["result"]
        designs: List[Dict[str, Any]] = result.get("designs") or []
        out: Dict[str, Any] = {
            "model": "Genie 3",
            "n_designs": result.get("n_designs", len(designs)),
            "designs_expected": result.get("designs_expected"),
            "seed": result.get("seed"),
            "batch_size": result.get("batch_size"),
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("mode"),
            # 1 = the kit claims byte-identical outputs against stock; 2 = its
            # documented tolerance tier. A caller comparing runs needs this.
            "tier": result.get("tier"),
            "levers": result.get("levers"),
            # True when this request changed the engine's key -- a different
            # request, seed or shard -- and the worker paid the checkpoint read
            # and the network construction again.
            "engine_rebuilt": result.get("engine_rebuilt"),
            # False means the designs came off a held engine whose generator
            # states were restored to a fresh process's; True means this request
            # built the engine, which is the stock order by construction.
            "rng_restored": result.get("rng_restored"),
            "graph_cache": result.get("graph_cache"),
            "kernels_line": result.get("kernels_line"),
        }
        if result.get("warning"):
            out["warning"] = result["warning"]

        summary = []
        for d in designs:
            summary.append(
                {
                    k: d[k]
                    for k in (
                        "name",
                        "problem",
                        "n_token_real",
                        "n_token_pad",
                        "batch_index",
                        "bytes",
                    )
                    if k in d
                }
            )
        out["designs"] = summary

        if not designs:
            return {
                "error": "Genie 3 produced no backbone for this request.",
                "timing": out["timing"],
                "kit_mode": out["kit_mode"],
                "warning": out.get("warning"),
            }

        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the PDB text; the "
                "per-design record above comes back either way"
            )
            return out

        # Upstream writes plain PDB through its own writer (postprocess.py ->
        # save_np_features_to_pdb) and compresses nothing, so there is nothing
        # to decompress on the way out.
        for entry, d in zip(summary, designs):
            path = d.get("structure")
            if not path:
                continue
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    entry["error"] = "exceeds the public output limit"
                    continue
                with open(path, encoding="utf-8") as f:
                    entry["pdb"] = f.read()
            except (OSError, UnicodeError) as exc:
                entry["error"] = type(exc).__name__
        return out


@register_mcp_tool(
    tool_type_name="genie3_design",
    config={
        "description": (
            "Design protein backbones with Genie 3. Either give a 'length' to "
            "sample unconditional backbones of that size, or a 'target' from "
            "the shipped binder-design benchmark to design binders against it. "
            "Returns a per-design record; the PDB text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "length": {
                    "type": "string",
                    "description": (
                        "Backbone length for unconditional design: '100', or a "
                        f"range '100-200' sampled in steps. {MIN_LENGTH}-{MAX_LENGTH}."
                    ),
                },
                "length_step": {
                    "type": "integer",
                    "description": (
                        "Step between lengths when 'length' is a range "
                        "(default: the whole range in one step, i.e. one length). "
                        "n_designs backbones are sampled at EACH length."
                    ),
                    "minimum": 1,
                },
                "target": {
                    "type": "string",
                    "description": (
                        "Binder-design target from the pinned checkout's "
                        "benchmark: " + ", ".join(BINDER_TARGETS) + "."
                    ),
                    "enum": list(BINDER_TARGETS),
                },
                "n_designs": {
                    "type": "integer",
                    "description": f"Backbones per length or per target (default 1, max {MAX_DESIGNS}).",
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_DESIGNS,
                },
                "n_steps": {
                    "type": "integer",
                    "description": (
                        f"DDIM sampling steps (default {DEFAULT_STEPS}, upstream's own; "
                        f"max {MAX_STEPS}). Fewer is faster and lower quality."
                    ),
                    "default": DEFAULT_STEPS,
                    "minimum": 1,
                    "maximum": MAX_STEPS,
                },
                "batch_size": {
                    "type": "integer",
                    "description": (
                        f"Designs per denoiser call (default 1, max {MAX_BATCH}). "
                        "Higher is faster per design and costs proportionally "
                        "more VRAM; the kit refuses a batch that does not fit "
                        "by name, before it runs."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_BATCH,
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed; the same seed reproduces the designs.",
                    "default": 0,
                    "minimum": 0,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": "Return the PDB text of every backbone (default false).",
                    "default": False,
                },
            },
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_designs": {"type": "integer"},
                "designs_expected": {"type": "integer"},
                "designs": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seed": {"type": "integer"},
                "batch_size": {"type": "integer"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "tier": {"type": "integer"},
                "levers": {"type": "array", "items": {"type": "string"}},
                "engine_rebuilt": {"type": "boolean"},
                "rng_restored": {"type": "boolean"},
                "graph_cache": {"type": "object"},
                "kernels_line": {"type": "string"},
                "warning": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "Genie 3 MCP Server",
        "host": "127.0.0.1",
        "port": 8048,
        "transport": "http",
    },
)
class Genie3DesignTool:
    """Design backbones. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        length = arguments.get("length")
        target = arguments.get("target")
        if (length is None) == (target is None):
            return {
                "error": (
                    "give exactly one of 'length' (unconditional design) or "
                    "'target' (binder design)."
                )
            }

        for name, lo, hi in (
            ("n_designs", 1, MAX_DESIGNS),
            ("n_steps", 1, MAX_STEPS),
            ("batch_size", 1, MAX_BATCH),
        ):
            value = arguments.get(
                name, {"n_designs": 1, "n_steps": DEFAULT_STEPS, "batch_size": 1}[name]
            )
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{name}' must be an integer."}
            if not lo <= value <= hi:
                return {"error": f"'{name}' must be between {lo} and {hi}."}
        n_designs = int(arguments.get("n_designs", 1))
        n_steps = int(arguments.get("n_steps", DEFAULT_STEPS))
        batch_size = int(arguments.get("batch_size", 1))

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}
        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        if length is not None:
            try:
                lo, hi = _lengths(length)
            except ValueError as exc:
                return {"error": str(exc)}
            step = arguments.get("length_step", hi - lo or 1)
            if not isinstance(step, int) or isinstance(step, bool) or step < 1:
                return {"error": "'length_step' must be an integer of at least 1."}
            kind, extra = (
                "unconditional",
                {"dataset": {"min_length": lo, "max_length": hi, "length_step": step}},
            )
        else:
            if target not in BINDER_TARGETS:
                return {
                    "error": (
                        f"unknown target {target!r}; the pinned checkout ships "
                        + ", ".join(BINDER_TARGETS)
                    )
                }
            kind, extra = (
                "target",
                {
                    "dataset": {"selections": target},
                    # Relative to the checkout, which is the cwd of every kit line.
                    "paths": {"dataset": BINDER_DATASET},
                },
            )

        try:
            request_text = _request_yaml(kind, n_designs, n_steps, extra)
            return _design(request_text, batch_size, seed, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"Genie 3's resident worker is not available ({reason}: "
                    f"{exc}). Run `tu remote setup genie3` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
