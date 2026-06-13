"""MHC Motif Atlas - naturally-presented MHC ligand peptides tool.

The MHC Motif Atlas (mhcmotifatlas.org) provides curated lists of
naturally-presented MHC ligand peptides per allele (MHC class I and class II)
across human, mouse, cattle and chicken, together with per-allele MHC protein
sequences. These data support binding-motif and specificity analysis.

This tool retrieves ligand peptides for a given allele and, optionally, the
MHC protein sequence for that allele. All endpoints are keyless plain-text
TSV files.

Endpoints:
- http://mhcmotifatlas.org/data/classI/all_peptides.txt        (Allele, Peptide)
- http://mhcmotifatlas.org/data/classII/MS/Peptides/all_peptides.txt
                                                  (Allele, Peptide, Core)
- http://mhcmotifatlas.org/data/classI/MHC_I_sequences.txt     (Allele, Sequence)
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

_BASE_URL = "http://mhcmotifatlas.org/data"
_REQUEST_TIMEOUT = 30

_PEPTIDE_URLS = {
    "I": f"{_BASE_URL}/classI/all_peptides.txt",
    "II": f"{_BASE_URL}/classII/MS/Peptides/all_peptides.txt",
}
_SEQUENCE_URLS = {
    "I": f"{_BASE_URL}/classI/MHC_I_sequences.txt",
    "II": f"{_BASE_URL}/classII/MHC_II_sequences.txt",
}


@register_tool("MHCMotifAtlasTool")
class MHCMotifAtlasTool(BaseTool):
    """Retrieve naturally-presented MHC ligand peptides per allele."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            allele = (arguments.get("allele") or "").strip()
            if not allele:
                return {
                    "status": "error",
                    "error": "allele is required (e.g. 'A0101' for class I, 'DRB1_01_01' for class II)",
                }

            mhc_class = self._normalize_class(arguments.get("mhc_class", "I"))
            if mhc_class not in ("I", "II"):
                return {
                    "status": "error",
                    "error": "mhc_class must be 'I' or 'II'",
                }

            include_sequence = bool(arguments.get("include_sequence", False))

            try:
                limit = int(arguments.get("limit", 100))
            except (TypeError, ValueError):
                limit = 100
            limit = max(1, min(1000, limit))

            return self._fetch_ligands(allele, mhc_class, include_sequence, limit)
        except Exception as exc:  # never raise
            return {"status": "error", "error": f"Unexpected error: {exc}"}

    @staticmethod
    def _normalize_class(value: Any) -> str:
        s = str(value).strip().upper()
        s = s.replace("MHC-", "").replace("CLASS", "").replace("MHC", "").strip()
        if s in ("1", "I"):
            return "I"
        if s in ("2", "II"):
            return "II"
        return s

    def _fetch_text(self, url: str) -> Dict[str, Any]:
        try:
            resp = request_with_retry(requests, "GET", url, timeout=_REQUEST_TIMEOUT)
        except Exception as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code} fetching {url}",
            }
        return {"status": "success", "text": resp.text}

    def _fetch_ligands(
        self,
        allele: str,
        mhc_class: str,
        include_sequence: bool,
        limit: int,
    ) -> Dict[str, Any]:
        result = self._fetch_text(_PEPTIDE_URLS[mhc_class])
        if result.get("status") == "error":
            return result

        lines = result["text"].splitlines()
        if not lines:
            return {"status": "error", "error": "Empty peptide table"}

        header = lines[0].split("\t")
        has_core = len(header) >= 3 and header[2].lower() == "core"

        peptides: List[Dict[str, str]] = []
        total_matches = 0
        for line in lines[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            if cols[0] != allele:
                continue
            total_matches += 1
            if len(peptides) < limit:
                rec = {"peptide": cols[1]}
                if has_core and len(cols) >= 3:
                    rec["core"] = cols[2]
                peptides.append(rec)

        if total_matches == 0:
            return {
                "status": "error",
                "error": (
                    f"No ligands found for allele '{allele}' in MHC class {mhc_class}. "
                    "Use the atlas allele format (e.g. 'A0101', 'B0702' for class I; "
                    "'DRB1_01_01' for class II)."
                ),
            }

        sequence = None
        if include_sequence:
            sequence = self._fetch_sequence(allele, mhc_class)

        return {
            "status": "success",
            "data": {
                "allele": allele,
                "mhc_class": mhc_class,
                "peptides": peptides,
                "sequence": sequence,
            },
            "metadata": {
                "source": "MHC Motif Atlas (mhcmotifatlas.org)",
                "total_matches": total_matches,
                "returned": len(peptides),
                "limit": limit,
                "truncated": total_matches > len(peptides),
                "has_core_column": has_core,
            },
        }

    def _fetch_sequence(self, allele: str, mhc_class: str):
        url = _SEQUENCE_URLS.get(mhc_class)
        if not url:
            return None
        result = self._fetch_text(url)
        if result.get("status") == "error":
            return None
        for line in result["text"].splitlines()[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) >= 2 and cols[0] == allele:
                return cols[1]
        return None
