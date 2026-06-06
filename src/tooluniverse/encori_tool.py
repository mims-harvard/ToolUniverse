"""ENCORI / starBase miRNA-target interaction tool for ToolUniverse.

ENCORI (the Encyclopedia of RNA Interactomes, formerly starBase) aggregates
CLIP-seq-supported and computationally predicted miRNA-target interactions and
exposes them through a public REST API. ToolUniverse previously had no miRNA
target-lookup tool (skills had to fall back to bulk TargetScan/miRTarBase
downloads); this fills that gap.

API: https://rnasysu.com/encori/api/  (public, no authentication)
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ENCORI_URL = "https://rnasysu.com/encori/api/miRNATarget/"
# Columns flagged 1 when that prediction program supports the interaction.
_PROGRAMS = ["PITA", "RNA22", "miRmap", "microT", "miRanda", "PicTar", "TargetScan"]


@register_tool("ENCORITool")
class ENCORITool(BaseTool):
    """Look up miRNA-target interactions (CLIP-supported + predicted) from ENCORI."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mirna = (arguments.get("mirna") or "").strip()
        gene = (arguments.get("gene") or arguments.get("gene_symbol") or "").strip()
        if not mirna and not gene:
            return {
                "status": "error",
                "error": "Provide 'mirna' (e.g. 'hsa-miR-21-5p') to get its targets, "
                "or 'gene' (e.g. 'TP53') to get the miRNAs that target it.",
            }

        try:
            clip_min = int(arguments.get("clip_min", 1))
        except (TypeError, ValueError):
            clip_min = 1
        try:
            program_min = int(arguments.get("program_min", 1))
        except (TypeError, ValueError):
            program_min = 1
        try:
            limit = max(1, min(int(arguments.get("limit", 50)), 500))
        except (TypeError, ValueError):
            limit = 50

        params = {
            "assembly": arguments.get("assembly", "hg38"),
            "geneType": "mRNA",
            "miRNA": mirna or "all",
            "target": gene or "all",
            "clipExpNum": clip_min,
            "degraExpNum": 0,
            "pancancerNum": 0,
            "programNum": program_min,
            "program": "None",
            "cellType": "all",
        }

        try:
            resp = requests.get(ENCORI_URL, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"ENCORI API returned HTTP {resp.status_code}",
                }
            lines = [
                ln for ln in resp.text.splitlines() if ln and not ln.startswith("#")
            ]
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ENCORI API timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"ENCORI API request failed: {e}"}

        if len(lines) < 2:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "ENCORI (starBase)",
                    "query": mirna or gene,
                    "total": 0,
                    "note": "No interactions met the CLIP/prediction thresholds.",
                },
            }

        header = lines[0].split("\t")
        idx = {h: i for i, h in enumerate(header)}
        rows = []
        for ln in lines[1:]:
            f = ln.split("\t")
            if len(f) < len(header):
                continue
            programs = [p for p in _PROGRAMS if p in idx and f[idx[p]] == "1"]
            rows.append(
                {
                    "mirna": f[idx["miRNAname"]],
                    "gene": f[idx["geneName"]],
                    "gene_id": f[idx["geneID"]],
                    "clip_experiments": int(f[idx["clipExpNum"]] or 0),
                    "predicted_by": programs,
                    "n_programs": len(programs),
                    "pan_cancer_num": int(f[idx.get("pancancerNum", -1)] or 0)
                    if "pancancerNum" in idx
                    else None,
                }
            )

        # Strongest experimental support first (CLIP), then prediction breadth.
        rows.sort(key=lambda r: (r["clip_experiments"], r["n_programs"]), reverse=True)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": {
                "source": "ENCORI (starBase)",
                "query": mirna or gene,
                "direction": "miRNA->targets" if mirna else "gene->miRNAs",
                "total": len(rows),
                "returned": min(len(rows), limit),
                "interpretation": (
                    "clip_experiments = number of CLIP-seq experiments supporting the "
                    "site (experimental evidence; higher = stronger). predicted_by lists "
                    "the algorithms predicting it. CLIP-supported targets outrank "
                    "prediction-only ones."
                ),
            },
        }
