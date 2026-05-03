"""ESMFold protein structure prediction tool.

Uses the ESM Metagenomic Atlas API to predict protein 3D structure
from amino acid sequence using the ESMFold language model.
Returns per-residue pLDDT confidence scores and summary statistics.

API: https://api.esmatlas.com/foldSequence/v1/pdb/
No authentication required. Max sequence length ~400 aa for fast results.
"""

import re
import urllib.request
from typing import Any, Dict

from tooluniverse.tool_registry import register_tool

ESMFOLD_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"


def _clean_sequence(raw: str) -> str:
    """Clean a protein sequence: remove FASTA headers, whitespace, numbers."""
    lines = raw.strip().splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            continue
        cleaned.append(line)
    seq = "".join(cleaned).upper()
    return "".join(ch for ch in seq if ch.isalpha())


def _parse_pdb_plddt(pdb_text: str) -> Dict[str, Any]:
    """Parse PDB text to extract per-residue pLDDT from B-factor column."""
    residue_plddt = {}
    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        atom_name = line[12:16].strip()
        if atom_name != "CA":
            continue
        res_name = line[17:20].strip()
        res_num = int(line[22:26].strip())
        plddt = float(line[60:66].strip())
        residue_plddt[res_num] = {"residue": res_name, "plddt": round(plddt, 2)}

    if not residue_plddt:
        return {"residues": [], "mean_plddt": 0.0, "length": 0}

    plddt_values = [v["plddt"] for v in residue_plddt.values()]
    mean_plddt = round(sum(plddt_values) / len(plddt_values), 2)

    confident = sum(1 for v in plddt_values if v >= 0.70)
    very_confident = sum(1 for v in plddt_values if v >= 0.90)
    low_confidence = sum(1 for v in plddt_values if v < 0.50)

    residues = []
    for num in sorted(residue_plddt.keys()):
        entry = residue_plddt[num]
        residues.append(
            {
                "position": num,
                "residue": entry["residue"],
                "plddt": entry["plddt"],
            }
        )

    return {
        "residues": residues,
        "mean_plddt": mean_plddt,
        "length": len(residue_plddt),
        "confident_residues": confident,
        "very_confident_residues": very_confident,
        "low_confidence_residues": low_confidence,
        "confident_fraction": round(confident / len(residue_plddt), 3),
    }


@register_tool(
    "ESMFoldTool",
    config={
        "name": "ESMFold_predict_structure",
        "type": "ESMFoldTool",
        "description": (
            "Predict protein 3D structure from amino acid sequence using ESMFold "
            "(Meta's ESM-2 language model). Returns per-residue pLDDT confidence "
            "scores (0-1 scale, higher=better) and summary statistics. Also returns "
            "the predicted PDB coordinate text. Fast single-sequence prediction "
            "(no MSA needed). Best for sequences under 400 residues. "
            "No authentication required."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": (
                        "Protein amino acid sequence in single-letter code. "
                        "Example: 'MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH'. "
                        "FASTA headers and whitespace are stripped. Max ~400 residues "
                        "recommended for fast results."
                    ),
                },
            },
            "required": ["sequence"],
        },
    },
)
class ESMFoldTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_seq = arguments.get("sequence", "")
        if not raw_seq:
            return {"status": "error", "error": "sequence is required"}

        seq = _clean_sequence(raw_seq)

        valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
        invalid = set(seq) - valid_aa
        if invalid:
            return {
                "status": "error",
                "error": "Invalid amino acid characters: {}. Use standard single-letter codes.".format(
                    ", ".join(sorted(invalid))
                ),
            }

        if len(seq) < 10:
            return {
                "status": "error",
                "error": "Sequence must be at least 10 amino acids long",
            }

        if len(seq) > 800:
            return {
                "status": "error",
                "error": "Sequence too long ({} aa). ESMFold works best under 400 residues, max 800.".format(
                    len(seq)
                ),
            }

        try:
            data = seq.encode("utf-8")
            req = urllib.request.Request(
                ESMFOLD_URL,
                data=data,
                headers={"Content-Type": "text/plain"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                pdb_text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "error": "ESMFold API returned HTTP {}: {}".format(e.code, e.reason),
            }
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error": "Failed to connect to ESMFold API: {}".format(str(e.reason)),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "ESMFold prediction failed: {}".format(str(e)),
            }

        if not pdb_text or "ATOM" not in pdb_text:
            return {
                "status": "error",
                "error": "ESMFold returned empty or invalid PDB output",
            }

        metrics = _parse_pdb_plddt(pdb_text)

        return {
            "status": "success",
            "data": {
                "sequence_length": len(seq),
                "mean_plddt": metrics["mean_plddt"],
                "confident_residues": metrics["confident_residues"],
                "very_confident_residues": metrics["very_confident_residues"],
                "low_confidence_residues": metrics["low_confidence_residues"],
                "confident_fraction": metrics["confident_fraction"],
                "per_residue_plddt": metrics["residues"],
                "pdb_text": pdb_text,
            },
        }
