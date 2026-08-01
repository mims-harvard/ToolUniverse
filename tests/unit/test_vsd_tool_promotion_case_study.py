from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.vsd import tool_promotion_cancer_case_study as study
from tooluniverse import vsd_dynamic_rest

pytestmark = pytest.mark.unit


def test_complex_case_promotes_loads_and_executes_two_tools(
    monkeypatch, tmp_path: Path
):
    calls = []

    def fake_get(url, params, *, timeout):
        assert url == "https://data.ny.gov/resource/2ig8-yxf8.json"
        assert params["$limit"] == 25
        assert timeout == 20.0
        filter_field = next(key for key in params if not key.startswith("$"))
        value = params[filter_field]
        calls.append((filter_field, value))
        rows = [
            {
                "date_opened": "2024-01-01T00:00:00.000",
                "protocol": f"RPCI-{index}",
                "primary_site": value if filter_field == "primary_site" else "Breast",
                "study_phase": value if filter_field == "study_phase" else "II",
                "title": f"Verified trial {index}",
                "principal_investigator": "Example Investigator",
            }
            for index in range(1, 3)
        ]
        return rows, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": len(json.dumps(rows)),
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    workspace = tmp_path / "promotion"
    output_json = tmp_path / "result.json"
    output_markdown = tmp_path / "result.md"
    result = study.run_case(
        workspace=workspace,
        output_json=output_json,
        output_markdown=output_markdown,
    )

    assert len(calls) == 8
    assert result["loaded_tools"] == [
        "VSDGeneratedCancerTrialsByPhase",
        "VSDGeneratedCancerTrialsBySite",
    ]
    assert [item["case_count"] for item in result["promotions"]] == [3, 3]
    assert [item["row_count"] for item in result["runtime_checks"]] == [2, 2]
    assert all(len(item["publication_sha256"]) == 64 for item in result["promotions"])
    assert result["promotion_state"] == {
        "drafts": sorted(item["draft_id"] for item in result["promotions"]),
        "evidence": sorted(item["draft_id"] for item in result["promotions"]),
        "approvals": sorted(item["draft_id"] for item in result["promotions"]),
        "approved": result["loaded_tools"],
    }
    assert json.loads(output_json.read_text(encoding="utf-8"))["case"] == (
        "one_discovered_source_to_two_reviewed_cancer_trial_tools"
    )
    report = output_markdown.read_text(encoding="utf-8")
    assert "One discovery candidate produced two distinct" in report
    assert "Fresh Runtime Check" in report
    assert "not trial quality" in report
