"""Proteina-Complexa de novo binder design -- MCP server.

Proteina-Complexa 1.1.0 is NVIDIA's flow-matching *binder generator*, not a
structure predictor. A request gives it a target protein's structure, the
residue range of that structure to crop to and a list of hotspot residues on
the target's surface; it invents proteins of a chosen length that bind there.
One design is a backbone AND an amino-acid sequence that did not exist before,
written as one PDB: chain A is the target crop, chain B is the new binder.

This server is the thin, CPU-only half of the provider. The model (a 160 M
parameter denoiser plus a frozen autoencoder, 7.0 GB of fp32 checkpoint, torch
2.7.0+cu128) runs in its own environment, a stack ToolUniverse's cannot import,
and is held resident between requests.

Four things an operator needs and will not guess.

**The target arrives as PDB text, never as a path.** A path would make the
worker read an arbitrary file off the host on a remote caller's say-so, which
is not a thing an MCP tool should offer.

**Residue numbers are the target PDB's own.** `target_input` ("A1-115") crops
chain A to the residues numbered 1 through 115 in the file, and every hotspot
("A37") must be one of them. Both are checked here, in milliseconds, against
the text that was sent: a typo refused here costs nothing, and inside the
model it would cost the caller a model-load's worth of time and read as a
model failure.

**This runs the generation stage ALONE.** Upstream's shipped configuration also
runs a best-of-n search that scores every design with an AlphaFold2 reward
model whose parameters this deployment does not carry. What comes back is the
model's raw samples, unranked and unscored: nothing here says one design is
better than another, and a caller who wants a ranking has to bring a predictor.

**Costs scale with the pair tensor.** Peak GPU memory grows with the square of
(target crop + binder) residues and linearly in the designs sampled per forward
pass, so the ceilings below bound that product rather than each factor.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason.
"""

import json
import os
import re
from typing import Any, Dict, List, Tuple

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# THE CEILINGS. They are the worker's (resident/complexa_resident_worker.py) and
# are repeated here only so a refusal costs milliseconds instead of a queue slot;
# tests/ and the acceptance run read both files and fail if they differ. They
# are bounded as a PRODUCT, because progen2's two individually sane limits
# multiplied to a 116.93 GiB request. provider.toml carries the ladder the
# product was measured against and the row [gpu] vram_budget_gb is declared at.
MAX_BINDER_LENGTH = 200
MIN_BINDER_LENGTH = 20
MAX_TARGET_RESIDUES = 300
MAX_DESIGNS = 16
MAX_PAIR_CELLS_X_BATCH = 4_000_000
MIN_STEPS = 10
MAX_STEPS = 400
MAX_PDB_BYTES = 4 * 1024 * 1024
MAX_REPLY_PDB_BYTES = 16 * 1024 * 1024

_TARGET_INPUT = re.compile(r"([A-Za-z0-9])(-?\d+)-(-?\d+)")
_HOTSPOT = re.compile(r"([A-Za-z0-9])(-?\d+)")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _target_residues(pdb: str) -> Dict[str, set]:
    """``{chain: {residue number, ...}}`` of the protein residues in ``pdb``.

    Read off the CA atoms of the first model only, which is what the model reads:
    a file with ten NMR models must not make a residue "present" because the
    ninth has it. Hetero atoms are not residues of the target.
    """
    seen: Dict[str, set] = {}
    for line in pdb.splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM") or len(line) < 27:
            continue
        if line[12:16].strip() != "CA":
            continue
        try:
            number = int(line[22:26])
        except ValueError:
            continue
        seen.setdefault(line[21], set()).add(number)
    return seen


