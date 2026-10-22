"""ColabFold structure prediction from a precomputed MSA -- MCP server.

Stock ColabFold 1.6.1 (`colabfold_batch`, alphafold-colabfold 2.3.13) on the
public AlphaFold2-Multimer v3 parameters (DeepMind's 2022-12-06 release,
CC BY 4.0), held resident between requests. This server is the thin, CPU-only
half of the provider; the model runs in its own environment (CPython 3.11,
jax 0.5.3 with the CUDA 12 plugin, a stack ToolUniverse's cannot import).

THREE THINGS AN OPERATOR NEEDS AND WILL NOT GUESS
-------------------------------------------------
* **The alignment is the caller's, and no MMseqs2 server is contacted.**
  ColabFold's usual route is a remote MMseqs2 API. This provider never reaches
  it: upstream takes that branch only when a query arrives WITHOUT an a3m, and
  every request here arrives with one. Pass ``a3m`` when you have a real
  alignment; pass ``sequences`` and this server writes an MSA-FREE a3m for you,
  in ColabFold's own complex dialect. An MSA-free prediction is a real
  prediction and a weak one -- the kit's own README says pLDDT near 35 is the
  expected result for its single-sequence example.
* **Every distinct total length costs one XLA compilation, about two minutes,
  and the held worker pays it once.** ColabFold pads only its monomer path and
  this provider runs the multimer parameters, so there are no buckets: 150
  residues and 151 residues are two compilations. Alignment DEPTH is free
  (upstream pads the MSA axis to 508 / 2048 rows whatever you send). Measured on
  an NVIDIA GB10: the first request of a length is minutes, a repeat of it is
  seconds.
* **Templates and amber relaxation are refused by name, not silently dropped.**
  Upstream's only template route for an a3m input asks the MMseqs2 server for
  its hits, and relaxation runs OpenMM in a forked child, which a resident
  worker that has already run host-tensor work must not allow.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason -- separately from a request the model itself refused, because
flattening the two into "re-run setup" throws away the only account of what
went wrong.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_resident.supervisor import (
    WorkerRequestError,
    WorkerStartError,
)

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CHAINS = 16
# Where this provider's VRAM reserve was measured: the 400-residue rung of the
# ladder in provider.toml. The pair track scales as N^2 and this path does not
# pad, so a longer request needs the reserve re-measured rather than this limit
# raised. It is also checked against the budget rather than only against
# MAX_CHAINS: 16 chains of 25 residues is 400 residues, which is the same
# envelope, so the two ceilings cannot multiply into a request no budget covers.
MAX_RESIDUES_TOTAL = 400
MAX_A3M_BYTES = 32 * 1024 * 1024
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
_PROTEIN_LETTERS = set("ACDEFGHIKLMNPQRSTVWYXBZUO")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _a3m_from_sequences(chains: Any) -> str:
    """ColabFold's own complex a3m dialect for an MSA-FREE query.

    THE SEQUENCE AND ITS INLINE ALIGNMENT ARE WRITTEN TOGETHER, which is the one
    thing a hand-edited a3m gets wrong: the header's lengths, the concatenated
    query on line 3 and every per-chain row's dash padding all encode the same
    lengths, and an alignment row that does not match its own query is fed to the
    model as an alignment. Built from one list of chains so they cannot disagree.

    The shape is exactly what `colabfold_batch` writes beside its own results and
    what the kit's `tests/inputs/1BRS_AD.a3m` is in:

        #<len1>,<len2>\\t<card1>,<card2>      aligned lengths, copies per chain
        >101\\t102                            the paired header
        <chain1><chain2>                      the concatenated query
        >101                                  chain 1, padded to the full width
        <chain1>------------
        >102                                  chain 2, likewise
        ------------<chain2>

    `unserialize_msa` reads the first row (amino acids in two segments) as the
    PAIRED MSA and each later row (amino acids in one segment) as that chain's
    UNPAIRED MSA, which is why the padded rows are not decoration.
    """
    if not isinstance(chains, list) or not chains:
        raise ValueError("'sequences' must be a non-empty array of chain objects.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per query.")

    sequences: List[str] = []
    cardinality: List[int] = []
    for i, chain in enumerate(chains):
        if isinstance(chain, str):
            chain = {"sequence": chain}
        if not isinstance(chain, dict):
            raise ValueError(f"chain {i} must be an object or a string.")
        sequence = chain.get("sequence")
        if not isinstance(sequence, str) or not sequence.strip():
            raise ValueError(f"chain {i}: 'sequence' must be a non-empty string.")
        sequence = "".join(sequence.split()).upper()
        bad = sorted(set(sequence) - _PROTEIN_LETTERS)
        if bad:
            raise ValueError(
                f"chain {i}: protein sequence has invalid letters {bad}. This "
                f"provider runs the AlphaFold2-Multimer parameters, which are "
                f"protein-only -- there is no ligand, DNA or RNA entity here."
            )
        copies = chain.get("copies", 1)
        if not isinstance(copies, int) or isinstance(copies, bool) or not 1 <= copies <= MAX_CHAINS:
            raise ValueError(f"chain {i}: 'copies' must be an integer between 1 and {MAX_CHAINS}.")
        sequences.append(sequence)
        cardinality.append(copies)

    if sum(cardinality) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per query, copies included.")
    # THE ALIGNMENT'S WIDTH IS THE UNIQUE CHAINS' LENGTHS SUMMED, NOT THE
    # COMPLEX'S RESIDUE COUNT, and getting that backwards is the one way to
    # write a syntactically perfect a3m that means something else.
    # `unserialize_msa` slices line 3 by the header's lengths -- one slice per
    # UNIQUE chain -- and `_split_by_aln` cuts every later row into exactly that
    # many segments of exactly those aligned widths. The copies are expanded
    # later, by `generate_input_feature`, from the cardinality field. Checked
    # against the kit's own `tests/inputs/1A3N_hemoglobin.a3m`: header
    # `#141,146<TAB>2,2`, a four-chain 574-residue complex, every line 287
    # columns wide.
    total = sum(len(s) for s in sequences)
    residues = sum(len(s) * n for s, n in zip(sequences, cardinality))
    if residues > MAX_RESIDUES_TOTAL:
        raise ValueError(
            f"{residues} residues exceeds this server's {MAX_RESIDUES_TOTAL} limit, "
            f"which is the envelope the provider's VRAM reserve was measured at "
            f"(the 400-residue rung). The pair track scales as N^2 and this path "
            f"does not pad, so a longer request needs the reserve re-measured, "
            f"not the limit raised."
        )

    header = (
        "#"
        + ",".join(str(len(s)) for s in sequences)
        + "\t"
        + ",".join(str(n) for n in cardinality)
    )
    labels = [str(101 + i) for i in range(len(sequences))]
    lines = [header, ">" + "\t".join(labels), "".join(sequences)]
    # One unpaired row per UNIQUE chain, placed at that chain's offset in the
    # concatenated query. Upstream keys the unpaired MSAs by unique sequence, so
    # the copies share one row, which is also what colabfold_batch writes.
    offset = 0
    offsets = []
    for s in sequences:
        offsets.append(offset)
        offset += len(s)
    for label, s, start in zip(labels, sequences, offsets):
        lines.append(">" + label)
        lines.append("-" * start + s + "-" * (total - start - len(s)))
    return "\n".join(lines) + "\n"


def _a3m_total_residues(text: str) -> int:
    """The query length an a3m declares, read the way upstream reads it."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("'a3m' is empty.")
    if lines[0].startswith("#"):
        fields = lines[0][1:].split("\t")
        if len(fields) != 2:
            raise ValueError(
                "an a3m whose first line starts with '#' must carry ColabFold's "
                "two tab-separated fields -- '#<len1>,<len2>\\t<card1>,<card2>' "
                "-- the aligned length of each unique chain and how many copies "
                "of it the complex has."
            )
        try:
            lengths = [int(x) for x in fields[0].split(",")]
            copies = [int(x) for x in fields[1].split(",")]
        except ValueError as exc:
            raise ValueError(f"the a3m header is not two integer lists: {exc}") from exc
        if len(lengths) != len(copies):
            raise ValueError(
                "the a3m header's two lists must be the same length: one aligned "
                "length and one copy count per unique chain."
            )
        if sum(copies) > MAX_CHAINS:
            raise ValueError(f"at most {MAX_CHAINS} chains per query, copies included.")
        return sum(n * c for n, c in zip(lengths, copies))
    for ln in lines:
        if not ln.startswith(">"):
            return len([c for c in ln if not c.islower()])
    raise ValueError("the a3m holds no sequence line.")


