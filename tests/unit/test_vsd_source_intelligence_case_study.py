from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse.vsd_demand import validate_proposal_export
from tooluniverse.vsd_source_intelligence import validate_core_handoff

pytestmark = pytest.mark.unit

MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "source_intelligence_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_source_intelligence_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)


def test_case_study_runs_eleven_cases_and_writes_review_artifacts(tmp_path):
    workspace = tmp_path / "source-intelligence"
    snapshot = study.run_case(workspace)
    output_json = tmp_path / "snapshot.json"
    output_markdown = tmp_path / "snapshot.md"
    output_handoff = tmp_path / "handoff.json"
    output_demand = tmp_path / "demand.json"
    study.write_artifacts(
        snapshot,
        json_path=output_json,
        markdown_path=output_markdown,
        handoff_path=output_handoff,
        demand_path=output_demand,
        workspace=workspace,
    )

    assert len(snapshot["case_results"]) == 11
    assert all(item["result"] == "passed" for item in snapshot["case_results"])
    assert all(snapshot["end_to_end_assertions"].values())
    assert snapshot["real_registry_baseline"]["tool_count"] >= 2700
    assert snapshot["real_registry_baseline"]["host_count"] >= 250
    assert snapshot["scan_summary"]["candidate_count"] == 7
    assert snapshot["scan_summary"]["candidate_gap_count"] == 6
    assert len(snapshot["snapshot_manifests"]) == 7
    assert len(snapshot["inspection_summary"]) == 7
    assert snapshot["demand_handoff"]["submitted"] is False
    assert json.loads(output_json.read_text(encoding="utf-8")) == snapshot
    validate_core_handoff(json.loads(output_handoff.read_text(encoding="utf-8")))
    validate_proposal_export(json.loads(output_demand.read_text(encoding="utf-8")))
    markdown = output_markdown.read_text(encoding="utf-8")
    assert "ALS Source Intelligence Case-Study Portfolio" in markdown
    assert "Real Registry Audit" in markdown
    assert "Bounded Discovery" in markdown
    assert "Snapshot And Inspection" in markdown
    assert "Cron And Core-Team Visibility" in markdown
    assert "submitted` remained **false**" in markdown

    tampered = copy.deepcopy(snapshot)
    tampered["scan_summary"]["candidate_count"] = 500
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)


def test_checked_case_study_artifacts_are_synchronized_and_tamper_detecting():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    handoff = json.loads(study.DEFAULT_HANDOFF.read_text(encoding="utf-8"))
    demand = json.loads(study.DEFAULT_DEMAND.read_text(encoding="utf-8"))
    study.validate_snapshot(snapshot)
    validate_core_handoff(handoff)
    validate_proposal_export(demand)
    assert snapshot["demand_handoff"]["handoff_id"] == handoff["handoff_id"]
    assert (
        snapshot["demand_handoff"]["proposal_id"]
        == demand["proposals"][0]["proposal_id"]
    )
    assert len(snapshot["audit_sha256"]) == 64
