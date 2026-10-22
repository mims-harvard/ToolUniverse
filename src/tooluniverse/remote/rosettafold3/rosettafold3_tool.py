"""RoseTTAFold3 structure prediction — MCP server.

RoseTTAFold3 (RosettaCommons foundry ``rf3``, commit 4010e3e2e) folds a
biomolecular assembly given its components: protein, DNA and RNA chains,
ligands and covalent modifications. This server is the thin, CPU-only half of
the provider; the model runs in its own environment and is held resident
between requests.

Residency is the whole reason this is not a subprocess. The kit's own ``pred``
verb spawns ``python -m rf3.cli fold`` once per seed, and its README states the
cost plainly: "Every call also pays ≈25 s of start-up and checkpoint load plus
each input's CPU featurization in any mode." The checkpoint alone is
3,038,876,446 bytes of fp32. A held worker reads it once. There is therefore no
subprocess fallback here, and that is deliberate rather than an omission: a
silent fall back to one would look like the provider working while quietly
costing the start-up on every call.

**Structure text is off by default.** ``diffusion_batch_size`` defaults to 5,
so a single fold of a real assembly is five mmCIF models plus their per-sample
confidence arrays — megabytes. Chai-1's provider learned what that does to this
transport: the reply was truncated at exactly 100,000 characters, which
produces invalid JSON rather than an honest refusal, so the caller gets a parse
error instead of a message saying the answer was too big. Paths and scores come
back either way; ``return_structures=true`` asks for the text, and even then
each file is size-checked before it is read.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_INPUT_BYTES = 1024 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# What the reply may carry in total when return_structures is asked for. Under
# the transport's own ceiling on purpose: a refusal that says so beats a
# truncation that does not.
MAX_TOTAL_STRUCTURE_BYTES = 8 * 1024 * 1024


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _fold(
    spec: str, seed: int, options: Dict[str, Any], return_structures: bool
) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="rosettafold3-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": spec,
                "out_dir": work,
                "name": "fold",
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        predictions: List[Dict[str, Any]] = list(result.get("predictions") or [])
        # Upstream writes the best sample twice: once in its own
        # seed-<s>_sample-<i>/ directory and once, copied, at the example
        # level. Both are reported -- the copy is the one a caller wants if it
        # wants exactly one file -- but only the distinct samples are counted
        # and only they are ever sent back as text.
        samples = [p for p in predictions if not p.get("top_ranked")] or predictions
        out: Dict[str, Any] = {
            "model": "RoseTTAFold3",
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
            "settings": result.get("settings"),
            "seed": result.get("seed"),
            "out_dir": result.get("out_dir"),
            "predictions": predictions,
            "n_structures": sum(1 for p in samples if p.get("cif")),
        }
        if result.get("peak_reserved_gib") is not None:
            out["peak_reserved_gib"] = result["peak_reserved_gib"]

        early = [p for p in predictions if p.get("early_stopped")]
        if early and not out["n_structures"]:
            return {
                "error": (
                    "RoseTTAFold3 stopped early and wrote no structure: mean pLDDT "
                    "fell below early_stopping_plddt_threshold. Lower or disable "
                    "that threshold on the worker, or give the input an MSA."
                ),
                "predictions": early,
                "timing": out["timing"],
            }
        if not out["n_structures"]:
            return {
                "error": "RoseTTAFold3 produced no structure for this input.",
                "files": result.get("files"),
                "timing": out["timing"],
            }

        # Off by default, as Chai-1's and Boltz-2's tools do it. The paths above
        # are inside a directory that goes away with this request, so a caller
        # that wants the coordinates asks for them; a caller that wants to rank
        # the samples already has everything it needs.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text of "
                "each distinct sample; the per-sample scores come back "
                "either way. The paths above name a per-request temporary "
                "directory that is removed when this call returns, so they "
                "identify the samples rather than outlive them -- the text "
                "is the only way to keep the coordinates."
            )
            return out

        structures = []
        budget = MAX_TOTAL_STRUCTURE_BYTES
        for prediction in samples:
            path = prediction.get("cif")
            if not path:
                continue
            name = os.path.basename(path)
            try:
                size = os.path.getsize(path)
            except OSError as exc:
                structures.append({"name": name, "error": type(exc).__name__})
                continue
            if size > MAX_STRUCTURE_BYTES or size > budget:
                structures.append(
                    {
                        "name": name,
                        "error": (
                            "omitted: this reply's structure-text budget is "
                            f"{MAX_TOTAL_STRUCTURE_BYTES} bytes and returning it "
                            "would exceed it"
                        ),
                    }
                )
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    structures.append({"name": name, "cif": fh.read()})
                budget -= size
            except (OSError, UnicodeError) as exc:
                structures.append({"name": name, "error": type(exc).__name__})
        out["structures"] = structures
        return out


@register_mcp_tool(
    tool_type_name="rosettafold3_predict",
    config={
        "description": (
            "Predict the all-atom structure of a biomolecular assembly with "
            "RoseTTAFold3 and return the per-sample confidence scores (pTM, "
            "ipTM, ranking score) with the paths to the predicted mmCIF "
            "models. Input is RoseTTAFold3's own specification as text: a "
            'JSON list of items, each {"name": ..., "components": [{"seq": '
            '..., "chain_id": ..., "chain_type": ...}]}, or a CIF/PDB '
            "structure to re-predict. No MSA server is used; set LOCAL_MSA_DIRS "
            "on the worker or give a component an msa_path to fold with MSAs."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "spec": {
                    "type": "string",
                    "description": (
                        "RoseTTAFold3 input specification. Example:\n"
                        '[{"name": "barstar", "components": [\n'
                        '  {"seq": "KKAVINGEQIRSISDLHQTL...", '
                        '"chain_id": "A", "chain_type": "polypeptide(L)"}]}]\n'
                        "chain_type is a PDB polymer type: 'polypeptide(L)', "
                        "'polyribonucleotide', 'polydeoxyribonucleotide'."
                    ),
                    "minLength": 10,
                    "maxLength": MAX_INPUT_BYTES,
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed; the same seed reproduces the fold.",
                    "default": 0,
                    "minimum": 0,
                },
                "annotate_b_factor_with_plddt": {
                    "type": "boolean",
                    "description": (
                        "Write per-atom pLDDT into the mmCIF B-factor column "
                        "(default false)."
                    ),
                    "default": False,
                },
                "dump_trajectories": {
                    "type": "boolean",
                    "description": (
                        "Also write the diffusion trajectory of each sample "
                        "(default false; large)."
                    ),
                    "default": False,
                },
                "one_model_per_file": {
                    "type": "boolean",
                    "description": "Write each sampled model to its own file (default false).",
                    "default": False,
                },
                "add_missing_atoms": {
                    "type": "boolean",
                    "description": (
                        "When the input is a CIF/PDB structure, add atoms "
                        "missing from its residues using the CCD (default true; "
                        "no effect on a JSON specification)."
                    ),
                    "default": True,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text of every sampled structure "
                        "(default false: five models of a real assembly are "
                        "megabytes, and a reply that large is what a transport "
                        "truncates into invalid JSON). The scores come back "
                        "either way; the paths do too, but they name a "
                        "temporary directory this call removes on return, so "
                        "set this to keep the coordinates."
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
                "predictions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "cif": {"type": "string"},
                            "summary_confidences": {"type": "string"},
                            "ptm": {"type": "number"},
                            "iptm": {"type": "number"},
                            "ranking_score": {"type": "number"},
                            "has_clash": {"type": "boolean"},
                            "top_ranked": {"type": "boolean"},
                            "early_stopped": {"type": "boolean"},
                        },
                    },
                },
                "n_structures": {"type": "integer"},
                "structures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "cif": {"type": "string"},
                            "error": {"type": "string"},
                        },
                    },
                },
                "structures_note": {"type": "string"},
                "out_dir": {"type": "string"},
                "seed": {"type": "integer"},
                "settings": {"type": "object"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "RoseTTAFold3 MCP Server",
        "host": "127.0.0.1",
        "port": 8034,
        "transport": "http",
    },
)
class RoseTTAFold3PredictTool:
    """Fold one assembly. Requests queue: the worker serves one at a time."""

    _FLAGS = (
        "annotate_b_factor_with_plddt",
        "dump_trajectories",
        "one_model_per_file",
        "add_missing_atoms",
    )
    _FLAG_DEFAULTS = {
        "annotate_b_factor_with_plddt": False,
        "dump_trajectories": False,
        "one_model_per_file": False,
        "add_missing_atoms": True,
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        spec = arguments.get("spec")
        if not isinstance(spec, str) or not spec.strip():
            return {
                "error": (
                    "'spec' must be RoseTTAFold3's input specification as text: "
                    "a JSON list of items, or a CIF/PDB structure."
                )
            }
        if len(spec.encode("utf-8")) > MAX_INPUT_BYTES:
            return {"error": f"'spec' exceeds {MAX_INPUT_BYTES} bytes."}

        options: Dict[str, Any] = {}
        for name in self._FLAGS:
            value = arguments.get(name, self._FLAG_DEFAULTS[name])
            if not isinstance(value, bool):
                return {"error": f"'{name}' must be a boolean."}
            options[name] = value

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        try:
            return _fold(spec, seed, options, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"RoseTTAFold3's resident worker is not available ({reason}). "
                    f"Run `tu remote setup rosettafold3` and read its named "
                    f"refusal; this provider has no subprocess fallback on "
                    f"purpose."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
