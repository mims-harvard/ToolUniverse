"""Posted outcome results must come back as results, not as one sentence.

arXiv 2609.26836 (*Silent Failures in Agent-Tool Interaction: An Audit of
ToolUniverse*) reports `extract_clinical_trial_outcomes` answering with
success and nothing in it. Measured live 2026-11-12, both of its branches
were broken and both reported success:

    extract_clinical_trial_outcomes {"nct_ids": ["NCT01874691"]}
      -> {"status": "success", "data": [{"NCT ID": "NCT01874691"}]}

    extract_clinical_trial_outcomes {"nct_ids": ["NCT04280705"]}
      -> {"status": "success",
          "data": ["Warning: Multiple classes found for outcome Time to
                    Recovery by Race in study NCT04280705."]}

NCT01874691 has posted no results; the bare id reads as "asked and answered,
nothing found", and the registry's own `hasResults` was never fetched.
NCT04280705 is ACTT-1, with 43 posted outcome measures and 438 measurement
rows: `classes` is the stratum list (one per timepoint), the handler assumed
there would never be more than one of them, and `return`ed that sentence from
inside the per-outcome loop, discarding every other measure of the study with
it.

The two shapes are asserted here against recorded upstream payloads, so the
guard holds without the network.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.ctg_tool import ClinicalTrialsDetailsTool

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "clinicaltrials_gov_tools.json"
)


def _config(name):
    for tool in json.loads(CONFIG.read_text()):
        if tool.get("name") == name:
            return tool
    raise AssertionError(f"{name} is not in {CONFIG}")


@pytest.fixture(scope="module")
def tool():
    return ClinicalTrialsDetailsTool(_config("extract_clinical_trial_outcomes"))


NO_RESULTS = {
    "protocolSection": {"identificationModule": {"nctId": "NCT01874691"}},
    "hasResults": False,
}

# The shape the handler used to refuse: several classes, each a timepoint,
# each with its own shrinking denominator.
MULTI_CLASS = {
    "protocolSection": {"identificationModule": {"nctId": "NCT04280705"}},
    "hasResults": True,
    "resultsSection": {
        "outcomeMeasuresModule": {
            "outcomeMeasures": [
                {
                    "type": "PRIMARY",
                    "title": "Change From Baseline in Alanine Transaminase",
                    "reportingStatus": "POSTED",
                    "paramType": "MEAN",
                    "dispersionType": "Standard Deviation",
                    "unitOfMeasure": "Units/Liter (U/L)",
                    "groups": [
                        {"id": "OG000", "title": "Placebo"},
                        {"id": "OG001", "title": "Remdesivir"},
                    ],
                    "denoms": [
                        {
                            "units": "Participants",
                            "counts": [
                                {"groupId": "OG000", "value": "463"},
                                {"groupId": "OG001", "value": "465"},
                            ],
                        }
                    ],
                    "classes": [
                        {
                            "title": "Day 3",
                            "denoms": [
                                {
                                    "units": "Participants",
                                    "counts": [
                                        {"groupId": "OG000", "value": "463"},
                                        {"groupId": "OG001", "value": "465"},
                                    ],
                                }
                            ],
                            "categories": [
                                {
                                    "measurements": [
                                        {
                                            "groupId": "OG000",
                                            "value": "14.3",
                                            "spread": "88",
                                        },
                                        {
                                            "groupId": "OG001",
                                            "value": "2.9",
                                            "spread": "31.5",
                                        },
                                    ]
                                }
                            ],
                        },
                        {
                            "title": "Day 5",
                            "categories": [
                                {
                                    "measurements": [
                                        {
                                            "groupId": "OG000",
                                            "value": "23.1",
                                            "spread": "70.6",
                                        },
                                        {
                                            "groupId": "OG001",
                                            "value": "4.4",
                                            "spread": "40.1",
                                        },
                                    ]
                                }
                            ],
                        },
                    ],
                    "analyses": [
                        {
                            "groupIds": ["OG000", "OG001"],
                            "pValue": "<0.001",
                            "statisticalMethod": "Log Rank",
                            "paramType": "Cox Proportional Hazard",
                            "paramValue": "1.29",
                            "ciPctValue": "95",
                            "ciLowerLimit": "1.12",
                            "ciUpperLimit": "1.49",
                        }
                    ],
                }
            ]
        }
    },
}


def test_a_trial_with_no_posted_results_says_so(tool):
    out = tool._extract_outcomes_from_output(NO_RESULTS, "primary")
    assert out["has_results"] is False
    assert out["outcomes"] == []
    assert "no posted results" in out["note"]


def test_every_stratum_of_a_multi_class_measure_is_returned(tool):
    out = tool._extract_outcomes_from_output(MULTI_CLASS, "primary")
    assert isinstance(out, dict), "the handler returned prose in place of the study"
    assert out["has_results"] is True
    assert len(out["outcomes"]) == 1
    rows = out["outcomes"][0]["measurements"]
    assert len(rows) == 4, "two timepoints x two arms"
    assert {r["class"] for r in rows} == {"Day 3", "Day 5"}
    # The arm is named on the row, not only in `groups`.
    assert {r["group_title"] for r in rows} == {"Placebo", "Remdesivir"}
    day3 = [r for r in rows if r["class"] == "Day 3"]
    assert {r["value"] for r in day3} == {"14.3", "2.9"}
    assert all("spread" in r for r in day3)


def test_the_confidence_interval_of_an_analysis_survives(tool):
    out = tool._extract_outcomes_from_output(MULTI_CLASS, "primary")
    analysis = out["outcomes"][0]["analyses"][0]
    # ciPctValue/ciLowerLimit/ciUpperLimit sit beside the p-value on every
    # analysis upstream and the old keep-list never read any of the three.
    assert analysis["ci_lower_limit"] == "1.12"
    assert analysis["ci_upper_limit"] == "1.49"
    assert analysis["ci_pct_value"] == "95"
    assert analysis["p_value"] == "<0.001"
    assert analysis["param_value"] == "1.29"


def test_no_branch_returns_a_warning_string(tool):
    for study in (NO_RESULTS, MULTI_CLASS):
        for measure in ("primary", "all", "alanine"):
            out = tool._extract_outcomes_from_output(study, measure)
            assert not isinstance(out, str), out


def test_the_outcome_request_asks_for_has_results():
    config = _config("extract_clinical_trial_outcomes")
    # The field list is what reaches the API; without HasResults on it the
    # handler cannot tell "no results posted" from "results did not arrive".
    source = (
        Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "ctg_tool.py"
    ).read_text()
    block = source.split('query_type = "outcome"', 1)[1].split("elif", 1)[0]
    assert '"HasResults"' in block
    assert config["return_schema"]["oneOf"][0]["items"]["properties"]["has_results"]


def test_all_cause_deaths_are_not_deleted_from_adverse_events():
    ae = ClinicalTrialsDetailsTool(_config("extract_clinical_trial_adverse_events"))
    study = {
        "protocolSection": {"identificationModule": {"nctId": "NCT04280705"}},
        "hasResults": True,
        "resultsSection": {
            "adverseEventsModule": {
                "frequencyThreshold": "5",
                "eventGroups": [
                    {
                        "id": "EG000",
                        "title": "Placebo",
                        "deathsNumAffected": 77,
                        "deathsNumAtRisk": 521,
                        "seriousNumAffected": 131,
                        "seriousNumAtRisk": 521,
                    }
                ],
                "seriousEvents": [],
            }
        },
    }
    out = ae._extract_safety_from_output(study, [], "serious")
    group = out["groups"][0]
    assert group["deathsNumAffected"] == 77
    assert group["deathsNumAtRisk"] == 521


def test_adverse_events_report_has_results():
    ae = ClinicalTrialsDetailsTool(_config("extract_clinical_trial_adverse_events"))
    out = ae._extract_safety_from_output(NO_RESULTS, [], "serious")
    assert out["has_results"] is False
    assert "no posted results" in out["note"]
