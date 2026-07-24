"""Hemolytik 2.0 hemolytic/toxic peptide tool (live REST, keyless).

Hemolytik 2.0 (Raghava lab, IIITD) is an updated database of experimentally
validated hemolytic and non-hemolytic peptides/proteins (~8,700 unique
peptides, ~13,215 entries; bioRxiv 2025). This tool fills the toxicity/safety
side of the therapeutic-peptide gap: given a record category it returns the
sequence, hemolytic activity (LC50/HC50), source organism, terminal and
chemical modifications, linear/cyclic form, and nature (Antimicrobial /
Anticancer / CPP, etc.).

The public API is keyless. It is queried with a ``dataType`` (the field to
filter on) and a ``dataValue`` (the value to match), e.g.::

    api.php?dataType=nature&dataValue=Anticancer
    api.php?dataType=source&dataValue=Human
    api.php?dataType=seq&dataValue=<sequence>

A successful response is a JSON object ``{"status": 200, "count": int,
"data": [ ... ]}``. A no-match query returns ``{"status": 404,
"message": "Record Not Found"}``.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://webs.iiitd.edu.in/raghava/hemolytik2/api/api.php"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}

# Supported filter fields for the dataType parameter.
_VALID_DATA_TYPES = ("nature", "source", "seq")


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


@register_tool(
    "Hemolytik2SearchPeptidesTool",
    config={
        "name": "Hemolytik2_search_peptides",
        "type": "Hemolytik2SearchPeptidesTool",
        "description": (
            "Search Hemolytik 2.0 (Raghava lab, IIITD) for experimentally "
            "validated HEMOLYTIC / TOXIC peptide records. Filter by 'nature' "
            "(e.g. Antimicrobial, Anticancer, CPP), 'source' (source organism, "
            "e.g. Human), or 'seq' (sequence). Each record returns the peptide "
            "sequence, hemolytic activity (LC50/HC50 with units), source "
            "organism, origin, N/C-terminus and chemical (non-natural) "
            "modifications, linear/cyclic form, L/D chirality mix, length, "
            "nature, PubMed ID, and year. Use to assess peptide safety / "
            "hemolysis liability. Keyless public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "dataType": {
                    "type": "string",
                    "description": (
                        "Field to filter on. One of: 'nature' (peptide nature, "
                        "e.g. Anticancer, Antimicrobial, CPP), 'source' (source "
                        "organism, e.g. Human), or 'seq' (sequence). "
                        "Default: 'nature'."
                    ),
                    "enum": ["nature", "source", "seq"],
                },
                "dataValue": {
                    "type": "string",
                    "description": (
                        "Value to match for the chosen dataType. Examples: "
                        "'Anticancer' (with dataType=nature) -> ~166 records; "
                        "'Human' (with dataType=source) -> ~9255 records."
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
                                "Matching hemolytic peptide records. Each has "
                                "id, pmid, year, seq, name, cter, nter, "
                                "lyn_cyc, ldmix, non_nat, length, nature, "
                                "activity (e.g. 'LC50 =1.4 µM'), source, "
                                "origin, exp_str, non_hem."
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
            {"dataType": "nature", "dataValue": "Anticancer"},
            {"dataType": "source", "dataValue": "Human"},
        ],
    },
)
class Hemolytik2SearchPeptidesTool(BaseTool):
    """Search Hemolytik 2.0 hemolytic/toxic peptide records."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        data_value = arguments.get("dataValue")
        if data_value is None or str(data_value).strip() == "":
            return _err("dataValue is required (e.g. 'Anticancer' or 'Human')")

        data_type = str(arguments.get("dataType") or "nature").strip()
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
            return _err(f"Request to Hemolytik 2.0 failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"Hemolytik 2.0 returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "Hemolytik 2.0 returned a non-JSON response",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        if not isinstance(payload, dict):
            return _err("Unexpected Hemolytik 2.0 response shape", url=resp.url)

        # No-match: API returns {"status": 404, "message": "Record Not Found"}.
        if payload.get("status") == 404 or "data" not in payload:
            return _err(
                payload.get("message")
                or f"No Hemolytik 2.0 records for {data_type}={data_value!r}",
                url=resp.url,
            )

        records = payload.get("data") or []
        if not isinstance(records, list):
            return _err("Unexpected Hemolytik 2.0 data shape", url=resp.url)

        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "Hemolytik 2.0 (Raghava lab, IIITD)",
                "url": resp.url,
                "data_type": data_type,
                "data_value": str(data_value),
                "total_count": payload.get("count", len(records)),
                "returned_count": len(records),
            },
        }
