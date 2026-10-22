"""RFdiffusion3 protein backbone design — MCP server.

RFdiffusion3 designs protein backbones: given a specification -- a length to
build unconditionally, or a contig string that scaffolds a motif out of an
input structure -- it samples N backbones by reverse diffusion. This server is
the thin, CPU-only half of the provider; the model runs in its own environment
and is held resident between requests.

This is the provider where residency pays most, and the reason is a property
of the kit rather than of the model. The kit's `fast` mode traces the denoiser
through torch.compile and captures it as a CUDA graph, and both are per
PROCESS: a process that exits takes them with it. Measured on one card, three
designs of an unconditional 60-mer take 19.4 s, 1.6 s and 1.6 s in one held
worker -- 12x, against Boltz-2's 2.0x.

Peak VRAM is driven by length rather than by count: 400 residues costs 4.8x
what 100 does at the same count, while doubling the count at 400 adds 5%. The
manifest declares 12.49 GiB measured at 400 residues and 4 designs, and this
server's limits are set to keep requests inside that envelope.

There is no subprocess fallback. When the worker cannot start, this says so
and names the reason.
"""

import gzip
import os
import re
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_LENGTH = 400
MAX_DESIGNS = 8
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# Upstream's own length grammar: "60" or "60-100" (a sampled range).
_LENGTH_RE = re.compile(r"^\d+(-\d+)?$")
# A contig string is upstream's, e.g. "10-40/A163-181/10-40". Kept to the
# characters that grammar uses so a typo is refused here rather than inside
# a design that has already cost a minute.
_CONTIG_RE = re.compile(r"^[A-Za-z0-9/,\-\s]+$")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _check_length(value: Any) -> str:
    """Normalise a length or length range, raising ValueError by name."""
    text = str(value).strip()
    if not _LENGTH_RE.match(text):
        raise ValueError("'length' must be a number like 60 or a range like 60-100.")
    bounds = [int(p) for p in text.split("-")]
    if bounds[-1] > MAX_LENGTH:
        raise ValueError(
            f"'length' above {MAX_LENGTH} is outside this provider's measured "
            f"VRAM envelope (12.49 GiB at 400 residues); re-measure before "
            f"raising it."
        )
    if bounds[0] < 1 or (len(bounds) == 2 and bounds[0] > bounds[1]):
        raise ValueError("'length' range must be increasing and at least 1.")
    return text


def _design(spec: Dict[str, Any], n_designs: int, seed: int, return_structures: bool):
    """One design request on the resident worker, or a named reason why not."""
    import json
    import tempfile

    document = {
        "specification": {"design": spec},
        "options": {"n_batches": n_designs},
    }
    with tempfile.TemporaryDirectory(prefix="rfdiffusion3-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(document),
                "out_dir": work,
                "name": "design",
                "seed": seed,
                "options": {},
            }
        )
        result = reply["result"]
        designs = result.get("designs") or []
        out: Dict[str, Any] = {
            "model": "RFdiffusion3",
            "n_designs": result.get("n_designs", len(designs)),
            "seed": result.get("seed"),
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("mode"),
            # True when this request changed a build-time parameter and the
            # engine had to be rebuilt -- the one case where a held worker
            # pays the compile trace again, and worth surfacing.
            "engine_rebuilt": result.get("engine_rebuilt"),
        }
        summary = []
        for d in designs:
            entry = {"example_id": d.get("example_id")}
            for field in ("metrics", "sequence", "task"):
                if field in d:
                    entry[field] = d[field]
            summary.append(entry)
        out["designs"] = summary

        if not designs:
            return {
                "error": "RFdiffusion3 produced no backbone for this specification.",
                "timing": out["timing"],
            }

        # Off by default, for the reason chai1's tool records: eight backbones
        # of mmCIF are megabytes, and a transport truncates an oversized reply
        # into invalid JSON rather than refusing it. Upstream writes .cif.gz,
        # so returning the text means decompressing it here.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; "
                "the per-design metrics above come back either way"
            )
            return out

        for entry, d in zip(summary, designs):
            path = d.get("structure")
            if not path:
                continue
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    entry["error"] = "exceeds the public output limit"
                    continue
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    entry["cif"] = f.read()
            except (OSError, UnicodeError, EOFError) as exc:
                entry["error"] = type(exc).__name__
        return out


@register_mcp_tool(
    tool_type_name="rfdiffusion3_design",
    config={
        "description": (
            "Design protein backbones with RFdiffusion3. Either give a "
            "'length' to build an unconditional backbone of that size, or a "
            "'contigs' string with an 'input_pdb' to scaffold a motif out of "
            "an existing structure. Returns per-design metrics; the mmCIF "
            "text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "length": {
                    "type": "string",
                    "description": (
                        "Backbone length for unconditional design: '60', or a "
                        f"sampled range '60-100'. Maximum {MAX_LENGTH}."
                    ),
                },
                "contigs": {
                    "type": "string",
                    "description": (
                        "Motif-scaffolding contig string, e.g. "
                        "'10-40/A163-181/10-40'. Requires input_pdb."
                    ),
                },
                "input_pdb": {
                    "type": "string",
                    "description": (
                        "Path to the input structure the contigs refer to. "
                        "Required with 'contigs', and must be readable by the "
                        "provider."
                    ),
                },
                "n_designs": {
                    "type": "integer",
                    "description": (
                        f"How many backbones to sample (default 1, max {MAX_DESIGNS})."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_DESIGNS,
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed; the same seed reproduces the designs.",
                    "default": 0,
                    "minimum": 0,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text of every backbone "
                        "(default false: megabytes)."
                    ),
                    "default": False,
                },
            },
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_designs": {"type": "integer"},
                "designs": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seed": {"type": "integer"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "engine_rebuilt": {"type": "boolean"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "RFdiffusion3 MCP Server",
        "host": "127.0.0.1",
        "port": 8040,
        "transport": "http",
    },
)
class RFdiffusion3DesignTool:
    """Design backbones. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        length = arguments.get("length")
        contigs = arguments.get("contigs")
        if (length is None) == (contigs is None):
            return {
                "error": (
                    "give exactly one of 'length' (unconditional design) or "
                    "'contigs' (motif scaffolding)."
                )
            }

        spec: Dict[str, Any] = {}
        if length is not None:
            try:
                spec["length"] = _check_length(length)
            except ValueError as exc:
                return {"error": str(exc)}
        else:
            if not isinstance(contigs, str) or not contigs.strip():
                return {"error": "'contigs' must be a non-empty string."}
            if not _CONTIG_RE.match(contigs):
                return {
                    "error": "'contigs' contains characters that grammar has no use for."
                }
            input_pdb = arguments.get("input_pdb")
            if not isinstance(input_pdb, str) or not input_pdb.strip():
                return {"error": "'contigs' requires 'input_pdb'."}
            if not os.path.isfile(input_pdb):
                return {"error": f"input_pdb not found: {input_pdb}"}
            spec["contigmap"] = {"contigs": contigs.strip()}
            spec["input"] = input_pdb

        n_designs = arguments.get("n_designs", 1)
        if not isinstance(n_designs, int) or isinstance(n_designs, bool):
            return {"error": "'n_designs' must be an integer."}
        if not 1 <= n_designs <= MAX_DESIGNS:
            return {"error": f"'n_designs' must be between 1 and {MAX_DESIGNS}."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        try:
            return _design(spec, n_designs, seed, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"RFdiffusion3's resident worker is not available "
                    f"({reason}). Run `tu remote setup rfdiffusion3` and read "
                    f"its named refusal; this provider has no subprocess "
                    f"fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
