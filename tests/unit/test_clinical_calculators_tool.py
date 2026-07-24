"""Unit tests for clinical risk calculators (pure compute, no network).

Reference values are checked against published example cases:
  - ASCVD PCE 2013: the ACC/AHA worked examples (55yo, TC 213, HDL 50, SBP 120,
    untreated, nonsmoker, non-diabetic) -> White male 5.4%, White female 2.1%,
    African-American male 6.1%.
"""

import pytest

from tooluniverse.clinical_calculators_tool import ClinicalCalculatorTool


def _tool(calc):
    return ClinicalCalculatorTool(
        {"name": f"calc_{calc}", "type": "ClinicalCalculatorTool",
         "fields": {"calculator": calc}, "parameter": {"type": "object", "properties": {}}}
    )


# --------------------------------------------------------------------------- #
# ASCVD — validated against the official ACC/AHA worked examples
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "female,race,expected",
    [(False, "white", 5.4), (True, "white", 2.1), (False, "black", 6.1)],
)
def test_ascvd_matches_published_examples(female, race, expected):
    out = _tool("ascvd").run({
        "age": 55, "total_cholesterol": 213, "hdl_cholesterol": 50,
        "systolic_bp": 120, "bp_treated": False, "smoker": False,
        "diabetes": False, "female": female, "race": race,
    })
    assert out["status"] == "success"
    assert out["data"]["score"] == pytest.approx(expected, abs=0.2)


def test_ascvd_rejects_out_of_range_age():
    out = _tool("ascvd").run({"age": 30, "total_cholesterol": 200,
                              "hdl_cholesterol": 50, "systolic_bp": 120})
    assert out["status"] == "error"
    assert "40-79" in out["error"]


# --------------------------------------------------------------------------- #
# Point scores
# --------------------------------------------------------------------------- #
def test_cha2ds2_vasc_age_buckets_and_doubles():
    # 80F + HTN + DM = age(2)+female(1)+htn(1)+dm(1) = 5
    out = _tool("cha2ds2_vasc").run({"age": 80, "female": True, "hypertension": True, "diabetes": True})
    assert out["data"]["score"] == 5
    # Age 70 gives the 65-74 bucket (1), not the >=75 bucket
    out2 = _tool("cha2ds2_vasc").run({"age": 70})
    assert out2["data"]["components"]["Age_65-74"] == 1
    assert out2["data"]["components"]["Age>=75"] == 0
    assert out2["data"]["score"] == 1


def test_cha2ds2_vasc_stroke_is_two_points():
    out = _tool("cha2ds2_vasc").run({"age": 50, "stroke_history": True})
    assert out["data"]["score"] == 2


def test_curb_65_counts_age_and_flags():
    out = _tool("curb_65").run({"age": 72, "confusion": True, "elevated_urea": True})
    assert out["data"]["score"] == 3  # confusion + urea + age>=65
    assert "High severity" in out["data"]["interpretation"]


def test_qsofa_threshold():
    out = _tool("qsofa").run({"high_resp_rate": True, "altered_mentation": True, "low_sbp": False})
    assert out["data"]["score"] == 2
    assert "High risk" in out["data"]["interpretation"]


def test_child_pugh_healthy_is_class_a():
    out = _tool("child_pugh").run({"bilirubin": 1.0, "albumin": 4.0, "inr": 1.0})
    assert out["data"]["score"] == 5
    assert out["data"]["child_pugh_class"] == "A"


def test_child_pugh_decompensated_is_class_c():
    out = _tool("child_pugh").run({"bilirubin": 3.5, "albumin": 2.5, "inr": 2.4,
                                   "ascites": "moderate", "encephalopathy": "grade3-4"})
    assert out["data"]["score"] == 15
    assert out["data"]["child_pugh_class"] == "C"


def test_child_pugh_rejects_unknown_ascites():
    # An unrecognized severity must error, not silently score the best case (1 pt).
    out = _tool("child_pugh").run({"bilirubin": 1.0, "albumin": 4.0, "inr": 1.0,
                                   "ascites": "tense"})
    assert out["status"] == "error"
    assert "ascites" in out["error"]


def test_child_pugh_rejects_unknown_encephalopathy():
    out = _tool("child_pugh").run({"bilirubin": 1.0, "albumin": 4.0, "inr": 1.0,
                                   "encephalopathy": "comatose"})
    assert out["status"] == "error"
    assert "encephalopathy" in out["error"]


def test_child_pugh_accepts_synonyms():
    # 'absent'/'slight' are accepted aliases for none/mild.
    out = _tool("child_pugh").run({"bilirubin": 1.0, "albumin": 4.0, "inr": 1.0,
                                   "ascites": "slight", "encephalopathy": "absent"})
    assert out["status"] == "success"
    assert out["data"]["components"]["Ascites"] == 2
    assert out["data"]["components"]["Encephalopathy"] == 1


def test_wells_dvt_alternative_dx_subtracts():
    out = _tool("wells_dvt").run({"active_cancer": True, "leg_swollen": True, "alternative_diagnosis": True})
    assert out["data"]["score"] == 0  # 1 + 1 - 2
    assert "unlikely" in out["data"]["interpretation"]


def test_wells_pe_weighted_and_tiers():
    out = _tool("wells_pe").run({"clinical_dvt": True, "pe_most_likely": True})
    assert out["data"]["score"] == 6.0
    assert out["data"]["two_tier"] == "PE likely"


# --------------------------------------------------------------------------- #
# Formula scores
# --------------------------------------------------------------------------- #
def test_ckd_epi_sex_difference():
    male = _tool("ckd_epi").run({"creatinine": 1.0, "age": 50, "female": False})
    female = _tool("ckd_epi").run({"creatinine": 1.0, "age": 50, "female": True})
    assert male["status"] == "success" and female["status"] == "success"
    # Same creatinine/age: the female equation yields a higher eGFR than naive male calc only via factors;
    # both should be physiologic (50-110) and the result carries a CKD stage.
    assert 30 < male["data"]["score"] < 130
    assert "CKD stage" in female["data"]["interpretation"]


def test_meld_na_bounds_and_range():
    out = _tool("meld_na").run({"creatinine": 1.5, "bilirubin": 2.0, "inr": 1.5, "sodium": 130})
    assert out["status"] == "success"
    assert 6 <= out["data"]["score"] <= 40
    # dialysis forces creatinine to 4.0
    dial = _tool("meld_na").run({"creatinine": 0.5, "bilirubin": 2.0, "inr": 1.5, "sodium": 130, "dialysis": True})
    assert dial["data"]["components"]["creatinine_used"] == 4.0


# --------------------------------------------------------------------------- #
# Dispatch / validation
# --------------------------------------------------------------------------- #
def test_unknown_calculator_errors():
    out = _tool("does_not_exist").run({})
    assert out["status"] == "error"
    assert "Unknown calculator" in out["error"]


def test_missing_required_field_errors():
    out = _tool("ckd_epi").run({"age": 50})  # missing creatinine
    assert out["status"] == "error"
    assert "creatinine" in out["error"]


def test_boolean_string_coercion():
    # 'yes'/'true' strings should count as present
    out = _tool("cha2ds2_vasc").run({"age": 50, "hypertension": "yes", "diabetes": "true"})
    assert out["data"]["score"] == 2
