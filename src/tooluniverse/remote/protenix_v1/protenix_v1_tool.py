"""Protenix v1 all-atom structure prediction — MCP server.

Protenix 1.1.0 is ByteDance's open reproduction of AlphaFold3: it folds a
complex of chains -- protein, DNA, RNA, ligand, ion -- into an all-atom
structure and scores every diffusion sample it draws. This server is the thin,
CPU-only half of the provider; the model runs in its own environment (torch
2.13.0+cu130, triton 3.7.1, numpy 2.4.1 -- a stack ToolUniverse's cannot
import) and is held resident between requests.

Three things an operator needs and will not guess.

**This provider runs no MSA search, and that is a deployment decision rather
than an oversight.** `protenix pred` posts the query's sequences to ByteDance's
MSA web service before it folds anything. A self-hosted provider that did the
same would make an outbound request to a third party on every caller's
sequences, so the step is simply not on this path: a request either supplies
its own alignments (`unpairedMsa` / `pairedMsa` inline, or `unpairedMsaPath` /
`pairedMsaPath` on disk) or folds single-sequence. Single-sequence Protenix is a
materially weaker model than MSA-fed Protenix; the reply says which was used
(`use_msa`) so no caller has to infer it.

**Templates are off and are not a request option**, for the same reason:
upstream's template featuriser downloads mmCIF files from PDBe on demand.

**Upstream catches per-item exceptions itself**, writes the traceback to an
`ERR/` file and returns normally -- the shape that had OpenFold3 reporting
success for a fold that produced nothing. The worker drives upstream's loop
without that `except` and asserts the structure count, so a failure arrives here
as a failure, carrying upstream's own words.

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
MAX_CHAINS = 20
MAX_TOKENS_TOTAL = 800
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
# `smcp.py` caps a serialized tool result at 100,000 characters and then falls
# back to raw string truncation, so a structure larger than this does not come
# back short -- it comes back unparseable. Leave room for the rest of the reply.
MAX_TRANSPORT_CHARS = 90_000
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
_MSA_FIELDS = ("unpairedMsa", "pairedMsa", "unpairedMsaPath", "pairedMsaPath")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate_chains(chains: Any) -> List[Dict[str, Any]]:
    """Return Protenix's own `sequences` list, or raise ValueError naming the
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
            # Each polymer residue is one Protenix token; a ligand's token count
            # depends on its atoms, so only polymers are counted here and the
            # ceiling is deliberately conservative for ligand-heavy complexes.
            tokens += len(sequence) * count
            body["sequence"] = sequence
        elif kind == "ligand":
            # Upstream takes SMILES verbatim, or a CCD code written `CCD_<id>`
            # (`protenix/data/inference/json_parser.py`: 'Please change the
            # "ligand" input format to "CCD_" or "FILE_"'). `FILE_<path>` is
            # upstream's third form and is REFUSED here: it makes the worker
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

        for field in _MSA_FIELDS:
            if field in chain:
                value = chain[field]
                if not isinstance(value, str) or not value:
                    raise ValueError(
                        f"chain {i}: {field!r} must be a non-empty string."
                    )
                if kind not in ("protein", "rna"):
                    raise ValueError(
                        f"chain {i}: {field!r} applies to protein and rna chains only."
                    )
                if field.endswith("Path") and not os.path.isfile(value):
                    raise ValueError(f"chain {i}: {field} {value!r} is not a file.")
                body[field] = value

        if kind == "protein" and "sequence" not in body:
            raise ValueError(f"chain {i}: a protein chain needs 'sequence'.")
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
    keep_dir: str = "",
) -> Dict[str, Any]:
    """One prediction on the resident worker, or a named reason why not."""
    import contextlib
    import json
    import tempfile

    query = [{"name": name, "sequences": chains}]
    # A named `keep_dir` survives the call; the default temporary directory
    # does not. The difference matters because the mmCIF cannot always come
    # back through the transport -- see `structures_note` below -- so for a
    # pipeline whose next stage needs the structures, a server-side directory
    # is the only handoff that works. `apnovo_generate_designs` already uses
    # exactly this shape, returning a `run_dir` its own evaluation reads.
    keeper = (
        contextlib.nullcontext(keep_dir)
        if keep_dir
        else tempfile.TemporaryDirectory(prefix="protenix_v1-")
    )
    with keeper as work:
        if keep_dir:
            os.makedirs(work, exist_ok=True)
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
            "model": "Protenix 1.1.0 (protenix_base_default_v1.0.0)",
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
        }
        if not result.get("use_msa"):
            out["msa_note"] = (
                "folded single-sequence: this provider runs no MSA search. "
                "Supply unpairedMsa/pairedMsa (or unpairedMsaPath/pairedMsaPath) "
                "on a chain for an MSA-fed prediction, which is materially more "
                "accurate."
            )

        if keep_dir:
            # Paths, not text: the next stage of a pipeline reads these.
            out["structure_paths"] = structures
            out["out_dir"] = work

        # Off by default: an all-atom mmCIF of a few hundred residues is
        # megabytes and five of them is tens, which is what a transport
        # truncates -- producing a broken answer rather than a refused one.
        #
        # MEASURED, and it is not a hypothetical: a 131-residue monomer comes
        # back as 102,306 characters of mmCIF, and `smcp.py` caps a tool
        # result at 100,000 before falling back to RAW STRING truncation --
        # which cuts the JSON mid-string and hands the caller something that
        # does not parse. `MAX_STRUCTURE_BYTES` below is 32 MiB, so the guard
        # this comment describes misses the failure it describes by a factor
        # of 335. The transport limit, not the output limit, is the binding
        # one, and the only way past it is `out_dir`.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text, or "
                "out_dir to have the files written somewhere that survives "
                "this call. Text is capped by the transport at 100,000 "
                "characters, which one monomer of ~130 residues already "
                "exceeds; out_dir is the route for anything larger. Without "
                "either, the files live in a temporary directory that is "
                "removed when this call returns."
            )
            return out

        texts = []
        for path in structures:
            try:
                size = os.path.getsize(path)
                # The transport's 100,000-character cap binds long before the
                # 32 MiB output limit, and exceeding it corrupts the reply
                # rather than failing it. Refuse here instead, and name the
                # way through.
                if size > MAX_TRANSPORT_CHARS:
                    texts.append(
                        {
                            "name": os.path.basename(path),
                            "error": (
                                f"{size:,} bytes exceeds the {MAX_TRANSPORT_CHARS:,} "
                                f"characters a tool result can carry; pass out_dir "
                                f"to have this written to a directory instead"
                            ),
                        }
                    )
                    continue
                if size > MAX_STRUCTURE_BYTES:
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
    tool_type_name="protenix_v1_fold",
    config={
        "description": (
            "Predict an all-atom biomolecular structure with Protenix 1.1.0, "
            "ByteDance's open AlphaFold3 reproduction. The query is a list of "
            "chains, each with a molecule_type (protein, dna, rna, ligand or "
            "ion) and a sequence -- SMILES or CCD_<id> for a ligand. Returns "
            "per-sample confidence scores (rank on ranking_score) and timings; "
            "the mmCIF text itself is opt-in. No MSA search is performed: pass "
            "alignments on a chain for an MSA-fed prediction."
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
                            "unpairedMsa": {
                                "type": "string",
                                "description": (
                                    "A3M text of the unpaired MSA for this "
                                    "chain. Nothing is searched for: this is "
                                    "the only way the provider gets one."
                                ),
                            },
                            "pairedMsa": {
                                "type": "string",
                                "description": "A3M text of the paired MSA.",
                            },
                            "unpairedMsaPath": {
                                "type": "string",
                                "description": (
                                    "Path to an A3M file readable by the "
                                    "worker, instead of inline text."
                                ),
                            },
                            "pairedMsaPath": {
                                "type": "string",
                                "description": "Path to a paired A3M file.",
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
                        "Upstream's default is 101."
                    ),
                    "default": 101,
                    "minimum": 0,
                },
                "num_diffusion_samples": {
                    "type": "integer",
                    "description": (
                        "Structures to sample (upstream's default is 5). Each "
                        "is scored separately, so this is how to compare "
                        "conformations; rank them on `scores`."
                    ),
                    "minimum": 1,
                    "maximum": 10,
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
                "out_dir": {
                    "type": "string",
                    "description": (
                        "Write the predicted structures to this directory on "
                        "the server instead of a temporary one, and return "
                        "their paths. This is how to get a structure larger "
                        "than the transport can carry, and how to hand one "
                        "provider's output to another's input without the "
                        "mmCIF making a round trip through the caller."
                    ),
                    "minLength": 1,
                    "maxLength": 4096,
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
                "structure_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Server-side mmCIF paths, when out_dir was given.",
                },
                "out_dir": {
                    "type": "string",
                    "description": "The directory the structures were written to.",
                },
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
        "server_name": "Protenix v1 MCP Server",
        "host": "127.0.0.1",
        "port": 8046,
        "transport": "http",
    },
)
class ProtenixV1FoldTool:
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

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}
        out_dir = arguments.get("out_dir", "")
        if out_dir is None:
            out_dir = ""
        if not isinstance(out_dir, str):
            return {"error": "'out_dir' must be a string."}
        out_dir = out_dir.strip()
        if out_dir and not os.path.isabs(out_dir):
            return {
                "error": (
                    "'out_dir' must be an absolute path on the server: a "
                    "relative one would resolve against whatever directory "
                    "this process happens to be in."
                )
            }

        seed = arguments.get("seed", 101)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        options: Dict[str, Any] = {}
        for key, low, high in (
            ("num_diffusion_samples", 1, 10),
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
            return _fold(chains, name, seed, options, return_structures, out_dir)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"Protenix v1's resident worker is not available ({reason}). "
                    f"Run `tu remote setup protenix_v1` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The worker composes this from
            # upstream's own ERR/<sample>.txt when a fold raised, so the text
            # is upstream's; flattening it to a type name would throw away the
            # only account of what went wrong.
            return {
                "error": f"Protenix could not fold this complex: {exc}",
                "note": (
                    "the worker is still up and the next request is unaffected; "
                    "upstream writes its own traceback to ERR/<name>.txt in the "
                    "request's output directory and the text above is that file."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"Protenix v1 failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
