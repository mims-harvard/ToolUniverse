from __future__ import annotations

import copy
import json

import pytest

from examples.vsd import growth_value_portfolio as study
from tooluniverse.vsd_demand import validate_proposal_export

pytestmark = pytest.mark.unit


def test_five_domain_portfolio_is_deterministic_and_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")
    first_manifest, first_studies = study.run_portfolio(tmp_path / "first")
    second_manifest, second_studies = study.run_portfolio(tmp_path / "second")

    assert first_manifest == second_manifest
    assert first_studies == second_studies
    assert first_manifest["study_count"] == 5
    assert len(first_manifest["end_to_end_assertions"]) == 10
    assert all(first_manifest["end_to_end_assertions"].values())
    assert first_manifest["combined_metrics"]["registry_tool_count"] >= 2700
    assert first_manifest["combined_metrics"]["new_study_assertions"] == 110
    assert first_manifest["combined_metrics"]["new_verification_cases"] == 15
    assert first_manifest["combined_metrics"]["new_post_verification_executions"] == 15

    assert {item["study_id"] for item in first_studies} == {
        scenario["id"] for scenario in study.SCENARIOS
    }
    assert all(len(item["end_to_end_assertions"]) == 22 for item in first_studies)
    assert all(all(item["end_to_end_assertions"].values()) for item in first_studies)
    assert all(
        item["promotion"]["verification_case_count"] == 3 for item in first_studies
    )
    assert all(len(item["runtime_evidence"]["records"]) == 3 for item in first_studies)

    for root in (tmp_path / "first", tmp_path / "second"):
        for scenario in study.SCENARIOS:
            proposal = json.loads(
                (root / scenario["id"] / "reviewed-demand-proposal.json").read_text(
                    encoding="utf-8"
                )
            )
            validate_proposal_export(proposal)
            assert proposal["transmission"].startswith("none;")


def test_checked_portfolio_and_five_reports_are_synchronized_and_tamper_evident():
    manifest = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    study.validate_portfolio(manifest)
    assert study.DEFAULT_MARKDOWN.read_text(
        encoding="utf-8"
    ) == study._portfolio_markdown(manifest)

    for scenario in study.SCENARIOS:
        json_path = study.ARTIFACTS / f"{scenario['id']}.json"
        markdown_path = study.ARTIFACTS / f"{scenario['id']}.md"
        snapshot = json.loads(json_path.read_text(encoding="utf-8"))
        study.validate_study_snapshot(snapshot)
        assert markdown_path.read_text(encoding="utf-8") == study._study_markdown(
            snapshot
        )
        assert snapshot["study_id"] == scenario["id"]
        assert snapshot["promotion"]["tool_name"] == scenario["tool_name"]

    tampered = copy.deepcopy(manifest)
    tampered["combined_metrics"]["new_verification_cases"] = 14
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_portfolio(tampered)

    first = json.loads(
        (study.ARTIFACTS / f"{study.SCENARIOS[0]['id']}.json").read_text(
            encoding="utf-8"
        )
    )
    first["runtime_evidence"]["record_ids"][0] = "SUBSTITUTED"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_study_snapshot(first)


def test_checked_value_artifacts_contain_no_fixture_credentials():
    artifact_text = "\n".join(
        path.read_text(encoding="utf-8")
        for scenario in study.SCENARIOS
        for path in (
            study.ARTIFACTS / f"{scenario['id']}.json",
            study.ARTIFACTS / f"{scenario['id']}.md",
        )
    )
    for scenario in study.SCENARIOS:
        assert study._secret(scenario["id"], "initial") not in artifact_text
        assert study._secret(scenario["id"], "rotated") not in artifact_text


def test_complete_evaluation_includes_cross_format_and_docker_evidence():
    manifest = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    assert manifest["end_to_end_assertions"]["six_format_total_proof_remains_valid"]
    assert manifest["end_to_end_assertions"]["docker_boundary_is_present_and_hardened"]
    assert (
        study.HERE.parent / "docker_llm" / "artifacts" / "docker_smoke_snapshot.json"
    ).exists()
