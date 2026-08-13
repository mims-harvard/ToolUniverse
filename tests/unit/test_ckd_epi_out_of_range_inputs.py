"""CKD-EPI must not call an impossible eGFR "normal", nor leak Python internals.

Three behaviours, all reproduced through the CLI before the change:

    {"creatinine": 0.01, "age": 82, "sex": "female"}
        -> score 240.2, interpretation "... CKD stage G1 (normal, >=90)"
    {"creatinine": -1, "age": 82, "sex": "female"}
        -> "ckd_epi calculation error: type complex doesn't define __round__"
    {"creatinine": 0.3, "age": 82, "sex": "female"}
        -> score 105.8, "CKD stage G1 (normal, >=90)", no qualification

An eGFR of 240 is above any human value including pregnancy hyperfiltration, so
labelling it normal is wrong rather than merely unqualified. The negative-input
message named neither the parameter nor the constraint (the equation raises
scr/kappa to a fractional power, so a negative creatinine yields a complex
number). And a creatinine of 0.3 in an 82-year-old is the textbook case where
creatinine-based eGFR overestimates GFR at low muscle mass -- the direction that
overdoses renally-cleared drugs.

The score itself is unchanged in every case; only the stage label for
non-physiological values and the added 'caveats' list are new.
"""

import json
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


def _config():
    with open(CONFIG) as fh:
        for cfg in json.load(fh):
            if cfg["name"] == "ClinicalCalc_eGFR_CKD_EPI":
                return cfg
    raise AssertionError("ClinicalCalc_eGFR_CKD_EPI not in clinical_calculators_tools.json")


def _run(args):
    return ClinicalCalculatorTool(_config()).run(args)


def test_supraphysiologic_egfr_is_not_labelled_normal():
    result = _run({"creatinine": 0.01, "age": 82, "sex": "female"})
    assert result["status"] == "success"
    # The number is unchanged; only what it is called changes.
    assert result["data"]["score"] == 240.2
    assert "normal" not in result["data"]["interpretation"]
    assert "not stageable" in result["data"]["interpretation"]


def test_below_assay_limit_creatinine_is_disclosed():
    caveats = _run({"creatinine": 0.01, "age": 82, "sex": "female"})["data"]["caveats"]
    assert any("quantitation" in c for c in caveats)


def test_non_positive_creatinine_names_the_parameter_and_the_constraint():
    result = _run({"creatinine": -1, "age": 82, "sex": "female"})
    assert result["status"] == "error"
    assert "creatinine" in result["error"]
    assert "greater than 0" in result["error"]
    # The old message was the Python internals of a complex number.
    assert "__round__" not in result["error"]
    assert "complex" not in result["error"]


def test_zero_creatinine_is_rejected_too():
    """0 divides into the same undefined power, and is a plausible typo."""
    assert _run({"creatinine": 0, "age": 82, "sex": "female"})["status"] == "error"


def test_low_creatinine_in_the_elderly_warns_about_muscle_mass():
    result = _run({"creatinine": 0.3, "age": 82, "sex": "female"})
    assert result["data"]["score"] == 105.8
    assert any("overestimate" in c for c in result["data"]["caveats"])


def test_paediatric_and_extreme_ages_are_disclosed():
    child = _run({"creatinine": 0.9, "age": 0.5, "sex": "female"})
    assert any("paediatric" in c for c in child["data"]["caveats"])
    old = _run({"creatinine": 0.9, "age": 200, "sex": "female"})
    assert any("beyond the ages" in c for c in old["data"]["caveats"])


def test_ordinary_adult_result_is_unchanged_and_carries_no_caveats():
    """Control: the shipped test_examples must not gain a caveat or move.

    A guard that fires on ordinary input would be worse than none.
    """
    for example in _config()["test_examples"]:
        result = _run(example)
        assert result["status"] == "success"
        assert "caveats" not in result["data"], example
        assert "CKD stage G" in result["data"]["interpretation"]
    # Exact values, read off the tool before the change, so an alteration to the
    # equation itself cannot hide behind the new branches.
    assert _run({"creatinine": 0.9, "age": 60, "female": True})["data"]["score"] == 73.2
    assert _run({"creatinine": 1.3, "age": 60, "female": False})["data"]["score"] == 62.9
    assert _run({"creatinine": 1.2, "age": 55, "sex": "female"})["data"]["score"] == 53.5


def test_caveats_is_declared_in_the_return_schema():
    """A field emitted but not declared is the defect this round set out to fix."""
    branches = _config()["return_schema"]["oneOf"]
    success = next(b for b in branches if "score" in b["properties"])
    assert "caveats" in success["properties"]
