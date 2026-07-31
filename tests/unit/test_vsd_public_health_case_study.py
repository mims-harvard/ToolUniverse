from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


MODULE_PATH = (
    Path(__file__).parents[2] / "examples" / "vsd" / "public_health_case_study.py"
)
SPEC = importlib.util.spec_from_file_location(
    "vsd_public_health_case_study", MODULE_PATH
)
assert SPEC and SPEC.loader
case_study = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = case_study
SPEC.loader.exec_module(case_study)


def _provenance(provider: str, endpoint: str) -> dict:
    return {
        "provider": provider,
        "endpoint": endpoint,
        "query_params": {},
        "retrieved_at": "2026-07-31T12:00:00+00:00",
        "http_status": 200,
        "content_type": "application/json",
        "response_bytes": 123,
        "redirects": 0,
        "payload_sha256": "a" * 64,
    }


def _study_run():
    reviewed = []
    source_metadata = {
        "VSDWHOHypertensionIndicator": (
            "who_gho",
            "WHO Global Health Observatory",
            "https://ghoapi.azureedge.net/api/Indicator",
        ),
        "VSDCDCPlacesCoronaryHeartDisease": (
            "cdc_places",
            "CDC PLACES",
            "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
        ),
        "VSDOpenFDALabelBySetId": (
            "openfda_labels",
            "openFDA Drug Labels",
            "https://api.fda.gov/drug/label.json",
        ),
    }
    for tool_name, (source_id, name, endpoint) in source_metadata.items():
        reviewed.append(
            {
                "source_id": source_id,
                "name": name,
                "endpoint": endpoint,
                "description": "Reviewed source fixture.",
                "default_params": {},
                "tool_name": tool_name,
                "review_scope": (
                    "Transport and response adapter reviewed; not scientific endorsement."
                ),
            }
        )

    outputs = {
        "VSDDiscoverSources": {"sources": reviewed},
        "VSDWHOHypertensionIndicator": {
            "indicator": {
                "indicator_code": "NCD_HYP_DIAGNOSIS_C",
                "indicator_name": "Hypertension diagnosis coverage (%)",
                "language": "EN",
            },
            "provenance": _provenance(
                "WHO Global Health Observatory",
                "https://ghoapi.azureedge.net/api/Indicator",
            ),
        },
        "VSDCDCPlacesCoronaryHeartDisease": {
            "measure": "Coronary heart disease among adults",
            "state_abbr": "AL",
            "county_name": "Autauga",
            "possibly_truncated": False,
            "tracts": [
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Autauga",
                    "locationname": "01001011207",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "7.1",
                    "low_confidence_limit": "6.3",
                    "high_confidence_limit": "8.0",
                },
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Autauga",
                    "locationname": "01001010900",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "10.5",
                    "low_confidence_limit": "9.4",
                    "high_confidence_limit": "11.7",
                },
            ],
            "provenance": _provenance(
                "CDC PLACES",
                "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
            ),
        },
        "VSDOpenFDALabelBySetId": {
            "label": {
                "set_id": case_study.ASPIRIN_LABEL_SET_ID,
                "effective_time": "20240416",
                "brand_name": "Low Dose Aspirin",
                "generic_name": "ASPIRIN",
                "route": "ORAL",
                "warnings": [
                    "Ask a doctor before use if you have heart disease or high "
                    "blood pressure or take a blood thinning drug."
                ],
            },
            "provenance": _provenance(
                "openFDA Drug Labels", "https://api.fda.gov/drug/label.json"
            ),
        },
    }
    calls = [
        {
            "sequence": sequence,
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "output_keys": sorted(outputs[tool_name]),
            "result_summary": case_study.summarize_tool_result(
                tool_name, outputs[tool_name]
            ),
        }
        for sequence, (tool_name, arguments) in enumerate(
            case_study.TOOL_CALLS, start=1
        )
    ]
    return case_study.StudyRun(outputs=outputs, calls=calls)


def test_artifact_is_deterministic_bounded_and_privacy_safe():
    """Produce stable descriptive output without retaining raw warning text."""
    generated_at = "2026-07-31T12:00:00Z"
    study_run = _study_run()
    first = case_study.build_artifact(study_run, generated_at=generated_at)
    reversed_run = case_study.StudyRun(
        outputs=dict(reversed(list(study_run.outputs.items()))), calls=study_run.calls
    )
    second = case_study.build_artifact(reversed_run, generated_at=generated_at)

    assert case_study.canonical_json(first) == case_study.canonical_json(second)
    assert first["schema_version"] == 2
    summary = first["findings"]["cdc_places_summary"]
    assert summary["tract_count"] == 2
    assert summary["mean_estimate_pct"] == 8.8
    assert summary["observed_range_percentage_points"] == 3.4
    assert first["tooluniverse_execution"]["call_count"] == 4
    assert first["tooluniverse_execution"]["calls"][2]["result_summary"] == {
        "possibly_truncated": False,
        "tract_count": 2,
    }
    serialized = case_study.canonical_json(first)
    assert "Ask a doctor" not in serialized
    assert "blood thinning" in serialized


def test_markdown_explains_exact_tooluniverse_and_vsd_workflow():
    """Render exact calls, VSD value, findings, and scientific boundaries."""
    artifact = case_study.build_artifact(
        _study_run(), generated_at="2026-07-31T12:00:00Z"
    )
    markdown = case_study.render_markdown(artifact)

    assert "Exactly How ToolUniverse Was Used" in markdown
    assert "ToolUniverse.run_one_function" not in markdown
    assert "run_one_function()" in markdown
    assert "VSDCDCPlacesCoronaryHeartDisease" in markdown
    assert '"county_name": "Autauga"' in markdown
    assert "Why VSD Was Useful" in markdown
    assert "What This Does Not Prove" in markdown
    assert "8.8%" in markdown
    assert markdown.count("SHA-256") == 3


def test_study_rejects_a_possibly_truncated_county_result():
    """Do not describe county coverage when the provider limit was reached."""
    study_run = _study_run()
    study_run.outputs["VSDCDCPlacesCoronaryHeartDisease"]["possibly_truncated"] = True

    with pytest.raises(ValueError, match="may be incomplete"):
        case_study.build_artifact(study_run, generated_at="2026-07-31T12:00:00Z")


def test_checked_live_artifacts_are_schema_valid_and_in_sync():
    """Keep checked JSON and Markdown disease-study artifacts synchronized."""
    artifact_dir = MODULE_PATH.parent / "artifacts"
    artifact = json.loads((artifact_dir / "snapshot.json").read_text(encoding="utf-8"))
    markdown = (artifact_dir / "snapshot.md").read_text(encoding="utf-8")

    assert artifact["schema_version"] == case_study.SCHEMA_VERSION
    assert artifact["case_study"]["id"] == case_study.CASE_STUDY_ID
    assert artifact["case_study"]["generated_at"].endswith("Z")
    assert artifact["tooluniverse_execution"]["loaded_tools"] == list(
        case_study.TOOL_NAMES
    )
    assert artifact["tooluniverse_execution"]["call_count"] == len(
        case_study.TOOL_CALLS
    )
    assert artifact["findings"]["cdc_places_summary"]["tract_count"] == len(
        artifact["cdc_places_estimates"]
    )
    assert all(len(source["payload_sha256"]) == 64 for source in artifact["provenance"])
    assert case_study.render_markdown(artifact) == markdown
