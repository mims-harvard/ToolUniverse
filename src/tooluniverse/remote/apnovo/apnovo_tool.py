"""AlphaProtein Novo de novo enzyme design — MCP server.

AP Novo scaffolds a catalytic motif: a joint sequence–structure diffusion model
co-generates a backbone and a sequence conditioned on fixed motif atoms and
fixed ligand atoms. This server is the thin, CPU-only half of the provider; the
model runs in its own environment and is held resident between requests.

Three operations, and the cheap one matters most in practice. `motif_str` is
the field that silently wastes GPU-hours -- a malformed one is otherwise only
visible after the generation stage -- so `apnovo_validate_motif` parses it with
upstream's own `MotifSpec` and needs neither weights nor the card.

Inputs arrive INLINE, not as paths. Upstream reads a manifest and the CIF files
it names off disk, but a caller of this server need not share a filesystem with
it, so a campaign is supplied as a manifest document plus a mapping of filename
to CIF text, and the worker lays them out in a scratch directory. Outputs go
the other way for the same reason: generation returns a server-side `run_dir`
that `apnovo_evaluate_designs` then reads, because a campaign is thousands of
files and an agent asked for a design job rather than a tarball.

What this provider does NOT do is as deliberate as what it does: there is no
folding operation, because AlphaFold 3 weights carry terms separate from AP
Novo's and that question is unsettled here. `provider.toml` and README.md carry
the reasoning.

The consequence for callers is sharper than it first looks. Upstream's
evaluation does not degrade gracefully on an unfolded campaign: it reads each
design's metadata, finds no folding seed, and refuses the whole run, rather
than computing the subset of metrics that need no structure prediction.

But upstream does not require THIS provider to have folded anything -- it
requires a directory shaped like `run_alphafold.py` output, and the filenames
it looks for are plain:
`<sample>_<state>_folded_seed<n>.cif` beside
`<sample>_<state>_confidences_seed<n>.json`, read from
`design_manifest.folded_state_paths` at the pinned commit. So
`apnovo_ingest_folded` takes predictions from any structure predictor that has
settled its own weights question -- five of them ship on this same standard --
and writes them where the evaluation looks. The entitlement question stays
unsettled and unanswered here; it just stops being the thing that makes the
operation unusable.

Two things were wrong before that, and only one of them was the licence.
`_evaluate` passed `--input_dir=01_generation` unconditionally, while the
flag's own help says "Directory with the output of run_alphafold.py" -- so a
campaign that HAD been folded failed in exactly the same way as one that had
not, and the shared error got read as the stronger claim.

There is no subprocess fallback, deliberately. When the resident worker cannot
start, this names the reason instead of quietly paying the start-up cost on
every call.
"""

import json
import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# A manifest is a small JSON document; a motif CIF is a few hundred kilobytes
# at most, since a motif is a handful of residues plus a ligand.
MAX_MANIFEST_BYTES = 256 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 64 * 1024 * 1024
# Upstream samples 1000 denoising steps per design and the published campaigns
# run hundreds of designs per motif. This ceiling is about one request's
# wall clock, not about what a campaign may total across requests.
MAX_DESIGNS_PER_REQUEST = 256
# What comes back when the caller asks for the structures themselves.
MAX_RETURNED_DESIGNS = 32


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


# The socket protocol defines exactly three ops -- ping, shutdown, predict --
# and anything else comes back `unknown_op`. A provider with several operations
# therefore rides them all on `predict` and dispatches on its own `task` field;
# the worker's `on_predict` reads it.


def _result(reply: Dict[str, Any]) -> Dict[str, Any]:
    """The operation's own body out of the socket's envelope.

    `ResidentWorker.request` returns the whole reply -- `{"ok": true,
    "result": {...}}` -- and raises when `ok` is false, so by the time a caller
    is here the body is under `result`. Returning the envelope instead is a
    quiet bug: the declared return_schema does not describe it, and a guard
    that looks for its own field at the top level reads an absent key as a
    failed run. That is how it was found here -- generation reported "produced
    no design" for a campaign that had in fact written one.
    """
    if isinstance(reply, dict) and "result" in reply:
        body = reply["result"]
        if isinstance(body, dict):
            return body
    return reply


