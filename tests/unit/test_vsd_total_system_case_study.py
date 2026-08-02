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
    Path(__file__).parents[2] / "examples" / "vsd" / "total_system_case_study.py"
)
SPEC = importlib.util.spec_from_file_location("vsd_total_system_case_study", MODULE_PATH)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_total_system_case_proves_the_complete_growth_loop(
    monkeypatch, tmp_path: Path
):
    """The full case must pass every boundary and produce verifiable artifacts."""
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")
    workspace = tmp_path / "total-system"

    snapshot = study.run_case(workspace)
    proposal = json.loads(
        (workspace / "reviewed-demand-proposal.json").read_text(encoding="utf-8")
    )
    output_json = tmp_path / "total-system.json"
    output_markdown = tmp_path / "total-system.md"
    output_proposal = tmp_path / "total-system-proposal.json"
    study.write_artifacts(
        snapshot,
        proposal,
        output_json,
        output_markdown,
        output_proposal,
    )

    assertions = snapshot["end_to_end_assertions"]
    assert set(assertions) == study.EXPECTED_ASSERTIONS
    assert all(value is True for value in assertions.values())
    assert snapshot["initial_gap"]["classification"] == "missing"
    assert snapshot["private_demand"]["initial_observation_count"] == 3
    assert snapshot["private_demand"]["resolved_observation_counts"] == {
        "exact": 1,
        "missing": 3,
        "partial": 0,
    }
    assert snapshot["private_demand"]["final_demand_count"] == 0
    assert snapshot["promotion"]["verification_case_count"] == 3
    assert snapshot["expanded_registry"]["classification"] == "existing_exact"
    assert snapshot["runtime"]["record_ids"] == ["RD-ALS", "RD-DMD", "RD-SMA"]
    assert len(snapshot["runtime"]["transport_log"]) == 6
    assert snapshot["lifecycle"]["states"] == ["suspended", "active"]
    assert snapshot["lifecycle"]["suspended_loaded_tools"] == []
    assert snapshot["lifecycle"]["final_loaded_tools"] == [study.TOOL_NAME]
    assert snapshot["docker_boundary"]["pull_request"].endswith("/pull/420")
    assert len(snapshot["audit_sha256"]) == 64

    validate_proposal_export(proposal)
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    assert json.loads(output_proposal.read_text(encoding="utf-8")) == proposal
    report = output_markdown.read_text(encoding="utf-8")
    assert "ALS Demand-To-Reviewed-Tool Total VSD System Study" in report
    assert "Organic Demand Loop" in report
    assert "Registry Growth And Use" in report
    assert "Drift And Recovery" in report
    assert "End-to-End Assertions" in report
    assert "#420" in report
    combined_artifacts = output_json.read_text() + output_proposal.read_text()
    assert study._secret("initial") not in combined_artifacts
    assert study._secret("rotated") not in combined_artifacts

    repeated_workspace = tmp_path / "total-system-repeated"
    repeated_snapshot = study.run_case(repeated_workspace)
    repeated_proposal = json.loads(
        (repeated_workspace / "reviewed-demand-proposal.json").read_text(
            encoding="utf-8"
        )
    )
    assert repeated_snapshot == snapshot
    assert repeated_proposal == proposal

    tampered = copy.deepcopy(snapshot)
    tampered["runtime"]["record_ids"][0] = "RD-TAMPERED"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)

    incomplete = copy.deepcopy(snapshot)
    incomplete["end_to_end_assertions"].pop("initial_capability_is_missing")
    with pytest.raises(ValueError, match="complete assertion set"):
        study.validate_snapshot(incomplete)


def test_checked_total_system_artifacts_are_synchronized_and_valid():
    """Checked JSON and Markdown must remain synchronized and audit-valid."""
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    proposal = json.loads(study.DEFAULT_PROPOSALS.read_text(encoding="utf-8"))

    study.validate_snapshot(snapshot)
    validate_proposal_export(proposal)
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == study._markdown(
        snapshot
    )
    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(value is True for value in snapshot["end_to_end_assertions"].values())
