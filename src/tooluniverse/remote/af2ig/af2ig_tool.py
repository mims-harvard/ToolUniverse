"""af2ig -- AlphaFold 2 initial-guess re-prediction of a binder-target complex.

The MCP server half of the provider: thin, CPU-only, and importing nothing
from the model's environment. The model (AlphaFold 2 `model_1_ptm`, the
`af2_initial_guess` step of nrbennet/dl_binder_design at commit cafa3853) runs
in its own interpreter -- CPython 3.11.5, jax 0.5.3, dm-haiku 0.0.16,
tensorflow 2.21.0 -- and is held resident between requests.

WHAT THIS TOOL IS FOR, SINCE "af2ig" DOES NOT SAY IT
----------------------------------------------------
"ig" is INITIAL GUESS. This is not structure prediction from sequence. It is
the standard in-silico filter for DESIGNED PROTEIN BINDERS: you hand it a
binder-target complex as coordinates, it re-predicts that complex with
AlphaFold 2 given the complex itself as the structural initial guess and the
target's residues as a template, and it reports how confident AlphaFold is in
the interface. Bennett et al. (2023, Nat. Commun. 14:2625) showed this raises
binder design success rates by roughly an order of magnitude as a filter.

THE NUMBER TO READ IS `pae_interaction`. It is the mean predicted aligned
error, in angstroms, across the binder-target interface, symmetrised over both
off-diagonal blocks. The field's working threshold is **< 10**: below it a
design is worth ordering, above it usually is not. `plddt_binder` and
`binder_aligned_rmsd` (how far the prediction moved from the design) are the
usual companions.

THREE THINGS AN OPERATOR NEEDS AND WILL NOT GUESS
-------------------------------------------------
* **The input is a structure.** One PDB file holding the complex. CHAIN 1 IS
  THE BINDER and every chain after it is the target -- dl_binder_design's own
  convention, and getting it backwards does not fail, it silently predicts the
  wrong thing. A single-chain file is treated as a monomer and the interface
  scores come back as nulls. There is no sequence-only route: without
  coordinates there is no initial guess and no template, which would be a
  different model.
* **No alignment is built and no service is contacted.** The MSA this model
  uses is the query sequence by itself (`make_msa_features(msas=[[seq]])`,
  `max_msa_clusters = 5`), and the template is generated from the input
  coordinates. There is nothing to precompute and nowhere to send a request.
* **The answer is deterministic and the seed is not yours.** Upstream fixes
  `jax.random.PRNGKey(0)` and `random_seed=0` as literals, so one input has
  one answer, byte for byte, every time. This tool exposes no `seed` for that
  reason.

AND ONE ABOUT COST. Every distinct TOTAL RESIDUE COUNT costs one XLA
compilation of the whole AlphaFold-2 forward pass the first time the held
worker sees it -- there is no bucketing here, unlike AlphaFold 3 -- and a
compilation is minutes where a repeat is seconds. Complexes of the same length
are cheap after the first; a campaign of one design length is the case this
provider is fastest at, which is also the case binder design actually
produces.

There is no subprocess fallback. When the worker cannot start, this says so
and names the reason, separately from a request the model itself refused.
"""

import os
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# THE CEILING IS THE BUDGET'S ENVELOPE, not a round number. provider.toml
# declares [gpu] vram_budget_gb at the 800-residue rung of a measured ladder,
# so this is where that measurement stops being evidence. The check that
# matters is the one progen2 failed: a tool whose ceilings multiply into a
# request no budget covers. There is nothing to multiply here -- one request
# is one complex and peak tracks its total residue count alone -- so a single
# bound is the whole bound, and it is the same number the budget was measured
# at rather than a different one that happens to sound safe.
MAX_RESIDUES_TOTAL = 800
MAX_STRUCTURE_BYTES = 8 * 1024 * 1024
MAX_RETURN_BYTES = 8 * 1024 * 1024


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _shape_of(text: str):
    """(total residues, [per-chain lengths]) from the PDB's CA records.

    Counted the way upstream's parser counts -- ATOM records only, chain id in
    column 22, residue key in columns 23-27, residues in file order -- so this
    pre-check cannot disagree with the number that sets the compiled shape.
    HETATM is ignored here because it is ignored there: the kit's own public
    inputs are built by dropping waters, ligands and modified residues.
    """
    chains = []
    seen = set()
    for line in text.splitlines():
        if not line.startswith("ATOM") or len(line) < 27:
            continue
        if line[12:16].strip() != "CA":
            continue
        key = (line[21], line[22:27])
        if key in seen:
            continue
        seen.add(key)
        if not chains or chains[-1][0] != line[21]:
            chains.append([line[21], 0])
        chains[-1][1] += 1
    return sum(n for _, n in chains), [n for _, n in chains]


