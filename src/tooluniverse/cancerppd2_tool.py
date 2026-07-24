"""CancerPPD 2.0 anticancer peptide tool (live REST, keyless).

CancerPPD 2.0 (Raghava lab, IIITD) is an updated repository of experimentally
validated anticancer peptides and proteins (NAR / PMC12060709, 2025). This
tool provides non-immune therapeutic-peptide (anticancer) coverage: given a
cancer type, cell line, or sequence-nature category it returns the peptide
sequence, length, chirality, linear/cyclic form, terminal and chemical
modifications, the assay used, test time, tissue, target cell line, and
cancer type.

The public API is keyless. It is queried with a ``dataType`` (the field to
filter on) and a ``dataValue`` (the value to match), e.g.::

    api.php?dataType=cancer_type&dataValue=Fibrosarcoma
    api.php?dataType=cell_line&dataValue=A-549
    api.php?dataType=seq&dataValue=Natural   (or Modified)

A successful response is a JSON object ``{"status": 200, "count": int,
"data": [ ... ]}``. A no-match query returns ``{"status": 404,
"message": "Record Not Found"}``.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://webs.iiitd.edu.in/raghava/cancerppd2/api/api.php"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}

_VALID_DATA_TYPES = ("cancer_type", "cell_line", "seq")


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


@register_tool(
    "CancerPPD2SearchPeptidesTool",
    config={
        "name": "CancerPPD2_search_peptides",
        "type": "CancerPPD2SearchPeptidesTool",
        "description": (
            "Search CancerPPD 2.0 (Raghava lab, IIITD) for experimentally "
            "validated ANTICANCER peptide records. Filter by 'cancer_type' "
            "(e.g. Fibrosarcoma), 'cell_line' (e.g. A-549), or 'seq' (sequence "
            "nature: Natural or Modified). Each record returns the peptide "
            "sequence, length, linear/cyclic form, chirality, chemical and "
            "N/C-terminus modifications, target cell line, cancer type, assay, "
            "test time, tissue, PubMed ID, and year. Use for non-immune "
            "anticancer-peptide discovery / target-cell-line surveys. Keyless "
            "public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "dataType": {
                    "type": "string",
                    "description": (
                        "Field to filter on. One of: 'cancer_type' (e.g. "
                        "Fibrosarcoma), 'cell_line' (e.g. A-549), or 'seq' "
                        "(sequence nature: Natural or Modified). "
                        "Default: 'cancer_type'."
                    ),
                    "enum": ["cancer_type", "cell_line", "seq"],
                },
                "dataValue": {
                    "type": "string",
                    "description": (
                        "Value to match for the chosen dataType. Examples: "
                        "'Fibrosarcoma' (with dataType=cancer_type) -> ~101 "
                        "records; 'A-549' (with dataType=cell_line) -> ~232 "
                        "records; 'Natural' or 'Modified' (with dataType=seq)."
                    ),
                },
            },
            "required": ["dataValue"],
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
                                "Matching anticancer peptide records. Each has "
                                "id, pmid, year, seq, name, length, lin_cyc, "
                                "chiral, chem_mod, cter, nter, cell_line, "
                                "cancer_type, assay, test_time, tissue."
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
            {"dataType": "cancer_type", "dataValue": "Fibrosarcoma"},
            {"dataType": "cell_line", "dataValue": "A-549"},
        ],
    },
)
class CancerPPD2SearchPeptidesTool(BaseTool):
    """Search CancerPPD 2.0 anticancer peptide records."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        data_value = arguments.get("dataValue")
        if data_value is None or str(data_value).strip() == "":
            return _err("dataValue is required (e.g. 'Fibrosarcoma' or 'A-549')")

        data_type = str(arguments.get("dataType") or "cancer_type").strip()
        if data_type not in _VALID_DATA_TYPES:
            return _err(
                f"Invalid dataType {data_type!r}. "
                f"Choose one of: {', '.join(_VALID_DATA_TYPES)}."
            )

        params = {"dataType": data_type, "dataValue": str(data_value)}
        try:
            resp = requests.get(
                _BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to CancerPPD 2.0 failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"CancerPPD 2.0 returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "CancerPPD 2.0 returned a non-JSON response",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(payload, dict):
            return _err("Unexpected CancerPPD 2.0 response shape", url=resp.url)

        if payload.get("status") == 404 or "data" not in payload:
            return _err(
                payload.get("message")
                or f"No CancerPPD 2.0 records for {data_type}={data_value!r}",
                url=resp.url,
            )

        records = payload.get("data") or []
        if not isinstance(records, list):
            return _err("Unexpected CancerPPD 2.0 data shape", url=resp.url)

        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "CancerPPD 2.0 (Raghava lab, IIITD)",
                "url": resp.url,
                "data_type": data_type,
                "data_value": str(data_value),
                "total_count": payload.get("count", len(records)),
                "returned_count": len(records),
            },
        }
