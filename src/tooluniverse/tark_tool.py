"""
Ensembl Tark tools for ToolUniverse — transcript archive + MANE mapping.

Tark (Transcript Archive, EMBL-EBI/Ensembl) is the authoritative archive of
transcript sequences and versions across Ensembl, RefSeq and GENCODE, including
the MANE Select / MANE Plus Clinical pairings (ENST <-> NM). It answers two
clinical-genomics questions the main Ensembl REST does not expose directly:
  - "What is the MANE Select transcript for this gene, and its RefSeq equivalent?"
  - "Give me the archived record (versions, checksums, UTRs) for this transcript."

API: https://tark.ensembl.org/api  (public, no authentication, JSON)
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

TARK_BASE = "https://tark.ensembl.org/api"

# The MANE list is a flat ~19k-row table returned in a single request. Cache it
# at module level so repeated gene lookups don't re-download it each call.
_MANE_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_mane_list(timeout: int) -> List[Dict[str, Any]]:
    global _MANE_CACHE
    if _MANE_CACHE is None:
        resp = requests.get(
            f"{TARK_BASE}/transcript/manelist/",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        _MANE_CACHE = data if isinstance(data, list) else data.get("results", [])
    return _MANE_CACHE


@register_tool("TarkManeTranscriptsTool")
class TarkManeTranscriptsTool(BaseTool):
    """Look up MANE Select / Plus Clinical transcripts (ENST <-> RefSeq NM)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (arguments.get("gene") or "").strip()
        ensembl_id = (arguments.get("ensembl_id") or "").strip()
        refseq_id = (arguments.get("refseq_id") or "").strip()
        if not (gene or ensembl_id or refseq_id):
            return {
                "status": "error",
                "error": "Provide one of 'gene', 'ensembl_id', or 'refseq_id'.",
            }

        try:
            rows = _load_mane_list(self.timeout)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Tark request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Tark request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "Tark returned a non-JSON response"}

        ens_strip = ensembl_id.split(".")[0].upper()
        refseq_strip = refseq_id.split(".")[0].upper()
        gene_up = gene.upper()
        matches = [
            r
            for r in rows
            if (gene_up and (r.get("ens_gene_name") or "").upper() == gene_up)
            or (ens_strip and (r.get("ens_stable_id") or "").upper() == ens_strip)
            or (
                refseq_strip
                and (r.get("refseq_stable_id") or "").upper() == refseq_strip
            )
        ]
        results = [
            {
                "gene": r.get("ens_gene_name"),
                "mane_type": r.get("mane_type"),
                "ensembl_transcript": _versioned(
                    r.get("ens_stable_id"), r.get("ens_stable_id_version")
                ),
                "refseq_transcript": _versioned(
                    r.get("refseq_stable_id"), r.get("refseq_stable_id_version")
                ),
            }
            for r in matches
        ]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": len(results),
                "query": {
                    "gene": gene,
                    "ensembl_id": ensembl_id,
                    "refseq_id": refseq_id,
                },
                "source": "Ensembl Tark MANE list",
            },
        }


@register_tool("TarkTranscriptTool")
class TarkTranscriptTool(BaseTool):
    """Get the archived transcript record (versions, checksums, UTRs) by ENST id."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        stable_id = (arguments.get("stable_id") or "").strip()
        if not stable_id:
            return {
                "status": "error",
                "error": "'stable_id' (e.g. 'ENST00000380152') is required",
            }
        stable_id = stable_id.split(".")[0]

        try:
            resp = requests.get(
                f"{TARK_BASE}/transcript/",
                params={"stable_id": stable_id, "expand": "transcript_release_set"},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Tark request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Tark request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "Tark returned a non-JSON response"}

        results = payload.get("results", []) if isinstance(payload, dict) else []
        if not results:
            return {
                "status": "success",
                "data": [],
                "metadata": {"total_results": 0, "query_stable_id": stable_id},
            }
        records = [
            {
                "stable_id": _versioned(r.get("stable_id"), r.get("stable_id_version")),
                "assembly": r.get("assembly"),
                "biotype": r.get("biotype"),
                "region": r.get("loc_region"),
                "start": r.get("loc_start"),
                "end": r.get("loc_end"),
                "strand": r.get("loc_strand"),
                "transcript_checksum": r.get("transcript_checksum"),
                "releases": [
                    rel.get("shortname")
                    for rel in (r.get("transcript_release_set") or [])
                    if isinstance(rel, dict)
                ],
            }
            for r in results
        ]
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "total_results": len(records),
                "query_stable_id": stable_id,
                "source": "Ensembl Tark transcript archive",
            },
        }


def _versioned(stable_id: Optional[str], version: Any) -> Optional[str]:
    """Join a stable id with its version (e.g. ENST00000380152 + 8 -> ...152.8)."""
    if not stable_id:
        return None
    return f"{stable_id}.{version}" if version not in (None, "") else stable_id
