"""Numeric ``subgroup`` values must keep the matching subjects.

``ClinicalTrialAESeverityTestTool`` receives ``subgroup`` as text, for example
``AGE=65``. ``pandas.read_csv`` stores AGE as int, or as float when any value
is missing. Comparing that column to the string ``"65"`` used to match nobody
and the tool then reported an empty cohort.
"""

import importlib.util
from pathlib import Path

import pytest

from tooluniverse.clinical_trial_stats_tool import (
    ClinicalTrialAESeverityTestTool,
    prepare_cohort,
)

pytestmark = pytest.mark.unit

_SKILL_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "tooluniverse-statistical-modeling"
    / "scripts"
    / "prepare_ae_cohort.py"
)

_DM = """USUBJID,AGE,expect_interact,TRTGRP
S1,65,Yes,BCG
S2,40,No,Placebo
S3,65,Yes,BCG
"""

_AE = """USUBJID,AESEV
S1,1
S1,2
S2,1
S3,3
"""

_DM_MISSING_AGE = """USUBJID,AGE,expect_interact,TRTGRP
S1,65,Yes,BCG
S2,,No,Placebo
S3,65,Yes,BCG
"""


def _skill_prepare_cohort():
    spec = importlib.util.spec_from_file_location(
        "prepare_ae_cohort_skill", _SKILL_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prepare_cohort


def _write(tmp_path: Path, dm: str = _DM) -> tuple[str, str]:
    dm_path = tmp_path / "DM.csv"
    ae_path = tmp_path / "AE.csv"
    dm_path.write_text(dm)
    ae_path.write_text(_AE)
    return str(dm_path), str(ae_path)


@pytest.mark.parametrize("prepare", [prepare_cohort, _skill_prepare_cohort()])
def test_integer_age_subgroup_keeps_matching_subjects(tmp_path, prepare):
    """AGE=65 keeps the two 65-year-old subjects and their max severity."""
    dm, ae = _write(tmp_path)
    cohort = prepare(dm, ae, "AGE=65")
    assert list(cohort["USUBJID"]) == ["S1", "S3"]
    assert list(cohort["AESEV"]) == [2, 3]


@pytest.mark.parametrize("prepare", [prepare_cohort, _skill_prepare_cohort()])
def test_missing_age_stays_numeric_and_still_matches(tmp_path, prepare):
    """A blank AGE makes the column float; AGE=65 still matches 65.0."""
    dm, ae = _write(tmp_path, _DM_MISSING_AGE)
    cohort = prepare(dm, ae, "AGE=65")
    assert list(cohort["USUBJID"]) == ["S1", "S3"]


@pytest.mark.parametrize("prepare", [prepare_cohort, _skill_prepare_cohort()])
def test_string_subgroup_still_matches(tmp_path, prepare):
    """Text filters such as expect_interact=Yes keep working."""
    dm, ae = _write(tmp_path)
    cohort = prepare(dm, ae, "expect_interact=Yes")
    assert list(cohort["USUBJID"]) == ["S1", "S3"]


@pytest.mark.parametrize("prepare", [prepare_cohort, _skill_prepare_cohort()])
def test_whitespace_around_numeric_subgroup(tmp_path, prepare):
    """Spaces around the column name and value are ignored."""
    dm, ae = _write(tmp_path)
    cohort = prepare(dm, ae, " AGE = 65 ")
    assert list(cohort["USUBJID"]) == ["S1", "S3"]


@pytest.mark.parametrize("prepare", [prepare_cohort, _skill_prepare_cohort()])
def test_non_numeric_value_on_numeric_column_is_an_error(tmp_path, prepare):
    """AGE=Yes is rejected instead of silently emptying the cohort."""
    dm, ae = _write(tmp_path)
    with pytest.raises(ValueError, match="not numeric"):
        prepare(dm, ae, "AGE=Yes")


def test_prepare_tool_reports_subjects_for_numeric_subgroup(tmp_path):
    """The prepare test returns the two matching subjects, not an empty cohort."""
    pytest.importorskip("scipy")
    dm, ae = _write(tmp_path, _DM_MISSING_AGE)
    tool = ClinicalTrialAESeverityTestTool(
        {
            "name": "clinical_trial_ae_severity_test",
            "type": "ClinicalTrialAESeverityTestTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )
    result = tool.run(
        {
            "dm_file": dm,
            "ae_file": ae,
            "test": "prepare",
            "subgroup": "AGE=65",
        }
    )
    assert result["status"] == "success"
    assert result["data"]["n_subjects"] == 2
    assert result["data"]["aesev_distribution"] == {2: 1, 3: 1}
