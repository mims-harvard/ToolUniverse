import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "examples" / "vsd" / "candidate_portfolio_review_study.py"
JSON_ARTIFACT = (
    ROOT / "examples" / "vsd" / "artifacts" / "candidate_portfolio_review_study.json"
)
MARKDOWN_ARTIFACT = (
    ROOT / "examples" / "vsd" / "artifacts" / "candidate_portfolio_review_study.md"
)
POLICY = ROOT / "examples" / "vsd" / "candidate_portfolio_review_policy.json"
SPEC = importlib.util.spec_from_file_location(
    "candidate_portfolio_review_study", SCRIPT
)
study = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(study)


def _checked():
    return study.validate_review(json.loads(JSON_ARTIFACT.read_text(encoding="utf-8")))


def test_checked_review_covers_every_candidate_and_current_contract():
    checked = _checked()
    summary = checked["summary"]
    contract = checked["contract_review"]

    assert summary["reviewed_candidate_count"] == 3097
    assert sum(summary["decision_counts"].values()) == 3097
    assert summary["unique_endpoint_identity_count"] == 3041
    assert contract["record_count"] == 290
    assert contract["refreshed_record_count"] == 290
    assert contract["failed_record_count"] == 0
    assert contract["current_candidate_count"] == 3097
    assert contract["changed_or_removed_candidate_count"] == 0
    assert (
        summary["review_eligible_count"] + summary["held_or_superseded_count"] == 3097
    )
    assert summary["scientific_review_eligible_count"] == sum(
        summary["decision_counts"][key]
        for key in (
            "eligible_scientific_no_input_live_verification",
            "eligible_scientific_parameterized_verification",
        )
    )


def test_every_candidate_has_a_deterministic_inert_disposition():
    checked = _checked()
    reviews = checked["candidate_reviews"]

    assert len({item["preview_config_sha256"] for item in reviews}) == 3097
    assert all(item["review_state"] == "contract_review_complete" for item in reviews)
    assert all(item["review_decision"] for item in reviews)
    assert all(
        item["approval_state"] == "unreviewed_operation_candidate" for item in reviews
    )
    assert all(item["execution_allowed"] is False for item in reviews)
    assert all(
        item["source_trust"] == "catalog_record_only_requires_provider_review"
        for item in reviews
    )
    assert all(
        item["contract_review_status"] == "current_candidate_confirmed"
        for item in reviews
    )


def test_live_review_is_hash_bound_and_never_publishes():
    checked = _checked()
    live = checked["live_review"]

    assert live["status"] == "completed"
    assert live["attempted_count"] == len(checked["live_shortlist"])
    assert live["verified_count"] >= 3
    assert all(
        item.get("approval_state") in {None, "unapproved_verified_draft"}
        and item.get("publication_state") in {None, "not_published"}
        for item in live["results"]
    )
    for item in live["results"]:
        if item["decision"] != "verified_live_unapproved":
            continue
        assert item["verification_case_count"] == 3
        assert item["premature_publication_blocked"] is True
        assert len(item["verification_sha256"]) == 64
        assert all(case["http_status"] == 200 for case in item["verification_cases"])
        assert all(case["redirects"] == 0 for case in item["verification_cases"])


def test_report_is_synchronized_and_policy_is_provider_independent():
    checked = _checked()
    assert MARKDOWN_ARTIFACT.read_text(encoding="utf-8") == study.render_markdown(
        checked
    )
    markdown = MARKDOWN_ARTIFACT.read_text(encoding="utf-8")
    assert "3,097" in markdown
    assert "290 / 290" in markdown
    assert "No candidate was approved or published" in markdown

    source = SCRIPT.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")
    for item in checked["live_shortlist"]:
        assert item["record_id"] not in source
        assert item["host"] not in source
        assert item["record_id"] not in policy
        assert item["host"] not in policy


def test_review_rejects_tampering_and_invalid_policy():
    checked = _checked()
    altered = copy.deepcopy(checked)
    altered["candidate_reviews"][0]["review_decision"] = "approved"
    with pytest.raises(ValueError, match="digest"):
        study.validate_review(altered)

    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    policy["side_effect_tokens"] = list(reversed(policy["side_effect_tokens"]))
    with pytest.raises(ValueError, match="normalized and sorted"):
        study.validate_policy(policy)
