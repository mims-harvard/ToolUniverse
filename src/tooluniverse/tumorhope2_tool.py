"""TumorHoPe 2 tumor-homing peptide tool (live REST, keyless).

TumorHoPe 2 / TumorHope2 (Raghava lab, IIITD) is a database of tumor-homing
peptides used for drug-delivery targeting. This tool provides a non-immune
targeting-peptide capability absent from ToolUniverse: given a source (peptide
source label), target tumor, source name, or conjugate it returns the peptide
sequence, target tumor / cell, receptor / biomarker, terminal modifications,
phage-display origin, and in-vitro / in-vivo evidence.

The public API is keyless. Unlike the other IIITD peptide APIs it does NOT use
``dataType``/``dataValue`` and does NOT support sequence queries; it accepts
one or more of these query parameters directly::

    api.php?source=A33H
    api.php?target_tumor=Brain%20tumor
    api.php?name_source=...
    api.php?conjugate=...

A successful response is a JSON object ``{"status": "success",
"message": ..., "count": int, "results": [ ... ]}``. A no-match query returns
``{"status": "success", "message": "No results found", "count": 0,
"results": []}``.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://webs.iiitd.edu.in/raghava/tumorhope2/restapi/api.php"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}

# user-arg -> TumorHope2 query parameter (all map 1:1 here).
_PARAM_KEYS = ("source", "target_tumor", "name_source", "conjugate")


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


@register_tool(
    "TumorHope2SearchPeptidesTool",
    config={
        "name": "TumorHope2_search_peptides",
        "type": "TumorHope2SearchPeptidesTool",
        "description": (
            "Search TumorHoPe 2 (Raghava lab, IIITD) for TUMOR-HOMING peptide "
            "records used in drug delivery. Filter by 'source' (peptide source "
            "label, e.g. A33H), 'target_tumor' (e.g. 'Brain tumor'), "
            "'name_source', or 'conjugate'. Each record returns the peptide "
            "sequence, target tumor / cell, receptor / biomarker, N/C-terminus "
            "modifications, sequence motif, phage-display origin, in-vitro and "
            "in-vivo evidence, conjugate, PubMed ID, year, and title. Note: "
            "this API does not support sequence search. Keyless public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": (
                        "Peptide source label. Example: 'A33H' -> 1 record "
                        "(SIWV, a brain-tumor-homing tetrapeptide)."
                    ),
                },
                "target_tumor": {
                    "type": "string",
                    "description": (
                        "Target tumor type. Example: 'Brain tumor' -> ~39 records."
                    ),
                },
                "name_source": {
                    "type": "string",
                    "description": "Source name to match.",
                },
                "conjugate": {
                    "type": "string",
                    "description": (
                        "Conjugate / payload label (e.g. a fluorophore or "
                        "nanoparticle)."
                    ),
                },
            },
            "required": [],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "success"},
                        "data": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": (
                                "Matching tumor-homing peptide records. Each "
                                "has id, title, pmid, year, source, "
                                "name_source, sequence, n_term, c_term, motif, "
                                "target_tumor, target_cell, "
                                "receptors_biomarker, phage_display, invitro, "
                                "invivo."
                            ),
                        },
                        "metadata": {"type": "object"},
                    },
                    "required": ["status", "data", "metadata"],
                },
                {
                    "type": "object",
                    "properties": {
                        "status": {"const": "error"},
                        "error": {"type": "string"},
                    },
                    "required": ["status", "error"],
                },
            ]
        },
        "test_examples": [
            {"source": "A33H"},
            {"target_tumor": "Brain tumor"},
        ],
    },
)
class TumorHope2SearchPeptidesTool(BaseTool):
    """Search TumorHoPe 2 tumor-homing peptide records."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        params: Dict[str, Any] = {}
        for key in _PARAM_KEYS:
            val = arguments.get(key)
            if val is not None and str(val).strip() != "":
                params[key] = str(val)

        if not params:
            return _err(
                "At least one search filter is required: source, "
                "target_tumor, name_source, or conjugate."
            )

        try:
            resp = requests.get(
                _BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to TumorHoPe 2 failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"TumorHoPe 2 returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "TumorHoPe 2 returned a non-JSON response",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(payload, dict):
            return _err("Unexpected TumorHoPe 2 response shape", url=resp.url)

        # The API signals a malformed query with status="error".
        if payload.get("status") == "error":
            return _err(
                payload.get("message") or "TumorHoPe 2 rejected the query",
                url=resp.url,
            )

        records = payload.get("results")
        if not isinstance(records, list):
            return _err("Unexpected TumorHoPe 2 data shape", url=resp.url)

        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "TumorHoPe 2 (Raghava lab, IIITD)",
                "url": resp.url,
                "query": params,
                "total_count": payload.get("count", len(records)),
                "returned_count": len(records),
                "message": payload.get("message"),
            },
        }
