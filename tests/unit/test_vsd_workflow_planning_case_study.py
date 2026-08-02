from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "workflow_planning_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_workflow_planning_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_workflow_case_routes_only_the_real_gap_and_writes_auditable_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    snapshot = study.run_case()
    output_json = tmp_path / "workflow-plan.json"
    output_markdown = tmp_path / "workflow-plan.md"
    monkeypatch.setattr(study, "DEFAULT_JSON", output_json)
    monkeypatch.setattr(study, "DEFAULT_MARKDOWN", output_markdown)
    study.write_artifacts(snapshot)

    assert all(snapshot["end_to_end_assertions"].values())
    assert len(snapshot["audit_sha256"]) == 64
    assert snapshot["als_plan"]["required_gap_count"] == 1
    assert snapshot["als_plan"]["execution_allowed"] is False
    assert (
        snapshot["existing_workflow_plan"]["workflow_shortcut"]["name"]
        == "ComprehensiveDrugDiscoveryPipeline"
    )
    assert (
        json.loads(output_json.read_text(encoding="utf-8"))["audit_sha256"]
        == snapshot["audit_sha256"]
    )

    report = output_markdown.read_text(encoding="utf-8")
    assert "Registry-First ALS Workflow Planning Case Study" in report
    assert "ALS Workflow Preflight" in report
    assert "Existing Workflow Shortcut" in report
    assert "Tool Finder Integration" in report
    assert "End-to-End Assertions" in report

    tampered = copy.deepcopy(snapshot)
    tampered["als_plan"]["steps"][0]["classification"] = "missing"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)
