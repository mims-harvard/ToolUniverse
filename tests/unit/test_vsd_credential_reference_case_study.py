from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "vsd"
    / "credential_reference_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_credential_reference_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_credential_case_runs_full_protected_api_pipeline(tmp_path):
    snapshot = study.run_case(tmp_path / "credential-workspace")
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    study.write_artifacts(snapshot, output_json, output_markdown)

    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["promotion"]["verification_case_count"] == 3
    assert snapshot["runtime"]["initial_record_id"] == "RD-ALS"
    assert snapshot["runtime"]["rotated_record_id"] == "RD-SMA"
    assert len(snapshot["runtime"]["transport_log"]) == 6
    assert snapshot["secret_persistence"] == {
        "persisted_secret_count": 0,
        "result_secret_count": 0,
        "persisted_reference": study.ENV_VAR,
    }
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    report = output_markdown.read_text(encoding="utf-8")
    assert "Environment-Backed Rare-Disease Credential Case Study" in report
    assert "Provider Boundary" in report
    assert "Promotion Evidence" in report
    assert "Runtime And Rotation" in report
    assert "Secret Boundary" in report

    tampered = copy.deepcopy(snapshot)
    tampered["runtime"]["operation_sha256_after_rotation"] = "0" * 64
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)


def test_checked_credential_artifact_is_synchronized_and_tamper_detecting():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    study.validate_snapshot(snapshot)
    assert set(snapshot["end_to_end_assertions"]) == study.EXPECTED_ASSERTIONS
    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["secret_persistence"]["persisted_secret_count"] == 0
    assert snapshot["secret_persistence"]["result_secret_count"] == 0

    tampered = copy.deepcopy(snapshot)
    tampered["runtime"]["transport_log"][0]["header_name"] = "X-Other-Key"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)
