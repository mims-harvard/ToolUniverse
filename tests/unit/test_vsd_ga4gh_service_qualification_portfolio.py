from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "vsd"
    / "ga4gh_service_qualification_portfolio.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_ga4gh_service_qualification_portfolio", MODULE_PATH
)
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_scenarios_are_data_driven_and_span_multiple_ga4gh_standards():
    scenarios = study.load_scenarios()

    assert len(scenarios) == 15
    assert sum(item["expected_qualification"] == "accepted" for item in scenarios) == 3
    assert {item["registry_record"]["type"]["artifact"] for item in scenarios} == {
        "service-registry",
        "drs",
        "trs",
        "wes",
        "rnaget",
    }
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert all(item["registry_record"]["id"] not in source for item in scenarios)
    assert all(item["registry_record"]["url"] not in source for item in scenarios)


@pytest.mark.timeout(420)
def test_replay_portfolio_exercises_acceptance_rejection_and_registry_growth(
    tmp_path,
):
    artifact = study.run_portfolio(
        workspace=tmp_path / "workspace",
        mode="replay",
        generated_at="2026-08-02T12:00:00+00:00",
    )
    output_json = tmp_path / "portfolio.json"
    output_markdown = tmp_path / "portfolio.md"
    study.write_artifacts(artifact, output_json, output_markdown)

    assert artifact["case_count"] == 15
    assert artifact["accepted_count"] == 3
    assert artifact["rejected_count"] == 12
    assert artifact["verification_execution_count"] == 9
    assert artifact["final_execution_count"] == 3
    assert artifact["all_assertions_passed"] is True
    accepted = [
        item
        for item in artifact["cases"]
        if item["with_vsd"]["qualification"] == "accepted"
    ]
    rejected = [
        item
        for item in artifact["cases"]
        if item["with_vsd"]["qualification"] == "rejected"
    ]
    assert all(
        item["with_vsd"]["governance"]["registered_duplicate_count"] >= 1
        and item["with_vsd"]["published_tool"]
        and len(item["catalog_provenance"]["payload_sha256"]) == 64
        for item in accepted
    )
    assert all(
        item["with_vsd"]["governance"]["promotion_state"]["approved"] == []
        and item["with_vsd"]["published_tool"] is None
        for item in rejected
    )
    assert {item["with_vsd"]["failure"]["category"] for item in rejected} == {
        "registered_metadata_mismatch",
        "http_status_failure",
        "response_media_type_mismatch",
        "redirect_rejected",
    }
    assert study.validate_portfolio(json.loads(output_json.read_text())) == artifact
    assert output_markdown.read_text(encoding="utf-8") == study.render_markdown(
        artifact
    )


def test_portfolio_digest_detects_tampering():
    artifact = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    altered = copy.deepcopy(artifact)
    altered["accepted_count"] = 15

    with pytest.raises(ValueError, match="digest"):
        study.validate_portfolio(altered)


def test_checked_artifacts_are_complete_synchronized_and_path_free():
    artifact = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))

    study.validate_portfolio(artifact)
    assert artifact["live_case_count"] + artifact["replay_case_count"] == 15
    assert artifact["accepted_count"] + artifact["rejected_count"] == 15
    assert all(
        item["catalog_provenance"]["http_status"] == 200
        and len(item["catalog_provenance"]["payload_sha256"]) == 64
        for item in artifact["cases"]
    )
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == (
        study.render_markdown(artifact)
    )
    serialized = study.DEFAULT_JSON.read_text(encoding="utf-8")
    assert "C:\\Users" not in serialized
    assert "TOOLUNIVERSE_VSD_ALLOWED_HOSTS" not in serialized