def _unavailable(exc: Exception) -> Dict[str, Any]:
    """The named reason a request failed, and it distinguishes two of them.

    `request_failed` means the worker was there and ran: the operation itself
    failed, and the operation's own message is the answer. Anything else means
    the request never reached a working model, and the setup hint is the
    answer. Collapsing the two sends someone to `tu remote setup` over a bad
    argument -- which is what this did when an evaluation died on a misspelled
    upstream flag and the reply blamed the deployment.
    """
    reason = getattr(exc, "reason", "") or type(exc).__name__
    if reason == "request_failed":
        return {
            "error": f"The AlphaProtein Novo operation failed: {exc}",
            "reason": reason,
        }
    return {
        "error": (
            f"AlphaProtein Novo's resident worker is not available ({reason}: "
            f"{exc}). Run `tu remote setup apnovo` and read its named refusal "
            f"— if it is `weights_terms_not_accepted`, that is intended and "
            f"this provider's README.md explains it. There is no subprocess "
            f"fallback on purpose."
        ),
        "reason": reason,
    }


def _checked_manifest(arguments: Dict[str, Any]) -> Any:
    """The manifest document, or an error dict."""
    manifest = arguments.get("manifest")
    if isinstance(manifest, dict):
        text = json.dumps(manifest)
    elif isinstance(manifest, str):
        text = manifest
    else:
        return {
            "error": (
                "'manifest' must be an AP Novo design manifest, as a JSON "
                "object or a JSON string. It needs at least a 'designs' list, "
                "each entry naming 'input_file', 'motif_str' and "
                "'is_author_naming'."
            )
        }
    if len(text.encode("utf-8")) > MAX_MANIFEST_BYTES:
        return {"error": f"'manifest' exceeds {MAX_MANIFEST_BYTES} bytes."}
    try:
        document = json.loads(text)
    except ValueError as exc:
        return {"error": f"'manifest' is not valid JSON: {exc}"}
    if not isinstance(document, dict) or "designs" not in document:
        return {"error": "'manifest' must be an object carrying a 'designs' list."}
    return document


