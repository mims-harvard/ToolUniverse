"""BoltzGen protein design — MCP server.

BoltzGen (`boltzgen` 0.3.2) designs protein backbones and sequences from a
design specification: an unconditional monomer of a given length, or a binder
against a target structure supplied as a PDB. This server is the thin,
CPU-only half of the provider; the model runs in its own environment and is
held resident between requests.

Residency matters differently here than for the predictors. Upstream is a
PIPELINE -- `configure`, then up to six steps, each of which upstream starts as
its own interpreter, and each GPU step loads its own checkpoint inside the
step. The kit's `inproc` lever removes the per-step interpreter; holding the
worker removes it for every request after the first as well. What is held is
the process -- the torch/rdkit/hydra import graph, the CUDA context, the Triton
and cuEquivariance JIT caches -- and NOT the weights, which upstream re-reads
per step and which neither the kit nor this provider memoises. Every reply says
so in `weights_held_by`.

As with Chai-1 there is no subprocess fallback, deliberately. When the resident
worker cannot start, this says so and names the reason rather than quietly
paying the start-up cost on every call.
"""

import json
import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_SPEC_BYTES = 256 * 1024
# A target structure is the one genuinely large input: an AlphaFold monomer PDB
# is a few hundred kilobytes.
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# What comes back when the caller asks for the structures themselves.
MAX_RETURNED_STRUCTURES = 32
# The ranked table. A campaign of thousands of designs has a row per design and
# the agent asked for a design job, not a spreadsheet.
MAX_METRIC_ROWS = 50


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _design(
    spec: str,
    files: Dict[str, str],
    seed: int,
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One design job on the resident worker, or a named reason why not."""
    import tempfile

    envelope = {"specification": spec, "options": options}
    if files:
        envelope["files"] = files

    with tempfile.TemporaryDirectory(prefix="boltzgen-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(envelope),
                "out_dir": work,
                "name": "design",
                "seed": seed,
                "options": {},
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            "model": "BoltzGen 0.3.2",
            "run_dir": result.get("run_dir"),
            "steps": result.get("steps"),
            "num_designs": result.get("num_designs"),
            "diffusion_batch_size": result.get("diffusion_batch_size"),
            # What every configured step actually ran, read back out of the
            # resolved config rather than echoed from the request: upstream
            # ships 500 for `design` and 200 for the scoring steps.
            "sampling_steps": result.get("sampling_steps"),
            "seed": result.get("seed"),
            "timing": result.get("timing"),
            "mode": result.get("mode"),
            "weights_held_by": result.get("weights_held_by"),
            "levers_applied": result.get("levers_applied"),
        }
        for key in ("peak_reserved_gib", "warning"):
            if key in result:
                out[key] = result[key]

        structures = list(result.get("structures") or [])
        out["n_structures"] = len(structures)
        out["structure_paths"] = structures[:MAX_RETURNED_STRUCTURES]
        if not structures:
            return {
                "error": (
                    "BoltzGen produced no structure for this specification. "
                    + str(result.get("warning") or "")
                ).strip(),
                "run_dir": out["run_dir"],
                "timing": out["timing"],
            }

        # The ranked table, when the `filtering` step ran. It is what a caller
        # ranks N designs on and the reason to return anything beyond paths.
        rows = result.get("metrics")
        if rows:
            out["metrics_file"] = result.get("metrics_file")
            out["metrics"] = rows[:MAX_METRIC_ROWS]
            out["n_metric_rows"] = result.get("n_metric_rows", len(rows))
            if out["n_metric_rows"] > MAX_METRIC_ROWS:
                out["metrics_note"] = (
                    f"the first {MAX_METRIC_ROWS} of {out['n_metric_rows']} rows; "
                    f"the whole table is at metrics_file"
                )

        # Off by default, as Boltz-2's and Chai-1's tools do it. A design job
        # writes one structure per design and several per design once the
        # refolding step has run -- megabytes of mmCIF that an agent wanting
        # the ranking would pay for, and a reply that large is what a transport
        # truncates, producing a broken answer rather than a refused one.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the structure text; "
                "the paths above are on the host that ran the model, and the "
                "ranking metrics come back either way"
            )
            return out

        texts = []
        for path in structures[:MAX_RETURNED_STRUCTURES]:
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    texts.append(
                        {
                            "name": os.path.basename(path),
                            "error": "exceeds the public output limit",
                        }
                    )
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    texts.append({"name": os.path.basename(path), "text": f.read()})
            except (OSError, UnicodeError) as exc:
                texts.append(
                    {"name": os.path.basename(path), "error": type(exc).__name__}
                )
        out["structures"] = texts
        return out


@register_mcp_tool(
    tool_type_name="boltzgen_design",
    config={
        "description": (
            "Design protein backbones and sequences with BoltzGen and return "
            "the designs with their ranking metrics. Input is a BoltzGen "
            "design specification in YAML: a mapping with an 'entities' list. "
            "An unconditional monomer is one protein entity with a length "
            "range ('sequence: 60..80'); a binder additionally names a target "
            "structure as a 'file' entity, whose PDB text is supplied through "
            "'target_files'. The whole six-step pipeline (design, inverse "
            "folding, refolding, analysis, filtering) runs unless 'steps' "
            "names fewer. No MSA server is used."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "spec": {
                    "type": "string",
                    "description": (
                        "BoltzGen design specification, YAML. Unconditional "
                        "60-mer:\n"
                        "entities:\n"
                        "  - protein:\n"
                        "      id: A\n"
                        "      sequence: 60..60\n"
                        "Binder against a target, whose PDB goes in "
                        "target_files under the same name:\n"
                        "entities:\n"
                        "  - protein: {id: B, sequence: 60..80}\n"
                        "  - file:\n"
                        "      path: target.pdb\n"
                        "      include: [{chain: {id: A}}]\n"
                        "      binding_types: [{chain: {id: A, binding: "
                        "'39,96,98'}}]\n"
                        "      structure_groups: all"
                    ),
                    "minLength": 10,
                    "maxLength": MAX_SPEC_BYTES,
                },
                "target_files": {
                    "type": "object",
                    "description": (
                        "Files the specification names by a relative path, as "
                        "{file name: text}. A spec's 'file' entity is resolved "
                        "against the specification's own directory, so a "
                        "target PDB must be supplied here."
                    ),
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
                "num_designs": {
                    "type": "integer",
                    "description": (
                        "How many designs to generate (default 4). Upstream's "
                        "own default is 10000, which is a campaign rather than "
                        "a request, so this provider does not use it."
                    ),
                    "default": 4,
                    "minimum": 2,
                    "maximum": 256,
                },
                "diffusion_batch_size": {
                    "type": "integer",
                    "description": (
                        "Designs per diffusion batch (default: min(num_designs, "
                        "4)). Must be at least 2 and no more than num_designs: "
                        "the optimization kit's mask-hoist lever cannot serve a "
                        "batch of one design and the kit refuses the run. "
                        "Larger batches are faster and use more GPU memory."
                    ),
                    "minimum": 2,
                    "maximum": 32,
                },
                "steps": {
                    "type": "array",
                    "description": (
                        "Pipeline steps to run, in upstream's own names "
                        "(design, inverse_folding, design_folding, folding, "
                        "analysis, filtering). Omit for all of them; "
                        "['design'] generates backbones only and returns no "
                        "ranking metrics."
                    ),
                    "items": {"type": "string"},
                },
                "protocol": {
                    "type": "string",
                    "description": (
                        "Upstream's design protocol (default "
                        "protein-anything), which picks the pipeline steps."
                    ),
                },
                "sampling_steps": {
                    "type": "integer",
                    "description": (
                        "Denoiser steps the design step runs. Omit for "
                        "upstream's own 500, which is what its published "
                        "results use. Lowering it trades design quality for "
                        "wall time and is for previews and smoke runs, not "
                        "for designs that will be ordered: the reply reports "
                        "the value every configured step actually ran."
                    ),
                    "minimum": 2,
                    "maximum": 1000,
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed; pipeline step i runs with seed + i, and "
                        "the same seed reproduces the job. Required by the "
                        "optimization kit, so 0 is used when none is given."
                    ),
                    "default": 0,
                    "minimum": 0,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF/PDB text of every design (default "
                        "false: megabytes). The paths and the ranking metrics "
                        "come back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["spec"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "run_dir": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}},
                "num_designs": {"type": "integer"},
                "diffusion_batch_size": {"type": "integer"},
                "sampling_steps": {"type": "object"},
                "seed": {"type": "integer"},
                "n_structures": {"type": "integer"},
                "structure_paths": {"type": "array", "items": {"type": "string"}},
                "structures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "text": {"type": "string"},
                        },
                    },
                },
                "structures_note": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "object"}},
                "metrics_file": {"type": "string"},
                "n_metric_rows": {"type": "integer"},
                "metrics_note": {"type": "string"},
                "peak_reserved_gib": {"type": "number"},
                "timing": {"type": "object"},
                "mode": {"type": "string"},
                "weights_held_by": {"type": "string"},
                "levers_applied": {"type": "array", "items": {"type": "string"}},
                "warning": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "BoltzGen MCP Server",
        "host": "127.0.0.1",
        "port": 8035,
        "transport": "http",
    },
)
class BoltzGenDesignTool:
    """Design one specification. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        spec = arguments.get("spec")
        if not isinstance(spec, str) or "entities" not in spec:
            return {
                "error": (
                    "'spec' must be a BoltzGen design specification in YAML, "
                    "whose top-level key is 'entities'."
                )
            }
        if len(spec.encode("utf-8")) > MAX_SPEC_BYTES:
            return {"error": f"'spec' exceeds {MAX_SPEC_BYTES} bytes."}

        files = arguments.get("target_files", {}) or {}
        if not isinstance(files, dict):
            return {"error": "'target_files' must be an object of name to text."}
        total = 0
        for name, text in files.items():
            if not isinstance(text, str):
                return {"error": f"'target_files[{name}]' must be a string."}
            if os.path.basename(name) != name or not name:
                return {
                    "error": (
                        f"'target_files' key {name!r} must be a plain file name, "
                        f"not a path."
                    )
                }
            total += len(text.encode("utf-8"))
        if total > MAX_FILE_BYTES:
            return {"error": f"'target_files' exceeds {MAX_FILE_BYTES} bytes in all."}

        num_designs = arguments.get("num_designs", 4)
        if (
            not isinstance(num_designs, int)
            or isinstance(num_designs, bool)
            or not 2 <= num_designs <= 256
        ):
            return {"error": "'num_designs' must be an integer between 2 and 256."}

        options: Dict[str, Any] = {"num_designs": num_designs}

        batch = arguments.get("diffusion_batch_size")
        if batch is not None:
            if not isinstance(batch, int) or isinstance(batch, bool):
                return {"error": "'diffusion_batch_size' must be an integer."}
            if not 2 <= batch <= 32:
                return {
                    "error": (
                        "'diffusion_batch_size' must be between 2 and 32: the "
                        "optimization kit's mask-hoist lever cannot serve a "
                        "diffusion batch of one design and refuses the run."
                    )
                }
            if batch > num_designs:
                return {
                    "error": ("'diffusion_batch_size' must not exceed 'num_designs'.")
                }
            options["diffusion_batch_size"] = batch

        steps = arguments.get("steps")
        if steps is not None:
            if not isinstance(steps, list) or not all(
                isinstance(s, str) for s in steps
            ):
                return {"error": "'steps' must be a list of step names."}
            if steps:
                options["steps"] = steps

        protocol = arguments.get("protocol")
        if protocol is not None:
            if not isinstance(protocol, str) or not protocol.strip():
                return {"error": "'protocol' must be a non-empty string."}
            options["protocol"] = protocol

        sampling_steps = arguments.get("sampling_steps")
        if sampling_steps is not None:
            if not isinstance(sampling_steps, int) or isinstance(
                sampling_steps, bool
            ):
                return {"error": "'sampling_steps' must be an integer."}
            if not 2 <= sampling_steps <= 1000:
                return {
                    "error": (
                        "'sampling_steps' must be between 2 and 1000: both of "
                        "upstream's noise schedules divide by "
                        "(sampling_steps - 1)."
                    )
                }
            options["sampling_steps"] = sampling_steps

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        try:
            return _design(spec, files, seed, options, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"BoltzGen's resident worker is not available ({reason}: "
                    f"{exc}). Run `tu remote setup boltzgen` and read its named "
                    f"refusal; this provider has no subprocess fallback on "
                    f"purpose."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
