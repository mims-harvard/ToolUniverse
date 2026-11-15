# pdbtm_tool.py
"""
PDBTM (Protein Data Bank of Transmembrane Proteins) tool for ToolUniverse.

PDBTM classifies transmembrane topology directly from solved PDB
structures: for each chain, whether it is alpha-helical, beta-barrel, or
not membrane-embedded, and how many transmembrane segments it has.

ToolUniverse already has OPM (membrane placement geometry and transfer
energy) and TopDB (curated per-region topology from experimental evidence).
PDBTM adds the third, independent view: per-chain classification computed
directly from structure coordinates, useful for cross-checking multi-chain
complexes chain by chain (e.g. which subunit of a photosynthetic reaction
centre is membrane-embedded and which is not).

API: https://pdbtm.unitmp.org/api/v1
No authentication required.
"""

from typing import Dict, Any, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

PDBTM_BASE_URL = "https://pdbtm.unitmp.org/api/v1"


SEGMENTS_PER_CHAIN = 200


def _topology_segments(chain, site_labels):
    """Collapse the per-residue site assignment into labelled ranges.

    PDBTM assigns every residue to one of eight regions -- Side1, Side2,
    Transmembrane Beta strand, Membrane Inside and so on -- and the entry
    carries the legend that turns a site_id into that name. The wrapper
    reported `num_tm_segments` and none of it, so a topology tool answered
    "16" to the question of which residues cross the membrane. For 2por's
    chain A that is 103 residues of transmembrane beta strand, 55 on Side1,
    108 on Side2 and 35 inside the membrane, every one of them curated.
    """
    segments = []
    for res in chain.get("residues") or []:
        site = (res.get("site_data") or [{}])[0]
        label = site_labels.get(site.get("site_id_ref"))
        confidence = site.get("confidence_classification")
        position = res.get("pdb_res_label")
        last = segments[-1] if segments else None
        if last and last["region"] == label and last["confidence"] == confidence:
            last["end_residue"] = position
            last["residue_count"] += 1
            last["amino_acids"].append(res.get("aa_type"))
            continue
        segments.append(
            {
                "region": label,
                "confidence": confidence,
                "start_residue": position,
                "end_residue": position,
                "residue_count": 1,
                "amino_acids": [res.get("aa_type")],
            }
        )
    return segments


@register_tool("PDBTMTool")
class PDBTMTool(BaseTool):
    """
    Tool for retrieving structure-derived transmembrane classification from
    PDBTM.

    Supports fetching one PDB entry's per-chain topology: whether each
    chain is alpha-helical, beta-barrel, or not membrane-embedded, and its
    transmembrane segment count.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_topology"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PDBTM lookup."""
        try:
            if self.operation == "get_topology":
                return self._get_topology(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PDBTM request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PDBTM. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"PDBTM returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "PDBTM returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying PDBTM: {str(e)}"}

    def _get_topology(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch per-chain transmembrane classification for one PDB entry."""
        pdb_id = (arguments.get("pdb_id") or "").strip().lower()
        if not pdb_id:
            return {
                "status": "error",
                "error": "pdb_id is required, e.g. '1prc' (photosynthetic "
                "reaction centre) or '2por' (porin).",
            }

        response = requests.get(
            f"{PDBTM_BASE_URL}/entry/{pdb_id}.json", timeout=self.timeout
        )
        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"No PDBTM entry for '{pdb_id}'. PDBTM only covers "
                "PDB structures it has classified as membrane proteins.",
            }
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("pdb_id"):
            return {
                "status": "error",
                "error": f"No PDBTM entry for '{pdb_id}'.",
            }

        site_labels = {
            site.get("site_id"): site.get("label")
            for site in (payload.get("sites") or [])
            if isinstance(site, dict)
        }

        chains: List[Dict[str, Any]] = []
        for chain in payload.get("chains") or []:
            annotations = chain.get("additional_chain_annotations") or {}
            tm_type = annotations.get("type")
            num_tm = annotations.get("num_tm")
            segments = _topology_segments(chain, site_labels)
            region_counts = {}
            for seg in segments:
                key = seg["region"] or "unlabelled"
                region_counts[key] = region_counts.get(key, 0) + seg["residue_count"]
            chains.append(
                {
                    "chain_label": chain.get("chain_label"),
                    "tm_type": tm_type,
                    "num_tm_segments": int(num_tm) if num_tm is not None else None,
                    "is_membrane_embedded": tm_type not in (None, "non_tm"),
                    "topology_segments": segments[:SEGMENTS_PER_CHAIN],
                    "topology_segments_total": len(segments),
                    "topology_segments_truncated": (
                        len(segments) > SEGMENTS_PER_CHAIN
                    ),
                    "residue_count": sum(x["residue_count"] for x in segments),
                    "residues_by_region": region_counts,
                }
            )

        membrane = (payload.get("additional_entry_annotations") or {}).get(
            "membrane"
        ) or {}

        return {
            "status": "success",
            "data": {
                "pdb_id": payload.get("pdb_id"),
                "release_date": payload.get("release_date"),
                "chains": chains,
                "membrane_radius_angstrom": membrane.get("radius"),
                # The region legend the per-residue assignment refers to.
                "regions": [
                    {"site_id": k, "label": v} for k, v in sorted(site_labels.items())
                ],
                # The membrane-positioned coordinates themselves, and the
                # PDBTM page. A structure database that returns no way to
                # fetch the structure is a dead end.
                "model_coordinates_url": payload.get("model_coordinates_url"),
                "entry_url": payload.get("resource_entry_url"),
                "includes_het_groups": payload.get("includes_het_groups"),
                # How the assignment was made, as an ECO term.
                "evidence_codes": payload.get("evidence_code_ontology") or [],
                "pdbtm_version": payload.get("resource_version"),
                "software_version": payload.get("software_version"),
            },
            "metadata": {
                "pdb_id": pdb_id,
                "chain_count": len(chains),
                "note": "tm_type is 'alpha', 'beta', or 'non_tm'. Compare "
                "with OPM_search_structures (geometry/energetics) or "
                "TopDB_get_topology (curated per-region evidence).",
                "source": "PDBTM (Protein Data Bank of Transmembrane Proteins)",
            },
        }
