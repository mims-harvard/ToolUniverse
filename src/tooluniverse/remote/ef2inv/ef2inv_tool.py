"""ESMFold2 gradient-guided binder design (ef2inv) — MCP server.

Given a target protein and a binder length, this designs a binder SEQUENCE: it
optimises a soft sequence by gradient descent through two ESMFold2 distogram
models with an ESMC-6B pseudo-perplexity term, 150 steps, and then refolds the
result with four frozen hero critics which score it (ipTM and the loop's own
losses). It is the first provider on this standard whose model runs BACKWARD
passes, and the first whose answer is a sequence rather than a structure.

This server is the thin, CPU-only half of the provider; the model runs in its
own environment and is held resident between requests. What residency buys here
is the load: 28.0 GiB of fp32 weights -- ESMC-6B once, shared by every model,
plus six ESMFold2 models -- plus the cookbook's own torch.compile of the
inversion models' MSA encoder and pair blocks. The kit's own launcher pays all
of that per design, in a fresh arm process; a held worker pays it once.

Two limits below are the kit's rather than ours, and they shape this schema:

* THE STEP COUNT IS NOT A PARAMETER. `STEPS = 150` is a module constant of the
  cookbook file and the kit refuses a changed loop constant, so there is no
  "fewer steps, faster answer" to offer. One design is one 150-step loop.
* THE COUNT COSTS TIME, NOT MEMORY. A kit mode refuses batch_size > 1, so
  n_designs designs are n_designs sequential loops in the held worker. Peak VRAM
  is one design's and is driven by the token count -- see provider.toml's [gpu].

`max_tokens` below (300) keeps a request inside the measured-to-be-derived part
of that ladder. Past about 500 tokens the kit's memory planner deliberately
fills the card, which is a decision for a deployment rather than for a caller.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason.
"""

import gzip
import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
# The cookbook's own built-in targets (binder_design.py TARGET_SEQUENCES, l.159)
# and their lengths, so a token count can be checked before a request is sent.
BUILT_IN_TARGETS = {
    "cd45": 185,
    "ctla4": 118,
    "egfr": 191,
    "pd-l1": 115,
    "pdgfr": 187,
}
MAX_TOKENS = 300
MAX_BINDER_LEN = 200
MIN_BINDER_LEN = 8
MAX_DESIGNS = 4
MAX_TARGET_LEN = 280
MAX_STRUCTURE_BYTES = 8 * 1024 * 1024
_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _read_structure(path: str) -> Dict[str, Any]:
    """The structure text of one file, or a named reason not to return it.

    This kit writes plain `.pdb` / `.cif` (outputs.write_complex), but the gzip
    case is handled anyway: chai1 returned megabytes once and the MCP transport
    truncated the reply at exactly 100,000 characters, producing invalid JSON
    rather than a refusal, so a size check and a compression check both belong on
    the way out rather than in the caller's hands.
    """
    try:
        if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
            return {"error": "exceeds the public output limit"}
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                return {"text": fh.read()}
        with open(path, "r", encoding="utf-8") as fh:
            return {"text": fh.read()}
    except (OSError, UnicodeError, EOFError) as exc:
        return {"error": type(exc).__name__}


