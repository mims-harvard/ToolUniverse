from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse.vsd_demand import validate_proposal_export

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "vsd"
    / "multicatalog_discovery_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_multicatalog_discovery_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_multicatalog_case_closes_a_real_gap_and_is_reproducible(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")
    workspace = tmp_path / "multicatalog"

    snapshot = study.run_case(workspace)
    proposal = json.loads(
        (workspace / "reviewed-demand-proposal.json").read_text(encoding="utf-8")
    )
    output_json = tmp_path / "multicatalog.json"
    output_markdown = tmp_path / "multicatalog.md"
    output_proposal = tmp_path / "multicatalog-proposal.json"
    study.write_artifacts(
        snapshot,
        proposal,
        output_json,
        output_markdown,
        output_proposal,
    )

    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["initial_gap"]["classification"] == "missing"
    assert snapshot["initial_gap"]["demand_observations"] == {
        "exact": 0,
        "missing": 3,
        "partial": 0,
    }
    assert snapshot["catalog_search"]["candidate_count"] == 5
    assert snapshot["catalog_search"]["cross_catalog_duplicate_count"] == 2
    assert [
        item["status"] for item in snapshot["catalog_search"]["provider_results"]
    ] == ["success"] * 5
    assert snapshot["promotion"]["verification_case_count"] == 3
    assert snapshot["promotion"]["loaded_tools"] == [study.TOOL_NAME]
    assert [item["cohort_id"] for item in snapshot["executed_cohorts"]] == list(
        study.RECORDS
    )
    assert snapshot["closed_gap"]["classification"] == "existing_exact"
    assert snapshot["closed_gap"]["registered_duplicate_count"] == 1
    assert len(snapshot["audit_sha256"]) == 64

    validate_proposal_export(proposal)
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    assert json.loads(output_proposal.read_text(encoding="utf-8")) == proposal
    report = output_markdown.read_text(encoding="utf-8")
    assert "Five-Catalog Search" in report
    assert "Contract Review and Promotion" in report
    assert "Post-Publication Registry Validation" in report
    assert "Why This Case Matters" not in report
    assert "FAIL" not in report

    repeated_snapshot = study.run_case(tmp_path / "repeated")
    repeated_proposal = json.loads(
        (tmp_path / "repeated" / "reviewed-demand-proposal.json").read_text(
            encoding="utf-8"
        )
    )
    assert repeated_snapshot == snapshot
    assert repeated_proposal == proposal


def test_checked_multicatalog_artifacts_are_synchronized_and_tamper_evident():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    proposal = json.loads(study.DEFAULT_PROPOSALS.read_text(encoding="utf-8"))

    study.validate_snapshot(snapshot)
    validate_proposal_export(proposal)
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == study._markdown(
        snapshot
    )

    tampered = copy.deepcopy(snapshot)
    tampered["executed_cohorts"][0]["participants"] = 1
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)

    incomplete = copy.deepcopy(snapshot)
    incomplete["end_to_end_assertions"].pop("all_five_catalog_providers_succeeded")
    with pytest.raises(ValueError, match="complete assertion set"):
        study.validate_snapshot(incomplete)
