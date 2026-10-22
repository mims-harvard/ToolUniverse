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
            # Atlas allele codes are conventionally uppercase (e.g. "A0101",
            # "DRB1_01_01") and matched by exact string equality below, so a
            # case-different but otherwise well-formed input (e.g. "a0201")
            # previously matched nothing -- confirmed live. Normalize case
            # here, matching the existing mhc_class normalization pattern.
            allele = (arguments.get("allele") or "").strip().upper()
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

            include_sequence = arguments.get("include_sequence", False)
            if not isinstance(include_sequence, bool):
                return {"status": "error", "error": "include_sequence must be a boolean"}

            limit = arguments.get("limit", 100)
            offset = arguments.get("offset", 0)
            if limit is None:
                limit = 100
            if offset is None:
                offset = 0
            if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
                return {"status": "error", "error": "limit must be an integer from 1 to 1000"}
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                return {"status": "error", "error": "offset must be a non-negative integer"}

            return self._fetch_ligands(
                allele, mhc_class, include_sequence, limit, offset
            )
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
        offset: int,
    ) -> Dict[str, Any]:
        result = self._fetch_text(_PEPTIDE_URLS[mhc_class])
        if result.get("status") == "error":
            return result

        lines = result["text"].splitlines()
        if not lines:
            return {"status": "error", "error": "Empty peptide table"}

        header = lines[0].split("\t")
        has_core = len(header) >= 3 and header[2].lower() == "core"

        matches: List[Dict[str, str]] = []
        for line in lines[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            if cols[0] != allele:
                continue
            rec = {"peptide": cols[1]}
            if has_core and len(cols) >= 3:
                rec["core"] = cols[2]
            matches.append(rec)

        if not matches:
            return {
                "status": "error",
                "error": (
                    f"No ligands found for allele '{allele}' in MHC class {mhc_class}. "
                    "Use the atlas allele format (e.g. 'A0101', 'B0702' for class I; "
                    "'DRB1_01_01' for class II)."
                ),
            }

        peptides = matches[offset : offset + limit]
        next_offset = offset + len(peptides)
        has_more = next_offset < len(matches)

        sequence = None
        sequence_error = None
        if include_sequence:
            sequence, sequence_error = self._fetch_sequence(allele, mhc_class)

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
                "total_matches": len(matches),
                "total_matches_is_exact": True,
                "returned": len(peptides),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "truncated": offset > 0 or has_more,
                "result_set_complete": offset == 0 and len(peptides) == len(matches),
                "has_core_column": has_core,
                "sequence_requested": include_sequence,
                "sequence_found": sequence is not None,
                "sequence_error": sequence_error,
                "requested_scope_complete": not include_sequence or sequence is not None,
            },
        }

    def _fetch_sequence(self, allele: str, mhc_class: str):
        url = _SEQUENCE_URLS.get(mhc_class)
        if not url:
            return None, f"No sequence table is configured for MHC class {mhc_class}"
        result = self._fetch_text(url)
        if result.get("status") == "error":
            return None, result.get("error")
        for line in result["text"].splitlines()[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) >= 2 and cols[0] == allele:
                return cols[1], None
        return None, f"No MHC protein sequence found for allele '{allele}'"
