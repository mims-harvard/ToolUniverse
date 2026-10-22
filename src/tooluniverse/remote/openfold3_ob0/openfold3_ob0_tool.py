"""OpenFold3 0.5.0 (OpenBind-0) all-atom structure prediction — MCP server.

OpenFold3 folds a query of chains -- protein, DNA, RNA, ligand -- into an
all-atom structure. This server is the thin, CPU-only half of the provider;
the model runs in its own environment (torch 2.10 + cu128, a stack this one
cannot import) and is held resident between requests.

**Which OpenFold3 this is.** The parameters are OpenBind-0
(`of3-ob-2025-06-30-174k.pt`) and the upstream is 0.5.0. The `openfold3`
provider on port 8039 is 0.4.1 with the `of3-p2-155k.pt` preview-2 parameters.
The two are not configurations of each other: upstream version-gates every
checkpoint (`version_compatibility`), 0.5.0 refuses the preview checkpoints as
legacy, and both releases are the same PyPI distribution name, so one
interpreter holds one of them. Two providers, two environments, two ports.

Two things an operator needs and will not guess:

* **Tracebacks are not in the request's output directory.** Upstream binds
  `log_dir` to the lightning module at construction, so a resident worker's
  failures all land in its BIRTH directory,
  `/tmp/openfold3_ob0-resident-*/logs/predict_err_rank0.log`.
* **Upstream catches per-query exceptions itself**, counts the query failed in
  a `summary.txt`, and returns normally. A fold that produced nothing is
  therefore not an exception in the ordinary sense; the worker reconstructs the
  reason from that summary plus its own slice of the traceback file and raises
  with it, and this server passes that text through rather than flattening it.

There is no subprocess fallback. When the worker cannot start, this says so
and names the reason.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
_PORT = 8052
MAX_CHAINS = 16
# The ceiling and the budget are checked against each other, not only each
# against sense. `[gpu] vram_budget_gb` is measured at this exact number of
# polymer residues, and peak grows roughly as N^2 here, so admitting a longer
# chain would admit a request no declared budget covers -- which is what
# progen2's two independently sane ceilings did at their product.
MAX_RESIDUES_TOTAL = 800
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
_MOLECULE_TYPES = ("protein", "dna", "rna", "ligand")
_ALPHABET = {
    "protein": set("ACDEFGHIKLMNPQRSTVWYXBZUO"),
    "dna": set("ACGTN"),
    "rna": set("ACGUN"),
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate_chains(chains: Any) -> List[Dict[str, Any]]:
    """Return the worker's chain list, or raise ValueError naming the problem."""
    if not isinstance(chains, list) or not chains:
        raise ValueError("'chains' must be a non-empty array of chain objects.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per query.")

    out: List[Dict[str, Any]] = []
    total = 0
    used_ids = set()
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

        # A ligand's "sequence" is SMILES, which has its own alphabet; the
        # polymer alphabets are checked here so a typo is refused by name
        # rather than becoming an unknown residue three minutes into a fold.
        if kind in _ALPHABET:
            bad = sorted(set(sequence) - _ALPHABET[kind])
            if bad:
                raise ValueError(
                    f"chain {i}: {kind} sequence has invalid letters {bad}."
                )
            total += len(sequence)

        ids = chain.get("chain_ids")
        if ids is None:
            ids = [chr(ord("A") + len(out))]
        if not isinstance(ids, list) or not all(isinstance(c, str) and c for c in ids):
            raise ValueError(f"chain {i}: 'chain_ids' must be an array of strings.")
        for c in ids:
            if c in used_ids:
                raise ValueError(f"chain id {c!r} is used twice.")
            used_ids.add(c)

        out.append({"molecule_type": kind, "chain_ids": ids, "sequence": sequence})

    if total > MAX_RESIDUES_TOTAL:
        raise ValueError(
            f"{total} polymer residues exceeds this server's {MAX_RESIDUES_TOTAL} "
            f"limit, which is the envelope the provider's VRAM budget was "
            f"measured at. Peak grows as N^2 here, so a longer chain needs the "
            f"budget re-measured, not just a larger limit."
        )
    return out


