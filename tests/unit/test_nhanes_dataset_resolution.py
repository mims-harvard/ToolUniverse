"""Regression guard for Fix-R16B-1 and Fix-R16B-2.

Fix-R16B-1: Examination and Questionnaire, like Laboratory, each span many
distinct files (Examination: BMX body measures, BPX blood pressure, AUX
audiometry, ...). The old _COMPONENT_PREFIX fallback silently picked one
arbitrary file (BPX for Examination) regardless of which `variables` were
actually requested, returning status:"success" with the requested variables
silently missing. Now requires `dataset_name` for these components too,
matching the existing Laboratory precedent.

Fix-R16B-2: nhanes_search_datasets' own results carry the cycle suffix
already (e.g. file_name "BMX_J"). Passing that value straight into
NHANES_download_and_parse's `dataset_name` used to append the suffix a
second time ("BMX_J" + "_J" -> 404 downloading BMX_J_J.XPT).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.nhanes_tool import NHANESTool

pytestmark = pytest.mark.unit


def _tool():
    return NHANESTool(
        {
            "name": "NHANES_download_and_parse",
            "fields": {"endpoint": "download_and_parse"},
        }
    )


def test_examination_without_dataset_name_is_rejected():
    tool = _tool()
    result = tool._download_and_parse(
        {"component": "Examination", "cycle": "2017-2018", "variables": ["SEQN", "BMXBMI"]}
    )
    assert result["status"] == "error"
    assert "dataset_name" in result["error"]


def test_questionnaire_without_dataset_name_is_rejected():
    tool = _tool()
    result = tool._download_and_parse(
        {"component": "Questionnaire", "cycle": "2017-2018", "variables": ["SEQN"]}
    )
    assert result["status"] == "error"
    assert "dataset_name" in result["error"]


def test_laboratory_still_requires_dataset_name():
    tool = _tool()
    result = tool._download_and_parse(
        {"component": "Laboratory", "cycle": "2017-2018", "variables": ["SEQN"]}
    )
    assert result["status"] == "error"
    assert "dataset_name" in result["error"]


def test_dataset_name_already_carrying_suffix_is_not_doubled():
    tool = _tool()
    filename = tool._resolve_filename("Examination", "2017-2018", dataset_name="BMX_J")
    assert filename == "BMX_J"


def test_dataset_name_without_suffix_gets_it_appended():
    tool = _tool()
    filename = tool._resolve_filename("Examination", "2017-2018", dataset_name="BMX")
    assert filename == "BMX_J"


def test_dataset_name_with_a_different_cycles_suffix_still_gets_current_appended():
    # A dataset_name ending in a DIFFERENT cycle's suffix than the one being
    # requested should not be mistaken for "already suffixed" -- only an
    # exact match against the requested cycle's own suffix should skip
    # appending.
    tool = _tool()
    filename = tool._resolve_filename("Examination", "2017-2018", dataset_name="BMX_H")
    assert filename == "BMX_H_J"
