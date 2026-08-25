"""Round-32 fix: sex-dependent clinical calculators must not silently ignore
a caller-supplied `sex` string.

Previously ClinicalCalc_eGFR_CKD_EPI, ClinicalCalc_CHA2DS2_VASc, and
ClinicalCalc_ASCVD_risk only read a `female` boolean. A caller who passed the
natural clinical parameter `sex: "female"` had it silently dropped (unknown
keys pass validation since the JSON config sets no `additionalProperties:
false`), and the tool fell back to `female=False` (male), while still
reporting a `sex`/`Female` field in the output that looked like it reflected
the caller's input.

This test file locks in the additive fix:
  - `sex` (case-insensitive female/f/male/m) is accepted on all three tools.
  - `female` keeps working exactly as before.
  - Supplying both `female` and `sex` in agreement is fine; in conflict is an
    explicit error naming both values.
  - An unrecognised `sex` string is a clear error, not a silent male default.
  - Omitting both `female` and `sex` keeps the existing default (male) and
    existing score, but now also discloses the assumption via a sibling
    `assumptions` key so it isn't silently baked into the result.
"""

import pytest

from tooluniverse.clinical_calculators_tool import ClinicalCalculatorTool


def _tool(calc):
    return ClinicalCalculatorTool(
        {
            "name": f"calc_{calc}",
            "type": "ClinicalCalculatorTool",
            "fields": {"calculator": calc},
            "parameter": {"type": "object", "properties": {}},
        }
    )


# --------------------------------------------------------------------------- #
# eGFR (CKD-EPI 2021) — the flagship reported bug: sex='female' silently
# ignored, returning a male eGFR ~33% higher than the correct female value.
# Verified against the official CKD-EPI 2021 equation (Inker et al., NEJM
# 2021;385(19):1737-1749; NIDDK "2021 CKD-EPI Creatinine Equation" summary):
# kappa=0.7/alpha=-0.241 (female), kappa=0.9/alpha=-0.302 (male),
# age factor 0.9938^age, female multiplier 1.012.
# --------------------------------------------------------------------------- #
def test_egfr_sex_string_female_matches_female_boolean():
    via_sex = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "sex": "female"})
    via_bool = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "female": True})
    assert via_sex["status"] == "success"
    assert via_sex["data"]["score"] == via_bool["data"]["score"]
    assert via_sex["data"]["components"]["sex"] == "female"


def test_egfr_sex_female_is_not_silently_treated_as_male():
    # Correct CKD-EPI 2021 value for 55yo female, Scr 1.2 mg/dL is ~53.5
    # (CKD stage G3a), not the ~71.4 male value.
    out = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "sex": "female"})
    assert out["data"]["score"] == pytest.approx(53.5, abs=0.2)
    assert "G3a" in out["data"]["interpretation"]


def test_egfr_female_boolean_unchanged():
    # Locks in the existing (pre-fix) male and female boolean behaviour.
    male = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "female": False})
    assert male["data"]["score"] == pytest.approx(71.4, abs=0.05)
    female = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "female": True})
    assert female["data"]["score"] == pytest.approx(53.5, abs=0.2)


def test_egfr_no_sex_supplied_keeps_default_but_discloses_assumption():
    out = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55})
    # Same score as before the fix (male assumed) — default not changed.
    assert out["data"]["score"] == pytest.approx(71.4, abs=0.05)
    assert out["data"]["components"]["sex"] == "male"
    # New: the silent default is now disclosed.
    assert "assumptions" in out["data"]
    assert any("male" in note.lower() for note in out["data"]["assumptions"])


def test_egfr_unrecognised_sex_string_errors_clearly():
    out = _tool("ckd_epi").run({"creatinine": 1.2, "age": 55, "sex": "woman"})
    assert out["status"] == "error"
    assert "sex" in out["error"]
    assert "female" in out["error"] and "male" in out["error"]


# --------------------------------------------------------------------------- #
# CHA2DS2-VASc
# --------------------------------------------------------------------------- #
def test_cha2ds2_vasc_sex_string_matches_female_boolean():
    via_sex = _tool("cha2ds2_vasc").run(
        {"age": 68, "sex": "female", "hypertension": True}
    )
    via_bool = _tool("cha2ds2_vasc").run(
        {"age": 68, "female": True, "hypertension": True}
    )
    assert via_sex["data"]["score"] == via_bool["data"]["score"] == 3
    assert via_sex["data"]["components"]["Female"] == 1