def _checked_files(arguments: Dict[str, Any]) -> Any:
    """The inline CIF inputs, or an error dict."""
    files = arguments.get("files") or {}
    if not isinstance(files, dict):
        return {
            "error": (
                "'files' must map each filename named by the manifest to that "
                "file's text, e.g. {\"motif.cif\": \"data_motif\\n...\"}."
            )
        }
    total = 0
    for name, text in files.items():
        if not isinstance(name, str) or not isinstance(text, str):
            return {"error": "'files' keys and values must both be strings."}
        if "/" in name or name.startswith("."):
            return {
                "error": (
                    f"'files' key {name!r} must be a bare filename — the "
                    f"manifest's paths resolve inside the scratch directory."
                )
            }
        size = len(text.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            return {"error": f"'files[{name}]' exceeds {MAX_FILE_BYTES} bytes."}
        total += size
    if total > MAX_TOTAL_FILE_BYTES:
        return {"error": f"'files' total exceeds {MAX_TOTAL_FILE_BYTES} bytes."}
    return files


_MANIFEST_SCHEMA = {
    "type": "string",
    "description": (
        "AP Novo design manifest as a JSON string (a JSON object is also "
        "accepted). Minimally {\"designs\": [{\"input_file\": \"motif.cif\", "
        "\"motif_str\": \"A1,A2|10-100,{},2-80,{},10-100/B1\", "
        "\"motif_atoms\": \"A1:OE2,OE1,CD,CG A2:OG,CB,CA\", "
        "\"is_author_naming\": false, \"num_designs\": 2}]}. In motif_str, "
        "'A1' fixes input chain A residue 1, '10-100' is a generated segment "
        "whose length is sampled once per design, '/B1' is a fixed ligand "
        "chain, and a leading '|' randomises segment order."
    ),
}

_FILES_SCHEMA = {
    "type": "object",
    "additionalProperties": {"type": "string"},
    "description": (
        "Each filename the manifest names, mapped to that file's text. The "
        "motif CIF is required; a partial-diffusion parent CIF is needed only "
        "if the manifest asks for one."
    ),
}


@register_mcp_tool(
    tool_type_name="apnovo_validate_motif",
    config={
        "description": (
            "Validate an AlphaProtein Novo design manifest and parse its "
            "catalytic motif specification, without running the model. "
            "Reports which atoms and ligand chains are fixed, whether motif "
            "conditioning is indexed or unindexed, whether partial diffusion "
            "is configured, and the folding states and evaluation suite the "
            "manifest declares. Run this before generating: a malformed "
            "motif_str is otherwise only visible after the generation stage "
            "has spent GPU-hours. Needs no weights and no GPU."
        ),
        "parameter_schema": {
            "type": "object",
            # Written out rather than left to `register_mcp_tool` to inject:
            # the schema-parity check reads this literal from the source AST,
            # so a closure added at import time would make the published JSON
            # and the decorator disagree while both were in fact closed.
            "additionalProperties": False,
            "properties": {"manifest": _MANIFEST_SCHEMA, "files": _FILES_SCHEMA},
            "required": ["manifest", "files"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "error": {"type": "string"},
                "designs": {
                    "type": "array",
                    "description": (
                        "One entry per design job: its name, resolved "
                        "motif_str, fixed atoms, ligand chains, whether "
                        "conditioning is indexed, and whether partial "
                        "diffusion is configured."
                    ),
                    "items": {"type": "object"},
                },
                "folding_states": {"type": "array", "items": {"type": "string"}},
                "evaluation_suite": {
                    "type": "string",
                    "description": (
                        "The reaction-specific metric suite, or absent. "
                        "Upstream ships kemp_eliminase, serine_esterase, "
                        "dehp_esterase, carbene_transfer and nitrene_transfer."
                    ),
                },
            },
        },
    },
    mcp_config={
        "server_name": "AlphaProtein Novo MCP Server",
        "host": "127.0.0.1",
        "port": 8059,
        "transport": "http",
    },
)
class ApNovoValidateMotifTool:
    """Parse a manifest and its motif spec. No weights, no card."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        manifest = _checked_manifest(arguments)
        if isinstance(manifest, dict) and "error" in manifest:
            return manifest
        files = _checked_files(arguments)
        if isinstance(files, dict) and "error" in files:
            return files
        if not files:
            return {
                "error": (
                    "'files' must carry the motif CIF the manifest's "
                    "'input_file' names — this server does not share a "
                    "filesystem with the caller."
                )
            }
        try:
            return _result(_worker().request(
                {
                    "op": "predict",
                    "task": "validate_motif",
                    "manifest": manifest,
                    "files": files,
                }
            ))
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


@register_mcp_tool(
    tool_type_name="apnovo_generate_designs",
    config={
        "description": (
            "Generate de novo enzyme designs with AlphaProtein Novo: a joint "
            "sequence–structure diffusion model co-generates backbones and "
            "sequences conditioned on a fixed catalytic motif and fixed "
            "ligand atoms. Returns the designs as mmCIF plus a server-side "
            "run directory that apnovo_evaluate_designs reads. This runs the "
            "generation stage only — neither LigandMPNN resequencing nor "
            "AlphaFold 3 folding is part of this provider, so a manifest's "
            "'resequence' and 'folding' sections are recorded but not acted "
            "on. Validate the motif first with apnovo_validate_motif."
        ),
        "parameter_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "manifest": _MANIFEST_SCHEMA,
                "files": _FILES_SCHEMA,
                "num_designs": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_DESIGNS_PER_REQUEST,
                    "description": (
                        "Override the manifest's per-job design count for "
                        "this request. The published campaigns run hundreds "
                        "per motif because many samples are needed to find "
                        "one that passes filters."
                    ),
                },
                "num_sampling_steps": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": (
                        "Denoising steps. Upstream's campaigns used 1000; "
                        "50 produces fast but poor designs and is for "
                        "checking a configuration, not for results."
                    ),
                },
                "seed_start": {"type": "integer", "description": "First RNG seed."},
                "return_designs": {
                    "type": "boolean",
                    "description": (
                        f"Return design mmCIF text inline, up to "
                        f"{MAX_RETURNED_DESIGNS}. The run directory always "
                        f"holds all of them."
                    ),
                },
            },
            "required": ["manifest", "files"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "error": {"type": "string"},
                "run_dir": {
                    "type": "string",
                    "description": (
                        "Server-side campaign directory. Pass it to "
                        "apnovo_evaluate_designs."
                    ),
                },
                "n_designs": {"type": "integer"},
                "designs": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Per design: name, sequence, and mmCIF text when "
                        "return_designs was set. The mmCIF carries upstream's "
                        "AP Novo Output Terms of Use notice; keep it."
                    ),
                },
                "timing": {"type": "object"},
                "peak_bytes_in_use": {
                    "type": "integer",
                    "description": (
                        "JAX's own high-water mark for this worker. On this "
                        "unified-memory card nvidia-smi reports no figure, and "
                        "a JAX budget is not comparable with a torch one."
                    ),
                },
                "weights_held_by": {"type": "string"},
                "output_terms_of_use": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AlphaProtein Novo MCP Server",
        "host": "127.0.0.1",
        "port": 8059,
        "transport": "http",
    },
)
class ApNovoGenerateDesignsTool:
    """One generation job. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        manifest = _checked_manifest(arguments)
        if isinstance(manifest, dict) and "error" in manifest:
            return manifest
        files = _checked_files(arguments)
        if isinstance(files, dict) and "error" in files:
            return files
        if not files:
            return {
                "error": (
                    "'files' must carry the motif CIF the manifest's "
                    "'input_file' names."
                )
            }

        overrides: Dict[str, Any] = {}
        for key, upper in (
            ("num_designs", MAX_DESIGNS_PER_REQUEST),
            ("num_sampling_steps", 1000),
        ):
            value = arguments.get(key)
            if value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{key}' must be an integer."}
            if not 1 <= value <= upper:
                return {"error": f"'{key}' must be between 1 and {upper}."}
            overrides[key] = value
        seed_start = arguments.get("seed_start")
        if seed_start is not None:
            if not isinstance(seed_start, int) or isinstance(seed_start, bool):
                return {"error": "'seed_start' must be an integer."}
            overrides["seed_start"] = seed_start

        return_designs = bool(arguments.get("return_designs", False))

        try:
            reply = _result(_worker().request(
                {
                    "op": "predict",
                    "task": "generate",
                    "manifest": manifest,
                    "files": files,
                    "overrides": overrides,
                    "return_designs": return_designs,
                    "max_returned": MAX_RETURNED_DESIGNS,
                }
            ))
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)

        # A generation run that exits cleanly having written nothing is a
        # failure, not an empty success: the motif may have been unsatisfiable
        # at the sampled lengths.
        if isinstance(reply, dict) and not reply.get("error"):
            if not reply.get("n_designs"):
                return {
                    "error": (
                        "AlphaProtein Novo produced no design for this "
                        "manifest. "
                        + str(reply.get("warning") or "")
                    ).strip(),
                    "run_dir": reply.get("run_dir"),
                    "timing": reply.get("timing"),
                }
        return reply


