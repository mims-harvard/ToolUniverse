from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse.vsd_federated_sources import validate_federated_scan

MODULE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "vsd"
    / "federated_biomedical_expansion_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_federated_biomedical_expansion_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_live_source_scan_covers_twenty_sources_and_533_inert_previews():
    scan = validate_federated_scan(
        json.loads(study.SCAN_ARTIFACT.read_text(encoding="utf-8"))
    )
    metrics = scan["metrics"]

    assert metrics["manifest_source_count"] == 20
    assert metrics["successful_source_count"] == 20
    assert metrics["failed_source_count"] == 0
    assert metrics["operation_candidate_count"] == 1142
    assert metrics["unique_operation_identity_count"] == 1142
    assert metrics["structurally_draftable_count"] == 533
    assert metrics["net_new_preview_count"] == 533
    assert metrics["existing_host_gap_count"] == 475
    assert metrics["new_host_candidate_count"] == 58
    assert all(item["execution_allowed"] is False for item in scan["operations"])
    assert all(len(item["semantic_sha256"]) == 64 for item in scan["sources"])


def test_live_cancer_study_proves_promotion_execution_and_rejection_boundaries():
    artifact = study.validate_study(
        json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    )

    assert artifact["study_design"] == {
        "scenario_count": 3,
        "accepted_tool_count": 7,
        "rejected_candidate_count": 3,
        "verification_execution_count": 21,
        "post_publication_execution_count": 21,
        "selected_source_count": 9,
    }
    assert artifact["comparison"]["after_vsd_review"] == {
        "tools_verified_approved_and_published": 7,
        "tools_loaded_into_one_local_runtime": 7,
        "accepted_live_execution_count": 42,
        "candidates_rejected_at_live_verification": 3,
        "built_in_registry_modified": False,
    }
    assert artifact["source_scan"]["cross_portfolio"] == {
        "baseline_candidate_row_count": 3097,
        "baseline_unique_operation_identity_count": 3041,
        "federated_preview_count": 533,
        "overlap_unique_operation_identity_count": 15,
        "federated_incremental_operation_identity_count": 518,
        "combined_unique_operation_identity_count": 3559,
    }
    assert all(artifact["assertions"].values())
    assert all(len(item["tool_results"]) == 7 for item in artifact["scenario_results"])
    assert all(
        item["approval_blocked"] and item["publication_blocked"]
        for item in artifact["rejections"]
    )


def test_report_is_synchronized_professional_and_data_driven():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    markdown = study.MARKDOWN_ARTIFACT.read_text(encoding="utf-8")
    scenarios = json.loads(study.SCENARIOS.read_text(encoding="utf-8"))
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert markdown == study.render_markdown(artifact)
    assert "1,142" in markdown
    assert "533" in markdown
    assert "518" in markdown
    assert "3,559" in markdown
    assert "The 533 previews are candidates, not 533 approved tools." in markdown
    assert "built-in registry was not changed" in markdown
    assert all(
        definition["source_id"] not in source
        for definition in [
            *scenarios["accepted_operations"],
            *scenarios["rejected_operations"],
        ]
    )


def test_study_rejects_tampered_evidence():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    changed = copy.deepcopy(artifact)
    changed["comparison"]["after_vsd_review"][
        "tools_verified_approved_and_published"
    ] = 533

    with pytest.raises(ValueError, match="evidence"):
        study.validate_study(changed)
