# skempi_tool.py
"""
SKEMPI 2.0 experimental binding affinity tool for ToolUniverse.

SKEMPI is the reference set of *measured* changes in protein-protein binding
affinity on mutation: ~7,000 mutations across ~350 complexes, each with the
wild-type and mutant dissociation constants from the primary literature.

ToolUniverse can predict the effect of a mutation on binding several ways
(DynaMut2, ESM, AlphaMissense and related tools) but had no measured values
to check a prediction against. This tool supplies that ground truth, so a
predicted ddG can be compared with an experimental one for the same complex
and substitution.

ddG is derived from the deposited affinities as RT.ln(Kd_mut / Kd_wt), using
the temperature recorded for each measurement. Positive ddG means the
mutation weakens binding.

Data: https://life.bsc.es/pid/skempi2/database/download/skempi_v2.csv
No authentication required.
"""

import csv
import io
import math
import re
import threading
from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

SKEMPI_CSV_URL = "https://life.bsc.es/pid/skempi2/database/download/skempi_v2.csv"

# Gas constant in kcal/(mol.K), matching the units ddG is reported in.
_R_KCAL = 1.987204258640832e-3
_DEFAULT_TEMPERATURE_K = 298.0


def _to_float(value: Any) -> Optional[float]:
    """Parse a numeric field, tolerating blanks and trailing annotations."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.match(r"[-+]?[\d.]+(?:[eE][-+]?\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _temperature(value: Any) -> float:
    """Read the measurement temperature, defaulting to 298 K when absent."""
    parsed = _to_float(value)
    if parsed is None or parsed <= 0:
        return _DEFAULT_TEMPERATURE_K
    # A few records record Celsius-like values; treat those as room temperature.
    return parsed if parsed > 100 else parsed + 273.15


def _ddg(
    kd_wt: Optional[float], kd_mut: Optional[float], temp_k: float
) -> Optional[float]:
    """Compute ddG in kcal/mol from wild-type and mutant dissociation constants."""
    if not kd_wt or not kd_mut or kd_wt <= 0 or kd_mut <= 0:
        return None
    return round(_R_KCAL * temp_k * math.log(kd_mut / kd_wt), 3)


def _parse_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Normalize one SKEMPI record and derive its ddG."""
    pdb_field = (row.get("#Pdb") or "").strip()
    parts = pdb_field.split("_")
    kd_wt = _to_float(row.get("Affinity_wt_parsed"))
    kd_mut = _to_float(row.get("Affinity_mut_parsed"))
    temp_k = _temperature(row.get("Temperature"))
    mutations = [m for m in (row.get("Mutation(s)_cleaned") or "").split(",") if m]

    return {
        "pdb_id": parts[0] if parts else None,
        "partner_chains": parts[1:] if len(parts) > 1 else [],
        "mutations": mutations,
        "mutation_count": len(mutations),
        "location": (row.get("iMutation_Location(s)") or "").strip() or None,
        "protein_1": (row.get("Protein 1") or "").strip() or None,
        "protein_2": (row.get("Protein 2") or "").strip() or None,
        "kd_wildtype_M": kd_wt,
        "kd_mutant_M": kd_mut,
        "temperature_K": temp_k,
        "ddg_kcal_per_mol": _ddg(kd_wt, kd_mut, temp_k),
        "pubmed_id": (row.get("Reference") or "").strip() or None,
    }


