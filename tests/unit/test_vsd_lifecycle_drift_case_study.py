from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "lifecycle_drift_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_lifecycle_drift_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_lifecycle_case_runs_drift_state_and_runtime_pipeline(tmp_path):
    snapshot = study.run_case(tmp_path / "lifecycle-workspace")
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    study.write_artifacts(snapshot, output_json, output_markdown)

    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["promotion"]["verification_case_count"] == 3
    assert {
        name: item["classification"]
        for name, item in snapshot["drift_assessments"].items()
    } == {
        "unchanged": "unchanged",
        "metadata_only": "metadata_only",
        "review_required": "review_required",
        "breaking_endpoint": "breaking",
        "breaking_auth": "breaking",
        "repaired": "unchanged",
    }
    assert snapshot["lifecycle"]["states"] == [
        "suspended",
        "active",
        "retired",
    ]
    assert snapshot["lifecycle"]["suspended_loaded_tools"] == []
    assert snapshot["lifecycle"]["active_loaded_tools"] == [study.TOOL_NAME]
    assert snapshot["lifecycle"]["retired_loaded_tools"] == []
    assert len(snapshot["runtime"]["transport_log"]) == 5
    assert snapshot["secret_boundary"]["persisted_secret_count"] == 0
    assert snapshot["secret_boundary"]["result_secret_count"] == 0
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    report = output_markdown.read_text(encoding="utf-8")
    assert "Provider Drift And Lifecycle Case Study" in report
    assert "Reviewed Publication" in report
    assert "Drift Classification" in report
    assert "Explicit Lifecycle" in report
    assert "Operational Boundary" in report

    tampered = copy.deepcopy(snapshot)
    tampered["lifecycle"]["states"][1] = "suspended"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)


def test_checked_lifecycle_artifact_is_synchronized_and_tamper_detecting():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    study.validate_snapshot(snapshot)
    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert len(snapshot["drift_assessments"]) == 6
    assert len(snapshot["lifecycle"]["event_sha256"]) == 3

    tampered = copy.deepcopy(snapshot)
    tampered["drift_assessments"]["breaking_endpoint"]["suspension_recommended"] = False
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)
