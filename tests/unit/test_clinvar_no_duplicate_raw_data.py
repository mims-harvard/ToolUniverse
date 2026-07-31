"""Regression guard for Fix-R8E-1/R6C-2: ClinVarGetVariantDetails and
ClinVarGetClinicalSignificance both returned the full raw esummary blob
twice -- once as the top-level "data" key (from the underlying
_make_request envelope) and again inside the formatted payload's
"raw_data" -- roughly tripling payload size for no informational gain and
making the two tools' outputs nearly indistinguishable from each other.

The formatted payload is now assigned *over* the raw envelope, so the
duplication stays gone and the payload is delivered under the "data" key
that both tools' return_schema declares (it was previously published under
a non-standard "formatted_data" key that no other tool in the registry
uses, so callers reading result["data"] by convention silently saw
nothing). Raw access remains available at data["raw_data"].
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import (
    ClinVarGetClinicalSignificance,
    ClinVarGetVariantDetails,
)

pytestmark = pytest.mark.unit

_VARIANT_DATA = {
    "accession": "VCV000000009",
    "obj_type": "single nucleotide variant",
    "chr_sort": "13",
    "variation_set": [
        {
            "variation_loc": [{"band": "13q13.1"}],
            "variation_name": "NM_007294.4(BRCA1):c.68_69delAG",
        }
    ],
    "title": "NM_007294.4(BRCA1):c.68_69delAG",
    "genes": [{"symbol": "BRCA1"}],
    "germline_classification": {
        "description": "Pathogenic",
        "review_status": "reviewed",
    },
    "clinical_impact_classification": {},
    "oncogenicity_classification": {},
}

_FETCH_RESULT = {
    "status": "success",
    "data": {"result": {"9": _VARIANT_DATA}},
    "url": "https://example.com",
}


def _count_variant_copies(node):
    """Count how many times the raw variant record appears anywhere in the
    response, so duplication is caught no matter where it is reintroduced."""
    if isinstance(node, dict):
        found = 1 if node == _VARIANT_DATA else 0
        return found + sum(_count_variant_copies(v) for v in node.values())
    if isinstance(node, list):
        return sum(_count_variant_copies(v) for v in node)
    return 0


def _fetch_variant_patch(tool_cls):
    return patch.object(
        tool_cls.__bases__[0],
        "_fetch_variant",
        return_value={"variant_data": _VARIANT_DATA, "result": dict(_FETCH_RESULT)},
    )


def _assert_payload_contract(result):
    # Payload is delivered under the schema-declared key, not the old one.
    assert "data" in result
    assert "formatted_data" not in result
    # Raw access is preserved...
    assert result["data"]["raw_data"] == _VARIANT_DATA
    # ...but the raw esummary envelope no longer sits at the top level, and
    # the variant record is present exactly once in the whole response.
    assert "result" not in result["data"]
    assert result["data"] != _FETCH_RESULT["data"]
    assert _count_variant_copies(result) == 1


def test_get_variant_details_has_no_duplicate_raw_data():
    tool = ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})
    with _fetch_variant_patch(ClinVarGetVariantDetails):
        result = tool.run({"variant_id": "9"})

    _assert_payload_contract(result)
    assert result["data"]["variant_id"] == "9"
    assert result["data"]["accession"] == "VCV000000009"
    assert result["data"]["clinical_significance"] == "Pathogenic"


def test_get_clinical_significance_has_no_duplicate_raw_data():
    tool = ClinVarGetClinicalSignificance({"name": "ClinVar_get_clinical_significance"})
    with _fetch_variant_patch(ClinVarGetClinicalSignificance):
        result = tool.run({"variant_id": "9"})

    _assert_payload_contract(result)
    assert result["data"]["variant_id"] == "9"
    assert result["data"]["germline_classification"]["description"] == "Pathogenic"
