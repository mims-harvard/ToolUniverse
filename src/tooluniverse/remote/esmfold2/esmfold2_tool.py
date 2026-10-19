"""ESMFold2 protein complex structure prediction — MCP server.

ESMFold2 folds one or more chains straight from sequence, with no MSA. This
server is the thin, CPU-only half of the provider; the model runs in its own
environment and is held resident between requests.

This is the provider residency matters most for on a per-byte basis. The stack
is 25.6 GiB of weights across sixteen files, ESMC-6B among them, and reading
them is most of a cold fold: measured on one card, three folds of an 89-residue
chain in a held worker take 2.7 s, 1.1 s and 1.1 s. The same three folds in
three processes would read 25.6 GiB three times. The cost of that speed is
stated in the manifest rather than hidden -- 14.2 GiB reserved at rest, rising
to 25.3 GiB at 800 residues -- because a host deciding what else fits on the
card needs the number, not the reassurance.

One variant per process is the kit's own rule, not ours; this provider serves
`fast` (ESMFold2-Fast), which is what [runtime] worker_args pins.

There is no subprocess fallback. When the worker cannot start, this says so
and names the reason.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CHAINS = 8
MAX_RESIDUES_TOTAL = 2000
MAX_STRUCTURE_BYTES = 32 * 1024 * 1024
_PROTEIN = set("ACDEFGHIKLMNPQRSTVWYXBZUO")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _validate_chains(chains: Any) -> List[Dict[str, Any]]:
    """Return the worker's sequence list, or raise ValueError naming why not."""
    if not isinstance(chains, list) or not chains:
        raise ValueError("'chains' must be a non-empty array of chain objects.")
    if len(chains) > MAX_CHAINS:
        raise ValueError(f"at most {MAX_CHAINS} chains per complex.")

    out: List[Dict[str, Any]] = []
    total = 0
    used = set()
    for i, chain in enumerate(chains):
        if isinstance(chain, str):
            chain = {"sequence": chain}
        if not isinstance(chain, dict):
            raise ValueError(f"chain {i} must be an object or a sequence string.")
        sequence = chain.get("sequence")
        if not isinstance(sequence, str) or not sequence.strip():
            raise ValueError(f"chain {i}: 'sequence' must be a non-empty string.")
        sequence = sequence.strip().upper()
        bad = sorted(set(sequence) - _PROTEIN)
        if bad:
            raise ValueError(f"chain {i}: sequence has invalid residues {bad}.")
        total += len(sequence)

        cid = chain.get("id") or chr(ord("A") + len(out))
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"chain {i}: 'id' must be a non-empty string.")
        if cid in used:
            raise ValueError(f"chain id {cid!r} is used twice.")
        used.add(cid)

        # msa=None is the kit's own "no MSA": ESMFold2-Fast has no MSA module,
        # and passing a key it cannot honour would be a silent lie.
        out.append({"type": "protein", "id": cid, "sequence": sequence, "msa": None})

    if total > MAX_RESIDUES_TOTAL:
        raise ValueError(
            f"{total} residues exceeds this server's {MAX_RESIDUES_TOTAL} limit; "
            f"the provider's declared VRAM budget is measured at 800."
        )
    return out


def _fold(
    sequences: List[Dict[str, Any]],
    seed: int,
    num_diffusion_samples: int,
    return_structures: bool,
) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import json
    import tempfile

    spec = [
        {
            "id": "query",
            "sequences": sequences,
            "seeds": [seed],
            "num_diffusion_samples": num_diffusion_samples,
        }
    ]
    with tempfile.TemporaryDirectory(prefix="esmfold2-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(spec),
                "out_dir": work,
                "name": "fold",
                "seed": seed,
                "options": {},
            }
        )
        result = reply["result"]
        predictions = result.get("predictions") or []
        out: Dict[str, Any] = {
            "model": "ESMFold2",
            "variant": result.get("variant"),
            "n_structures": len(predictions),
            # Per sampled structure: pTM and ipTM, which are the reason to ask
            # for more than one sample.
            "scores": [
                {
                    "sample": p.get("sample"),
                    "seed": p.get("seed"),
                    "ptm": p.get("ptm"),
                    "iptm": p.get("iptm"),
                }
                for p in predictions
            ],
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }
        if not predictions:
            return {
                "error": "ESMFold2 produced no structure for this input.",
                "timing": out["timing"],
            }

        # Off by default, for the reason chai1's tool records: a multi-sample
        # mmCIF reply is megabytes, and a transport truncates it into invalid
        # JSON rather than refusing it.
        if not return_structures:
            out["structures_note"] = (
                "pass return_structures=true to receive the mmCIF text; "
                "the pTM/ipTM scores above come back either way"
            )
            return out

        texts = []
        for p in predictions:
            path = p.get("cif")
            if not path:
                continue
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
    tool_type_name="esmfold2_fold",
    config={
        "description": (
            "Predict a protein (or protein complex) structure with ESMFold2 "
            "directly from sequence -- no MSA and no template search. Give one "
            "chain for a monomer or several for a complex. Returns pTM/ipTM "
            "per sampled structure; the mmCIF text itself is opt-in."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "chains": {
                    "type": "array",
                    "description": (
                        "Protein chains of one complex. Each item is either a "
                        "bare sequence string or an object with 'sequence' and "
                        "an optional 'id'."
                    ),
                    "minItems": 1,
                    "maxItems": MAX_CHAINS,
                    "items": {
                        "type": "object",
                        "properties": {
                            "sequence": {"type": "string", "minLength": 1},
                            "id": {
                                "type": "string",
                                "description": "Chain label; defaults to A, B, C...",
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
                        "Structures to sample (default 1). Each is scored "
                        "separately, so >1 is how to compare conformations."
                    ),
                    "default": 1,
                    "minimum": 1,
                    "maximum": 5,
                },
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text as well as the scores "
                        "(default false: megabytes)."
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
                "variant": {"type": "string"},
                "n_structures": {"type": "integer"},
                "scores": {"type": "array", "items": {"type": "object"}},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "ESMFold2 MCP Server",
        "host": "127.0.0.1",
        "port": 8038,
        "transport": "http",
    },
)
class ESMFold2FoldTool:
    """Fold one complex. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequences = _validate_chains(arguments.get("chains"))
        except ValueError as exc:
            return {"error": str(exc)}

        seed = arguments.get("seed", 0)
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            return {"error": "'seed' must be a non-negative integer."}

        samples = arguments.get("num_diffusion_samples", 1)
        if not isinstance(samples, int) or isinstance(samples, bool):
            return {"error": "'num_diffusion_samples' must be an integer."}
        if not 1 <= samples <= 5:
            return {"error": "'num_diffusion_samples' must be between 1 and 5."}

        return_structures = arguments.get("return_structures", False)
        if not isinstance(return_structures, bool):
            return {"error": "'return_structures' must be a boolean."}

        try:
            return _fold(sequences, seed, samples, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"ESMFold2's resident worker is not available ({reason}). "
                    f"Run `tu remote setup esmfold2` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
