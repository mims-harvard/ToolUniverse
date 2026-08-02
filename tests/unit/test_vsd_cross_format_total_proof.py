from __future__ import annotations

import copy
import json

import pytest

from examples.vsd import cross_format_total_proof as study

pytestmark = pytest.mark.unit


def test_cross_format_total_proof_is_complete_and_deterministic(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_PERSIST", "false")
    first = study.run_case(tmp_path / "first")
    second = study.run_case(tmp_path / "second")
    assert first == second
    assert first["portfolio_case_count"] == 16
    assert first["promotion_stage"]["promoted_format_count"] == 6
    assert first["promotion_stage"]["verification_case_count"] == 18
    assert set(first["promotion_stage"]["loaded_tools"]) == set(
        study.FORMAT_TOOL_NAMES.values()
    )
    assert len(first["adversarial_binding_cases"]) == 8
    assert all(
        item["result"] == "rejected" for item in first["adversarial_binding_cases"]
    )
    assert len(first["end_to_end_assertions"]) == 21
    assert all(first["end_to_end_assertions"].values())

    asyncapi = next(
        item
        for item in first["promotion_stage"]["records"]
        if item["source_format"] == "asyncapi"
    )
    assert asyncapi["contract_binding"]["identity"]["event_schema_sha256"] != (
        study._digest({})
    )


def test_checked_cross_format_artifacts_are_synchronized_and_tamper_evident():
    snapshot = json.loads(study.DEFAULT_JSON.read_text(encoding="utf-8"))
    study.validate_snapshot(snapshot)
    assert study.DEFAULT_MARKDOWN.read_text(encoding="utf-8") == study._markdown(
        snapshot
    )
    assert snapshot["portfolio_case_count"] == 16
    assert len(snapshot["prior_case_studies"]) == 15
    assert all(item["all_checks_passed"] for item in snapshot["prior_case_studies"])

    tampered = copy.deepcopy(snapshot)
    tampered["promotion_stage"]["records"][0]["tool_name"] = "SubstitutedTool"
    with pytest.raises(ValueError, match="audit digest"):
        study.validate_snapshot(tampered)

    incomplete = copy.deepcopy(snapshot)
    incomplete["end_to_end_assertions"].pop(
        "all_eight_substitution_attacks_were_rejected"
    )
    incomplete["audit_sha256"] = study._digest(
        {key: value for key, value in incomplete.items() if key != "audit_sha256"}
    )
    with pytest.raises(ValueError, match="assertions"):
        study.validate_snapshot(incomplete)