@register_tool("SKEMPITool")
class SKEMPITool(BaseTool):
    """
    Tool for retrieving measured protein-protein binding affinity changes.

    Supports listing every measured mutation for a PDB complex, looking up a
    specific substitution, and searching by protein name.

    No authentication required.
    """

    _cache: Optional[List[Dict[str, Any]]] = None
    _cache_lock = threading.Lock()

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_by_structure"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SKEMPI lookup."""
        try:
            if self.operation == "search_by_structure":
                return self._search_by_structure(arguments)
            if self.operation == "get_mutation":
                return self._get_mutation(arguments)
            if self.operation == "search_by_protein":
                return self._search_by_protein(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SKEMPI request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SKEMPI. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"SKEMPI returned HTTP {code}"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying SKEMPI: {str(e)}"}

    def _records(self) -> List[Dict[str, Any]]:
        """Return the parsed dataset, downloading it once per process."""
        if SKEMPITool._cache is not None:
            return SKEMPITool._cache
        with SKEMPITool._cache_lock:
            if SKEMPITool._cache is None:
                response = requests.get(SKEMPI_CSV_URL, timeout=self.timeout)
                response.raise_for_status()
                reader = csv.DictReader(
                    io.StringIO(response.text), delimiter=";"
                )
                SKEMPITool._cache = [_parse_row(r) for r in reader]
        return SKEMPITool._cache

    @staticmethod
    def _summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize the ddG distribution over a set of measurements."""
        values = [
            r["ddg_kcal_per_mol"]
            for r in rows
            if r["ddg_kcal_per_mol"] is not None
        ]
        if not values:
            return {"measurements_with_ddg": 0}
        return {
            "measurements_with_ddg": len(values),
            "ddg_min": min(values),
            "ddg_max": max(values),
            "ddg_mean": round(sum(values) / len(values), 3),
            "destabilizing_count": sum(1 for v in values if v > 0),
            "stabilizing_count": sum(1 for v in values if v < 0),
        }

    def _limit(self, arguments: Dict[str, Any], default: int = 50) -> int:
        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = default
        return min(limit, 500)

    def _search_by_structure(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all measured mutations for a PDB complex."""
        pdb_id = (arguments.get("pdb_id") or "").strip().upper()
        if not pdb_id:
            return {
                "status": "error",
                "error": "pdb_id is required, e.g. '1CSE' (subtilisin/eglin c) "
                "or '1VFB' (antibody/lysozyme).",
            }

        rows = [r for r in self._records() if (r["pdb_id"] or "").upper() == pdb_id]
        if not rows:
            return {
                "status": "error",
                "error": f"No SKEMPI measurements for PDB '{pdb_id}'. SKEMPI "
                "covers roughly 350 protein-protein complexes; not every PDB "
                "entry has binding measurements.",
            }

        if arguments.get("only_single_mutants"):
            rows = [r for r in rows if r["mutation_count"] == 1]

        limit = self._limit(arguments)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": dict(
                self._summarize(rows),
                pdb_id=pdb_id,
                total_matching=len(rows),
                returned=len(rows[:limit]),
                partners=[rows[0]["protein_1"], rows[0]["protein_2"]],
                note="ddG derived as RT.ln(Kd_mut/Kd_wt); positive weakens binding.",
                source="SKEMPI 2.0",
            ),
        }

    def _get_mutation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up measurements for a specific substitution in a complex."""
        pdb_id = (arguments.get("pdb_id") or "").strip().upper()
        mutation = (arguments.get("mutation") or "").strip()
        if not pdb_id or not mutation:
            return {
                "status": "error",
                "error": "pdb_id and mutation are both required. Mutations use "
                "SKEMPI's cleaned notation: wild-type residue, chain, position, "
                "mutant residue, e.g. 'LI38G' for Leu38->Gly on chain I.",
            }

        wanted = mutation.upper()
        rows = [
            r
            for r in self._records()
            if (r["pdb_id"] or "").upper() == pdb_id
            and any(m.upper() == wanted for m in r["mutations"])
        ]
        if not rows:
            return {
                "status": "error",
                "error": f"No SKEMPI measurement for mutation '{mutation}' in "
                f"PDB '{pdb_id}'. Use SKEMPI_search_by_structure to list the "
                "mutations measured for this complex.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": dict(
                self._summarize(rows),
                pdb_id=pdb_id,
                mutation=mutation,
                measurement_count=len(rows),
                note="Multiple rows mean the substitution was measured more "
                "than once, or appears within different mutation sets.",
                source="SKEMPI 2.0",
            ),
        }

    def _search_by_protein(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find complexes involving a named protein."""
        name = (arguments.get("name") or "").strip().lower()
        if not name:
            return {
                "status": "error",
                "error": "name is required, e.g. 'lysozyme', 'barnase', "
                "'trypsin'. Matched case-insensitively against both partners.",
            }

        rows = [
            r
            for r in self._records()
            if name in (r["protein_1"] or "").lower()
            or name in (r["protein_2"] or "").lower()
        ]
        if not rows:
            return {
                "status": "error",
                "error": f"No SKEMPI complexes involving a protein matching "
                f"'{name}'.",
            }

        structures = sorted({r["pdb_id"] for r in rows if r["pdb_id"]})
        limit = self._limit(arguments)
        return {
            "status": "success",
            "data": rows[:limit],
            "metadata": dict(
                self._summarize(rows),
                query=name,
                total_matching=len(rows),
                returned=len(rows[:limit]),
                structures=structures[:50],
                structure_count=len(structures),
                source="SKEMPI 2.0",
            ),
        }
