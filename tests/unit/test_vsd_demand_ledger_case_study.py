from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse.vsd_demand import VSDDemandError, validate_proposal_export

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "demand_ledger_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_demand_ledger_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_demand_case_runs_hash_bound_plan_ranking_and_explicit_export(tmp_path):
    snapshot = study.run_case(tmp_path / "private-ledger")
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    output_proposals = tmp_path / "proposals.json"
    study.write_artifacts(
        snapshot,
        json_path=output_json,
        markdown_path=output_markdown,
        proposals_path=output_proposals,
    )

    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["observation_summary"] == {
        "plan_runs_recorded": 3,
        "plan_step_observations_recorded": 15,
        "duplicate_step_observations_rejected": 5,
        "retinal_observations_recorded": 2,
        "satisfied_observations_recorded": 1,
    }
    assert [
        item["priority_score"] for item in snapshot["ranking"]["ranked_demands"]
    ] == [15, 10, 6, 6, 6, 6]
    assert len(snapshot["proposal_export"]["proposals"]) == 2
    assert len(snapshot["audit_sha256"]) == 64
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    assert (
        json.loads(output_proposals.read_text(encoding="utf-8"))
        == snapshot["proposal_export"]
    )
    report = output_markdown.read_text(encoding="utf-8")
    assert "Private ALS Capability-Demand Ledger Case Study" in report
    assert "Hash-Bound Workflow Input" in report
    assert "Local Priority Ranking" in report
    assert "Explicit Proposal Export" in report
    assert "Privacy And Execution Boundary" in report

    tampered = copy.deepcopy(snapshot)
    tampered["ranking"]["ranked_demands"][0]["priority_score"] = 500
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)


def test_checked_proposal_artifact_is_synchronized_and_tamper_detecting():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    proposals = json.loads(study.DEFAULT_PROPOSALS.read_text(encoding="utf-8"))
    study.validate_snapshot(snapshot)
    validate_proposal_export(proposals)
    assert snapshot["proposal_export"] == proposals

    tampered = copy.deepcopy(proposals)
    tampered["proposals"][0]["public_summary"] = "A changed public proposal summary"
    with pytest.raises(VSDDemandError, match="derived fields"):
        validate_proposal_export(tampered)
