"""PEPlife 2.0 peptide half-life / stability tool (live REST, keyless).

PEPlife 2.0 (Raghava lab, IIITD) is an updated repository of experimentally
measured peptide half-lives (bioRxiv 2025). This tool informs
therapeutic-peptide stability / druggability — a non-immune capability absent
from ToolUniverse: given a linear/cyclic form, organism/media, or sequence it
returns the measured half-life (value + units), the protease, incubation
time, concentration, and assay used.

The public API is keyless. It is queried with a ``dataType`` (the field to
filter on) and a ``dataValue`` (the value to match), e.g.::

    api.php?dataType=lin_cyc&dataValue=Linear   (or Cyclic)
    api.php?dataType=org&dataValue=<organism/media>
    api.php?dataType=seq&dataValue=<sequence>

A successful response is a JSON object ``{"status": 200, "count": int,
"data": [ ... ]}``. A no-match query returns ``{"status": 404,
"message": "Record Not Found"}``.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://webs.iiitd.edu.in/raghava/peplife2/api/api.php"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}

_VALID_DATA_TYPES = ("lin_cyc", "org", "seq")


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


@register_tool(
    "PEPlife2SearchPeptidesTool",
    config={
        "name": "PEPlife2_search_peptides",
        "type": "PEPlife2SearchPeptidesTool",
        "description": (
            "Search PEPlife 2.0 (Raghava lab, IIITD) for experimentally "
            "measured peptide HALF-LIFE / proteolytic-stability records. "
            "Filter by 'lin_cyc' (Linear or Cyclic), 'org' (origin organism / "
            "incubation media), or 'seq' (sequence). Each record returns the "
            "peptide sequence, half-life value and units, protease, incubation "
            "time, concentration, assay, linear/cyclic form, chirality, "
            "chemical and N/C-terminus modifications, origin, nature, PubMed "
            "ID, and year. Use to assess therapeutic-peptide stability / "
            "druggability. Keyless public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "dataType": {
                    "type": "string",
                    "description": (
                        "Field to filter on. One of: 'lin_cyc' (Linear or "
                        "Cyclic), 'org' (origin organism / incubation media), "
                        "or 'seq' (sequence). Default: 'lin_cyc'."
                    ),
                    "enum": ["lin_cyc", "org", "seq"],
                },
                "dataValue": {
                    "type": "string",
                    "description": (
                        "Value to match for the chosen dataType. Examples: "
                        "'Linear' (with dataType=lin_cyc) -> ~3777 records; "
                        "'Cyclic' (with dataType=lin_cyc) -> ~49 records."
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
                                "Matching half-life records. Each has id, "
                                "pmid, year, seq, name, length, lin_cyc, "
                                "chiral, chem_mod, cter, nter, origin, nature, "
                                "incubation_time, conc, half_life, units_half, "
                                "protease, assay."
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
            {"dataType": "lin_cyc", "dataValue": "Linear"},
            {"dataType": "lin_cyc", "dataValue": "Cyclic"},
        ],
    },
)
class PEPlife2SearchPeptidesTool(BaseTool):
    """Search PEPlife 2.0 peptide half-life / stability records."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        data_value = arguments.get("dataValue")
        if data_value is None or str(data_value).strip() == "":
            return _err("dataValue is required (e.g. 'Linear' or 'Cyclic')")

        data_type = str(arguments.get("dataType") or "lin_cyc").strip()
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
            return _err(f"Request to PEPlife 2.0 failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"PEPlife 2.0 returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "PEPlife 2.0 returned a non-JSON response",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(payload, dict):
            return _err("Unexpected PEPlife 2.0 response shape", url=resp.url)

        if payload.get("status") == 404 or "data" not in payload:
            return _err(
                payload.get("message")
                or f"No PEPlife 2.0 records for {data_type}={data_value!r}",
                url=resp.url,
            )

        records = payload.get("data") or []
        if not isinstance(records, list):
            return _err("Unexpected PEPlife 2.0 data shape", url=resp.url)

        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "PEPlife 2.0 (Raghava lab, IIITD)",
                "url": resp.url,
                "data_type": data_type,
                "data_value": str(data_value),
                "total_count": payload.get("count", len(records)),
                "returned_count": len(records),
            },
        }