def test_cha2ds2_vasc_female_boolean_unchanged():
    out = _tool("cha2ds2_vasc").run({"age": 68, "female": True, "hypertension": True})
    assert out["data"]["score"] == 3


def test_cha2ds2_vasc_conflicting_sex_inputs_error():
    out = _tool("cha2ds2_vasc").run({"age": 68, "female": True, "sex": "male"})
    assert out["status"] == "error"
    assert "female" in out["error"] and "sex" in out["error"]


def test_cha2ds2_vasc_agreeing_sex_inputs_proceed():
    out = _tool("cha2ds2_vasc").run({"age": 68, "female": True, "sex": "female"})
    assert out["status"] == "success"
    assert out["data"]["components"]["Female"] == 1


def test_cha2ds2_vasc_no_sex_supplied_keeps_default_and_discloses():
    with_sex = _tool("cha2ds2_vasc").run({"age": 68, "hypertension": True})
    assert with_sex["data"]["score"] == 2  # unchanged from pre-fix behaviour
    assert "assumptions" in with_sex["data"]


# --------------------------------------------------------------------------- #
# ASCVD risk
# --------------------------------------------------------------------------- #
def test_ascvd_sex_string_matches_female_boolean():
    args_common = {
        "age": 60,
        "total_cholesterol": 240,
        "hdl_cholesterol": 40,
        "systolic_bp": 140,
        "bp_treated": True,
        "smoker": True,
        "diabetes": True,
        "race": "black",
    }
    via_sex = _tool("ascvd").run({**args_common, "sex": "female"})
    via_bool = _tool("ascvd").run({**args_common, "female": True})
    assert via_sex["data"]["score"] == via_bool["data"]["score"]
    assert via_sex["data"]["components"]["group"] == "black_female"


def test_ascvd_sex_was_previously_silently_ignored_now_fixed():
    # Reported bug: sex='female' produced the male coefficient group
    # ("black_male", 47.2%) instead of the correct female group
    # ("black_female", 46.8%).
    out = _tool("ascvd").run(
        {
            "age": 60,
            "total_cholesterol": 240,
            "hdl_cholesterol": 40,
            "systolic_bp": 140,
            "bp_treated": True,
            "smoker": True,
            "diabetes": True,
            "sex": "female",
            "race": "black",
        }
    )
    assert out["data"]["components"]["group"] == "black_female"
    assert out["data"]["score"] == pytest.approx(46.8, abs=0.1)


def test_ascvd_female_boolean_unchanged():
    out = _tool("ascvd").run(
        {
            "age": 55,
            "total_cholesterol": 213,
            "hdl_cholesterol": 50,
            "systolic_bp": 120,
            "bp_treated": False,
            "smoker": False,
            "diabetes": False,
            "female": True,
            "race": "white",
        }
    )
    assert out["data"]["score"] == pytest.approx(2.1, abs=0.2)


def test_ascvd_conflicting_sex_inputs_error():
    out = _tool("ascvd").run(
        {
            "age": 60,
            "total_cholesterol": 240,
            "hdl_cholesterol": 40,
            "systolic_bp": 140,
            "female": True,
            "sex": "male",
        }
    )
    assert out["status"] == "error"
    assert "female" in out["error"] and "sex" in out["error"]


def test_ascvd_unrecognised_sex_string_errors():
    out = _tool("ascvd").run(
        {
            "age": 60,
            "total_cholesterol": 240,
            "hdl_cholesterol": 40,
            "systolic_bp": 140,
            "sex": "unspecified",
        }
    )
    assert out["status"] == "error"
    assert "sex" in out["error"]


def test_ascvd_no_race_supplied_discloses_assumption():
    out = _tool("ascvd").run(
        {
            "age": 60,
            "total_cholesterol": 240,
            "hdl_cholesterol": 40,
            "systolic_bp": 140,
            "female": True,
        }
    )
    assert out["status"] == "success"
    assert out["data"]["components"]["group"] == "white_female"
    assert "assumptions" in out["data"]
    assert any("race" in note.lower() for note in out["data"]["assumptions"])


def test_ascvd_no_sex_and_no_race_discloses_both_assumptions():
    out = _tool("ascvd").run(
        {
            "age": 60,
            "total_cholesterol": 240,
            "hdl_cholesterol": 40,
            "systolic_bp": 140,
        }
    )
    assert out["status"] == "success"
    assert out["data"]["components"]["group"] == "white_male"  # unchanged default
    notes = out["data"]["assumptions"]
    assert any("sex" in n.lower() or "male" in n.lower() for n in notes)
    assert any("race" in n.lower() for n in notes)
