"""Pep-Calc.com peptide property calculator tool.

Pep-Calc.com (https://pep-calc.com) computes physicochemical properties for
peptides that may carry N-terminal and C-terminal chemical modifications
(e.g. N-terminal acetylation, C-terminal amidation) and non-standard /
peptoid residues. This is the synthetic / therapeutic-peptide case that a
bare-sequence calculator (such as ExPASy ProtParam) cannot model, because the
terminal group changes the molecular formula, monoisotopic / average
molecular weight, isoelectric point (pI), and extinction coefficient.

API: https://api.pep-calc.com
  GET /peptide?seq={SEQ}&N_term={N}&C_term={C}
      -> seqString, seqList, nString, cString, nName, cName, nModified,
         cModified, seqLength, formula, molecularWeight (monoisotopic),
         molecularWeightAverage
  GET /peptide/iso?seq={SEQ}&N_term={N}&C_term={C}   -> {pI}
  GET /peptide/extinction?seq={SEQ}                  -> {oxidized, reduced}

Errors are returned as JSON {message, status, errorCode} with HTTP 400.
No API key required.
"""

from __future__ import annotations

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

_TIMEOUT = 30


@register_tool("PepCalcTool")
class PepCalcTool(BaseTool):
    """Terminal-modification-aware peptide physicochemical properties."""

    BASE_URL = "https://api.pep-calc.com"

    # Fields copied verbatim from the /peptide endpoint into the output record.
    _CORE_FIELDS = (
        "seqString",
        "seqList",
        "seqLength",
        "nString",
        "cString",
        "nName",
        "cName",
        "nModified",
        "cModified",
        "formula",
        "molecularWeight",
        "molecularWeightAverage",
    )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq = (arguments.get("seq") or arguments.get("sequence") or "").strip()
        if not seq:
            return {"status": "error", "error": "seq is required"}

        # N_term / C_term are the chemical group strings Pep-Calc expects.
        # Defaults match an unmodified peptide: free amine (H) and free acid (OH).
        n_term = str(arguments.get("N_term", "H")).strip() or "H"
        c_term = str(arguments.get("C_term", "OH")).strip() or "OH"

        params = {"seq": seq, "N_term": n_term, "C_term": c_term}

        # Core properties (formula, MW, modification flags) — required.
        core = self._get_json("/peptide", params)
        if core.get("status") == "error":
            return core
        core_data = core["data"]

        # isoelectric point — best effort (do not fail the whole call if absent).
        iso_data = self._get_json("/peptide/iso", params)
        pi_value = None
        if iso_data.get("status") == "success":
            pi_value = iso_data["data"].get("pI")

        # extinction coefficient — only needs the sequence.
        ext = self._get_json("/peptide/extinction", {"seq": seq})
        ext_value = ext["data"] if ext.get("status") == "success" else None

        data = {field: core_data.get(field) for field in self._CORE_FIELDS}
        data["isoelectricPoint"] = pi_value
        data["extinctionCoefficient"] = ext_value

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source": "Pep-Calc.com",
                "endpoint": f"{self.BASE_URL}/peptide",
                "N_term": n_term,
                "C_term": c_term,
                "molecular_weight_units": "Da (monoisotopic)",
                "molecular_weight_average_units": "Da (average)",
            },
        }

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        try:
            resp = request_with_retry(
                requests, "GET", url, params=params, timeout=_TIMEOUT
            )
        except Exception as exc:
            return {"status": "error", "error": f"Request failed: {exc}"}

        try:
            payload = resp.json()
        except Exception:
            return {
                "status": "error",
                "error": "Failed to parse JSON response",
                "detail": resp.text[:500],
            }

        # Pep-Calc signals errors with a JSON {message, status, errorCode} body.
        if isinstance(payload, dict) and "errorCode" in payload:
            return {
                "status": "error",
                "error": payload.get("message", "Pep-Calc API error"),
                "errorCode": payload.get("errorCode"),
            }

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code}",
                "detail": resp.text[:500],
            }

        return {"status": "success", "data": payload}
