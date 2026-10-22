"""AF3-torch structure prediction -- MCP server.

AF3-torch is the xfold PyTorch port of the AlphaFold 3 architecture running the
public OpenFold3-preview2 parameters. This server is the thin, CPU-only half of
the provider; the model runs in its own environment and is held resident
between requests, because the alternative pays a 1.37 GB parameter read, a CUDA
context, the kit's Triton compiles and a torch.compile of the sampler on every
call.

Input is an AlphaFold 3 fold-input JSON -- the same dialect `run_alphafold.py`
takes -- and **each chain must carry its own MSAs inline**. No genetic-database
search runs here: a resident GPU worker is the wrong place to run HMMER against
public_databases, and this deployment has none. A chain with
`"unpairedMsa": ">query\\n<its own sequence>\\n"` and `"pairedMsa": ""` is a
single-sequence prediction and is accepted.

There is no subprocess fallback, deliberately, as with Chai-1: a per-request
process would look like the provider working while quietly costing several
times as much. When the resident worker cannot start, this says so and names
the reason -- and on a machine without the kit's second, CPU-only interpreter
the reason will be `jax_interpreter_unset`, which is the honest answer.

Structures are NOT returned by default. Five sampled mmCIFs of a real complex
are megabytes, and the MCP transport truncates a reply at exactly 100,000
characters, which produces invalid JSON rather than an honest refusal. Paths
and scores come back instead; `return_structures=true` asks for the text.
"""

