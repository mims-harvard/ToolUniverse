"""Clinical calculators must refuse physiologically impossible inputs.

Fix Round 48. Fix-R46 closed this for CKD-EPI from inside that one equation;
the same class was still live in every other calculator that takes a
laboratory value, because the shared input helper `_req_number` enforced type
but never range. Reproduced through the CLI before the change:

    ClinicalCalc_ASCVD_risk {"age": 55, "sex": "female", "race": "white",
        "total_cholesterol": 0, "hdl_cholesterol": 50, "systolic_bp": 120}
      -> "Error: math domain error"
         (math.log(0); names neither the parameter nor the constraint)

    ClinicalCalc_Child_Pugh {"bilirubin": 1.0, "albumin": -1, "inr": 1.0,
        "ascites": "none", "encephalopathy": "none"}
      -> status success, "Class B (score 7): significant functional compromise"
         (albumin -1 falls in the <2.8 band and scores its WORST component,
         so an impossible input produced a confident severity class)

MELD-Na floors creatinine/bilirubin/INR at 1.0 per the UNOS specification, so a
negative value was absorbed into the floor and contributed as though normal.
CHA2DS2-VASc scored both age buckets 0 for a negative age and returned a
confident low-risk total.

The constraint now lives on `_req_number(..., must_exceed=0)` rather than in
each equation, so the tests below assert on the tools rather than the helper:
what matters is that the caller cannot get a score out of an impossible value.
"""

import json
from functools import lru_cache
from pathlib import Path

import pytest

from tooluniverse.clinical_calculators_tool import ClinicalCalculatorTool

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "clinical_calculators_tools.json"
)


@lru_cache(maxsize=None)
def _configs():
    """Cached -- this file is re-read once per parametrised case otherwise."""
    with open(CONFIG) as fh:
        return {cfg["name"]: cfg for cfg in json.load(fh)}


def _config(name):
    configs = _configs()
    if name not in configs:
        raise AssertionError(f"{name} not in clinical_calculators_tools.json")
    return configs[name]


def _run(name, args):
    return ClinicalCalculatorTool(_config(name)).run(args)


# Valid baselines, each of which must keep working unchanged.
VALID = {
    "ClinicalCalc_ASCVD_risk": {
        "age": 55,
        "sex": "female",
        "race": "white",
        "total_cholesterol": 213,
        "hdl_cholesterol": 50,
        "systolic_bp": 120,
    },
    "ClinicalCalc_Child_Pugh": {
        "bilirubin": 1.0,
        "albumin": 3.8,
        "inr": 1.0,
        "ascites": "none",
        "encephalopathy": "none",
    },
    "ClinicalCalc_MELD_Na": {
        "creatinine": 1.2,
        "bilirubin": 2.0,
        "inr": 1.3,
        "sodium": 134,
    },
    "ClinicalCalc_CHA2DS2_VASc": {"age": 70, "sex": "female"},
}

# (tool, parameter, impossible value). Zero is included where zero is as
# impossible as a negative -- a total cholesterol of 0 mg/dL is not a low
# reading, it is not a reading.
IMPOSSIBLE = [
    ("ClinicalCalc_ASCVD_risk", "total_cholesterol", 0),
    ("ClinicalCalc_ASCVD_risk", "hdl_cholesterol", 0),
    ("ClinicalCalc_ASCVD_risk", "systolic_bp", -120),
    ("ClinicalCalc_Child_Pugh", "albumin", -1),
    ("ClinicalCalc_Child_Pugh", "bilirubin", -2),
    ("ClinicalCalc_Child_Pugh", "inr", 0),
    ("ClinicalCalc_MELD_Na", "creatinine", -1),
    ("ClinicalCalc_MELD_Na", "bilirubin", -5),
    ("ClinicalCalc_MELD_Na", "sodium", -134),
    ("ClinicalCalc_CHA2DS2_VASc", "age", -70),
]


@pytest.mark.parametrize("tool,param,bad", IMPOSSIBLE)
def test_impossible_value_is_refused_and_names_the_parameter(tool, param, bad):
    result = _run(tool, dict(VALID[tool], **{param: bad}))

    assert result.get("status") == "error", (
        f"{tool} accepted {param}={bad} and returned a score: {result}"
    )
    # Naming the parameter is the point: "math domain error" was already an
    # error, just an unactionable one.
    assert param in result.get("error", ""), (
        f"{tool} rejected {param}={bad} without naming it: {result}"
    )