def _fold(
    chains: List[Dict[str, Any]],
    seed: int,
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import json
    import tempfile

    query = {"queries": {"query": {"chains": chains}}}
    with tempfile.TemporaryDirectory(prefix="openfold3_ob0-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(query),
                "out_dir": work,
                "name": "fold",
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        structures = [
            p for p in (result.get("structures") or []) if p.endswith((".cif", ".pdb"))
        ]
        out: Dict[str, Any] = {
            "model": "OpenFold3 0.5.0 (OpenBind-0)",
            "n_structures": len(structures),
            "seeds": result.get("seeds"),
            # The confidence JSONs upstream writes beside each structure. With
            # five diffusion samples the one thing a caller must do is rank
            # them, and avg_plddt is how.
            "scores": result.get("scores"),
            # Named when upstream's per-residue record is too large to return.
            # `<sample>_confidences.json` carries the full N x N PDE matrix and
            # measures 61 KB at 35 residues and 29 MB at 800, five of them per
            # request, so the worker caps it at 64 KiB and says which files it
            # left on disk. The ~270-byte
            # `<sample>_confidences_aggregated.json` -- avg_plddt, ptm, iptm,
            # sample_ranking_score, has_clash -- always comes back, and it is
            # what ranking the samples actually needs.
            "scores_omitted": result.get("scores_omitted"),
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }

        # Off by default: an all-atom mmCIF of a few hundred residues is
        # megabytes, and a reply that large is what a transport truncates --
        # producing a broken answer rather than a refused one.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text"
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
    tool_type_name="openfold3_ob0_fold",
    config={
        "description": (
            "Predict an all-atom biomolecular structure with OpenFold3 0.5.0 "
            "and the OpenBind-0 parameters. The query is a list of chains, "
            "each with a molecule_type (protein, dna, rna or ligand) and a "
            "sequence -- SMILES for a ligand. Returns the structure file "
            "paths, the per-sample confidence scores and timings; the mmCIF "
            "text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "chains": {
                    "type": "array",
                    "description": "The chains of one complex.",
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
                "seed": {
                    "type": "integer",
                    "description": "Random seed; the same seed reproduces the fold.",
                    "default": 0,
                    "minimum": 0,
                },
                "num_diffusion_samples": {
                    "type": "integer",
                    "description": (
                        "Structures to sample per seed (upstream's default is "
                        "5). Each is scored separately, so this is how to "
                        "compare conformations; rank them on `scores`."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
                "num_model_seeds": {
                    "type": "integer",
                    "description": (
                        "How many model seeds to run (default 1). Total "
                        "structures is this times num_diffusion_samples."
                    ),
                    "minimum": 1,
                    "maximum": 5,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text (default false: megabytes). "
                        "The per-sample ranking scores come back either way; "
                        "the full per-residue confidence record is returned "
                        "only when it is under 64 KiB, and `scores_omitted` "
                        "names it otherwise."
                    ),
                    "default": False,
                },
            },
            "required": ["chains"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "n_structures": {"type": "integer"},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seeds": {"type": "array", "items": {"type": "integer"}},
                "scores": {"type": "object"},
                "scores_omitted": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "OpenFold3 OpenBind-0 MCP Server",
        "host": "127.0.0.1",
        "port": _PORT,
        "transport": "http",
    },
)
class OpenFold3OB0FoldTool:
    """Fold one query. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            chains = _validate_chains(arguments.get("chains"))
        except ValueError as exc:
            return {"error": str(exc)}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        # The worker takes four options. Two are compute knobs and are the
        # caller's; `use_msa_server` and `use_templates` are not exposed here
        # because they make the provider reach out to an external service, or
        # read template files it has none of, on somebody else's request --
        # a deployment decision rather than a per-call parameter.
        options: Dict[str, Any] = {}
        for name, low, high in (
            ("num_diffusion_samples", 1, 10),
            ("num_model_seeds", 1, 5),
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
            return _fold(chains, seed, options, return_structures)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"OpenFold3 (OpenBind-0)'s resident worker is not available "
                    f"({reason}). Run `tu remote setup openfold3_ob0` and read its "
                    f"named refusal; this provider has no subprocess fallback."
                )
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The worker composes this text from
            # upstream's own summary.txt plus its slice of the traceback file
            # -- flattening it to a type name, and telling the caller to re-run
            # setup, throws away the only account of what went wrong.
            return {
                "error": f"OpenFold3 (OpenBind-0) could not fold this query: {exc}",
                "note": (
                    "upstream catches per-query exceptions itself; the text "
                    "above is its own. The full traceback is in the worker's "
                    "birth directory, /tmp/openfold3_ob0-resident-*/logs/"
                    "predict_err_rank0.log, not in this request's output."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {
                "error": f"OpenFold3 (OpenBind-0) failed: {type(exc).__name__}: {exc}"
            }


if __name__ == "__main__":
    start_mcp_server()
