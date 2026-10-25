"""The MCP surface for BioEmu-2's resident worker.

Runs in ToolUniverse's environment and imports nothing of the model's: the
request crosses a Unix socket as JSON, per STANDARD section 2.

ONE TOOL, TWO MODES, AND A THIRD CAPABILITY DELIBERATELY NOT EXPOSED.
``mode`` is not a task switch dressed up as a parameter -- it changes the
sampler's step scale and sharpening, and upstream documents the two as
answering different questions: ``structure`` wants one accurate fold,
``equilibrium`` wants a spread of conformations from the modelled ensemble.
Both take the same system and return the same shape, so they are one tool.

``propagate`` -- stepping a sampled conformation forward 1 ns to 1 us, which
is the thing BioEmu-2 does that nothing else in ToolUniverse does -- is NOT
here. It needs a starting ensemble round-tripped back in, which over this
interface means base64 XTC, and nothing in this provider has run it. Adding
an operation whose only evidence is that the Python API exists is the mistake
STANDARD section 9 names. It is a second PR, with its own measurement.

WHAT THE INPUT IS. Either ``sequences`` (the common case: one entry per chain,
chains lettered in order) or ``system_yaml`` (upstream's own system YAML, which
is what covers ligands, nucleic acids, modified residues and non-standard
bonds). Exactly one. Both are composed into the same request document the
worker parses, so the smoke file and a tool call travel identical paths.
"""

import json
import os
import re
import string
from typing import Any, Dict

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

PROVIDER_DIR = os.path.dirname(os.path.abspath(__file__))

MAX_SAMPLES = 16

# THE TOKEN CEILING IS NOT CHECKED HERE, AND THAT IS DELIBERATE. The worker
# refuses above 448 tokens, counted as BioEmu-2 counts them by building the
# structure -- which needs `bioemu2` itself, and this half of the provider
# must not import the model's environment. The arithmetic that looks like a
# substitute is wrong in the dangerous direction: summing sequence lengths
# gives 214 where BioEmu-2 counts 271 (PDB 1AKE) and 624 where it counts 676
# (6LU7), so a ceiling enforced on that sum would admit systems a fifth larger
# than the one the VRAM budget was measured at. A caller over the ceiling is
# refused one round trip later, by name, with the real number.
MAX_TOKENS_ENFORCED_BY_WORKER = 448
MAX_SYSTEM_BYTES = 256 * 1024
MAX_MSA_BYTES = 4 * 1024 * 1024
MAX_TOPOLOGY_BYTES = 32 * 1024 * 1024

MODES = ("structure", "equilibrium")
PHYSICALITY_MODES = (
    "no_filter",
    "no_violations",
    "high_quality",
    "high_quality_per_residue",
)

# The 20 standard amino acids plus X, which upstream uses for an unidentified
# residue. Anything else is a typo or a three-letter code pasted by mistake,
# and both are cheaper to refuse than to sample.
_RESIDUES = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYX]+$")


def _worker():
    from tooluniverse.remote_resident import backend

    return backend.worker_for_provider_dir(PROVIDER_DIR)


def _system_from_sequences(sequences: Any) -> Dict[str, Any]:
    """Upstream's system block for a list of protein chains, lettered in order."""
    if not isinstance(sequences, list) or not sequences:
        raise ValueError("'sequences' must be a non-empty list of strings.")
    if len(sequences) > len(string.ascii_uppercase):
        raise ValueError(
            f"'sequences' has {len(sequences)} chains; this tool letters chains "
            f"A-Z, so pass 'system_yaml' with explicit asym_ids beyond 26."
        )
    entities = []
    for index, sequence in enumerate(sequences):
        if not isinstance(sequence, str) or not sequence.strip():
            raise ValueError(f"'sequences[{index}]' must be a non-empty string.")
        cleaned = "".join(sequence.split()).upper()
        if not _RESIDUES.match(cleaned):
            bad = sorted(set(cleaned) - set("ACDEFGHIKLMNPQRSTVWYX"))
            raise ValueError(
                f"'sequences[{index}]' contains {', '.join(bad)}, which are not "
                f"one-letter amino acids. Use 'X' for an unidentified residue; "
                f"for nucleic acids or ligands use 'system_yaml'."
            )
        entities.append(
            {
                "entity_type": "protein",
                "asym_ids": [string.ascii_uppercase[index]],
                "sequence": cleaned,
                "mods": [],
            }
        )
    return {"entities": entities, "bonds": []}