@pytest.mark.parametrize("tool", sorted(VALID))
def test_valid_inputs_still_score(tool):
    """Control: the guard must not reject clinically ordinary values."""
    result = _run(tool, VALID[tool])
    assert result.get("status") == "success", result


def test_child_pugh_no_longer_stages_a_negative_albumin():
    """The specific wrong answer that motivated this: Class B from albumin -1."""
    result = _run(
        "ClinicalCalc_Child_Pugh", dict(VALID["ClinicalCalc_Child_Pugh"], albumin=-1)
    )
    assert result.get("status") == "error"
    assert "Class B" not in json.dumps(result)


def test_ascvd_no_longer_leaks_a_bare_math_domain_error():
    result = _run(
        "ClinicalCalc_ASCVD_risk",
        dict(VALID["ClinicalCalc_ASCVD_risk"], total_cholesterol=0),
    )
    assert result.get("status") == "error"
    assert result.get("error") != "math domain error"
    assert "total_cholesterol" in result["error"]


# --------------------------------------------------------------------------- #
# Fix Round 49: the same class at the other end of the range.
#
# Round 48 closed the bottom and left the top open, so an impossible value was
# still scored confidently as long as it was impossibly large. Reproduced
# through the CLI before this change:
#
#     ClinicalCalc_MELD_Na {"bilirubin": 1.0, "creatinine": 1.0, "inr": 1.0,
#         "sodium": 134000}
#       -> status success, "MELD-Na 6: low (~1.9% 90-day mortality)"
#
#     ClinicalCalc_Child_Pugh {"bilirubin": 1.0, "albumin": 1000, "inr": 1.0}
#       -> status success, "Class A (score 5): well-compensated disease"
#
# and sodium 5 mmol/L, which is not compatible with life, was clamped into the
# MELD-Na formula and reported as a risk band rather than refused.
# --------------------------------------------------------------------------- #

IMPOSSIBLY_LARGE = [
    ("ClinicalCalc_MELD_Na", "sodium", 134000),
    ("ClinicalCalc_MELD_Na", "bilirubin", 5000),
    ("ClinicalCalc_Child_Pugh", "albumin", 1000),
    ("ClinicalCalc_Child_Pugh", "inr", 750),
    ("ClinicalCalc_ASCVD_risk", "total_cholesterol", 21300),
    ("ClinicalCalc_ASCVD_risk", "systolic_bp", 1200),
    ("ClinicalCalc_ASCVD_risk", "hdl_cholesterol", 5000),
    ("ClinicalCalc_CHA2DS2_VASc", "age", 700),
    # Not merely large: 5 mmol/L is below the bottom of the survivable window,
    # and `must_exceed=0` let it through because zero is not a floor for a
    # concentration.
    ("ClinicalCalc_MELD_Na", "sodium", 5),
]


@pytest.mark.parametrize("tool,param,bad", IMPOSSIBLY_LARGE)
def test_value_outside_the_plausible_range_is_refused_and_names_it(tool, param, bad):
    result = _run(tool, dict(VALID[tool], **{param: bad}))
    assert result.get("status") == "error", (
        f"{tool} accepted {param}={bad} and returned a score: {result}"
    )
    assert param in result.get("error", ""), (
        f"{tool} rejected {param}={bad} without naming it: {result}"
    )
    # No score, band or class may survive alongside the refusal. Asserted as
    # the absence of `data` itself rather than as `"score" not in
    # result.get("data", {})`, which is true by construction on the error path
    # and could never fail. (Not `"score" not in json.dumps(result)` either --
    # the refusal message contains the word "score".)
    assert "data" not in result


# A patient in genuine crisis, at values a clinician really does see. The cost
# of an upper bound is that it can refuse a real reading, so this is the
# control that keeps the bounds honest rather than merely strict.
EXTREME_BUT_REAL = [
    (
        "ClinicalCalc_MELD_Na",
        {"creatinine": 8.0, "bilirubin": 45.0, "inr": 6.5, "sodium": 118},
    ),
    ("ClinicalCalc_Child_Pugh", {"bilirubin": 38.0, "albumin": 1.4, "inr": 4.2}),
    ("ClinicalCalc_CHA2DS2_VASc", {"age": 104, "sex": "female"}),
    (
        "ClinicalCalc_ASCVD_risk",
        {
            "age": 79,
            "sex": "male",
            "race": "white",
            "total_cholesterol": 480,
            "hdl_cholesterol": 22,
            "systolic_bp": 220,
        },
    ),
]


@pytest.mark.parametrize("tool,args", EXTREME_BUT_REAL)
def test_extreme_but_genuine_values_still_score(tool, args):
    result = _run(tool, args)
    assert result.get("status") == "success", (
        f"{tool} refused a value a clinician really sees: {result}"
    )


