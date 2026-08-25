# codon_usage_tool.py
"""
Codon usage table tool for ToolUniverse.

Supplies species-specific codon usage from the Codon Usage Database
(Kazusa), which derives tables from GenBank coding sequences and indexes
them by NCBI taxonomy identifier.

ToolUniverse already codon-optimizes sequences with DNA_codon_optimize, but
that tool carries hardcoded tables for four species (human, E. coli, mouse,
yeast). This supplies the underlying reference data for any organism with a
table, so optimization targets are not limited to those four.

Data: https://www.kazusa.or.jp/codon/
No authentication required.
"""

import re
from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

KAZUSA_URL = "https://www.kazusa.or.jp/codon/cgi-bin/showcodon.cgi"

# Rows look like: "Leu     CTG    1611801.00     39.53      0.00"
_ROW_RE = re.compile(r"^([A-Za-z]{3})\s+([ACGTU]{3})\s+([\d.]+)\s+([\d.]+)", re.M)
_SPECIES_RE = re.compile(r"<i>([^<]+)</i>")

# Stop codons are reported under this label by the source.
_STOP_LABEL = "End"


def _parse_table(text: str) -> List[Dict[str, Any]]:
    """Parse the codon rows out of a Kazusa GCG-style report."""
    rows: List[Dict[str, Any]] = []
    for amino_acid, codon, count, per_thousand in _ROW_RE.findall(text):
        rows.append(
            {
                "codon": codon.replace("U", "T"),
                "amino_acid": amino_acid,
                "count": int(float(count)),
                "per_thousand": float(per_thousand),
            }
        )
    return rows


def _add_fractions(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add each codon's share of its amino acid's total usage.

    The source reports a fraction column but leaves it at zero in this
    output style, so it is computed here from the counts.
    """
    totals: Dict[str, int] = {}
    for row in rows:
        totals[row["amino_acid"]] = totals.get(row["amino_acid"], 0) + row["count"]
    for row in rows:
        total = totals.get(row["amino_acid"], 0)
        row["fraction"] = round(row["count"] / total, 4) if total else 0.0
    return rows


@register_tool("CodonUsageTool")
class CodonUsageTool(BaseTool):
    """
    Tool for retrieving species-specific codon usage tables.

    Supports the full 64-codon table for an organism, and the most-used
    codon per amino acid for codon optimization.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get("operation", "get_table")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the codon usage lookup."""
        try:
            if self.operation == "get_table":
                return self._get_table(arguments)
            if self.operation == "get_optimal_codons":
                return self._get_optimal_codons(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Codon usage request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the Codon Usage Database.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"Codon Usage Database returned HTTP {code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying codon usage: {str(e)}",
            }

    def _fetch(self, taxid: str) -> Dict[str, Any]:
        """Fetch and parse one species table, or return an error dict."""
        response = requests.get(
            KAZUSA_URL,
            params={"species": taxid, "aa": 1, "style": "GCG"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.text

        rows = _add_fractions(_parse_table(text))
        if not rows:
            return {
                "status": "error",
                "error": f"No codon usage table for NCBI taxid '{taxid}'. Tables "
                "are built per sequenced organism and are often held at strain "
                "rather than species level: E. coli is 83333 (K-12), not 562. "
                "Try a strain-level taxid, or a well-sequenced relative.",
            }

        species = _SPECIES_RE.search(text)
        return {
            "rows": rows,
            "species": species.group(1).strip() if species else None,
        }

    @staticmethod
    def _taxid(arguments: Dict[str, Any]) -> Optional[str]:
        taxid = arguments.get("taxid")
        if taxid is None or str(taxid).strip() == "":
            return None
        return str(taxid).strip()

    def _get_table(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the full 64-codon usage table for an organism."""
        taxid = self._taxid(arguments)
        if not taxid:
            return {
                "status": "error",
                "error": "taxid is required: an NCBI taxonomy identifier such as "
                "9606 (human), 83333 (E. coli K-12), 4932 (yeast), "
                "7227 (fruit fly), 3702 (Arabidopsis).",
            }

        fetched = self._fetch(taxid)
        if fetched.get("status") == "error":
            return fetched

        rows = fetched["rows"]
        amino_acid = arguments.get("amino_acid")
        if amino_acid:
            wanted = str(amino_acid).strip().lower()
            rows = [r for r in rows if r["amino_acid"].lower() == wanted]
            if not rows:
                return {
                    "status": "error",
                    "error": f"No codons found for amino acid '{amino_acid}'. Use "
                    "three-letter codes such as 'Leu', 'Ala', or 'End' for stop "
                    "codons.",
                }

        rows = sorted(rows, key=lambda r: (r["amino_acid"], -r["count"]))
        total_codons = sum(r["count"] for r in fetched["rows"])

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "taxid": taxid,
                "species": fetched["species"],
                "codons_returned": len(rows),
                "total_codons_counted": total_codons,
                "amino_acid_filter": amino_acid,
                "note": "fraction is each codon's share of its amino acid's "
                "usage; per_thousand is its frequency across all codons.",
                "source": "Codon Usage Database (Kazusa)",
            },
        }

    def _get_optimal_codons(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the most-used codon for each amino acid in an organism."""
        taxid = self._taxid(arguments)
        if not taxid:
            return {
                "status": "error",
                "error": "taxid is required: an NCBI taxonomy identifier such as "
                "9606 (human) or 83333 (E. coli K-12).",
            }

        fetched = self._fetch(taxid)
        if fetched.get("status") == "error":
            return fetched

        best: Dict[str, Dict[str, Any]] = {}
        for row in fetched["rows"]:
            current = best.get(row["amino_acid"])
            if current is None or row["count"] > current["count"]:
                best[row["amino_acid"]] = row

        include_stop = bool(arguments.get("include_stop_codons"))
        rows = [
            {
                "amino_acid": aa,
                "preferred_codon": row["codon"],
                "fraction": row["fraction"],
                "per_thousand": row["per_thousand"],
                "count": row["count"],
            }
            for aa, row in sorted(best.items())
            if include_stop or aa != _STOP_LABEL
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "taxid": taxid,
                "species": fetched["species"],
                "amino_acids": len(rows),
                "note": "Highest-usage codon per amino acid. Optimizing every "
                "position to these codons maximizes codon adaptation but can "
                "deplete tRNA pools and disrupt folding; sampling in proportion "
                "to fraction is often preferred.",
                "source": "Codon Usage Database (Kazusa)",
            },
        }