def _validate(arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """``(the worker's input document, "")`` or ``({}, the refusal)``."""
    pdb = arguments.get("target_pdb")
    if not isinstance(pdb, str) or not pdb.strip():
        return {}, "'target_pdb' must be the target structure as PDB text."
    if len(pdb.encode("utf-8", "replace")) > MAX_PDB_BYTES:
        return {}, f"'target_pdb' is larger than {MAX_PDB_BYTES} bytes."

    crop = arguments.get("target_input")
    match = _TARGET_INPUT.fullmatch(crop.strip()) if isinstance(crop, str) else None
    if not match:
        return {}, (
            "'target_input' must be a chain and a residue range such as 'A1-115': "
            "the residues of that chain the binder is designed against."
        )
    chain, first, last = match.group(1), int(match.group(2)), int(match.group(3))
    if last < first:
        return {}, f"'target_input' {crop!r} runs backwards."
    crop_n = last - first + 1
    if crop_n > MAX_TARGET_RESIDUES:
        return {}, (
            f"'target_input' crops {crop_n} residues; this server accepts at most "
            f"{MAX_TARGET_RESIDUES}, the envelope its GPU budget was measured at."
        )

    residues = _target_residues(pdb)
    if chain not in residues:
        return {}, (
            f"chain {chain!r} has no protein residues in 'target_pdb' "
            f"(chains present: {sorted(residues) or 'none'})."
        )
    present = residues[chain]
    in_crop = [n for n in present if first <= n <= last]
    if not in_crop:
        return {}, (
            f"chain {chain} has no residue numbered {first}..{last} in 'target_pdb' "
            f"(it runs {min(present)}..{max(present)})."
        )

    hotspots = arguments.get("hotspot_residues")
    if not isinstance(hotspots, list) or not hotspots:
        return {}, (
            "'hotspot_residues' must be a non-empty array such as ['A37', 'A39']: "
            "the residues on the target's surface the binder is designed against."
        )
    clean: List[str] = []
    for item in hotspots:
        hm = _HOTSPOT.fullmatch(item.strip()) if isinstance(item, str) else None
        if not hm:
            return {}, f"hotspot {item!r} must be <chain><residue number>, e.g. 'A37'."
        h_chain, h_num = hm.group(1), int(hm.group(2))
        if h_chain != chain:
            return {}, (
                f"hotspot {item!r} is on chain {h_chain}; the crop {crop!r} is chain "
                f"{chain}, and a hotspot has to be inside it."
            )
        if not first <= h_num <= last:
            return {}, f"hotspot {item!r} is outside the crop {crop!r}."
        if h_num not in present:
            return {}, f"hotspot {item!r} is not a residue of 'target_pdb'."
        if item.strip() not in clean:
            clean.append(item.strip())

    def _int(key: str, default: int, low: int, high: int) -> Tuple[int, str]:
        value = arguments.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool):
            return 0, f"'{key}' must be an integer."
        if not low <= value <= high:
            return 0, f"'{key}' must be between {low} and {high}."
        return value, ""

    binder, err = _int("binder_length", 80, MIN_BINDER_LENGTH, MAX_BINDER_LENGTH)
    if err:
        return {}, err
    designs, err = _int("num_designs", 1, 1, MAX_DESIGNS)
    if err:
        return {}, err
    batch, err = _int("batch_size", designs, 1, MAX_DESIGNS)
    if err:
        return {}, err
    batch = min(batch, designs)
    steps, err = _int("num_steps", MAX_STEPS, MIN_STEPS, MAX_STEPS)
    if err:
        return {}, err
    seed, err = _int("seed", 5, 0, 2**31 - 1)
    if err:
        return {}, err

    # THE BOUND IS ON THE PRODUCT, not on either factor.
    tokens = crop_n + binder
    if tokens * tokens * batch > MAX_PAIR_CELLS_X_BATCH:
        return {}, (
            f"(target crop {crop_n} + binder {binder})^2 x batch {batch} = "
            f"{tokens * tokens * batch} exceeds this server's "
            f"{MAX_PAIR_CELLS_X_BATCH}, the envelope its GPU budget was measured "
            f"at. Lower 'batch_size' to split the same number of designs into "
            f"more forward passes."
        )
    return {
        "target_pdb": pdb,
        "target_input": f"{chain}{first}-{last}",
        "hotspot_residues": clean,
        "binder_length": binder,
        "num_designs": designs,
        "batch_size": batch,
        "num_steps": steps,
        "seed": seed,
    }, ""


