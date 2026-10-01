"""AF3-JAX all-atom structure prediction -- MCP server.

AlphaFold 3, as released open-source by the sokrypton/alphafold3 fork, running
on the *public* OpenFold3-preview2 parameters converted into AlphaFold 3's
record layout. This server is the thin, CPU-only half of the provider; the
model runs in its own environment (CPython 3.12.1, jax 0.10.2 with the CUDA 12
plugin, a stack ToolUniverse's cannot import) and is held resident between
requests.

No DeepMind parameters are involved: the weights are Apache-2.0, from a public
bucket, and there is no licence gate and no credential anywhere in this path.

THREE THINGS AN OPERATOR NEEDS AND WILL NOT GUESS
-------------------------------------------------
* **Alignments are the caller's.** The provider runs with
  ``--norun_data_pipeline``, so nothing here builds an MSA or searches for
  templates, and nothing reaches out to a network service on a caller's
  request. Every protein chain must carry ``unpairedMsa`` and ``pairedMsa``
  (``""`` is the explicit MSA-free sentinel, not ``null``) and ``templates``.
  The ``sequences`` shortcut below fills those in as MSA-free for you; pass
  ``fold_input`` when you have real alignments.
* **Token count, not residue count, sets the cost, and the first request into a
  bucket is 20x the rest.** This fork pads every input to a bucket (multiples of
  64 here), so 35 and 60 residues cost the same, while crossing a boundary costs
  one XLA compilation plus one tokamax autotune pass. Measured on an NVIDIA
  GB10: 170.5 s for the first 35-residue request of a worker, then 8.3, 7.0,
  7.0; 258.6 s for the first 100-residue request, then 13-15 s. That is the
  model compiling and autotuning, not a stall, and a worker restart pays it
  again because nothing persists the autotune.
* **``num_recycles`` and ``num_diffusion_samples`` are compile-time.** They are
  baked into the model config, so changing either rebuilds the held model and
  recompiles. The reply says ``config_rebuilt`` when that happened.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason -- separately from a request that the model itself refused,
because flattening the two into "re-run setup" throws away the only account of
what went wrong.
"""

import json
import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CHAINS = 16
# Where this provider's VRAM reserve was derived: the 832-token bucket, which
# 800 polymer residues pads into on the kit's 64-multiple padding row. A longer
# request needs the reserve re-measured rather than this limit raised.
MAX_RESIDUES_TOTAL = 800
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
_MOLECULE_TYPES = ("protein", "dna", "rna", "ligand")
_ALPHABET = {
    "protein": set("ACDEFGHIKLMNPQRSTVWYXBZUO"),
    "dna": set("ACGTN"),
    "rna": set("ACGUN"),
}
_AF3_KEY = {"protein": "protein", "dna": "dna", "rna": "rna", "ligand": "ligand"}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _chain_ids(used, given, index):
    """One chain's labels, registering them so the next auto-label is free.

    The auto-label must skip what is already taken and must itself be taken
    afterwards. Both halves were wrong in the first draft and the fork caught
    it: a first chain given `chain_ids = ["A", "B"]` followed by a ligand with
    none produced a second "B", and `Input.__post_init__` refused the whole
    query with "Input JSON contains sequences with duplicate IDs." -- a
    confusing refusal for a caller who supplied one explicit list and nothing
    else.
    """
    if given is None:
        for code in range(ord("A"), ord("Z") + 1):
            label = chr(code)
            if label not in used:
                used.add(label)
                return [label]
        raise ValueError(
            f"chain {index}: no single-letter chain id is free; give "
            f"'chain_ids' explicitly."
        )
    if not isinstance(given, list) or not all(isinstance(c, str) and c for c in given):
        raise ValueError(f"chain {index}: 'chain_ids' must be an array of strings.")
    for c in given:
        if c in used:
            raise ValueError(f"chain id {c!r} is used twice.")
        used.add(c)
    return given


