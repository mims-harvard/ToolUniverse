from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tooluniverse import vsd_tool

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


def _cdc_estimates() -> list[dict]:
    values = {
        "ACCESS2": [5.0, 10.0, 15.0],
        "BPHIGH": [30.0, 40.0, 50.0],
        "CHD": [4.0, 7.0, 10.0],
        "CHECKUP": [90.0, 80.0, 70.0],
        "CSMOKING": [8.0, 13.0, 18.0],
        "HIGHCHOL": [30.0, 40.0, 50.0],
        "LPA": [15.0, 25.0, 35.0],
        "OBESITY": [25.0, 35.0, 45.0],
    }
    estimates = []
    definitions = vsd_tool.VSDCDCPlacesHeartHealthProfile.MEASURES
    for tract_index, tract in enumerate(("01001020100", "01001020200", "01001020300")):
        for measure_id in case_study.CDC_MEASURE_IDS:
            value = values[measure_id][tract_index]
            interval = 0.5 if measure_id == "CHD" else 1.0
            estimates.append(
                {
                    "year": "2023",
                    "stateabbr": "AL",
                    "countyname": "Autauga",
                    "locationname": tract,
                    "measure": definitions[measure_id]["name"],
                    "measureid": measure_id,
                    "data_value": str(value),
                    "low_confidence_limit": str(value - interval),
                    "high_confidence_limit": str(value + interval),
                }
            )
    return estimates