def _design(spec: Dict[str, Any], name: str, return_pdb: bool) -> Dict[str, Any]:
    """One request on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="complexa-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(spec),
                "out_dir": work,
                "name": name,
                "seed": spec["seed"],
            }
        )
        result = reply["result"]
        designs = []
        budget = MAX_REPLY_PDB_BYTES
        for d in result.get("designs") or []:
            item = {
                "name": d.get("name"),
                "binder_sequence": d.get("binder_sequence"),
                "binder_length": d.get("binder_length"),
            }
            if return_pdb:
                try:
                    size = os.path.getsize(d["path"])
                    if size > budget:
                        item["pdb_error"] = "reply size limit reached"
                    else:
                        with open(d["path"], "r", encoding="utf-8") as handle:
                            item["pdb"] = handle.read()
                        budget -= size
                except (OSError, UnicodeError, KeyError) as exc:
                    item["pdb_error"] = type(exc).__name__
            designs.append(item)
        out: Dict[str, Any] = {
            "model": "Proteina-Complexa 1.1.0 (complexa.ckpt + complexa_ae.ckpt)",
            "n_designs": len(designs),
            "designs": designs,
            "seed": result.get("seed"),
            "target_residues": result.get("target_residues"),
            "binder_length": result.get("binder_length"),
            "num_steps": result.get("num_steps"),
            "batch_size": result.get("batch_size"),
            "stage": "generation only: raw samples, no reward model, no ranking",
            "timing": result.get("timing"),
            "request_peak_reserved_gib": result.get("request_peak_reserved_gib"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }
        if not return_pdb:
            out["pdb_note"] = (
                "pass return_pdb=true to receive each design's PDB text (chain A "
                "the target crop, chain B the binder); the files themselves live "
                "in a temporary directory that is removed when this call returns"
            )
        return out


@register_mcp_tool(
    tool_type_name="complexa_design_binder",
    config={
        "description": (
            "Design de novo protein binders against a target with Proteina-Complexa "
            "1.1.0 (NVIDIA's flow-matching binder generator). Give the target "
            "structure as PDB text, the chain and residue range to crop it to "
            "(e.g. 'A1-115'), and hotspot residues on its surface (e.g. 'A37'); "
            "it samples binders of the requested length and returns, per design, "
            "the decoded binder amino-acid sequence, with the full complex "
            "(chain A target crop, chain B new binder) as PDB text on request. "
            "Generation stage only: samples are raw, not scored or ranked."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "target_pdb": {
                    "type": "string",
                    "description": (
                        "The target protein structure as PDB text (ATOM "
                        "records). Residue numbers in it are the ones "
                        "target_input and hotspot_residues refer to."
                    ),
                    "minLength": 1,
                },
                "target_input": {
                    "type": "string",
                    "description": (
                        "Chain and residue range of the target to design "
                        f"against, e.g. 'A1-115' (at most {MAX_TARGET_RESIDUES} "
                        "residues)."
                    ),
                    "pattern": r"^[A-Za-z0-9]-?\d+--?\d+$",
                },
                "hotspot_residues": {
                    "type": "array",
                    "description": (
                        "Target residues the binder should contact, each "
                        "<chain><number> and inside target_input, e.g. "
                        "['A37', 'A39', 'A49']."
                    ),
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "binder_length": {
                    "type": "integer",
                    "description": (
                        f"Residues in each designed binder, "
                        f"{MIN_BINDER_LENGTH}..{MAX_BINDER_LENGTH} (default 80)."
                    ),
                    "default": 80,
                    "minimum": MIN_BINDER_LENGTH,
                    "maximum": MAX_BINDER_LENGTH,
                },
                "num_designs": {
                    "type": "integer",
                    "description": (
                        f"Designs to sample, 1..{MAX_DESIGNS} (default 1)."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_DESIGNS,
                },
                "batch_size": {
                    "type": "integer",
                    "description": (
                        "Designs per forward pass (default: all of them). "
                        "Lowering it trades time for peak GPU memory; "
                        "(target crop + binder)^2 x batch_size is bounded at "
                        f"{MAX_PAIR_CELLS_X_BATCH}."
                    ),
                    "minimum": 1,
                    "maximum": MAX_DESIGNS,
                },
                "num_steps": {
                    "type": "integer",
                    "description": (
                        "Flow-matching integration steps per design "
                        f"({MIN_STEPS}..{MAX_STEPS}, default {MAX_STEPS}, "
                        "upstream's own). Fewer is faster and rougher."
                    ),
                    "default": MAX_STEPS,
                    "minimum": MIN_STEPS,
                    "maximum": MAX_STEPS,
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed (upstream's default is 5). The same seed "
                        "and inputs reproduce the designs."
                    ),
                    "default": 5,
                    "minimum": 0,
                },
                "name": {
                    "type": "string",
                    "description": "A label for this target; defaults to 'design'.",
                },
                "return_pdb": {
                    "type": "boolean",
                    "description": (
                        "Return each design's PDB text (default false: ~100 KB "
                        "per design). Sequences come back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["target_pdb", "target_input", "hotspot_residues"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_designs": {"type": "integer"},
                "designs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "binder_sequence": {"type": "string"},
                            "binder_length": {"type": "integer"},
                            "pdb": {"type": "string"},
                            "pdb_error": {"type": "string"},
                        },
                    },
                },
                "seed": {"type": "integer"},
                "target_residues": {"type": "integer"},
                "binder_length": {"type": "integer"},
                "num_steps": {"type": "integer"},
                "batch_size": {"type": "integer"},
                "stage": {"type": "string"},
                "timing": {"type": "object"},
                "request_peak_reserved_gib": {"type": "number"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "pdb_note": {"type": "string"},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "Proteina-Complexa MCP Server",
        "host": "127.0.0.1",
        "port": 8056,
        "transport": "http",
    },
)
class ComplexaDesignBinderTool:
    """Design binders against one target. Requests queue: one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        spec, problem = _validate(arguments)
        if problem:
            return {"error": problem}

        name = arguments.get("name", "design")
        if not isinstance(name, str) or not name.strip():
            return {"error": "'name' must be a non-empty string."}
        name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name.strip())

        return_pdb = arguments.get("return_pdb", False)
        if not isinstance(return_pdb, bool):
            return {"error": "'return_pdb' must be a boolean."}

        try:
            return _design(spec, name, return_pdb)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"Proteina-Complexa's resident worker is not available "
                    f"({reason}). Run `tu remote setup complexa` and read its "
                    f"named refusal; this provider has no subprocess fallback."
                )
            }
        except WorkerRequestError as exc:
            return {
                "error": f"Proteina-Complexa could not design for this target: {exc}",
                "note": ("the worker is still up and the next request is unaffected."),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"Proteina-Complexa failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