def _fold_input_from_chains(chains: Any, seed: int) -> Dict[str, Any]:
    """An AlphaFold 3 fold-input dict from the simple `sequences` form.

    Every protein and RNA chain is given the MSA-free sentinel the fork
    documents (``""`` for both MSA fields, ``[]`` for templates). Without them
    featurisation raises "Protein chain 1 is missing unpaired MSA.", which is
    the single most likely way to get a confusing failure out of this provider.
    """
    if not isinstance(chains, list) or not chains:
        raise ValueError("'sequences' must be a non-empty array of chain objects.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per query.")

    sequences: List[Dict[str, Any]] = []
    total = 0
    used: set = set()
    for i, chain in enumerate(chains):
        if not isinstance(chain, dict):
            raise ValueError(f"chain {i} must be an object.")
        kind = chain.get("molecule_type", "protein")
        if kind not in _MOLECULE_TYPES:
            raise ValueError(
                f"chain {i}: 'molecule_type' must be one of {list(_MOLECULE_TYPES)}."
            )
        sequence = chain.get("sequence")
        if not isinstance(sequence, str) or not sequence.strip():
            raise ValueError(f"chain {i}: 'sequence' must be a non-empty string.")
        sequence = sequence.strip().upper()
        if kind in _ALPHABET:
            bad = sorted(set(sequence) - _ALPHABET[kind])
            if bad:
                raise ValueError(
                    f"chain {i}: {kind} sequence has invalid letters {bad}."
                )
            total += len(sequence)

        ids = _chain_ids(used, chain.get("chain_ids"), len(sequences))
        entry: Dict[str, Any] = {"id": ids if len(ids) > 1 else ids[0]}
        if kind == "ligand":
            entry["smiles"] = sequence
        else:
            entry["sequence"] = sequence
        if kind == "protein":
            entry["modifications"] = []
            entry["templates"] = []
            entry["unpairedMsa"] = f">query\n{sequence}\n"
            entry["pairedMsa"] = ""
        elif kind == "rna":
            entry["modifications"] = []
            entry["unpairedMsa"] = f">query\n{sequence}\n"
        sequences.append({_AF3_KEY[kind]: entry})

    if total > MAX_RESIDUES_TOTAL:
        raise ValueError(
            f"{total} polymer residues exceeds this server's "
            f"{MAX_RESIDUES_TOTAL} limit, which is the envelope the provider's "
            f"VRAM reserve was derived at (the 832-token bucket). The pair "
            f"track scales as N^2 and this fork pads to the next bucket, so a "
            f"longer request needs the reserve re-measured, not the limit "
            f"raised."
        )
    return {
        "name": "query",
        "dialect": "alphafold3",
        "version": 2,
        "modelSeeds": [seed],
        "sequences": sequences,
    }


def _predict(
    fold_input: Dict[str, Any],
    seed: int,
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One prediction on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="af3-jax-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(fold_input),
                "out_dir": work,
                "name": fold_input.get("name", "query"),
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        structures = [p for p in (result.get("structures") or []) if p.endswith(".cif")]
        out: Dict[str, Any] = {
            "model": result.get("model", "AlphaFold 3 (JAX)"),
            "n_structures": len(structures),
            "seeds": result.get("seeds"),
            # With five diffusion samples the one thing a caller must do is
            # rank them; these are upstream's own confidence terms, sorted
            # best-first by the fork's ranking score.
            "scores": result.get("scores"),
            "best": result.get("best"),
            "num_recycles": result.get("num_recycles"),
            "num_diffusion_samples": result.get("num_diffusion_samples"),
            "config_rebuilt": result.get("config_rebuilt"),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }

        # Off by default: an all-atom mmCIF of a few hundred residues is
        # megabytes, and five samples is five of them -- a reply that large is
        # what a transport truncates, producing a broken answer rather than a
        # refused one.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; the "
                "confidence scores come back either way"
            )
            return out

        texts = []
        for path in structures:
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
                    texts.append({"name": os.path.basename(path), "cif": f.read()})
            except (OSError, UnicodeError) as exc:
                texts.append(
                    {"name": os.path.basename(path), "error": type(exc).__name__}
                )
        out["structures"] = texts
        return out


