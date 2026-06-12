"""HLA Ligand Atlas - benign-tissue immunopeptidome reference tool.

The HLA Ligand Atlas (hla-ligand-atlas.org) is a curated reference of
HLA-presented peptides eluted from non-malignant ("benign") human tissues.
It is widely used to filter self-peptides during cancer neoantigen discovery.

This tool retrieves benign HLA ligands from the aggregated release table and
the companion donor-allele table. All endpoints are keyless and return
gzip-compressed (aggregated) or plain (donors) TSV files.

Endpoints (release 2020.12):
- https://hla-ligand-atlas.org/rel/2020.12/aggregated.tsv.gz
- https://hla-ligand-atlas.org/rel/2020.12/donors.tsv.gz
"""

from __future__ import annotations

import gzip
import io
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

_BASE_URL = "https://hla-ligand-atlas.org/rel/2020.12"
_REQUEST_TIMEOUT = 30


@register_tool("HLALigandAtlasTool")
class HLALigandAtlasTool(BaseTool):
    """Retrieve benign-tissue HLA-presented peptides from the HLA Ligand Atlas."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            operation = (
                (self.tool_config.get("fields") or {}).get("operation")
                or arguments.get("operation")
                or "get_benign_peptides"
            )
            if operation == "get_benign_peptides":
                return self._get_benign_peptides(arguments)
            if operation == "get_donors":
                return self._get_donors(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
            }
        except Exception as exc:  # never raise
            return {"status": "error", "error": f"Unexpected error: {exc}"}

    # ------------------------------------------------------------------ #
    # benign peptides (aggregated.tsv.gz)
    # ------------------------------------------------------------------ #
    def _get_benign_peptides(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        peptide = (arguments.get("peptide") or "").strip().upper()
        hla_class = (arguments.get("hla_class") or "").strip().upper()
        allele = (arguments.get("allele") or "").strip()
        tissue = (arguments.get("tissue") or "").strip().lower()

        try:
            limit = int(arguments.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(500, limit))

        if hla_class and hla_class not in ("HLA-I", "HLA-II"):
            return {
                "status": "error",
                "error": "hla_class must be 'HLA-I' or 'HLA-II'",
            }

        url = f"{_BASE_URL}/aggregated.tsv.gz"
        try:
            resp = request_with_retry(requests, "GET", url, timeout=_REQUEST_TIMEOUT)
        except Exception as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code} fetching aggregated table",
            }

        try:
            raw = gzip.decompress(resp.content)
            text = raw.decode("utf-8", errors="replace")
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Failed to decompress aggregated TSV: {exc}",
            }

        lines = text.splitlines()
        if not lines:
            return {"status": "error", "error": "Empty aggregated table"}

        header = lines[0].split("\t")
        rows: List[Dict[str, Any]] = []
        scanned = 0
        for line in lines[1:]:
            if not line:
                continue
            scanned += 1
            cols = line.split("\t")
            if len(cols) < 5:
                continue
            pep = cols[1]
            cls = cols[2]
            donor_alleles = cols[3]
            tissues = cols[4]

            if peptide and pep.upper() != peptide:
                continue
            if hla_class and cls.upper() != hla_class:
                continue
            if allele and allele not in donor_alleles:
                continue
            if tissue and tissue not in tissues.lower():
                continue

            rows.append(
                {
                    "peptide_sequence_id": cols[0],
                    "peptide_sequence": pep,
                    "hla_class": cls,
                    "donor_alleles": [a for a in donor_alleles.split(",") if a],
                    "tissues": [t for t in tissues.split(",") if t],
                }
            )
            if len(rows) >= limit:
                break

        return {
            "status": "success",
            "data": {"peptides": rows},
            "metadata": {
                "source": "HLA Ligand Atlas (release 2020.12)",
                "columns": header,
                "returned": len(rows),
                "rows_scanned": scanned,
                "limit": limit,
                "truncated": len(rows) >= limit,
                "filters": {
                    "peptide": peptide or None,
                    "hla_class": hla_class or None,
                    "allele": allele or None,
                    "tissue": tissue or None,
                },
            },
        }

    # ------------------------------------------------------------------ #
    # donors (donors.tsv.gz)
    # ------------------------------------------------------------------ #
    def _get_donors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        donor_filter = (arguments.get("donor") or "").strip()
        allele_filter = (arguments.get("allele") or "").strip()

        url = f"{_BASE_URL}/donors.tsv.gz"
        try:
            resp = request_with_retry(requests, "GET", url, timeout=_REQUEST_TIMEOUT)
        except Exception as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code} fetching donors table",
            }

        text = self._maybe_gunzip(resp.content)
        if text is None:
            return {
                "status": "error",
                "error": "Failed to read donors table",
            }

        lines = text.splitlines()
        if not lines:
            return {"status": "error", "error": "Empty donors table"}

        header = lines[0].split("\t")
        records: List[Dict[str, str]] = []
        for line in lines[1:]:
            if not line:
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            donor, hla_allele = cols[0], cols[1]
            if donor_filter and donor_filter not in donor:
                continue
            if allele_filter and allele_filter not in hla_allele:
                continue
            records.append({"donor": donor, "hla_allele": hla_allele})

        return {
            "status": "success",
            "data": {"donors": records},
            "metadata": {
                "source": "HLA Ligand Atlas (release 2020.12)",
                "columns": header,
                "returned": len(records),
                "filters": {
                    "donor": donor_filter or None,
                    "allele": allele_filter or None,
                },
            },
        }

    @staticmethod
    def _maybe_gunzip(content: bytes) -> Optional[str]:
        """Decode content, decompressing if it is gzip-framed."""
        try:
            if content[:2] == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                    content = gz.read()
            return content.decode("utf-8", errors="replace")
        except Exception:
            return None
