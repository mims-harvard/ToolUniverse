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
    / "scanner_cancer_qualification_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_scanner_cancer_qualification_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_checked_cancer_qualification_proves_promotion_and_rejection_gates():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    checked = study.validate_study(artifact)

    assert checked["evaluation_mode"] == "live_network"
    assert checked["expansion_evidence"] == {
        "portfolio_sha256": (
            "10ce696555b9de42a2bdf1fa1c86ac746a8c631b8c0e4e9b2dff3d3c513e7bd8"
        ),
        "catalog_record_count": 2799,
        "processed_record_count": 1748,
        "unique_operation_count": 37570,
        "unique_draft_ready_count": 3097,
        "scientific_draft_ready_count": 309,
        "blocked_operation_count": 36362,
    }
    assert len(checked["promotions"]) == 4
    assert len(checked["rejections"]) == 4
    assert len(checked["studies"]) == 5
    assert sum(len(item["calls"]) for item in checked["studies"]) == 20
    assert all(checked["assertions"].values())
    assert all(
        item["verification_case_count"] == 5
        and len(item["verification_cases"]) == 5
        and all(
            len(case["payload_sha256"]) == 64
            and case["http_status"] == 200
            and case["redirects"] == 0
            for case in item["verification_cases"]
        )
        and item["early_publication_blocked"]
        for item in checked["promotions"]
    )
    assert all(
        item["decision"] == "rejected_at_live_verification"
        and item["approval_blocked"]
        and item["publication_blocked"]
        for item in checked["rejections"]
    )


def test_cancer_studies_preserve_identifiers_and_distinct_provenance():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    payloads: dict[str, set[str]] = {}

    for case in artifact["studies"]:
        assert len(case["calls"]) == 4
        calls = {item["key"]: item for item in case["calls"]}
        approved = calls["gene_relationships"]["observations"][0]["value"]
        gene_id = calls["gene_regulation"]["observations"][0]["value"]
        hypotheses = calls["drug_hypotheses"]["observations"][0]
        concepts = calls["cohd_concepts"]["observations"][0]
        assert approved == [case["gene_symbol"]]
        assert gene_id == case["gene_symbol"]
        assert hypotheses["full_count"] == 5
        assert concepts["full_count"] >= 1
        for call in case["calls"]:
            provenance = call["provenance"]
            assert provenance["http_status"] == 200
            assert provenance["redirects"] == 0
            assert provenance["endpoint"].startswith("https://")
            payloads.setdefault(call["key"], set()).add(provenance["payload_sha256"])
    assert all(len(values) == 5 for values in payloads.values())


def test_cancer_report_is_synchronized_professional_and_data_driven():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    markdown = study.MARKDOWN_ARTIFACT.read_text(encoding="utf-8")

    assert markdown == study.render_markdown(artifact)
    assert "Five evidence workflows" in markdown
    assert "Primary malignant neoplasm of colon" in markdown
    assert "The live frequency is decimal" in markdown
    assert "error_details" not in markdown
    assert "Why This Is Hard" not in markdown
    assert "Exact VSD Advantage" not in markdown
    assert "C:\\Users" not in study.JSON_ARTIFACT.read_text(encoding="utf-8")

    manifest = json.loads(study.SCENARIOS.read_text(encoding="utf-8"))
    source = MODULE_PATH.read_text(encoding="utf-8")
    record_ids = {
        item["record_id"]
        for item in [
            *manifest["accepted_operations"],
            *manifest["rejected_operations"],
        ]
    }
    assert all(record_id not in source for record_id in record_ids)


def test_cancer_qualification_digest_rejects_tampering():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    altered = copy.deepcopy(artifact)
    altered["expansion_evidence"]["unique_draft_ready_count"] = 100_000
    with pytest.raises(ValueError, match="digest"):
        study.validate_study(altered)

    resealed = copy.deepcopy(artifact)
    resealed["assertions"]["twenty_live_runtime_calls_succeeded"] = False
    body = {key: value for key, value in resealed.items() if key != "study_sha256"}
    resealed["study_sha256"] = study._digest(body)
    with pytest.raises(ValueError, match="assertions"):
        study.validate_study(resealed)
