"""OpenDDE 1.1.1 all-atom structure prediction — MCP server.

OpenDDE (Aureka AI Research, Apache 2.0) is an AlphaFold3-class co-folding
model: it takes a complex of protein, DNA and RNA chains, ligands and ions and
returns diffusion-sampled all-atom structures, each scored with pLDDT, pTM,
ipTM, PAE and a ranking score. Its code descends from Protenix's, and so does
its input dialect (an AlphaFold-Server style job: ``proteinChain`` /
``dnaSequence`` / ``rnaSequence`` / ``ligand`` / ``ion`` entities with a
``count``). This server is the thin, CPU-only half of the provider; the model
runs in its own environment (torch 2.7.1+cu128, numpy 2.4.1 -- a stack
ToolUniverse's cannot import) and is held resident between requests.

**One request is one complex folded for one seed**: ``num_diffusion_samples``
structures (default 5), each separately scored -- rank them on
``ranking_score``.

Four things an operator needs and will not guess.

**This provider runs no MSA search, and that is a deployment decision rather
than an oversight.** `opendde pred` posts the query's sequences to an MSA web
service before it folds anything. A self-hosted provider that did the same
would make an outbound request to a third party on every caller's sequences,
so the step is simply not on this path, and OpenDDE accepts alignments only as
FILE PATHS, which a remote caller must not be able to name. Every request is
folded single-sequence, and the reply says so (`use_msa`): single-sequence
OpenDDE is a materially weaker model than MSA-fed OpenDDE.

**Templates and RNA MSA are off** and are not request options, for the same
reason: templates are fetched from PDBe on demand.

**Ligands are SMILES or `CCD_<id>`.** Upstream's third form, `FILE_<path>`,
makes the worker read an arbitrary file off the host on a remote caller's say-so
and is refused. A ligand's token count is its atom count, which only the
featuriser knows, so the worker enforces the token ceiling again after
featurisation, before the model runs.

**A fold that produces no structure comes back as a failure** carrying
upstream's words, never as a reply that looks like success: the worker asserts
the structure count.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
_PORT = 8058
MAX_CHAINS = 20
# THE CEILING AND THE BUDGET ARE THE SAME NUMBER ON PURPOSE. `[gpu]
# vram_budget_gb` is measured at MAX_TOKENS_TOTAL tokens with MAX_SAMPLES
# diffusion samples, and a bound that admits a request no declared budget covers
# is not a bound (progen2's two sane ceilings multiplied to 116.93 GiB).
#
# WHICH AXIS DRIVES THE PEAK, MEASURED: tokens, not diffusion samples. One fresh
# worker per point: 200 tokens peak at 6.85 GiB with 1 sample AND with 5; 400
# tokens at 22.53 with 1 and 22.55 with 5. The footprint is the trunk's, which
# the sample count does not touch, so MAX_SAMPLES is a time bound and not a
# memory one. Peak is steep in tokens: 3.69 / 6.85 / 22.55 GiB at 100 / 200 /
# 400 (two independent workers agree to the hundredth). 400 is the largest
# point measured, so it is the ceiling; 800 (the other folding providers') was
# not run, and at this growth would be several times the 400-token figure on a
# shared card. The worker checks the FEATURISED token count too, which is the
# only place a ligand's tokens (its atoms) are known.
MAX_TOKENS_TOTAL = 400
MAX_SAMPLES = 5
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
_MOLECULE_TYPES = ("protein", "dna", "rna", "ligand", "ion")
_CHAIN_KEY = {
    "protein": "proteinChain",
    "dna": "dnaSequence",
    "rna": "rnaSequence",
    "ligand": "ligand",
    "ion": "ion",
}
_ALPHABET = {
    "protein": set("ACDEFGHIKLMNPQRSTVWYXBZUO"),
    "dna": set("ACGTN"),
    "rna": set("ACGUN"),
}


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate_chains(chains: Any) -> List[Dict[str, Any]]:
    """Return OpenDDE's own `sequences` list, or raise ValueError naming the
    problem. Refusing a typo here costs milliseconds; refusing it inside the
    featuriser costs the caller a minute and reads as a model failure."""
    if not isinstance(chains, list) or not chains:
        raise ValueError("'chains' must be a non-empty array of chain objects.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per complex.")

    out: List[Dict[str, Any]] = []
    tokens = 0
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
        sequence = sequence.strip()

        count = chain.get("count", 1)
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 1 <= count <= 16
        ):
            raise ValueError(f"chain {i}: 'count' must be an integer 1..16.")

        body: Dict[str, Any] = {"count": count}
        if kind in _ALPHABET:
            sequence = sequence.upper()
            bad = sorted(set(sequence) - _ALPHABET[kind])
            if bad:
                raise ValueError(
                    f"chain {i}: {kind} sequence has invalid letters {bad}."
                )
            # Each polymer residue is one token; a ligand's token count depends
            # on its atoms, so only polymers are counted here. The worker counts
            # the rest after featurisation.
            tokens += len(sequence) * count
            body["sequence"] = sequence
        elif kind == "ligand":
            # Upstream takes SMILES verbatim, or a CCD code written `CCD_<id>`.
            # `FILE_<path>` is its third form and is REFUSED: it makes the worker
            # read an arbitrary file off the host's disk on a remote caller's
            # say-so, which is not a thing an MCP tool should offer.
            if sequence.startswith("FILE_"):
                raise ValueError(
                    f"chain {i}: upstream's FILE_<path> ligand form is not "
                    f"accepted by this server; give SMILES or CCD_<id>."
                )
            body["ligand"] = sequence
        else:  # ion
            body["ion"] = sequence.upper()
        out.append({_CHAIN_KEY[kind]: body})

    if tokens > MAX_TOKENS_TOTAL:
        raise ValueError(
            f"{tokens} polymer tokens exceeds this server's {MAX_TOKENS_TOTAL} "
            f"limit, which is the envelope the provider's VRAM budget was "
            f"measured at. Peak grows as N^2 in this architecture, so a larger "
            f"complex needs the budget re-measured rather than the limit raised."
        )
    return out


def _fold(
    chains: List[Dict[str, Any]],
    name: str,
    seed: int,
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One prediction on the resident worker, or a named reason why not."""
    import json
    import tempfile

    query = [{"name": name, "sequences": chains}]
    with tempfile.TemporaryDirectory(prefix="opendde-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(query),
                "out_dir": work,
                "name": name,
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        structures = [p for p in (result.get("structures") or []) if p.endswith(".cif")]
        out: Dict[str, Any] = {
            "model": "OpenDDE 1.1.1 (opendde_v1, opendde.pt)",
            "n_structures": len(structures),
            "seeds": result.get("seeds"),
            # Always returned. Five diffusion samples come back per seed and
            # ranking them on `ranking_score` is the only way to use them, so
            # dropping these would make every caller re-read a disk this
            # process just wrote -- in a temporary directory that is about to
            # be removed.
            "scores": result.get("scores"),
            "inputs": result.get("inputs"),
            "use_msa": result.get("use_msa"),
            "options_applied": result.get("options_applied"),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
            "msa_note": (
                "folded single-sequence: this provider runs no MSA search. "
                "Single-sequence OpenDDE is materially less accurate than "
                "MSA-fed OpenDDE."
            ),
        }

        # Off by default: an all-atom mmCIF of a few hundred residues is
        # megabytes and five of them is tens, which is what a transport
        # truncates -- producing a broken answer rather than a refused one.
        # The files live in a temporary directory removed when this call
        # returns, so no path is offered: a path that was true for a
        # millisecond is worse than an absent field.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; the "
                "files themselves live in a temporary directory that is "
                "removed when this call returns"
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
    tool_type_name="opendde_fold",
    config={
        "description": (
            "Predict an all-atom biomolecular structure with OpenDDE 1.1.1, "
            "Aureka's open AlphaFold3-class model. The query is a list of "
            "chains, each with a molecule_type (protein, dna, rna, ligand or "
            "ion) and a sequence -- SMILES or CCD_<id> for a ligand, the "
            "element symbol for an ion. One call folds one complex for one "
            "seed into up to 5 diffusion samples; returns per-sample "
            "confidence scores (rank on ranking_score) and timings, and the "
            "mmCIF text is opt-in. Folds single-sequence: no MSA search is "
            "performed."
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
                                    "Residue sequence; SMILES or CCD_<id> "
                                    "when molecule_type is 'ligand'; the "
                                    "element symbol when it is 'ion'."
                                ),
                                "minLength": 1,
                            },
                            "count": {
                                "type": "integer",
                                "description": (
                                    "Identical copies of this chain in the "
                                    "complex (default 1)."
                                ),
                                "default": 1,
                                "minimum": 1,
                                "maximum": 16,
                            },
                        },
                        "required": ["sequence"],
                    },
                },
                "name": {
                    "type": "string",
                    "description": (
                        "A label for this complex; it names the output files. "
                        "Defaults to 'complex'."
                    ),
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed; the same seed reproduces the prediction. "
                        "Default 101."
                    ),
                    "default": 101,
                    "minimum": 0,
                },
                "num_diffusion_samples": {
                    "type": "integer",
                    "description": (
                        "Structures to sample (upstream's default is 5, and "
                        "5 is this server's ceiling: peak memory scales with "
                        "it). Each is scored separately, so this is how to "
                        "compare conformations; rank them on `scores`."
                    ),
                    "minimum": 1,
                    "maximum": MAX_SAMPLES,
                },
                "num_diffusion_steps": {
                    "type": "integer",
                    "description": (
                        "Diffusion steps per sample (upstream's default is "
                        "200). Fewer is faster and coarser."
                    ),
                    "minimum": 1,
                    "maximum": 400,
                },
                "num_recycles": {
                    "type": "integer",
                    "description": (
                        "Pairformer recycling cycles (upstream's default is "
                        "10). Fewer is faster and less accurate."
                    ),
                    "minimum": 1,
                    "maximum": 20,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text (default false: megabytes). "
                        "The confidence scores come back either way."
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
                "inputs": {"type": "array", "items": {"type": "object"}},
                "use_msa": {"type": "boolean"},
                "msa_note": {"type": "string"},
                "options_applied": {"type": "object"},
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
        "server_name": "OpenDDE MCP Server",
        "host": "127.0.0.1",
        "port": _PORT,
        "transport": "http",
    },
)
class OpenDDEFoldTool:
    """Fold one complex. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            chains = _validate_chains(arguments.get("chains"))
        except ValueError as exc:
            return {"error": str(exc)}

        name = arguments.get("name", "complex")
        if not isinstance(name, str) or not name.strip():
            return {"error": "'name' must be a non-empty string."}
        name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name.strip())
        # Upstream reserves the job name "ERR" (any case) for its error reports.
        if name.casefold() == "err":
            name = "complex"

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        seed = arguments.get("seed", 101)
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
            return {"error": "'seed' must be an integer in [0, 2**32)."}

        options: Dict[str, Any] = {}
        for key, low, high in (
            ("num_diffusion_samples", 1, MAX_SAMPLES),
            ("num_diffusion_steps", 1, 400),
            ("num_recycles", 1, 20),
        ):
            if key not in arguments:
                continue
            value = arguments[key]
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{key}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{key}' must be between {low} and {high}."}
            options[key] = value
        try:
            return _fold(chains, name, seed, options, return_structures)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"OpenDDE's resident worker is not available ({reason}). "
                    f"Run `tu remote setup opendde` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }
        except WorkerRequestError as exc:
            # The request, not the provider: the worker composes this from
            # upstream's own error text, so flattening it to a type name would
            # throw away the only account of what went wrong.
            return {
                "error": f"OpenDDE could not fold this complex: {exc}",
                "note": (
                    "the worker is still up and the next request is unaffected."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"OpenDDE failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
