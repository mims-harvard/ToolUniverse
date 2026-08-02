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
    / "continuous_catalog_scanner_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_continuous_catalog_scanner_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = study
SPEC.loader.exec_module(study)

pytestmark = pytest.mark.unit


def test_checked_live_portfolio_proves_large_inert_operation_inventory():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    checked = study.validate_portfolio(artifact)
    results = checked["combined_results"]

    assert checked["evaluation_mode"] == "live_network"
    assert checked["live_scale_input"]["catalog_record_count"] == 2529
    assert checked["live_scale_input"]["compatible_openapi_3_count"] == 1521
    assert checked["real_registry"]["tool_count"] == 2744
    assert results["unique_contract_count"] == 127
    assert results["operation_candidate_count"] == 4925
    assert results["draftable_tool_count"] == 717
    assert results["draftable_host_count"] == 31
    assert results["blocked_operation_count"] == 4281
    assert results["failed_contract_count"] == 24
    assert results["blocker_counts"]["server_host_not_publicly_addressable"] == 4
    assert all(checked["assertions"].values())
    assert all(
        sample["approval_state"] == "unreviewed_operation_candidate"
        and sample["execution_allowed"] is False
        and len(sample["preview_config_sha256"]) == 64
        for sample in checked["draftable_samples"]
    )


def test_checked_markdown_is_synchronized_and_professional():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    markdown = study.MARKDOWN_ARTIFACT.read_text(encoding="utf-8")

    assert markdown == study.render_markdown(artifact)
    assert "4,925" in markdown
    assert "717" in markdown
    assert "No provider operation was called" in markdown
    assert "not a published tool" in markdown
    assert "C:\\Users" not in study.JSON_ARTIFACT.read_text(encoding="utf-8")
    assert "TOOLUNIVERSE_VSD_SCANNER_CREDENTIAL" not in (
        study.JSON_ARTIFACT.read_text(encoding="utf-8")
    )
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert all(
        sample["record_id"] not in source for sample in artifact["draftable_samples"]
    )


def test_portfolio_digest_and_assertions_reject_tampering():
    artifact = json.loads(study.JSON_ARTIFACT.read_text(encoding="utf-8"))
    altered = copy.deepcopy(artifact)
    altered["combined_results"]["draftable_tool_count"] = 100_000
    with pytest.raises(ValueError, match="hash"):
        study.validate_portfolio(altered)

    resealed = copy.deepcopy(artifact)
    resealed["assertions"][
        "at_least_five_hundred_unique_tool_configs_were_draftable"
    ] = False
    body = {key: value for key, value in resealed.items() if key != "portfolio_sha256"}
    resealed["portfolio_sha256"] = study._digest(body)
    with pytest.raises(ValueError, match="assertions"):
        study.validate_portfolio(resealed)
