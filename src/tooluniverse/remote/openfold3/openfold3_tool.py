"""OpenFold3 all-atom structure prediction — MCP server.

OpenFold3 folds a query of chains -- protein, DNA, RNA, ligand -- into an
all-atom structure. This server is the thin, CPU-only half of the provider;
the model runs in its own environment (torch 2.10 + cu128, a stack this one
cannot import) and is held resident between requests.

Residency here buys less than it does for Chai-1 or RFdiffusion3, and the
manifest says so honestly: the checkpoint is only ~2.1 GiB and the build takes
5.9 s, so a held worker turns a ~15 s cold fold into a ~6-9 s warm one rather
than a 3x saving. It is still the right shape, because the alternative is
paying that build on every request and because the resident route is what
makes the provider schedulable -- 4.24 GiB reserved at 800 residues, declared
in the manifest, is a number a host can add up.

There is no subprocess fallback. When the worker cannot start, this says so
and names the reason rather than quietly running something slower.
"""

import os
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_CHAINS = 16
MAX_RESIDUES_TOTAL = 4000
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
            f"limit; the provider's declared VRAM budget is measured at 800."
        )
    return out


def _fold(chains: List[Dict[str, Any]], return_structures: bool) -> Dict[str, Any]:
    """One fold on the resident worker, or a named reason why not."""
    import json
    import tempfile

    query = {"queries": {"query": {"chains": chains}}}
    with tempfile.TemporaryDirectory(prefix="openfold3-") as work:
        reply = _worker().request(
            {
                "op": "predict",
                "input": json.dumps(query),
                "out_dir": work,
                "name": "fold",
                "seed": 0,
                "options": {},
            }
        )
        result = reply["result"]
        structures = [
            p for p in (result.get("structures") or []) if p.endswith((".cif", ".pdb"))
        ]
        out: Dict[str, Any] = {
            "model": "OpenFold3",
            "n_structures": len(structures),
            "seeds": result.get("seeds"),
            "timing": result.get("timing"),
            "weights_held_by": result.get("weights_held_by"),
            "kit_mode": result.get("kit_mode"),
        }
        if not structures:
            return {
                "error": "OpenFold3 produced no structure for this query.",
                "timing": out["timing"],
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
    tool_type_name="openfold3_fold",
    config={
        "description": (
            "Predict an all-atom biomolecular structure with OpenFold3. The "
            "query is a list of chains, each with a molecule_type (protein, "
            "dna, rna or ligand) and a sequence -- SMILES for a ligand. "
            "Returns the structure file paths and timings; the mmCIF text "
            "itself is opt-in."
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
                "return_structures": {
                    "type": "boolean",
                    "description": (
                        "Return the mmCIF text as well as the paths "
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
                "n_structures": {"type": "integer"},
                "structures": {"type": "array", "items": {"type": "object"}},
                "structures_note": {"type": "string"},
                "seeds": {"type": "array", "items": {"type": "integer"}},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "kit_mode": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "OpenFold3 MCP Server",
        "host": "127.0.0.1",
        "port": 8039,
        "transport": "http",
    },
)
class OpenFold3FoldTool:
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

        try:
            return _fold(chains, return_structures)
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"OpenFold3's resident worker is not available ({reason}). "
                    f"Run `tu remote setup openfold3` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }


if __name__ == "__main__":
    start_mcp_server()
