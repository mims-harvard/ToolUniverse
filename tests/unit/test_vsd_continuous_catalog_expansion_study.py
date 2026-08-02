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
    / "continuous_catalog_expansion_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_continuous_catalog_expansion_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_checked_expansion_artifact_proves_exhaustive_inert_scale():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    checked = study.validate_portfolio(artifact)
    results = checked["combined_results"]

    assert checked["evaluation_mode"] == "live_network"
    assert results["catalog_record_count"] == 2799
    assert results["compatible_record_count"] == 1748
    assert results["processed_record_count"] == 1748
    assert results["attempted_record_count"] == 1875
    assert results["redundant_attempt_count"] == 127
    assert results["unique_contract_count"] == 1626
    assert results["unique_operation_count"] == 37570
    assert results["unique_draft_ready_count"] == 3097
    assert results["draft_ready_host_count"] == 203
    assert results["scientific_draft_ready_count"] == 309
    assert results["blocked_operation_count"] == 36362
    assert len(checked["scientific_candidate_inventory"]) == 309
    assert all(checked["assertions"].values())
    assert all(
        item["approval_state"] == "unreviewed_operation_candidate"
        and item["execution_allowed"] is False
        and len(item["preview_config_sha256"]) == 64
        for item in checked["scientific_candidate_inventory"]
    )


def test_checked_expansion_report_is_synchronized_and_states_boundaries():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    markdown = study.MARKDOWN_ARTIFACT.read_text(encoding="utf-8")

    assert markdown == study.render_markdown(artifact)
    assert "37,570" in markdown
    assert "3,097" in markdown
    assert "127 redundant attempts" in markdown
    assert "unverified, unapproved, unpublished, unloaded, and non-executable" in (
        markdown
    )
    assert "C:\\Users" not in study.JSON_ARTIFACT.read_text(encoding="utf-8")


def test_expansion_artifact_rejects_tampering_and_scanner_remains_generic():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    altered = copy.deepcopy(artifact)
    altered["combined_results"]["unique_draft_ready_count"] = 100_000
    with pytest.raises(ValueError, match="digest"):
        study.validate_portfolio(altered)

    resealed = copy.deepcopy(artifact)
    resealed["assertions"]["both_catalogs_completed"] = False
    body = {key: value for key, value in resealed.items() if key != "portfolio_sha256"}
    resealed["portfolio_sha256"] = study._digest(body)
    with pytest.raises(ValueError, match="assertions"):
        study.validate_portfolio(resealed)

    scanner_source = (
        Path(__file__).parents[2] / "src" / "tooluniverse" / "vsd_continuous_scanner.py"
    ).read_text(encoding="utf-8")
    scenario_path = (
        Path(__file__).parents[2]
        / "examples"
        / "vsd"
        / "scanner_cancer_studies"
        / "scenarios.json"
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    record_ids = {
        item["record_id"]
        for item in [
            *scenario["accepted_operations"],
            *scenario["rejected_operations"],
        ]
    }
    assert all(record_id not in scanner_source for record_id in record_ids)
