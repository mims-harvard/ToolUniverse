from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.network]

MODULE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "vsd"
    / "multicatalog_cancer_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_multicatalog_cancer_live_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_live_multicatalog_cancer_case_completes_the_reviewed_growth_loop(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")

    snapshot = study.run_case(workspace=tmp_path / "workspace", mode="live")

    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert {item["provider"] for item in snapshot["catalog_searches"]} == set(
        study.CATALOG_CASES
    )
    assert [item["tool_name"] for item in snapshot["promotions"]] == [
        study.TRIAL_TOOL,
        study.SCREENING_TOOL,
    ]
    assert snapshot["qualification_decisions"]["datagov"]["approved"] is False
    assert snapshot["qualification_decisions"]["ckan_data_gov_uk"][
        "approved"
    ] is False
    assert snapshot["qualification_decisions"]["apis_guru"][
        "approved"
    ] is False
