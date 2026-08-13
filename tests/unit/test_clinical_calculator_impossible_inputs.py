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
    result = _run("ClinicalCalc_Child_Pugh", dict(VALID["ClinicalCalc_Child_Pugh"], albumin=-1))
    assert result.get("status") == "error"
    assert "Class B" not in json.dumps(result)


def test_ascvd_no_longer_leaks_a_bare_math_domain_error():
    result = _run(
        "ClinicalCalc_ASCVD_risk", dict(VALID["ClinicalCalc_ASCVD_risk"], total_cholesterol=0)
    )
    assert result.get("status") == "error"
    assert result.get("error") != "math domain error"
    assert "total_cholesterol" in result["error"]