def _design(doc: Dict[str, Any], return_structures: bool) -> Dict[str, Any]:
    """One request on the resident worker, or a named reason why not."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory(prefix="ef2inv-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(doc),
                "out_dir": work,
                "name": "design",
                "seed": int(doc.get("seed", 0)),
                "options": {},
            }
        )
        result = reply["result"]
        designs = result.get("designs") or []
        out: Dict[str, Any] = {
            "model": "ESMFold2 binder design (ESM cookbook binder_design)",
            "pass": result.get("pass"),
            "target_name": result.get("target_name"),
            "target_len": result.get("target_len"),
            "binder_len": result.get("binder_len"),
            "n_tokens": result.get("n_tokens"),
            "n_designs": result.get("n_designs"),
            "seed": result.get("seed"),
            "steps": None,
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "kit_mode": result.get("mode"),
            "weights_held_by": result.get("weights_held_by"),
            # The kit's own activation report on this worker's first design: the
            # levers that engaged, the ones that stood aside by name, and any
            # refusal. `evidence_ok` false means a lever of the composition did
            # not confirm -- the designs still ran and are returned, which is
            # this provider's one documented divergence from the kit's exit 3.
            "evidence_ok": result.get("evidence_ok"),
            "kit_evidence": result.get("kit_evidence"),
        }
        if result.get("warning"):
            out["warning"] = result["warning"]

        summary = []
        for d in designs:
            entry = {
                "seed": d.get("seed"),
                # The per-design answer: the designed binder sequence, and the
                # hero critics' scores, which are what a caller ranks N designs
                # on. They come back whether or not the structures do.
                "binder_sequence": d.get("binder_sequence"),
                "n_steps": d.get("n_steps"),
                "critics": d.get("critics"),
                "peak_reserved_gib": d.get("peak_reserved_gib"),
                "timing": d.get("timing"),
            }
            if d.get("first_steps_s"):  # the warm pass
                entry["first_steps_s"] = d["first_steps_s"]
                entry["first_folds_s"] = d.get("first_folds_s")
            if out["steps"] is None:
                out["steps"] = d.get("n_steps")
            if return_structures:
                for name in ("design.cif", "design.pdb"):
                    path = os.path.join(d.get("out_dir") or "", name)
                    if os.path.isfile(path):
                        got = _read_structure(path)
                        entry[name.split(".")[-1]] = got.get("text")
                        if got.get("error"):
                            entry["structure_error"] = got["error"]
                        break
            summary.append(entry)
        out["designs"] = summary
        if not designs:
            return {
                "error": "ef2inv produced no design for this specification.",
                "timing": out["timing"],
            }
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true for the mmCIF text of each design "
                "(the first hero critic's refold); the binder sequence and the "
                "per-design critic scores come back either way"
            )
        return out


@register_mcp_tool(
    tool_type_name="ef2inv_design",
    config={
        "description": (
            "Design a binder SEQUENCE against a target protein with the ESM "
            "cookbook's gradient-guided ESMFold2 recipe. Give a built-in target "
            "name (cd45, ctla4, egfr, pd-l1, pdgfr) or any label plus its "
            "'target_sequence', and a 'binder_len'. Returns each design's binder "
            "sequence and the four hero critics' scores; the refolded structure "
            "is opt-in. One design is a fixed 150-step optimisation -- the step "
            "count is the recipe's own constant and cannot be lowered."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": (
                        "A built-in target (cd45, ctla4, egfr, pd-l1, pdgfr: the "
                        "recipe's own sequences, give no target_sequence), or any "
                        "label for a target_sequence you supply."
                    ),
                },
                "target_sequence": {
                    "type": "string",
                    "description": (
                        "The target's amino-acid sequence, required when "
                        "target_name is not one of the built-ins and forbidden "
                        f"when it is. Up to {MAX_TARGET_LEN} residues."
                    ),
                },
                "binder_len": {
                    "type": "integer",
                    "description": (
                        f"Length of the binder to design, {MIN_BINDER_LEN}-"
                        f"{MAX_BINDER_LEN}. target_len + binder_len must not "
                        f"exceed {MAX_TOKENS} tokens."
                    ),
                    "minimum": MIN_BINDER_LEN,
                    "maximum": MAX_BINDER_LEN,
                },
                "n_designs": {
                    "type": "integer",
                    "description": (
                        f"How many designs to run (default 1, max {MAX_DESIGNS}). "
                        "Each is an independent 150-step optimisation at seed+k, "
                        "run one after another: the count costs time, not memory."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_DESIGNS,
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed of the first design.",
                    "default": 0,
                    "minimum": 0,
                },
                "target_hotspot_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Target residue ids to treat as the epitope, e.g. "
                        '["56", "57"]. Omit to let the recipe choose.'
                    ),
                },
                "epitope_contact_distance": {
                    "type": "number",
                    "description": "The recipe's epitope contact distance in angstroms.",
                    "default": 12.0,
                },
                "warm_only": {
                    "type": "boolean",
                    "description": (
                        "Run the recipe's one-time costs and a single "
                        "design-step-shaped gradient pass instead of a design "
                        "(seconds rather than minutes). Use it to check that the "
                        "provider is live and what it costs on this card."
                    ),
                    "default": False,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return each design's refolded mmCIF text (default "
                        "false: hundreds of kilobytes per design)."
                    ),
                    "default": False,
                },
            },
            "required": ["target_name"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "pass": {"type": "string"},
                "target_name": {"type": "string"},
                "target_len": {"type": "integer"},
                "binder_len": {"type": "integer"},
                "n_tokens": {"type": "integer"},
                "n_designs": {"type": "integer"},
                "steps": {"type": "integer"},
                "designs": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seed": {"type": "integer"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "kit_mode": {"type": "string"},
                "weights_held_by": {"type": "string"},
                "evidence_ok": {"type": "boolean"},
                "kit_evidence": {"type": "object"},
                "warning": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "ef2inv Binder Design MCP Server",
        "host": "127.0.0.1",
        "port": 8042,
        "transport": "http",
    },
)
class EF2InvDesignTool:
    """Design binder sequences. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        target_name = arguments.get("target_name")
        if not isinstance(target_name, str) or not target_name.strip():
            return {"error": "'target_name' must be a non-empty string."}
        target_name = target_name.strip()
        target_sequence = arguments.get("target_sequence")
        built_in = target_name in BUILT_IN_TARGETS
        if built_in and target_sequence is not None:
            return {
                "error": (f"{target_name!r} is a preset target; omit target_sequence.")
            }
        if not built_in:
            if not isinstance(target_sequence, str) or not target_sequence.strip():
                return {
                    "error": (
                        f"{target_name!r} is not a preset target; provide "
                        f"target_sequence (presets: {sorted(BUILT_IN_TARGETS)})."
                    )
                }
            target_sequence = target_sequence.strip().upper()
            bad = sorted(set(target_sequence) - _AA)
            if bad:
                return {"error": f"'target_sequence' has non-standard residues: {bad}"}
            if len(target_sequence) > MAX_TARGET_LEN:
                return {
                    "error": (
                        f"'target_sequence' is {len(target_sequence)} residues; "
                        f"this provider's limit is {MAX_TARGET_LEN}."
                    )
                }
        target_len = BUILT_IN_TARGETS[target_name] if built_in else len(target_sequence)

        binder_len = arguments.get("binder_len")
        if not isinstance(binder_len, int) or isinstance(binder_len, bool):
            return {"error": "'binder_len' must be an integer."}
        if not MIN_BINDER_LEN <= binder_len <= MAX_BINDER_LEN:
            return {
                "error": (
                    f"'binder_len' must be between {MIN_BINDER_LEN} and "
                    f"{MAX_BINDER_LEN}."
                )
            }
        if target_len + binder_len > MAX_TOKENS:
            return {
                "error": (
                    f"target_len {target_len} + binder_len {binder_len} = "
                    f"{target_len + binder_len} tokens exceeds this provider's "
                    f"limit of {MAX_TOKENS}. Peak VRAM is quadratic in the token "
                    f"count and past about 500 tokens this kit's memory planner "
                    f"fills the whole card; re-measure before raising it."
                )
            }

        n_designs = arguments.get("n_designs", 1)
        if not isinstance(n_designs, int) or isinstance(n_designs, bool):
            return {"error": "'n_designs' must be an integer."}
        if not 1 <= n_designs <= MAX_DESIGNS:
            return {"error": f"'n_designs' must be between 1 and {MAX_DESIGNS}."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        hotspots = arguments.get("target_hotspot_ids")
        if hotspots is not None:
            if not isinstance(hotspots, list) or not all(
                isinstance(h, (str, int)) and not isinstance(h, bool) for h in hotspots
            ):
                return {"error": "'target_hotspot_ids' must be a list of residue ids."}
            hotspots = [str(h) for h in hotspots]

        distance = arguments.get("epitope_contact_distance", 12.0)
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            return {"error": "'epitope_contact_distance' must be a number."}
        if not 0 < float(distance) <= 50:
            return {
                "error": "'epitope_contact_distance' must be between 0 and 50 angstroms."
            }

        warm_only = arguments.get("warm_only", False)
        if not isinstance(warm_only, bool):
            return {"error": "'warm_only' must be a boolean."}
        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        doc: Dict[str, Any] = {
            "pass": "warm" if warm_only else "design",
            "target_name": target_name,
            "binder_len": binder_len,
            "n_designs": n_designs,
            "seed": seed,
            "epitope_contact_distance": float(distance),
        }
        if not built_in:
            doc["target_sequence"] = target_sequence
        if hotspots:
            doc["target_hotspot_ids"] = hotspots

        try:
            return _design(doc, return_structures and not warm_only)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"ef2inv's resident worker is not available ({reason}: {exc}). "
                    f"Run `tu remote setup ef2inv` and read its named refusal; "
                    f"this provider has no subprocess fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