def test_creatinine_is_disclosed_rather_than_refused():
    """Deliberately outside the bounds table, in both directions of the family.

    Refusal is the right protection only where the calculator cannot disclose.
    Both calculators taking a creatinine do: CKD-EPI caveats the units
    (Fix-R46) and MELD-Na names the value it clamped away. An upper bound here
    would have reversed a shipped decision from another round.

    The MELD-Na half of that claim was not true when it was first written --
    `creatinine_used: 4.0` was the whole of the "disclosure", and 900 appeared
    nowhere -- so this asserts the caller is actually told, not merely that a
    clamped number is present.
    """
    meld = _run(
        "ClinicalCalc_MELD_Na",
        dict(VALID["ClinicalCalc_MELD_Na"], creatinine=900),
    )
    assert meld["status"] == "success"
    comp = meld["data"]["components"]
    assert comp["creatinine_used"] == 4.0
    assert comp["creatinine_reported"] == 900.0
    assert "900" in comp["bounded_inputs_note"]

    egfr = ClinicalCalculatorTool(_config("ClinicalCalc_eGFR_CKD_EPI")).run(
        {"creatinine": 1000, "age": 40, "sex": "female"}
    )
    assert egfr["status"] == "success"
    assert any("units" in caveat for caveat in egfr["data"]["caveats"])


def test_every_bounded_input_is_disclosed_the_same_way_not_just_sodium():
    """Three floors fire at once; none of them may be silent.

    Reporting only the post-clamp value is what let creatinine 900 read as
    `creatinine_used: 4.0` with nothing saying 900 had been clamped. Sodium
    was given a `_reported` twin and a note first; a breakdown with two
    disclosure conventions in it is worse than either alone.
    """
    result = _run(
        "ClinicalCalc_MELD_Na",
        {"creatinine": 0.4, "bilirubin": 0.3, "inr": 0.8, "sodium": 134},
    )
    comp = result["data"]["components"]
    for name, reported in (("creatinine", 0.4), ("bilirubin", 0.3), ("inr", 0.8)):
        assert comp[f"{name}_used"] == 1.0
        assert comp[f"{name}_reported"] == reported
        assert name in comp["bounded_inputs_note"]


def test_no_bounded_inputs_note_when_nothing_was_clamped():
    """Control: a note that fires on ordinary input would be worse than none."""
    result = _run(
        "ClinicalCalc_MELD_Na",
        {"creatinine": 2.0, "bilirubin": 5.0, "inr": 2.0, "sodium": 130},
    )
    assert "bounded_inputs_note" not in result["data"]["components"]


def test_meld_na_reports_the_sodium_the_formula_actually_used():
    """`sodium_used` named the raw argument, not the bounded value.

    MELD-Na bounds sodium to [125, 137]. A patient with sodium 118 was told the
    score used 118. The three sibling components already reported the bounded
    value they used, and the breakdown exists to make the score auditable.
    """
    result = _run(
        "ClinicalCalc_MELD_Na",
        {"creatinine": 2.0, "bilirubin": 5.0, "inr": 2.0, "sodium": 118},
    )
    comp = result["data"]["components"]
    assert comp["sodium_used"] == 125.0
    assert comp["sodium_reported"] == 118.0
    assert "sodium 118 entered the formula as 125" in comp["bounded_inputs_note"]


def test_meld_na_does_not_claim_a_sodium_it_never_applied():
    """Below the MELD>11 threshold the sodium term is not evaluated at all."""
    result = _run(
        "ClinicalCalc_MELD_Na",
        {"creatinine": 1.0, "bilirubin": 1.0, "inr": 1.0, "sodium": 140},
    )
    comp = result["data"]["components"]
    assert result["data"]["score"] <= 11
    assert comp["sodium_used"] is None
    assert comp["sodium_reported"] == 140.0
    assert "did not affect" in comp["sodium_note"]


def test_an_in_range_sodium_above_the_threshold_is_used_verbatim():
    """Control: no note, and no discrepancy, when nothing was bounded away."""
    result = _run(
        "ClinicalCalc_MELD_Na",
        {"creatinine": 2.0, "bilirubin": 5.0, "inr": 2.0, "sodium": 130},
    )
    comp = result["data"]["components"]
    assert result["data"]["score"] > 11
    assert comp["sodium_used"] == 130.0 == comp["sodium_reported"]
    assert "sodium_note" not in comp
    assert "bounded_inputs_note" not in comp