def _predict(
    a3m: str,
    name: str,
    seed: int,
    options: Dict[str, Any],
    return_structures: bool,
) -> Dict[str, Any]:
    """One prediction on the resident worker, or a named reason why not."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="colabfold-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": a3m,
                "out_dir": work,
                "name": name,
                "seed": seed,
                "options": options,
            }
        )
        result = reply["result"]
        structures = [
            p for p in (result.get("structures") or []) if str(p).endswith(".pdb")
        ]
        out: Dict[str, Any] = {
            "model": result.get("model", "ColabFold / AlphaFold2-Multimer v3"),
            "model_type": result.get("model_type"),
            "n_structures": len(structures),
            # Ranked best-first by upstream's own metric, which for a complex is
            # 0.8*ipTM + 0.2*pTM and for one chain is mean pLDDT. With five
            # models the one thing a caller must do is rank them.
            "scores": result.get("scores"),
            "best": result.get("best"),
            "query_length": result.get("query_length"),
            "chains": result.get("chains"),
            "msa_rows": result.get("msa_rows"),
            "msa_source": result.get("msa_source"),
            "num_models": result.get("num_models"),
            "num_recycles": result.get("num_recycles"),
            "engine_rebuilt": result.get("engine_rebuilt"),
            "timing": result.get("timing"),
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }

        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the PDB text; the "
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
                    texts.append({"name": os.path.basename(path), "pdb": f.read()})
            except (OSError, UnicodeError) as exc:
                texts.append(
                    {"name": os.path.basename(path), "error": type(exc).__name__}
                )
        out["structures"] = texts
        return out


@register_mcp_tool(
    tool_type_name="colabfold_predict",
    config={
        "description": (
            "Predict a protein (or protein-complex) structure with ColabFold "
            "1.6.1 on the public AlphaFold2-Multimer v3 parameters, FROM A "
            "PRECOMPUTED ALIGNMENT. Give 'a3m' -- the text of an a3m, either a "
            "plain one for a single chain or ColabFold's complex dialect "
            "('#<len1>,<len2>\\t<card1>,<card2>' on the first line) -- or "
            "'sequences', a list of chains which is run MSA-FREE. No alignment "
            "is built here, no MMseqs2 server is contacted, and templates are "
            "not available. Returns per-model confidence scores ranked "
            "best-first; the PDB text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "a3m": {
                    "type": "string",
                    "description": (
                        "The text of an a3m carrying your own alignment. A plain "
                        "a3m is one chain and the whole file is its unpaired MSA. "
                        "A first line of '#<len1>,<len2>\\t<card1>,<card2>' is "
                        "ColabFold's complex dialect: the aligned length of each "
                        "unique chain and how many copies of it, with the "
                        "concatenated query on line 3 and each later row split by "
                        "aligned columns into paired and unpaired halves. "
                        "Mutually exclusive with 'sequences'."
                    ),
                },
                "sequences": {
                    "type": "array",
                    "description": (
                        "The chains of one complex, run MSA-FREE: this server "
                        "writes the a3m for you. Mutually exclusive with 'a3m'. "
                        "An MSA-free AlphaFold2 prediction is markedly less "
                        "accurate -- pLDDT near 35 is normal for a single "
                        "sequence."
                    ),
                    "minItems": 1,
                    "maxItems": MAX_CHAINS,
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {
                                "type": "string",
                                "description": "One-letter protein sequence.",
                                "minLength": 1,
                            },
                            "copies": {
                                "type": "integer",
                                "description": (
                                    "How many identical copies of this chain the "
                                    "complex has (a homo-oligomer)."
                                ),
                                "default": 1,
                                "minimum": 1,
                                "maximum": MAX_CHAINS,
                            },
                        },
                        "required": ["sequence"],
                    },
                },
                "name": {
                    "type": "string",
                    "description": "A job name; it prefixes the output files.",
                    "default": "query",
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed (upstream's --random-seed). The same seed "
                        "reproduces the prediction."
                    ),
                    "default": 0,
                    "minimum": 0,
                },
                "num_models": {
                    "type": "integer",
                    "description": (
                        "How many of the five parameter sets to run (upstream's "
                        "default is 5). Each is scored separately and they are "
                        "ranked, which is the point of running more than one. "
                        "Changing this rebuilds the held model."
                    ),
                    "minimum": 1,
                    "maximum": 5,
                },
                "num_recycles": {
                    "type": "integer",
                    "description": (
                        "Trunk recycling iterations. Upstream's default is the "
                        "model config's 20 with early stop at tolerance 0.5; "
                        "fewer is faster and less accurate. Changing this "
                        "rebuilds the held model and recompiles."
                    ),
                    "minimum": 1,
                    "maximum": 48,
                },
                "num_seeds": {
                    "type": "integer",
                    "description": (
                        "How many consecutive seeds to run, starting at 'seed'. "
                        "Each seed runs every model, so the cost multiplies."
                    ),
                    "minimum": 1,
                    "maximum": 5,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the PDB text (default false: a few hundred "
                        "kilobytes per model). The scores come back either way."
                    ),
                    "default": False,
                },
            },
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "model_type": {"type": "string"},
                "n_structures": {"type": "integer"},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "scores": {"type": "array", "items": {"type": "object"}},
                "best": {"type": "string"},
                "query_length": {"type": "integer"},
                "chains": {"type": "integer"},
                "msa_rows": {"type": "integer"},
                "msa_source": {"type": "string"},
                "num_models": {"type": "integer"},
                "num_recycles": {"type": "integer"},
                "engine_rebuilt": {"type": "boolean"},
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
        "server_name": "ColabFold MCP Server",
        "host": "127.0.0.1",
        "port": 8051,
        "transport": "http",
    },
)
class ColabFoldPredictTool:
    """Fold one query. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        a3m = arguments.get("a3m")
        sequences = arguments.get("sequences")
        if (a3m is None) == (sequences is None):
            return {
                "error": (
                    "give exactly one of 'a3m' (your own alignment) or "
                    "'sequences' (run MSA-free)."
                )
            }

        if a3m is not None:
            if not isinstance(a3m, str) or not a3m.strip():
                return {"error": "'a3m' must be a non-empty string."}
            if len(a3m.encode("utf-8", "ignore")) > MAX_A3M_BYTES:
                return {
                    "error": (
                        f"'a3m' exceeds {MAX_A3M_BYTES // (1024 * 1024)} MB. "
                        f"Alignment depth beyond 508 rows changes no shape here "
                        f"-- upstream crops the MSA to the model config's width "
                        f"-- so a deeper file costs transport and nothing else."
                    )
                }
            try:
                total = _a3m_total_residues(a3m)
            except ValueError as exc:
                return {"error": str(exc)}
            if total > MAX_RESIDUES_TOTAL:
                return {
                    "error": (
                        f"{total} residues exceeds this server's "
                        f"{MAX_RESIDUES_TOTAL} limit, which is the envelope the "
                        f"provider's VRAM reserve was measured at. The pair track "
                        f"scales as N^2 and this path does not pad, so a longer "
                        f"request needs the reserve re-measured, not the limit "
                        f"raised."
                    )
                }
        else:
            try:
                a3m = _a3m_from_sequences(sequences)
            except ValueError as exc:
                return {"error": str(exc)}

        name = arguments.get("name", "query")
        if not isinstance(name, str) or not name.strip():
            return {"error": "'name' must be a non-empty string."}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        options: Dict[str, Any] = {}
        for key, low, high in (
            ("num_models", 1, 5),
            ("num_recycles", 1, 48),
            ("num_seeds", 1, 5),
        ):
            if key not in arguments:
                continue
            value = arguments[key]
            if not isinstance(value, int) or isinstance(value, bool):
                return {"error": f"'{key}' must be an integer."}
            if not low <= value <= high:
                return {"error": f"'{key}' must be between {low} and {high}."}
            options[key] = value

        # THE CEILINGS ARE CHECKED AGAINST THE REQUEST TIMEOUT, NOT ONLY AGAINST
        # EACH OTHER -- progen2's failure in the time dimension rather than the
        # memory one. Every (model, seed) pair is one full forward pass of the
        # held engine, so the work is their PRODUCT, and the measured worst case
        # at this server's 400-residue ceiling is 1736 s for five passes against
        # a 3600 s request timeout. Five models x five seeds would be
        # twenty-five passes and could not finish, so the product is bounded at
        # upstream's own default of five. More than that is several requests with
        # different seeds, which is also the better shape on a shared card.
        passes = options.get("num_models", 5) * options.get("num_seeds", 1)
        if passes > 5:
            return {
                "error": (
                    f"num_models x num_seeds is {passes}; this server allows 5, "
                    f"which is upstream's own default (5 models, 1 seed). Each "
                    f"pair is one full forward pass of the held model, and five "
                    f"passes at this server's 400-residue ceiling were measured "
                    f"at 1736 s against a 3600 s request timeout. Send several "
                    f"requests with different seeds instead."
                )
            }

        try:
            return _predict(a3m, name.strip(), seed, options, return_structures)
        except WorkerStartError as exc:  # the provider, not the request
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"ColabFold's resident worker is not available ({reason}). "
                    f"Run `tu remote setup colabfold` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                ),
                "note": (
                    "two causes are specific to this provider and are named "
                    "rather than guessed: the AlphaFold2-Multimer v3 parameters "
                    "absent or off their pins under COLABFOLD_OPT_DATA_DIR, and "
                    "that directory missing upstream's own "
                    "download_complexes_multimer_v3_finished.txt marker, without "
                    "which upstream's CLI would fetch 2 GB at run time -- which "
                    "this provider refuses to let happen."
                ),
            }
        except WorkerRequestError as exc:
            # The request, not the provider. The model stays up; this text is
            # upstream's own account of why THIS input did not fold, and
            # flattening it into the message above would discard it.
            return {
                "error": f"ColabFold could not fold this query: {exc}",
                "note": (
                    "the alignment is the caller's here: this provider runs with "
                    "no MSA search and no templates, so a malformed a3m is "
                    "refused by upstream's own parser rather than rebuilt. The "
                    "complex dialect's first line is "
                    "'#<len1>,<len2>\\t<card1>,<card2>', tab-separated, and the "
                    "aligned lengths must match the concatenated query on line 3."
                ),
            }
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            return {"error": f"ColabFold failed: {type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    start_mcp_server()
