"""
AlphaFill tool for ToolUniverse — ligands/cofactors transplanted into AlphaFold models.

AlphaFold predicts apo (ligand-free) protein structures. AlphaFill enriches them by
transplanting ligands, cofactors, and ions from homologous experimental PDB structures
into the predicted model. For a UniProt accession, this tool reports which small
molecules can be modeled into its AlphaFold structure, from which PDB entries, and at
what local fit quality — useful for hypothesizing cofactor/ligand/drug binding that the
bare AlphaFold model does not show.

API: https://alphafill.eu/v1/aff/{uniprot}/json  (public, no authentication, JSON)
"""

from collections import defaultdict
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ALPHAFILL_BASE = "https://alphafill.eu/v1/aff"


@register_tool("AlphaFillTransplantsTool")
class AlphaFillTransplantsTool(BaseTool):
    """List ligands/cofactors AlphaFill transplants into a UniProt's AlphaFold model."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        uniprot = (arguments.get("uniprot") or "").strip().upper()
        if not uniprot:
            return {
                "status": "error",
                "error": "'uniprot' accession is required (e.g. 'P00520')",
            }

        try:
            resp = requests.get(
                f"{ALPHAFILL_BASE}/{uniprot}/json",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {"uniprot": uniprot, "transplants": []},
                    "metadata": {
                        "uniprot": uniprot,
                        "note": f"No AlphaFill model for '{uniprot}' (no AlphaFold model or no transplants).",
                    },
                }
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"AlphaFill request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"AlphaFill request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "AlphaFill returned a non-JSON response",
            }

        if not isinstance(payload, dict):
            payload = {}
        hits = payload.get("hits", [])
        # Aggregate transplanted molecules by compound, keeping the best (lowest
        # local RMSD) instance and the set of source PDB entries.
        agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "best_local_rmsd": None, "source_pdb_ids": set()}
        )
        for hit in hits:
            pdb_id = hit.get("pdb_id")
            for transplant in hit.get("transplants", []) or []:
                cid = transplant.get("compound_id") or transplant.get("analogue_id")
                if not cid:
                    continue
                rec = agg[cid]
                rec["count"] += 1
                if pdb_id:
                    rec["source_pdb_ids"].add(pdb_id)
                rmsd = transplant.get("local_rmsd")
                if isinstance(rmsd, (int, float)) and (
                    rec["best_local_rmsd"] is None or rmsd < rec["best_local_rmsd"]
                ):
                    rec["best_local_rmsd"] = rmsd

        transplants = sorted(
            (
                {
                    "compound_id": cid,
                    "occurrences": rec["count"],
                    "best_local_rmsd": rec["best_local_rmsd"],
                    "source_pdb_ids": sorted(rec["source_pdb_ids"])[:10],
                }
                for cid, rec in agg.items()
            ),
            key=lambda x: -x["occurrences"],
        )
        return {
            "status": "success",
            "data": {
                "uniprot": uniprot,
                "alphafill_version": payload.get("alphafill_version"),
                "n_homolog_hits": len(hits),
                "transplants": transplants,
            },
            "metadata": {
                "uniprot": uniprot,
                "distinct_ligands": len(transplants),
                "note": "compound_id is the PDB chemical component (ligand/cofactor/ion) code; lower best_local_rmsd = better fit",
                "source": "AlphaFill",
            },
        }