@register_mcp_tool(
    tool_type_name="apnovo_resequence_designs",
    config={
        "description": (
            "Redesign the sequences of an AlphaProtein Novo campaign's "
            "backbones with LigandMPNN, keeping the backbone and the ligand "
            "context fixed. Takes the run_dir that apnovo_generate_designs "
            "returned and writes a 02_resequence stage beside the generated "
            "one. Runs on the CPU in its own interpreter, so it does not "
            "compete with the generator for the GPU. Beyond producing an "
            "alternative sequence, this is the input to the strongest filter "
            "in the AP Novo paper: generate N sequences for one backbone and "
            "score the BACKBONE by how many of them pass your filter set "
            "(multi-resequence scoring, worth 2.5x to 5.4x hit-rate "
            "enrichment at 50% recall). Set num_sequences to 7-10 for that; "
            "the default pipeline uses 1."
        ),
        "parameter_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": (
                        "The server-side campaign directory returned by "
                        "apnovo_generate_designs."
                    ),
                },
                "num_sequences": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 32,
                    "description": (
                        "Sequences per backbone. 1 is the published default "
                        "pipeline; 7-10 is what multi-resequence backbone "
                        "scoring needs (the paper used 7 for Kemp eliminase, "
                        "pass >= 6/7 then 7/7, and 10 for serine esterase, "
                        "pass 10/10)."
                    ),
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": (
                        "Sampling temperature. The published campaigns used "
                        "0.1."
                    ),
                },
                "model_type": {
                    "type": "string",
                    "enum": ["ligand_mpnn", "protein_mpnn"],
                    "description": (
                        "LigandMPNN conditions on the ligand; ProteinMPNN "
                        "does not. For enzyme design the ligand is the point."
                    ),
                },
                "use_side_chain_context": {
                    "type": "boolean",
                    "description": (
                        "Condition on the fixed residues' side chains as well "
                        "as their backbones."
                    ),
                },
            },
            "required": ["run_dir"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "error": {"type": "string"},
                "n_designs": {"type": "integer"},
                "designs": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "Per resequenced design: name, sequence, LigandMPNN's "
                        "own overall_confidence / ligand_confidence / seq_rec, "
                        "and the path of the resequenced mmCIF."
                    ),
                },
                "device": {
                    "type": "string",
                    "description": (
                        "Always cpu on a card whose compute capability "
                        "LigandMPNN's pinned torch does not target."
                    ),
                },
                "run_dir": {"type": "string"},
                "timing": {"type": "object"},
            },
        },
    },
    mcp_config={
        "server_name": "AlphaProtein Novo MCP Server",
        "host": "127.0.0.1",
        "port": 8059,
        "transport": "http",
    },
)
class ApNovoResequenceDesignsTool:
    """LigandMPNN over a campaign. A third environment, on the CPU."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        run_dir = arguments.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir.strip():
            return {
                "error": (
                    "'run_dir' must be the campaign directory returned by "
                    "apnovo_generate_designs."
                )
            }
        payload: Dict[str, Any] = {
            "op": "predict",
            "task": "resequence",
            "run_dir": run_dir,
        }
        num = arguments.get("num_sequences")
        if num is not None:
            if not isinstance(num, int) or isinstance(num, bool):
                return {"error": "'num_sequences' must be an integer."}
            if not 1 <= num <= 32:
                return {"error": "'num_sequences' must be between 1 and 32."}
            payload["num_sequences"] = num
        temp = arguments.get("temperature")
        if temp is not None:
            if isinstance(temp, bool) or not isinstance(temp, (int, float)):
                return {"error": "'temperature' must be a number."}
            if not 0.0 <= float(temp) <= 1.0:
                return {"error": "'temperature' must be between 0.0 and 1.0."}
            payload["temperature"] = float(temp)
        model_type = arguments.get("model_type")
        if model_type is not None:
            if model_type not in ("ligand_mpnn", "protein_mpnn"):
                return {
                    "error": (
                        "'model_type' must be 'ligand_mpnn' or 'protein_mpnn'."
                    )
                }
            payload["model_type"] = model_type
        side_chain = arguments.get("use_side_chain_context")
        if side_chain is not None:
            if not isinstance(side_chain, bool):
                return {"error": "'use_side_chain_context' must be a boolean."}
            payload["use_side_chain_context"] = side_chain

        try:
            return _result(_worker().request(payload))
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


@register_mcp_tool(
    tool_type_name="apnovo_ingest_folded",
    config={
        "description": (
            "Lay externally predicted structures into a campaign as "
            "upstream's folded stage, so apnovo_evaluate_designs can score "
            "it. This provider has no folding operation — AlphaFold 3 "
            "weights carry terms separate from AP Novo's — but upstream's "
            "evaluation does not require THIS provider to have folded "
            "anything: it requires a directory shaped like run_alphafold.py "
            "output. Fold each design's states with any structure predictor "
            "that has settled its own weights question (openfold3, "
            "protenix_v1, esmfold2, chai1 and rosettafold3 are siblings on "
            "this standard), then send the mmCIF text here. Whatever "
            "confidence fields the predictor reported ride along into the "
            "metric rows; only the seed and the designed-structure filename "
            "are load-bearing."
        ),
        "parameter_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": (
                        "The server-side campaign directory returned by "
                        "apnovo_generate_designs."
                    ),
                },
                "states": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 512,
                    "description": (
                        "One entry per (design, state, seed) that was folded. "
                        "Seeds must start at 0 and be contiguous: upstream "
                        "counts up from 0 and stops at the first gap, so a "
                        "missing seed silently truncates the rest."
                    ),
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["sample_name", "state", "folded_cif"],
                        "properties": {
                            "sample_name": {
                                "type": "string",
                                "description": (
                                    "The design's name, as "
                                    "apnovo_generate_designs reported it."
                                ),
                            },
                            "state": {
                                "type": "string",
                                "description": (
                                    "The folding state's name, from the "
                                    "manifest's folding.states."
                                ),
                            },
                            "seed": {
                                "type": "integer",
                                "minimum": 0,
                                "default": 0,
                                "description": "Prediction seed index.",
                            },
                            "folded_cif": {
                                "type": "string",
                                "description": "Predicted structure as mmCIF text.",
                            },
                            "confidences": {
                                "type": "object",
                                "description": (
                                    "The predictor's own confidence record. "
                                    "Every key becomes a prefixed metric on "
                                    "the evaluation row."
                                ),
                            },
                            "designed_cif": {
                                "type": "string",
                                "description": (
                                    "Filename of the generated structure this "
                                    "prediction is scored against, as it "
                                    "appears in 01_generation. Required on "
                                    "the first state of each design; upstream "
                                    "refuses a design whose first confidence "
                                    "record does not name one."
                                ),
                            },
                        },
                    },
                },
            },
            "required": ["run_dir", "states"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "error": {"type": "string"},
                "folded_dir": {"type": "string"},
                "n_states_written": {"type": "integer"},
                "states": {"type": "array", "items": {"type": "object"}},
                "designed_cifs_missing": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Named designed structures that were not found in "
                        "01_generation; evaluation will refuse these designs."
                    ),
                },
                "seed_gaps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Designs whose seeds are not contiguous from 0, with "
                        "how far upstream will actually read."
                    ),
                },
            },
        },
    },
    mcp_config={
        "server_name": "AlphaProtein Novo MCP Server",
        "host": "127.0.0.1",
        "port": 8059,
        "transport": "http",
    },
)
class ApNovoIngestFoldedTool:
    """Write a folded stage upstream's evaluation can read."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        run_dir = arguments.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir.strip():
            return {
                "error": (
                    "'run_dir' must be the campaign directory returned by "
                    "apnovo_generate_designs."
                )
            }
        states = arguments.get("states")
        if not isinstance(states, list) or not states:
            return {
                "error": (
                    "'states' must be a non-empty list of folded states, each "
                    "naming its design, its state and its mmCIF text."
                )
            }
        try:
            return _result(_worker().request(
                {
                    "op": "predict",
                    "task": "ingest_folded",
                    "run_dir": run_dir,
                    "states": states,
                }
            ))
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