def _study_run() -> case_study.StudyRun:
    cdc_definitions = [
        {"measure_id": measure_id, **definition}
        for measure_id, definition in vsd_tool.VSDCDCPlacesHeartHealthProfile.MEASURES.items()
    ]
    source_metadata = {
        "VSDWHOHypertensionIndicator": (
            "who_gho",
            "WHO Global Health Observatory",
            "https://ghoapi.azureedge.net/api/Indicator",
        ),
        case_study.CDC_TOOL_NAME: (
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
    reviewed = [
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
        for tool_name, (source_id, name, endpoint) in source_metadata.items()
    ]

    outputs = {
        "VSDDiscoverSources": {"sources": reviewed},
        case_study.CDC_TOOL_NAME: {
            "measure_definitions": cdc_definitions,
            "state_abbr": "AL",
            "county_name": "Autauga",
            "possibly_truncated": False,
            "estimates": _cdc_estimates(),
            "provenance": _provenance(
                "CDC PLACES",
                "https://chronicdata.cdc.gov/resource/cwsq-ngmh.json",
            ),
        },
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
        "VSDOpenFDALabelBySetId": {
            "label": {
                "set_id": case_study.ASPIRIN_LABEL_SET_ID,
                "effective_time": "20240416",
                "brand_name": "Low Dose Aspirin",
                "generic_name": "ASPIRIN",
                "route": "ORAL",
                "warnings": [
                    (
                        "Ask a doctor before use if you have heart disease or high "
                        "blood pressure or take a blood thinning drug."
                    )
                ],
            },
            "provenance": _provenance(
                "openFDA Drug Labels", "https://api.fda.gov/drug/label.json"
            ),
        },
        "PubMed_search_articles": [
            {
                "pmid": "35354074",
                "title": "Neighborhood-level Social Vulnerability and Prevalence of Cardiovascular Risk Factors and Coronary Heart Disease.",
                "authors": ["Bevan G", "Pandey A"],
                "journal": "S\u00c3\u00a3o cardiovascular journal",
                "pub_year": "2023",
                "doi": "10.1016/j.cpcardiol.2022.101182",
                "article_type": "Journal Article, Review",
                "url": "https://pubmed.ncbi.nlm.nih.gov/35354074/",
            }
        ],
        "ClinicalTrials_search_studies": {
            "studies": [
                {
                    "nct_id": "NCT04562532",
                    "brief_title": "Coronary stent trial",
                    "status": "ACTIVE_NOT_RECRUITING",
                    "study_type": "INTERVENTIONAL",
                    "phases": ["NA"],
                    "enrollment": 1720,
                    "conditions": ["Coronary Artery Disease"],
                    "interventions": ["Device"],
                    "sponsor": "Example sponsor",
                    "start_date": "2021-02-17",
                    "completion_date": "2027-06-30",
                }
            ],
            "total_count": 29,
        },
    }
    calls = [
        {
            "sequence": sequence,
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "result_summary": case_study.summarize_tool_result(
                tool_name, outputs[tool_name]
            ),
        }
        for sequence, (tool_name, arguments) in enumerate(
            case_study.TOOL_CALLS, start=1
        )
    ]
    return case_study.StudyRun(outputs=outputs, calls=calls)


def test_artifact_is_deterministic_complete_and_privacy_safe():
    """Build a stable multi-measure dossier without raw label warnings."""
    generated_at = "2026-07-31T12:00:00Z"
    study_run = _study_run()
    first = case_study.build_artifact(study_run, generated_at=generated_at)
    reversed_run = case_study.StudyRun(
        outputs=dict(reversed(list(study_run.outputs.items()))), calls=study_run.calls
    )
    second = case_study.build_artifact(reversed_run, generated_at=generated_at)

    assert case_study.canonical_json(first) == case_study.canonical_json(second)
    assert first["schema_version"] == 3
    assert first["executive_summary"] == {
        "tract_count": 3,
        "measure_count": 8,
        "estimate_count": 24,
        "years": ["2023"],
        "chd_unweighted_mean_pct": 7.0,
        "chd_median_pct": 7.0,
        "chd_minimum_pct": 4.0,
        "chd_maximum_pct": 10.0,
        "screening_candidate_count": 1,
        "strict_screening_candidate_count": 1,
        "pubmed_article_count": 1,
        "trial_records_returned": 1,
        "trial_records_total_match": 29,
    }
    assert first["findings"]["screening"]["candidates"][0]["census_tract"] == (
        "01001020300"
    )
    assert first["findings"]["screening"]["strict_candidate_census_tracts"] == [
        "01001020300"
    ]
    assert [
        row["candidate_count"]
        for row in first["findings"]["screening"]["sensitivity_by_threshold"]
    ] == [1, 1, 1, 1, 1]
    correlations = {
        row["measure_id"]: row["pearson_r"]
        for row in first["findings"]["exploratory_co_variation"][
            "correlations_with_chd"
        ]
    }
    assert correlations["BPHIGH"] == 1.0
    assert correlations["CHECKUP"] == -1.0
    assert first["tooluniverse_execution"]["call_count"] == 6
    assert first["tooluniverse_execution"]["calls"][1]["result_summary"] == {
        "estimate_count": 24,
        "measure_count": 8,
        "possibly_truncated": False,
        "tract_count": 3,
    }
    serialized = case_study.canonical_json(first)
    assert "Ask a doctor" not in serialized
    assert "blood thinning" in serialized


def test_professional_report_and_csvs_explain_the_full_workflow():
    """Render calls, decision rule, evidence candidates, and analyst exports."""
    artifact = case_study.build_artifact(
        _study_run(), generated_at="2026-07-31T12:00:00Z"
    )
    markdown = case_study.render_markdown(artifact)
    tract_csv = case_study.render_tract_csv(artifact)
    measure_csv = case_study.render_measure_csv(artifact)

    assert "Executive Brief" in markdown
    assert "Exactly How ToolUniverse Was Used" in markdown
    assert case_study.CDC_TOOL_NAME in markdown
    assert '"county_name": "Autauga"' in markdown
    assert "Follow-Up Screening Set" in markdown
    assert "Threshold Sensitivity" in markdown
    assert "does not rank neighborhoods" in markdown
    assert "PubMed Candidates" in markdown
    assert "35354074" in markdown
    assert "NCT04562532" in markdown
    assert "S\u00e3o cardiovascular journal" in markdown
    assert "Why The VSD Layer Matters" in markdown
    assert markdown.count("SHA-256") == 3
    assert tract_csv.count("\n") == 4
    assert "CHD_estimate_pct" in tract_csv
    assert measure_csv.count("\n") == 9
    assert "Current cigarette smoking among adults" in measure_csv


def test_study_rejects_truncation_and_incomplete_measure_grid():
    """Do not issue a county dossier from partial CDC retrievals."""
    truncated = _study_run()
    truncated.outputs[case_study.CDC_TOOL_NAME]["possibly_truncated"] = True
    with pytest.raises(ValueError, match="may be incomplete"):
        case_study.build_artifact(truncated, generated_at="2026-07-31T12:00:00Z")

    incomplete = _study_run()
    incomplete.outputs[case_study.CDC_TOOL_NAME]["estimates"].pop()
    with pytest.raises(ValueError, match="incomplete tract measure grids"):
        case_study.build_artifact(incomplete, generated_at="2026-07-31T12:00:00Z")


def test_checked_live_artifacts_are_schema_valid_and_in_sync():
    """Keep checked JSON, report, and CSV artifacts synchronized."""
    artifact_dir = MODULE_PATH.parent / "artifacts"
    artifact = json.loads((artifact_dir / "snapshot.json").read_text(encoding="utf-8"))
    markdown = (artifact_dir / "snapshot.md").read_text(encoding="utf-8")
    tract_csv = (artifact_dir / "tract_profiles.csv").read_text(encoding="utf-8")
    measure_csv = (artifact_dir / "measure_summary.csv").read_text(encoding="utf-8")

    assert artifact["schema_version"] == case_study.SCHEMA_VERSION
    assert artifact["case_study"]["id"] == case_study.CASE_STUDY_ID
    assert artifact["case_study"]["generated_at"].endswith("Z")
    assert artifact["tooluniverse_execution"]["loaded_tools"] == list(
        case_study.TOOL_NAMES
    )
    assert artifact["tooluniverse_execution"]["call_count"] == len(
        case_study.TOOL_CALLS
    )
    assert artifact["executive_summary"]["estimate_count"] == len(
        artifact["cdc_places_estimates"]
    )
    assert all(
        len(source["payload_sha256"]) == 64 for source in artifact["vsd_provenance"]
    )
    assert case_study.render_markdown(artifact) == markdown
    assert case_study.render_tract_csv(artifact) == tract_csv
    assert case_study.render_measure_csv(artifact) == measure_csv