@register_mcp_tool(
    tool_type_name="af3_jax_predict",
    config={
        "description": (
            "Predict an all-atom biomolecular structure with AlphaFold 3 (the "
            "open JAX fork) on public OpenFold3-preview2 weights. Give either "
            "'sequences' -- a simple list of chains, which is run MSA-free -- "
            "or 'fold_input', a complete AlphaFold 3 fold-input JSON carrying "
            "your own MSAs and templates. No alignment is built here and no "
            "external service is contacted. Returns per-sample confidence "
            "scores ranked best-first; the mmCIF text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequences": {
                    "type": "array",
                    "description": (
                        "The chains of one complex, run MSA-free. Mutually "
                        "exclusive with 'fold_input'."
                    ),
                    "minItems": 1,
                    "maxItems": MAX_CHAINS,
                    "items": {
                        "type": "object",
                        "properties": {
                            "molecule_type": {
                                "type": "string",
                                "enum": list(_MOLECULE_TYPES),
                                "default": "protein",
                            },
                            "sequence": {
                                "type": "string",
                                "description": (
                                    "Residue sequence, or SMILES when "
                                    "molecule_type is 'ligand'."
                                ),
                                "minLength": 1,
                            },
                            "chain_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Chain labels; defaults to A, B, C... "
                                    "Give several to place identical copies."
                                ),
                            },
                        },
                        "required": ["sequence"],
                    },
                },
                "fold_input": {
                    "type": "object",
                    "description": (
                        "A complete AlphaFold 3 fold-input JSON object "
                        "(dialect 'alphafold3'). Use this when you have real "
                        "MSAs or templates: every protein chain needs "
                        "'unpairedMsa', 'pairedMsa' and 'templates', where an "
                        "empty string means MSA-free and null means 'the data "
                        "pipeline will fill this', which this provider does "
                        "not run."
                    ),
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed; replaces 'modelSeeds' in a supplied "
                        "fold_input. The same seed reproduces the prediction."
                    ),
                    "default": 1,
                    "minimum": 0,
                },
                "num_diffusion_samples": {
                    "type": "integer",
                    "description": (
                        "Structures to sample per seed (upstream's default is "
                        "5). Each is scored separately, so this is how to "
                        "compare conformations. Changing it recompiles the "
                        "held model."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
                "num_recycles": {
                    "type": "integer",
                    "description": (
                        "Trunk recycling iterations (upstream's default is "
                        "10). Fewer is faster and less accurate. Changing it "
                        "recompiles the held model."
                    ),
                    "minimum": 1,
                    "maximum": 20,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text (default false: megabytes per "
                        "sample). The confidence scores come back either way."
                    ),
                    "default": False,
                },
            },
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_structures": {"type": "integer"},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seeds": {"type": "array", "items": {"type": "integer"}},
                "scores": {"type": "array", "items": {"type": "object"}},
                "best": {"type": "string"},
                "num_recycles": {"type": "integer"},
                "num_diffusion_samples": {"type": "integer"},
                "config_rebuilt": {"type": "boolean"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AF3-JAX MCP Server",
        "host": "127.0.0.1",
        "port": 8045,
        "transport": "http",
    },
)
class AF3JaxPredictTool:
    """Fold one query. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        supplied = arguments.get("fold_input")
        sequences = arguments.get("sequences")
        if (supplied is None) == (sequences is None):
            return {
                "error": (
                    "give exactly one of 'sequences' (run MSA-free) or "
                    "'fold_input' (a complete AlphaFold 3 fold-input JSON)."
                )
            }

        seed = arguments.get("seed", 1)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        if supplied is not None:
            if not isinstance(supplied, dict):
                return {"error": "'fold_input' must be an object."}
            fold_input = dict(supplied)
            fold_input.setdefault("dialect", "alphafold3")
            fold_input.setdefault("version", 2)
            fold_input.setdefault("name", "query")
            fold_input["modelSeeds"] = [seed]
        else:
            try:
                fold_input = _fold_input_from_chains(sequences, seed)
            except ValueError as exc:
                return {"error": str(exc)}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        options: Dict[str, Any] = {}
        for name, low, high in (
            ("num_diffusion_samples", 1, 10),
            ("num_recycles", 1, 20),
        ):
            if name not in arguments:
                continue
            value = arguments[name]
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{name}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{name}' must be between {low} and {high}."}
            options[name] = value

        try:
            return _predict(fold_input, seed, options, return_structures)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"AF3-JAX's resident worker is not available ({reason}). "
                    f"Run `tu remote setup af3_jax` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                ),
                "note": (
                    "two causes are specific to this provider and are named "
                    "rather than guessed: AF3_JAX_REPO unset (the fork "
                    "checkout, which is not the installed package), and the "
                    "converted parameter file absent from "
                    "<AF3_JAX_PARAMS_ROOT>/p2/."
                ),
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The model stays up; this text is
            # upstream's own account of why THIS input did not fold, and
            # flattening it into the message above would discard it.
            return {
                "error": f"AF3-JAX could not fold this query: {exc}",
                "note": (
                    "the provider runs with the data pipeline off, so a "
                    "protein chain without 'unpairedMsa', 'pairedMsa' and "
                    "'templates' is refused by featurisation rather than "
                    "filled in. An empty string is the MSA-free sentinel; "
                    "null is not."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"AF3-JAX failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