@register_mcp_tool(
    tool_type_name="apnovo_evaluate_designs",
    config={
        "description": (
            "Score an AlphaProtein Novo campaign with upstream's own metrics "
            "and return one row per design. REQUIRES A FOLDED CAMPAIGN: "
            "upstream's evaluation reads each design's folding seeds and "
            "refuses an unfolded campaign outright — it does not fall back to "
            "the metrics that need no structure prediction. This provider has "
            "no folding operation (AlphaFold 3 weights carry terms separate "
            "from AP Novo's), so the structures have to come from elsewhere: "
            "fold each design's states with any structure predictor that has "
            "settled its own weights question, send them to "
            "apnovo_ingest_folded, then call this. On a campaign with no "
            "folded stage this returns a named error saying so."
        ),
        "parameter_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": (
                        "The server-side campaign directory returned by "
                        "apnovo_generate_designs."
                    ),
                },
                "eval_suite": {
                    "type": "string",
                    "enum": [
                        "kemp_eliminase",
                        "serine_esterase",
                        "dehp_esterase",
                        "carbene_transfer",
                        "nitrene_transfer",
                    ],
                    "description": (
                        "Reaction-specific metric suite. Omit for generic "
                        "metrics only. A suite whose metrics need folded "
                        "states cannot produce them here."
                    ),
                },
            },
            "required": ["run_dir"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "error": {"type": "string"},
                "n_designs": {"type": "integer"},
                "metric_families": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "The metric families present in the rows, e.g. "
                        "['apo', 'complex', 'sampled', 'sequence'] — the "
                        "state-prefixed ones exist only for states that were "
                        "folded."
                    ),
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "One row per design.",
                },
                "summary_csv_path": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AlphaProtein Novo MCP Server",
        "host": "127.0.0.1",
        "port": 8059,
        "transport": "http",
    },
)
class ApNovoEvaluateDesignsTool:
    """Upstream's metrics over a campaign directory."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        run_dir = arguments.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir.strip():
            return {
                "error": (
                    "'run_dir' must be the campaign directory returned by "
                    "apnovo_generate_designs."
                )
            }
        suite = arguments.get("eval_suite")
        if suite is not None and not isinstance(suite, str):
            return {"error": "'eval_suite' must be a string."}

        try:
            return _result(_worker().request(
                {
                    "op": "predict",
                    "task": "evaluate",
                    "run_dir": run_dir,
                    "eval_suite": suite,
                }
            ))
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return _unavailable(exc)


if __name__ == "__main__":
    start_mcp_server()
