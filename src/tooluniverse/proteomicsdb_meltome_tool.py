"""ProteomicsDB meltome / thermal-proteome-profiling tool (live OData, keyless).

ProteomicsDB (https://www.proteomicsdb.org) exposes a keyless OData v2 API. This
module wraps its **meltome** (thermal proteome profiling / TPP) data: protein
melting curves whose inflection point (apparent melting temperature, Tm) shifts
when a ligand binds — the basis of CETSA/TPP target deconvolution. It is kept in
its own module, disjoint from the existing ``proteomicsdb_tool.py`` (expression /
search / peptides).

``ProteomicsDBGetProteinMeltomeTool`` (ProteomicsDB_get_protein_meltome): given a
gene symbol or UniProt accession, return the protein's melting curves with their
apparent Tm and fit quality.

COVERAGE NOTE: the meltome is a soluble-proteome resource. Membrane proteins —
including most GPCRs (e.g. GLP1R returns zero curves) — are typically absent.
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE = "https://www.proteomicsdb.org/proteomicsdb/logic/api_v2/api.xsodata"
_TIMEOUT = 30
_MELTING_CURVE_TYPE_ID = 2  # ProteomicsDB curve type for protein melting curves
_TM_MIN, _TM_MAX = 30.0, 90.0  # plausible Tm range (deg C) for the inflection param


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _num(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _odata_get(path: str) -> List[Dict[str, Any]]:
    """GET an OData path under the ProteomicsDB API; return the results list."""
    resp = requests.get(f"{_BASE}{path}", timeout=_TIMEOUT)
    resp.raise_for_status()
    return (resp.json().get("d") or {}).get("results", [])


def _apparent_tm(fitted: List[Dict[str, Any]]) -> Optional[float]:
    """The melting-curve inflection parameter is the fitted value in the Tm range."""
    temps = [
        v
        for p in fitted
        if (v := _num(p.get("VALUE"))) is not None and _TM_MIN < v < _TM_MAX
    ]
    return round(temps[-1], 2) if temps else None


@register_tool(
    "ProteomicsDBGetProteinMeltomeTool",
    config={
        "name": "ProteomicsDB_get_protein_meltome",
        "type": "ProteomicsDBGetProteinMeltomeTool",
        "description": (
            "Get a protein's thermal proteome profiling (meltome / TPP) melting "
            "curves from ProteomicsDB by gene symbol or UniProt accession. Each "
            "curve yields an apparent melting temperature (Tm) and fit quality "
            "(R^2 / p-value); a ligand-induced Tm shift is the basis of CETSA/TPP "
            "target deconvolution. Keyless. NOTE: the meltome covers SOLUBLE "
            "proteins — most membrane GPCRs (e.g. GLP1R) have no data."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": ["string", "null"],
                    "description": "HGNC gene symbol, e.g. 'MAPK1'. Provide this OR uniprot_accession.",
                },
                "uniprot_accession": {
                    "type": ["string", "null"],
                    "description": "UniProt accession, e.g. 'P28482'. Provide this OR gene_symbol.",
                },
                "max_curves": {
                    "type": "integer",
                    "description": "Max melting curves to return (default 25, max 200).",
                },
            },
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "properties": {
                                "gene_name": {"type": ["string", "null"]},
                                "uniprot": {"type": ["string", "null"]},
                                "protein_name": {"type": ["string", "null"]},
                                "protein_id": {"type": ["integer", "null"]},
                                "n_melting_curves": {"type": "integer"},
                                "median_apparent_tm_celsius": {
                                    "type": ["number", "null"]
                                },
                                "curves": {"type": "array"},
                            },
                        },
                        "metadata": {"type": "object"},
                    },
                    "required": ["status", "data"],
                },
                {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "error": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["status", "error"],
                },
            ]
        },
        "test_examples": [
            {"gene_symbol": "MAPK1"},
            {"gene_symbol": "CDK2", "max_curves": 5},
            {"uniprot_accession": "P28482"},
        ],
    },
)
class ProteomicsDBGetProteinMeltomeTool(BaseTool):
    """Fetch ProteomicsDB meltome (TPP) melting curves for a protein."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (arguments.get("gene_symbol") or "").strip()
        acc = (arguments.get("uniprot_accession") or "").strip()
        if not gene and not acc:
            return _err("Provide gene_symbol or uniprot_accession")
        try:
            max_curves = int(arguments.get("max_curves", 25))
        except (TypeError, ValueError):
            max_curves = 25
        max_curves = max(1, min(200, max_curves))

        pfilter = f"UNIQUE_IDENTIFIER eq '{acc}'" if acc else f"GENE_NAME eq '{gene}'"
        try:
            proteins = _odata_get(
                f"/Protein?$filter={requests.utils.quote(pfilter)}&$format=json&$top=1"
            )
        except requests.RequestException as exc:
            return _err(f"ProteomicsDB protein lookup failed: {exc}", url=_BASE)
        except ValueError as exc:
            return _err(f"ProteomicsDB returned non-JSON: {exc}", url=_BASE)

        if not proteins:
            return _err(f"No ProteomicsDB protein for {acc or gene!r}", url=_BASE)
        protein = proteins[0]
        pid = protein.get("PROTEIN_ID")

        cfilter = f"PROTEIN_ID eq {pid} and CURVE_TYPE_ID eq {_MELTING_CURVE_TYPE_ID}"
        try:
            curves = _odata_get(
                f"/Curve?$filter={requests.utils.quote(cfilter)}"
                f"&$expand=FittedParameters&$format=json&$top={max_curves}"
            )
        except requests.RequestException as exc:
            return _err(f"ProteomicsDB curve lookup failed: {exc}", url=_BASE)
        except ValueError as exc:
            return _err(f"ProteomicsDB returned non-JSON: {exc}", url=_BASE)

        records: List[Dict[str, Any]] = []
        for c in curves:
            fitted = (c.get("FittedParameters") or {}).get("results") or []
            records.append(
                {
                    "curve_id": c.get("CURVE_ID"),
                    "apparent_tm_celsius": _apparent_tm(fitted),
                    "r_squared": _num(c.get("COD")),
                    "p_value": _num(c.get("P_VALUE")),
                    "bic": _num(c.get("BIC")),
                    "scope": c.get("SCOPE"),
                    "fitted_parameter_values": [p.get("VALUE") for p in fitted],
                }
            )

        tms = sorted(
            r["apparent_tm_celsius"]
            for r in records
            if r["apparent_tm_celsius"] is not None
        )
        median_tm = tms[len(tms) // 2] if tms else None

        return {
            "status": "success",
            "data": {
                "gene_name": protein.get("GENE_NAME"),
                "uniprot": protein.get("UNIQUE_IDENTIFIER"),
                "protein_name": protein.get("PROTEIN_NAME"),
                "protein_id": pid,
                "n_melting_curves": len(records),
                "median_apparent_tm_celsius": median_tm,
                "curves": records,
            },
            "metadata": {
                "source": "ProteomicsDB meltome (thermal proteome profiling)",
                "url": f"{_BASE}/Protein({pid})",
                "curve_type": "melting curve (CURVE_TYPE_ID=2)",
                "note": (
                    "apparent_tm_celsius is the inflection-point parameter of each fitted "
                    "melting curve. Soluble-proteome resource; membrane GPCRs are typically absent."
                ),
            },
        }
