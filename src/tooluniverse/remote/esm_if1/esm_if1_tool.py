"""ESM-IF1 inverse folding (esm_if1) -- MCP server.

Given a protein BACKBONE this returns SEQUENCES that are predicted to fold into
it: Meta FAIR's GVP-Transformer (``esm_if1_gvp4_t16_142M_UR50``, 142M
parameters) encodes the N/CA/C coordinates and autoregressively samples amino
acids. It is the inverse of the eleven folding providers beside it, and unlike
ef2inv -- which also answers with a sequence -- it needs no gradients and no
folding model: one encoder pass and one decode per sample.

This server is the thin, CPU-only half of the provider. The model runs in its
own environment and is held resident between requests.

**This provider's model also runs on the CPU, and that is declared rather than
incidental.** ``provider.toml``'s ``[gpu] policy = "none"`` carries the
measurement: the kit pins torch 2.4.0, and the CUDA 12.4 cuBLAS such a stack
loads carries cubins for sm_50 through sm_90 and no PTX at all, so nothing in it
can execute on this card's sm_121. What residency buys is therefore unchanged by
the device -- a 1.7 GB checkpoint read once instead of once per request, measured
at 8.7x -- but a caller should expect seconds rather than milliseconds, and the
time is roughly linear in the backbone's length because the decoder takes one
sequential step per designed position.

Three limits below are worth reading before a request:

* ``num_samples`` and the backbone's length are cheap separately and expensive
  together, because one forward pass holds ``batch_size`` rows of the encoder's
  output and the decoder's incremental state for each. The bound is on the
  PRODUCT (``MAX_ROW_TOKENS``), which is the shape of bound progen2's two
  individually-sane ceilings taught this project to use.
* ``batch_size`` groups samples into one forward pass. It changes speed and
  memory, never the distribution: the kit's own statement is that batched
  multinomial sampling "draws from the same distribution as upstream's
  one-sequence calls, not the same bits".
* ``multichain_backbone`` conditions the design on every chain in the file while
  designing only ``chain``, which is upstream's second route and needs ``chain``
  named.

There is no subprocess fallback. When the worker cannot start, this says so and
names the reason.
"""

import os
from typing import Any, Dict, Optional

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

# These three mirror the worker's own module constants exactly. They are
# restated here rather than imported because this process must not import
# anything from the model's environment -- and they are checked here as well as
# there because a ceiling that only the worker knows is a ceiling a caller
# discovers by having a request fail.
MAX_TOKENS = 1600
MAX_SAMPLES = 64
MAX_ROW_TOKENS = 6400
MAX_BATCH = 64
# A backbone, not a whole PDB entry. 8 MB is ~100k atoms, far past MAX_TOKENS,
# and it keeps a caller from pushing a megabyte through the MCP transport by
# accident: chai1 once returned enough text that the transport truncated the
# reply at exactly 100,000 characters and produced invalid JSON rather than a
# refusal, so sizes are checked on the way in and on the way out.
MAX_STRUCTURE_BYTES = 8 * 1024 * 1024
FORMATS = ("pdb", "cif")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _ca_count(
    text: str, fmt: str, chain: Optional[str], multichain: bool
) -> Optional[int]:
    """How many backbone residues the loader will see, or None when unsure.

    This is the cheap half of the row-token bound, and it is deliberately
    conservative: PDB is counted exactly (``ATOM`` records whose atom name is
    ``CA``, filtered to ``chain`` on the single-chain route), mmCIF is counted
    by scanning for a ``CA`` atom-name field, and anything this cannot read
    returns None so the request goes through and the WORKER refuses with the
    real number. A guess that refused a valid request would be worse than no
    guess, which is the lesson three of this layer's own checks have taught.
    """
    try:
        if fmt == "pdb":
            n = 0
            for line in text.splitlines():
                if not line.startswith("ATOM"):
                    continue
                if len(line) < 22 or line[12:16].strip() != "CA":
                    continue
                if line[16] not in (" ", "A"):  # altloc: the first conformer
                    continue
                if not multichain and chain and line[21] != chain:
                    continue
                n += 1
            if multichain:
                # upstream concatenates the chains with 10-residue pads between
                # them (_concatenate_coords); the pads are what the encoder
                # sees, so they count toward the ceiling.
                chains = {
                    line[21]
                    for line in text.splitlines()
                    if line.startswith("ATOM") and len(line) > 21
                }
                n += 10 * max(len(chains) - 1, 0)
            return n or None
        # mmCIF: the atom_site loop's atom-name column, whichever position it
        # sits in. Counting tokens equal to "CA" over-counts nothing a backbone
        # carries and under-counts nothing either, since calcium would be
        # HETATM.
        n = 0
        for line in text.splitlines():
            if not line.startswith(("ATOM", "HETATM")):
                continue
            parts = line.split()
            if "CA" in parts[:6]:
                n += 1
        return n or None
    except (IndexError, ValueError, AttributeError):
        return None