@register_mcp_tool(
    tool_type_name="bioemu2_sample_structures",
    config={
        "description": (
            "Sample all-atom 3D structures of a biomolecular system with "
            "BioEmu-2. Give it the composition -- protein chains as sequences, "
            "or a system definition that may also contain ligands, RNA, DNA, "
            "modified residues and non-standard bonds -- and it returns an "
            "ensemble of conformations, not a single structure. 'structure' "
            "mode asks for one accurate fold; 'equilibrium' mode asks for a "
            "spread of conformations from the modelled equilibrium ensemble. "
            "Sampling frequency is NOT a calibrated Boltzmann probability and "
            "the model predicts neither sequences nor binding affinities. "
            "Structures are written to the worker's output directory; "
            "per-frame physicality checks come back either way. The system "
            "must be at most 448 tokens, which is BioEmu-2's own count and "
            "includes a ligand's atoms, so it is larger than the residue "
            "count; a bigger system is refused by name."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One one-letter amino-acid sequence per protein chain, "
                        "lettered A, B, C... in the order given. Identical "
                        "sequences become one entity with several chains. Use "
                        "'system_yaml' instead for anything that is not a "
                        "plain protein chain."
                    ),
                },
                "system_yaml": {
                    "type": "string",
                    "description": (
                        "BioEmu-2's own system YAML, as written by "
                        "System.to_yaml(): an 'entities' list and a 'bonds' "
                        "list. This is the way to describe ligands by CCD code "
                        "or SMILES, nucleic acids, modified residues, explicit "
                        "chain ids and covalent bonds. Mutually exclusive with "
                        "'sequences'."
                    ),
                },
                "mode": {
                    "type": "string",
                    "description": (
                        "'structure' sharpens towards one accurate fold; "
                        "'equilibrium' samples the modelled ensemble without "
                        "sharpening. They differ in the sampler, not in what "
                        "they accept."
                    ),
                    "enum": list(MODES),
                    "default": "structure",
                },
                "num_samples": {
                    "type": "integer",
                    "description": (
                        f"Conformations to generate, 1 to {MAX_SAMPLES}. On the "
                        f"verified card this barely moved peak memory at 76 "
                        f"residues but it does cost wall-clock."
                    ),
                    "default": 1,
                },
                "msa_a3m": {
                    "type": "object",
                    "description": (
                        "Optional alignment per chain id, as A3M text whose "
                        "first record is that chain's query sequence. OMITTING "
                        "THIS SENDS A QUERY TO THE PUBLIC COLABFOLD SERVER on a "
                        "cache miss, which leaves this machine and depends on a "
                        "third party. Supply your own to stay local; a "
                        "query-only alignment is valid A3M and degrades the "
                        "model rather than failing."
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed. Omit for a random one.",
                },
                "physicality": {
                    "type": "string",
                    "description": (
                        "Which geometry checks to report per frame: chain "
                        "breaks, clashes and bond lengths. Failing frames are "
                        "still returned and still saved; this only labels them."
                    ),
                    "enum": list(PHYSICALITY_MODES),
                    "default": "high_quality",
                },
                "return_topology": {
                    "type": "boolean",
                    "description": (
                        "Return the topology.cif text in the reply as well as "
                        "writing it. Off by default: a transport truncates an "
                        "oversized reply into invalid JSON rather than "
                        "refusing it. The trajectory frames are never inlined."
                    ),
                    "default": False,
                },
            },
            "additionalProperties": False,
        },
        "return_schema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "mode": {"type": "string"},
                "num_samples": {"type": "integer"},
                "tokens": {"type": "integer"},
                "chains": {"type": "array", "items": {"type": "string"}},
                "msa": {"type": "string"},
                "seed": {"type": "integer"},
                "physicality": {"type": "object"},
                "files": {"type": "array", "items": {"type": "string"}},
                "output_dir": {"type": "string"},
                "topology_cif": {"type": "string"},
                "structures_note": {"type": "string"},
                "timing": {"type": "object"},
                "weights_held_by": {"type": "string"},
                "peak_reserved_gib": {"type": "number"},
                "peak_allocated_gib": {"type": "number"},
                "error": {"type": "string"},
            },
        },
    },
    mcp_config={
        "server_name": "BioEmu-2 MCP Server",
        "host": "127.0.0.1",
        "port": 8063,
        "transport": "http",
    },
)
class BioEmu2SampleStructuresTool:
    """Sample conformations. Requests queue: the worker serves one at a time."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}

        try:
            document = self._document(arguments)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            # JSON is a subset of YAML, so the worker's yaml.safe_load reads
            # this as the same document a hand-written smoke file produces --
            # without this tool having to quote YAML correctly.
            reply = _worker().request(
                {"op": "predict", "input": json.dumps(document)}
            )
        except Exception as exc:  # noqa: BLE001 - the reason is the answer
            reason = getattr(exc, "reason", "") or type(exc).__name__
            return {
                "error": (
                    f"BioEmu-2's resident worker is not available ({reason}). "
                    f"Run `tu remote setup bioemu2` and read its named "
                    f"refusal; this provider has no subprocess fallback."
                )
            }

        result = reply["result"]
        out = {
            key: result.get(key)
            for key in (
                "model",
                "mode",
                "num_samples",
                "tokens",
                "chains",
                "msa",
                "seed",
                "physicality",
                "files",
                "output_dir",
                "timing",
                "weights_held_by",
                "peak_reserved_gib",
                "peak_allocated_gib",
            )
        }
        topology = result.get("topology_cif")
        if topology is not None:
            if len(topology.encode("utf-8")) > MAX_TOPOLOGY_BYTES:
                out["structures_note"] = (
                    "topology.cif exceeds the public output limit; it was "
                    "written to the worker's output directory"
                )
            else:
                out["topology_cif"] = topology
        elif result.get("structures_note"):
            out["structures_note"] = result["structures_note"]
        return out

    def _document(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """The request document, or a ValueError naming what is wrong with it."""
        sequences = arguments.get("sequences")
        system_yaml = arguments.get("system_yaml")
        if (sequences is None) == (system_yaml is None):
            raise ValueError(
                "Pass exactly one of 'sequences' (protein chains) or "
                "'system_yaml' (upstream's system definition)."
            )

        if sequences is not None:
            system = _system_from_sequences(sequences)
        else:
            if not isinstance(system_yaml, str) or not system_yaml.strip():
                raise ValueError("'system_yaml' must be a non-empty string.")
            if len(system_yaml.encode("utf-8")) > MAX_SYSTEM_BYTES:
                raise ValueError(
                    f"'system_yaml' is above {MAX_SYSTEM_BYTES} bytes; a "
                    f"system definition is composition, not coordinates."
                )
            # Passed through as text. The worker owns BioEmu-2's own
            # validation, and a tool that parsed the YAML here to second-guess
            # it would be a second schema to keep in step with upstream's.
            system = system_yaml

        document: Dict[str, Any] = {"system": system}

        mode = arguments.get("mode", "structure")
        if mode not in MODES:
            raise ValueError(f"'mode' must be one of {', '.join(MODES)}.")
        document["mode"] = mode

        num_samples = arguments.get("num_samples", 1)
        if not isinstance(num_samples, int) or isinstance(num_samples, bool):
            raise ValueError("'num_samples' must be an integer.")
        if not 1 <= num_samples <= MAX_SAMPLES:
            raise ValueError(f"'num_samples' must be between 1 and {MAX_SAMPLES}.")
        document["num_samples"] = num_samples

        msa = arguments.get("msa_a3m")
        if msa is not None:
            if not isinstance(msa, dict) or not msa:
                raise ValueError(
                    "'msa_a3m' must be a non-empty object of chain id to A3M text."
                )
            total = 0
            for chain_id, a3m in msa.items():
                if not isinstance(a3m, str) or not a3m.lstrip().startswith(">"):
                    raise ValueError(
                        f"'msa_a3m[{chain_id}]' must be A3M text whose first "
                        f"record is that chain's query sequence."
                    )
                total += len(a3m.encode("utf-8"))
            if total > MAX_MSA_BYTES:
                raise ValueError(
                    f"'msa_a3m' totals {total} bytes, above {MAX_MSA_BYTES}."
                )
            document["msa"] = msa

        seed = arguments.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or isinstance(seed, bool):
                raise ValueError("'seed' must be an integer.")
            document["seed"] = seed

        physicality = arguments.get("physicality", "high_quality")
        if physicality not in PHYSICALITY_MODES:
            raise ValueError(
                f"'physicality' must be one of {', '.join(PHYSICALITY_MODES)}."
            )
        document["physicality"] = physicality

        return_topology = arguments.get("return_topology", False)
        if not isinstance(return_topology, bool):
            raise ValueError("'return_topology' must be a boolean.")
        document["return_topology"] = return_topology

        return document


if __name__ == "__main__":
    start_mcp_server()
