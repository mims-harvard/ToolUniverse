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
    / "biomedical_evaluation_portfolio.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_biomedical_evaluation_portfolio", MODULE_PATH
)
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_five_scenarios_are_data_driven_and_cover_existing_registry_tools():
    scenarios = study.load_scenarios()

    assert len(scenarios) == 5
    assert {item["promotion_mode"] for item in scenarios} == {
        "strict",
        "reviewed_response",
    }
    assert sum(len(item["reused_tools"]) for item in scenarios) == 17
    source = MODULE_PATH.read_text(encoding="utf-8")
    for scientific_literal in (
        "MONDO:0004976",
        "PDCD1",
        "Arsenic trioxide",
        "BRD-K12343256",
        "tuberculosis_resistance_integration",
    ):
        assert scientific_literal not in source


def test_replay_portfolio_runs_all_lifecycle_boundaries_and_writes_artifacts(
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

    assert artifact["case_count"] == 5
    assert artifact["published_tool_count"] == 5
    assert artifact["verification_execution_count"] == 15
    assert artifact["all_assertions_passed"] is True
    assert all(
        case["without_vsd"]["planned_operation_classification"] == "missing"
        and case["with_vsd"]["planned_operation_classification"]
        == "existing_exact"
        and all(case["assertions"].values())
        for case in artifact["cases"]
    )
    reviewed = [
        case
        for case in artifact["cases"]
        if case["source"]["promotion_mode"] == "reviewed_response"
    ]
    assert len(reviewed) == 2
    assert all(
        case["governance"]["resolved_blockers"] == ["json_response_missing"]
        for case in reviewed
    )
    assert study.validate_portfolio(json.loads(output_json.read_text())) == artifact
    assert output_markdown.read_text(encoding="utf-8") == study.render_markdown(
        artifact
    )
    serialized = output_json.read_text(encoding="utf-8")
    assert "C:\\Users" not in serialized
    assert "TOOLUNIVERSE_VSD_ALLOWED_HOSTS" not in serialized


def test_portfolio_digest_detects_tampering():
    artifact = json.loads(
        (study.DEFAULT_JSON).read_text(encoding="utf-8")
    )
    altered = copy.deepcopy(artifact)
    altered["cases"][0]["with_vsd"]["runtime"]["observations"][0]["value"] = (
        "changed"
    )

    with pytest.raises(ValueError, match="digest"):
        study.validate_portfolio(altered)


def test_checked_network_backed_artifacts_are_complete_and_synchronized():
    artifact = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))

    study.validate_portfolio(artifact)
    assert artifact["requested_mode"] == "network_backed"
    assert artifact["live_case_count"] == 2
    assert artifact["replay_case_count"] == 3
    assert artifact["live_case_count"] + artifact["replay_case_count"] == 5
    assert all(
        case["evidence_mode"] == "live"
        or (
            case["live_attempt"]["completed"] is False
            and case["live_attempt"]["fallback"] == "checked replay"
        )
        for case in artifact["cases"]
    )
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == (
        study.render_markdown(artifact)
    )


def test_virtual_cell_case_extends_an_existing_provider_without_replacing_it():
    artifact = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    case = next(
        item
        for item in artifact["cases"]
        if item["case_id"] == "virtual_cell_perturbation_selection"
    )

    assert any(
        item["name"] == "L1000FWD_sig_search"
        for item in case["existing_tooluniverse_coverage"]
    )
    assert case["with_vsd"]["published_tool"] == "VSDL1000PerturbagenResolver"
    assert case["source"]["operation_path"] == "/synonyms/{query_string}"
