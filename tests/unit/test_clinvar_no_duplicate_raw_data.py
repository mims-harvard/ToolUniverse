"""Regression guard for Fix-R8E-1/R6C-2: ClinVarGetVariantDetails and
ClinVarGetClinicalSignificance both returned the full raw esummary blob
twice -- once as the top-level "data" key (from the underlying
_make_request envelope) and again inside formatted_data["raw_data"] --
roughly tripling payload size for no informational gain and making the
two tools' outputs nearly indistinguishable from each other. The
top-level duplicate is now dropped; raw access remains available via
formatted_data.raw_data.
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
    "variation_set": [{"variation_loc": [{"band": "13q13.1"}], "variation_name": "NM_007294.4(BRCA1):c.68_69delAG"}],
    "title": "NM_007294.4(BRCA1):c.68_69delAG",
    "genes": [{"symbol": "BRCA1"}],
    "germline_classification": {"description": "Pathogenic", "review_status": "reviewed"},
    "clinical_impact_classification": {},
    "oncogenicity_classification": {},
}

_FETCH_RESULT = {
    "status": "success",
    "data": {"result": {"9": _VARIANT_DATA}},
    "url": "https://example.com",
}


def _fetch_variant_patch():
    return patch.object(
        ClinVarGetVariantDetails.__bases__[0],
        "_fetch_variant",
        return_value={"variant_data": _VARIANT_DATA, "result": dict(_FETCH_RESULT)},
    )


def test_get_variant_details_has_no_duplicate_top_level_data():
    tool = ClinVarGetVariantDetails({"name": "ClinVar_get_variant_details"})
    with _fetch_variant_patch():
        result = tool.run({"variant_id": "9"})

    assert "data" not in result
    assert result["formatted_data"]["raw_data"] == _VARIANT_DATA


def test_get_clinical_significance_has_no_duplicate_top_level_data():
    tool = ClinVarGetClinicalSignificance({"name": "ClinVar_get_clinical_significance"})
    with patch.object(
        ClinVarGetClinicalSignificance.__bases__[0],
        "_fetch_variant",
        return_value={"variant_data": _VARIANT_DATA, "result": dict(_FETCH_RESULT)},
    ):
        result = tool.run({"variant_id": "9"})

    assert "data" not in result
    assert result["formatted_data"]["raw_data"] == _VARIANT_DATA
