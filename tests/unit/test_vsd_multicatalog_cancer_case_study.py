from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "multicatalog_cancer_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_multicatalog_cancer_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_cancer_case_exercises_all_catalog_decisions_and_closes_two_gaps(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")
    monkeypatch.setenv(
        "TOOLUNIVERSE_DATAGOV_API_KEY", "fixture-secret-that-must-not-leak"
    )
    workspace = tmp_path / "workspace"

    with study._replay_transport():
        snapshot = study.run_case(
            workspace=workspace,
            mode="replay",
            generated_at="2026-08-02T06:30:00+00:00",
        )

    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert {item["provider"] for item in snapshot["catalog_searches"]} == set(
        study.CATALOG_CASES
    )
    assert snapshot["demand"]["observation_counts"] == [3, 3]
    assert snapshot["qualification_decisions"]["datagov"]["decision"] == (
        "withheld_after_quality_review"
    )
    assert snapshot["qualification_decisions"]["ckan_data_gov_uk"]["decision"] == (
        "blocked_at_verification"
    )
    assert snapshot["qualification_decisions"]["apis_guru"]["promotable_count"] == 0
    assert [item["tool_name"] for item in snapshot["promotions"]] == [
        study.TRIAL_TOOL,
        study.MORTALITY_TOOL,
    ]
    assert snapshot["runtime_evidence"]["present_before_explicit_load"] == []
    assert snapshot["closed_loop"]["final_plan_states"] == {
        "program_review": "agent_native",
        "mortality_context": "existing_exact",
        "trial_inventory": "existing_exact",
    }
    assert "fixture-secret-that-must-not-leak" not in json.dumps(
        snapshot, sort_keys=True
    )


def test_checked_live_cancer_artifacts_are_synchronized_and_tamper_evident():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))

    study.validate_snapshot(snapshot)
    assert snapshot["mode"] in {"live", "network_backed"}
    if snapshot["mode"] == "network_backed":
        assert snapshot["evidence_summary"] == {
            "candidate_qualification": "live",
            "live_catalog_count": 4,
            "replayed_catalogs": ["datagov"],
        }
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == (
        study.render_markdown(snapshot)
    )

    tampered = copy.deepcopy(snapshot)
    tampered["runtime_evidence"]["mortality_summary"]["latest_cancer_deaths"] = 1
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)

    incomplete = copy.deepcopy(snapshot)
    incomplete["end_to_end_assertions"].pop(
        "all_five_catalogs_returned_live_or_replayed_results"
    )
    with pytest.raises(ValueError, match="assertions"):
        study.validate_snapshot(incomplete)