import json
import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_INPUT_BYTES = 8 * 1024 * 1024  # fold inputs carry their MSAs, so this is large
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _predict(fold_input: str, name: str, return_structures: bool) -> Dict[str, Any]:
    """One prediction on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="af3_torch-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": fold_input,
                "out_dir": work,
                "name": name,
            }
        )
        result = reply["result"]
        out: Dict[str, Any] = {
            "model": "AF3-torch (xfold on OpenFold3-preview2 weights)",
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
            "seeds": result.get("seeds"),
        }
        for key in ("summary_confidences", "ranking_scores_csv", "peak_reserved_gib"):
            if result.get(key) is not None:
                out[key] = result[key]

        cifs = [p for p in (result.get("structures") or []) if p.endswith(".cif")]
        out["n_structures"] = len(cifs)
        out["structure_paths"] = cifs
        out["out_dir"] = result.get("out_dir")
        if not cifs:
            return {
                "error": "AF3-torch produced no structure for this input.",
                "timing": out["timing"],
                "out_dir": out["out_dir"],
            }

        # Off by default. The paths above point at files on the host running
        # the model, and the ranking scores are already here; an agent that
        # only wanted to rank samples should not be charged megabytes of mmCIF
        # -- nor silently handed a reply the transport cut in half.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text of the "
                "best-ranked model; the paths and the confidence scores above "
                "come back either way"
            )
            return out

        # Even when asked, only the best-ranked model's text is returned. The
        # per-sample copies are on disk at structure_paths.
        best = [p for p in cifs if p.endswith("_model.cif")] or cifs[:1]
        structures = []
        for path in best:
            try:
                if os.path.getsize(path) > MAX_STRUCTURE_BYTES:
                    structures.append(
                        {
                            "name": os.path.basename(path),
                            "error": "exceeds the public output limit",
                        }
                    )
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    structures.append({"name": os.path.basename(path), "cif": f.read()})
            except (OSError, UnicodeError) as exc:
                structures.append(
                    {"name": os.path.basename(path), "error": type(exc).__name__}
                )
        out["structures"] = structures
        return out


@register_mcp_tool(
    tool_type_name="af3_torch_predict",
    config={
        "description": (
            "Predict the all-atom structure of a biomolecular complex with "
            "AF3-torch (the xfold PyTorch port of AlphaFold 3, running the "
            "public OpenFold3-preview2 parameters). Input is an AlphaFold 3 "
            "fold-input JSON (dialect 'alphafold3'), and every chain must "
            "carry its own MSAs inline: no genetic-database search is run. "
            "Returns the paths of the predicted mmCIF files and their "
            "confidence and ranking scores; the mmCIF text itself only when "
            "return_structures is true."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "fold_input": {
                    "type": "string",
                    "description": (
                        "An AlphaFold 3 fold-input JSON, as text. Example:\n"
                        '{"name": "x", "dialect": "alphafold3", "version": 2, '
                        '"sequences": [{"protein": {"id": "A", "sequence": '
                        '"MKTAYIAKQRQ...", "modifications": [], "templates": [], '
                        '"unpairedMsa": ">query\\nMKTAYIAKQRQ...\\n", '
                        '"pairedMsa": ""}}], "modelSeeds": [1]}\n'
                        "modelSeeds chooses the sampler seeds; one prediction "
                        "runs per seed. unpairedMsa may be the query alone for "
                        "a single-sequence prediction, but accuracy is much "
                        "lower than with a real MSA."
                    ),
                    "minLength": 20,
                    "maxLength": MAX_INPUT_BYTES,
                },
                "name": {
                    "type": "string",
                    "description": (
                        "A job name used for the output file names "
                        "(default 'fold'). Letters, digits, '-' and '_'."
                    ),
                    "default": "fold",
                    "maxLength": 64,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text of the best-ranked model "
                        "(default false: it is megabytes for a real complex, "
                        "and the transport truncates a reply at 100,000 "
                        "characters). Paths and scores come back either way."
                    ),
                    "default": False,
                },
            },
            "required": ["fold_input"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "structure_paths": {"type": "array", "items": {"type": "string"}},
                "n_structures": {"type": "integer"},
                "structures": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "cif": {"type": "string"},
                        },
                    },
                },
                "structures_note": {"type": "string"},
                "summary_confidences": {"type": "object"},
                "ranking_scores_csv": {"type": "string"},
                "seeds": {"type": "array", "items": {"type": "integer"}},
                "out_dir": {"type": "string"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AF3-torch MCP Server",
        "host": "127.0.0.1",
        "port": 8036,
        "transport": "http",
    },
)
class AF3TorchPredictTool:
    """Predict one complex. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        fold_input = arguments.get("fold_input")
        if not isinstance(fold_input, str) or not fold_input.strip():
            return {"error": "'fold_input' must be an AlphaFold 3 fold-input JSON."}
        if len(fold_input.encode("utf-8")) > MAX_INPUT_BYTES:
            return {"error": f"'fold_input' exceeds {MAX_INPUT_BYTES} bytes."}
        try:
            parsed = json.loads(fold_input)
        except ValueError as exc:
            return {"error": f"'fold_input' is not valid JSON: {exc}"}
        if not isinstance(parsed, dict) or not parsed.get("sequences"):
            return {
                "error": (
                    "'fold_input' must be an object with a 'sequences' list "
                    "(the AlphaFold 3 fold-input dialect)."
                )
            }
        if parsed.get("dialect") not in (None, "alphafold3"):
            return {
                "error": (
                    f"'fold_input' declares dialect {parsed.get('dialect')!r}; "
                    f"this tool takes the 'alphafold3' dialect."
                )
            }

        name = arguments.get("name", "fold")
        if not isinstance(name, str) or not name:
            return {"error": "'name' must be a non-empty string."}
        if not all(c.isalnum() or c in "-_" for c in name) or len(name) > 64:
            return {
                "error": "'name' must be <= 64 characters of letters, digits, '-' or '_'."
            }

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        try:
            return _predict(fold_input, name, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"AF3-torch's resident worker is not available ({reason}). "
                    f"Run `tu remote setup af3_torch` and read its named "
                    f"refusal. This kit needs TWO interpreters: the model's "
                    f"(TOOLUNIVERSE_AF3_TORCH_PYTHON) and a second, CPU-only "
                    f"one for featurisation and the mmCIF writers "
                    f"(AF3_TORCH_JAX_PY, AF3_TORCH_JAX_REPO). This provider "
                    f"has no subprocess fallback on purpose."
                ),
                "detail": str(exc)[:2000],
            }


if __name__ == "__main__":
    start_mcp_server()