@register_mcp_tool(
    tool_type_name="af2ig_predict",
    config={
        "description": (
            "Re-predict a designed binder-target complex with AlphaFold 2 "
            "using the complex itself as the structural initial guess "
            "(nrbennet/dl_binder_design af2_initial_guess, model_1_ptm). This "
            "is the standard in-silico filter for designed binders: give it "
            "the complex as PDB text with the BINDER AS THE FIRST CHAIN and "
            "the target as the chains after it, and it returns the predicted "
            "complex and the interface confidence scores. The headline number "
            "is pae_interaction, in angstroms, where the field's working "
            "threshold is below 10. No MSA is built, no template is searched "
            "and no external service is contacted; the result is "
            "deterministic. The input must be a structure -- there is no "
            "sequence-only route."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "structure": {
                    "type": "string",
                    "description": (
                        "The complex as PDB text. CHAIN 1 IS THE BINDER and "
                        "every following chain is the target; a single-chain "
                        "file is predicted as a monomer and the interface "
                        "scores come back null. ATOM records of standard "
                        "residues are read; HETATM, waters and ligands are "
                        "ignored. Backbone-only coordinates are enough."
                    ),
                    "minLength": 1,
                },
                "num_recycle": {
                    "type": "integer",
                    "description": (
                        "AlphaFold recycling iterations (upstream's default "
                        "is 3). This is compile-time: changing it rebuilds "
                        "the held model and recompiles, which the reply "
                        "reports as config_rebuilt."
                    ),
                    "minimum": 0,
                    "maximum": 20,
                    "default": 3,
                },
                "initial_guess": {
                    "type": "boolean",
                    "description": (
                        "Use the input coordinates as the structural initial "
                        "guess (default true, and the whole point of the "
                        "method). False runs the same template-conditioned "
                        "prediction without it, which is a different and "
                        "weaker filter. Compile-time, as num_recycle is."
                    ),
                    "default": True,
                },
                "force_monomer": {
                    "type": "boolean",
                    "description": (
                        "Treat the first chain alone as the whole input and "
                        "drop the rest. Used to score a binder's own fold "
                        "independently of its target."
                    ),
                    "default": False,
                },
                "max_amide_dist": {
                    "type": "number",
                    "description": (
                        "Angstroms. A C-N amide distance above this is read "
                        "as a chain break and gets AlphaFold's +200 "
                        "residue-index offset (upstream's default 3.0)."
                    ),
                    "minimum": 0.1,
                    "maximum": 100.0,
                    "default": 3.0,
                },
                "return_structure": {
                    "type": "boolean",
                    "description": (
                        "Return the predicted complex as PDB text, with "
                        "per-residue pLDDT in the B-factor column (default "
                        "false: the scores are what a filter reads, and a "
                        "few-hundred-residue PDB is hundreds of kilobytes). "
                        "This is the ONLY way to get the structure: the "
                        "server keeps no output directory and returns no "
                        "host path."
                    ),
                    "default": False,
                },
            },
            "required": ["structure"],
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "pae_interaction": {"type": "number"},
                "scores": {"type": "object"},
                "structure_name": {"type": "string"},
                "structure": {"type": "string"},
                "structure_note": {"type": "string"},
                "sha256": {"type": "string"},
                "n_residues": {"type": "integer"},
                "n_chains": {"type": "integer"},
                "binder_length": {"type": "integer"},
                "monomer": {"type": "boolean"},
                "num_recycle": {"type": "integer"},
                "initial_guess": {"type": "boolean"},
                "config_rebuilt": {"type": "boolean"},
                "new_length": {"type": "boolean"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "seed": {"type": "string"},
                "note": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "AF2 initial-guess MCP Server",
        "host": "127.0.0.1",
        "port": 8053,
        "transport": "http",
    },
)
class AF2IGPredictTool:
    """Score one complex. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        structure = arguments.get("structure")
        if not isinstance(structure, str) or not structure.strip():
            return {
                "error": (
                    "'structure' must be the text of a PDB file holding the "
                    "complex, with the binder as the first chain."
                )
            }
        if len(structure) > MAX_STRUCTURE_BYTES:
            return {
                "error": (
                    f"'structure' is {len(structure)} bytes, over this "
                    f"server's {MAX_STRUCTURE_BYTES} limit."
                )
            }

        total, chains = _shape_of(structure)
        if total == 0:
            return {
                "error": (
                    "'structure' holds no ATOM records with a CA atom. "
                    "Upstream's parser reads ATOM lines of standard residues "
                    "only, so a file of HETATM records parses as empty."
                )
            }
        if total > MAX_RESIDUES_TOTAL:
            return {
                "error": (
                    f"{total} residues exceeds this server's "
                    f"{MAX_RESIDUES_TOTAL} limit, which is the envelope the "
                    f"provider's VRAM reserve was measured at. AlphaFold 2's "
                    f"pair track scales as N^2 and this model compiles one "
                    f"program per exact length, so a longer complex needs the "
                    f"reserve re-measured, not the limit raised."
                )
            }

        options: Dict[str, Any] = {}
        for name, low, high, kind in (
            ("num_recycle", 0, 20, int),
            ("max_amide_dist", 0.1, 100.0, float),
        ):
            if name not in arguments:
                continue
            value = arguments[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return {"error": f"'{name}' must be a number."}
            if kind is int and not isinstance(value, int):
                return {"error": f"'{name}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{name}' must be between {low} and {high}."}
            options[name] = kind(value)
        for name in ("initial_guess", "force_monomer"):
            if name not in arguments:
                continue
            if not isinstance(arguments[name], bool):
                return {"error": f"'{name}' must be a boolean."}
            options[name] = arguments[name]

        return_structure = arguments.get("return_structure", False)
        if not isinstance(return_structure, bool):
            return {"error": "'return_structure' must be a boolean."}

        import tempfile

        try:
            with tempfile.TemporaryDirectory(prefix="af2ig-") as work:
                reply = _worker().request(
                    {
                        "op": "predict",
                        "input": structure,
                        "out_dir": work,
                        "name": "query",
                        "options": options,
                    }
                )
                result = reply["result"]
                scores = result.get("scores") or {}
                out: Dict[str, Any] = {
                    "model": result.get("model"),
                    # Lifted out of `scores` because it is the one number this
                    # tool exists to produce and a caller should not have to
                    # know which of nine keys to read.
                    "pae_interaction": scores.get("pae_interaction"),
                    "scores": scores,
                    # NOT a path. The worker writes into a directory this
                    # server creates per request and removes when the request
                    # returns, so a path in the reply would be a path that no
                    # longer exists -- which is what the first draft returned,
                    # and running the documented example is how that was found.
                    # The name is provenance (it is upstream's own
                    # `<tag>_af2pred.pdb`); the bytes come back under
                    # `structure` when asked for.
                    "structure_name": (
                        os.path.basename((result.get("structures") or [""])[0]) or None
                    ),
                    "sha256": result.get("sha256"),
                    "n_residues": result.get("n_residues"),
                    "n_chains": result.get("n_chains"),
                    "binder_length": result.get("binder_length"),
                    "monomer": result.get("monomer"),
                    "num_recycle": result.get("num_recycle"),
                    "initial_guess": result.get("initial_guess"),
                    "config_rebuilt": result.get("config_rebuilt"),
                    "new_length": result.get("new_length"),
                    "timing": result.get("timing"),
                    "peak_reserved_gib": result.get("peak_reserved_gib"),
                    "weights_held_by": result.get("weights_held_by"),
                    "kit_mode": result.get("kit_mode"),
                    "seed": result.get("seed"),
                }
                if out["monomer"]:
                    out["note"] = (
                        "predicted as a monomer, so pae_interaction, "
                        "plddt_target and target_aligned_rmsd are null: there "
                        "is no interface to score. Give the target as chains "
                        "after the binder to get them."
                    )
                path = (result.get("structures") or [None])[0]
                # Read INSIDE the TemporaryDirectory: the worker wrote into it
                # and the context manager removes it on exit, so this is the
                # only moment the bytes exist.
                if return_structure and path and os.path.isfile(path):
                    if os.path.getsize(path) > MAX_RETURN_BYTES:
                        out["structure_note"] = (
                            "the predicted PDB exceeds this server's "
                            f"{MAX_RETURN_BYTES}-byte return limit, so it is "
                            "not included; the scores above are complete"
                        )
                    else:
                        with open(path, "r", encoding="utf-8") as fh:
                            out["structure"] = fh.read()
                elif not return_structure:
                    out["structure_note"] = (
                        "pass return_structure=true for the predicted PDB "
                        "(per-residue pLDDT in the B-factor column). It is the "
                        "only way to get it: this server keeps no output "
                        "directory, so there is no path to fetch it from "
                        "afterwards. The scores come back either way, and the "
                        "scores are what a design filter reads."
                    )
                return out
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"af2ig's resident worker is not available ({reason}). "
                    f"Run `tu remote setup af2ig` and read its named refusal; "
                    f"this provider has no subprocess fallback."
                ),
                "note": (
                    "two causes are specific to this provider and are named "
                    "rather than guessed: the patched dl_binder_design tree "
                    "absent (it is produced by the kit step, not installed by "
                    "pip -- AF2IG_DIR), and params/params_model_1_ptm.npz "
                    "absent from the directory AF2_PARAMS names."
                ),
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The model stays up, and this text
            # is upstream's own account of why THIS complex did not predict.
            return {
                "error": f"af2ig could not predict this complex: {exc}",
                "note": (
                    "the commonest cause is the chain order: chain 1 must be "
                    "the binder and the target must follow it. A complex "
                    "whose coordinates are missing backbone atoms, or whose "
                    "residues are non-standard, is dropped by upstream's "
                    "parser before the model sees it."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"af2ig failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