def _design(doc: Dict[str, Any]) -> Dict[str, Any]:
    """One request on the resident worker, or a named reason why not."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory(prefix="esm_if1-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(doc),
                "out_dir": work,
                "name": "design",
                "seed": int(doc.get("seed", 37)),
                "options": {},
            }
        )
        result = reply["result"]
        sequences = result.get("sequences") or []
        out: Dict[str, Any] = {
            "model": "ESM-IF1 (fair-esm esm_if1_gvp4_t16_142M_UR50)",
            # The answer. One record per requested sample, in the order the kit
            # writes them (>sampled_seq_1 .. >sampled_seq_N).
            "sequences": sequences,
            # The structure's own sequence, so a caller can see what the design
            # was compared against without a second request.
            "native_sequence": result.get("native_seq"),
            # Per sample: the fraction of positions equal to the native
            # residue, which is upstream's own `Sequence recovery:` figure
            # (sample_sequences.py:40-41).
            "sequence_recovery": result.get("recovery"),
            "chain": result.get("chain"),
            "route": result.get("route"),
            "n_tokens": result.get("n_tokens"),
            "designed_length": result.get("designed_length"),
            "num_samples": result.get("num_samples"),
            "temperature": result.get("temperature"),
            "seed": result.get("seed"),
            "batch_size": result.get("batch_size"),
            "rows_per_forward": result.get("rows_per_forward"),
            "n_batches": result.get("n_batches"),
            "device": result.get("device"),
            "timing": result.get("timing"),
            # None on this host by design: a CPU provider has no VRAM figure.
            # peak_rss_gib is what a scheduler reads instead, and it is a
            # high-water mark for the whole worker rather than this request.
            "peak_reserved_gib": result.get("peak_reserved_gib"),
            "peak_rss_gib": result.get("peak_rss_gib"),
            "kit_mode": result.get("kit_mode"),
            "kit_levers": result.get("kit_levers"),
            "weights_held_by": result.get("weights_held_by"),
        }
        if not sequences:
            return {
                "error": (
                    "esm_if1 produced no sequence for this backbone. The worker "
                    "writes a FASTA only once every requested sample is "
                    "sampled, so an empty result means the pass did not "
                    "complete; its transcript names why."
                ),
                "timing": out["timing"],
            }
        return out


@register_mcp_tool(
    tool_type_name="esm_if1_design",
    config={
        "description": (
            "Design protein SEQUENCES for a given backbone with ESM-IF1 "
            "(inverse folding). Give the backbone as PDB or mmCIF text and, "
            "optionally, the chain to design; returns num_samples sampled "
            "sequences, the structure's own sequence, and each sample's "
            "sequence recovery against it. Raise 'temperature' for diversity. "
            "Use multichain_backbone=true to design one chain of a complex "
            "while conditioning on all of its backbones. Runs on the CPU: "
            "expect ~1.5 s for a 64-residue backbone and ~40 s for 800 "
            "residues, roughly linear in length."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "structure": {
                    "type": "string",
                    "description": (
                        "The backbone, as the text of a PDB or mmCIF file. Only "
                        "the N, CA and C atoms of amino-acid residues are read; "
                        "side chains, waters and ligands are ignored. Up to "
                        f"{MAX_STRUCTURE_BYTES // (1024 * 1024)} MB."
                    ),
                },
                "structure_format": {
                    "type": "string",
                    "enum": list(FORMATS),
                    "description": (
                        "Which of the two the 'structure' text is (default "
                        "pdb). Upstream's loader dispatches on this, so a cif "
                        "sent as pdb fails to parse rather than being sniffed."
                    ),
                    "default": "pdb",
                },
                "chain": {
                    "type": "string",
                    "description": (
                        "The chain id to design. Omit to take every chain the "
                        "file's loader returns as one backbone. Required when "
                        "multichain_backbone is true."
                    ),
                },
                "num_samples": {
                    "type": "integer",
                    "description": (
                        f"How many sequences to sample (default 1, max "
                        f"{MAX_SAMPLES}). Samples are independent draws from "
                        f"the same conditional distribution."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": MAX_SAMPLES,
                },
                "temperature": {
                    "type": "number",
                    "description": (
                        "Sampling temperature (default 1.0). Higher is more "
                        "diverse and lower recovers the native sequence more "
                        "often."
                    ),
                    "default": 1.0,
                    "exclusiveMinimum": 0,
                    "maximum": 10.0,
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed, applied once per request (default 37, the "
                        "kit's own). At a fixed seed, num_samples and "
                        "batch_size the sampled sequences repeat exactly."
                    ),
                    "default": 37,
                    "minimum": 0,
                },
                "batch_size": {
                    "type": "integer",
                    "description": (
                        f"How many samples share one forward pass (default "
                        f"{MAX_BATCH}, max {MAX_BATCH}). It changes speed and "
                        f"memory, not the distribution. "
                        f"min(batch_size, num_samples) x the backbone's length "
                        f"must not exceed {MAX_ROW_TOKENS}."
                    ),
                    "default": MAX_BATCH,
                    "minimum": 1,
                    "maximum": MAX_BATCH,
                },
                "multichain_backbone": {
                    "type": "boolean",
                    "description": (
                        "Design 'chain' conditioned on the backbones of every "
                        "chain in the file (upstream's multichain route) rather "
                        "than on that chain alone. Needs 'chain'."
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
                "sequences": {"type": "array", "items": {"type": "string"}},
                "native_sequence": {"type": "string"},
                "sequence_recovery": {"type": "array", "items": {"type": "number"}},
                "chain": {"type": "string"},
                "route": {"type": "string"},
                "n_tokens": {"type": "integer"},
                "designed_length": {"type": "integer"},
                "num_samples": {"type": "integer"},
                "temperature": {"type": "number"},
                "seed": {"type": "integer"},
                "batch_size": {"type": "integer"},
                "rows_per_forward": {"type": "integer"},
                "n_batches": {"type": "integer"},
                "device": {"type": "string"},
                "timing": {"type": "object"},
                "peak_reserved_gib": {"type": "number"},
                "peak_rss_gib": {"type": "number"},
                "kit_mode": {"type": "string"},
                "kit_levers": {"type": "array", "items": {"type": "string"}},
                "weights_held_by": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "ESM-IF1 Inverse Folding MCP Server",
        "host": "127.0.0.1",
        "port": 8050,
        "transport": "http",
    },
)
class ESMIF1DesignTool:
    """Design sequences for a backbone. Requests queue: one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        structure = arguments.get("structure")
        if not isinstance(structure, str) or not structure.strip():
            return {
                "error": (
                    "'structure' must be the text of a PDB or mmCIF file "
                    "holding the backbone to design for."
                )
            }
        if len(structure.encode("utf-8", "replace")) > MAX_STRUCTURE_BYTES:
            return {
                "error": (
                    f"'structure' is larger than "
                    f"{MAX_STRUCTURE_BYTES // (1024 * 1024)} MB; send the "
                    f"chains you want designed or conditioned on, not a whole "
                    f"assembly."
                )
            }

        fmt = arguments.get("structure_format", "pdb")
        if not isinstance(fmt, str) or fmt.lower().lstrip(".") not in FORMATS:
            return {"error": f"'structure_format' must be one of {list(FORMATS)}."}
        fmt = fmt.lower().lstrip(".")

        chain = arguments.get("chain")
        if chain is not None:
            if not isinstance(chain, str) or not chain.strip():
                return {"error": "'chain' must be a non-empty chain id."}
            chain = chain.strip()

        multichain = arguments.get("multichain_backbone", False)
        if not isinstance(multichain, bool):
            return {"error": "'multichain_backbone' must be a boolean."}
        if multichain and not chain:
            return {
                "error": (
                    "'multichain_backbone' needs 'chain': the chain to design. "
                    "Every chain of the file then conditions it."
                )
            }

        num_samples = arguments.get("num_samples", 1)
        if not isinstance(num_samples, int) or isinstance(num_samples, bool):
            return {"error": "'num_samples' must be an integer."}
        if not 1 <= num_samples <= MAX_SAMPLES:
            return {"error": f"'num_samples' must be between 1 and {MAX_SAMPLES}."}

        temperature = arguments.get("temperature", 1.0)
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            return {"error": "'temperature' must be a number."}
        if not 0 < float(temperature) <= 10:
            return {"error": "'temperature' must be greater than 0 and at most 10."}

        seed = arguments.get("seed", 37)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        batch_size = arguments.get("batch_size", MAX_BATCH)
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            return {"error": "'batch_size' must be an integer."}
        if not 1 <= batch_size <= MAX_BATCH:
            return {"error": f"'batch_size' must be between 1 and {MAX_BATCH}."}

        # The product bound, checked here when the length can be read cheaply.
        # progen2 allowed 16 sequences of 1024 tokens -- each ceiling sane, the
        # product 116.93 GiB -- so the ceiling that matters is this one, and it
        # has to exist on the caller's side of the socket too.
        tokens = _ca_count(structure, fmt, chain, multichain)
        if tokens is not None:
            if tokens > MAX_TOKENS:
                return {
                    "error": (
                        f"the backbone has about {tokens} residues and this "
                        f"provider's measured budget stops at {MAX_TOKENS}. "
                        f"Time is roughly linear in length and the 800-residue "
                        f"rung already takes ~40 s on this host."
                    )
                }
            rows = min(batch_size, num_samples)
            if rows * tokens > MAX_ROW_TOKENS:
                return {
                    "error": (
                        f"{rows} rows per forward pass x about {tokens} "
                        f"residues = {rows * tokens} exceeds this provider's "
                        f"limit of {MAX_ROW_TOKENS} row-tokens. Each ceiling "
                        f"alone is fine and their product is what costs memory, "
                        f"so lower 'batch_size' -- it only groups samples into "
                        f"one pass and the sequences are drawn from the same "
                        f"distribution either way (try "
                        f"{max(MAX_ROW_TOKENS // max(tokens, 1), 1)})."
                    )
                }

        doc: Dict[str, Any] = {
            "structure": structure,
            "structure_format": fmt,
            "num_samples": num_samples,
            "temperature": float(temperature),
            "seed": seed,
            "batch_size": batch_size,
            "multichain_backbone": multichain,
        }
        if chain:
            doc["chain"] = chain

        try:
            return _design(doc)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"esm_if1's resident worker is not available ({reason}: "
                    f"{exc}). Run `tu remote setup esm_if1` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
