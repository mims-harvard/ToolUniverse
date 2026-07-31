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


def _results():
    definitions = {source["source_id"]: source for source in case_study.SOURCES}
    request = {
        "status_code": 200,
        "content_type": "application/json",
        "response_bytes": 123,
        "redirects": 0,
    }
    return [
        case_study.SourceResult(
            definitions["cdc_places"],
            [
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Jefferson",
                    "locationname": "01073011207",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "7.1",
                    "low_confidence_limit": "6.3",
                    "high_confidence_limit": "8.0",
                },
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Jefferson",
                    "locationname": "01073010900",
                    "measure": "Coronary heart disease among adults",
                    "data_value": "10.5",
                    "low_confidence_limit": "9.4",
                    "high_confidence_limit": "11.7",
                },
            ],
            request,
        ),
        case_study.SourceResult(
            definitions["openfda_labels"],
            {
                "results": [
                    {
                        "set_id": "fixed-label-id",
                        "effective_time": "20240416",
                        "warnings": [
                            "Ask a doctor before use if you have heart disease or "
                            "high blood pressure or take a blood thinning drug."
                        ],
                        "openfda": {
                            "brand_name": ["Low Dose Aspirin"],
                            "generic_name": ["ASPIRIN"],
                            "route": ["ORAL"],
                        },
                    }
                ]
            },
            request,
        ),
        case_study.SourceResult(
            definitions["who_gho"],
            {
                "value": [
                    {
                        "IndicatorCode": "NCD_HYP_DIAGNOSIS_C",
                        "IndicatorName": "Hypertension diagnosis coverage (%)",
                        "Language": "EN",
                    }
                ]
            },
            request,
        ),
    ]


def test_artifact_is_deterministic_bounded_and_privacy_safe():
    """Reduce fixtures into stable bounded output without retaining raw data."""
    generated_at = "2026-07-31T12:00:00Z"
    first = case_study.build_artifact(_results(), generated_at=generated_at)
    second = case_study.build_artifact(
        list(reversed(_results())), generated_at=generated_at
    )

    assert case_study.canonical_json(first) == case_study.canonical_json(second)
    assert first["schema_version"] == 1
    assert first["case_study"]["generated_at"] == generated_at
    assert len(first["observations"]["cdc_places_estimates"]) == 2
    assert [
        row["locationname"] for row in first["observations"]["cdc_places_estimates"]
    ] == ["01073010900", "01073011207"]
    assert first["observations"]["openfda_label"]["warning_terms_found"] == [
        "blood thinning",
        "heart disease",
        "high blood pressure",
    ]
    serialized = case_study.canonical_json(first)
    assert "Ask a doctor" not in serialized
    assert all(len(source["payload_sha256"]) == 64 for source in first["provenance"])


def test_markdown_contains_evidence_and_nonclinical_limits():
    """Render provenance and explicit interpretation limits in the report."""
    artifact = case_study.build_artifact(
        _results(), generated_at="2026-07-31T12:00:00Z"
    )
    markdown = case_study.render_markdown(artifact)

    assert "NCD_HYP_DIAGNOSIS_C" in markdown
    assert "01073010900" in markdown
    assert "does not establish causation" in markdown
    assert "must not guide medical care" in markdown
    assert markdown.count("SHA-256") == 3


def test_checked_live_artifacts_are_schema_valid_and_in_sync():
    """Keep checked JSON and Markdown artifacts structurally synchronized."""
    artifact_dir = MODULE_PATH.parent / "artifacts"
    artifact = json.loads((artifact_dir / "snapshot.json").read_text(encoding="utf-8"))
    markdown = (artifact_dir / "snapshot.md").read_text(encoding="utf-8")

    assert artifact["schema_version"] == case_study.SCHEMA_VERSION
    assert artifact["case_study"]["id"] == case_study.CASE_STUDY_ID
    assert artifact["case_study"]["generated_at"].endswith("Z")
    assert len(artifact["observations"]["cdc_places_estimates"]) <= 5
    assert {source["source_id"] for source in artifact["provenance"]} == {
        source["source_id"] for source in case_study.SOURCES
    }
    assert case_study.render_markdown(artifact) == markdown
