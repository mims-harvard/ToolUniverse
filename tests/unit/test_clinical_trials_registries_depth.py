"""Depth tests for clinical-trials-registries coverage tools.

Covers three new/enriched tools that reuse existing tool classes (no new
registration):

* ``CTIS_search_trials_filtered`` (CTISSearchTrialsTool) — structured search of
  the EU CTIS register. Assembles a ``searchCriteria`` body from registry
  filters (medical condition, status, phase, age group, gender, has-results,
  sponsor, country/MSC) rather than only free text.
* ``ISRCTN_search_trials_fielded`` (ISRCTNSearchTool) — forwards an ISRCTN
  field-scoped boolean query DSL (``condition:diabetes``,
  ``gender:Female AND condition:asthma``) and returns detailed records.
* ``ISRCTN_get_trial`` (ISRCTNGetTrialTool) — enriched parser that now extracts
  interventions, primary/secondary outcomes, inclusion/exclusion eligibility,
  sponsors, funders, recruitment countries and dates, drug names, enrolment,
  IPD-sharing statement, and the plain-English summary.

All HTTP is mocked so the suite is offline/deterministic; live verification is
done separately via the CLI.
"""

import json
import os

import pytest
import requests

from tooluniverse.ctis_tool import CTISSearchTrialsTool
from tooluniverse.isrctn_tool import ISRCTNGetTrialTool, ISRCTNSearchTool

pytestmark = pytest.mark.unit

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_tool_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    matches = [c for c in configs if c.get("name") == tool_name]
    assert matches, f"{tool_name} not found in {filename}"
    return matches[0]


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("no JSON body")
        return self._json_data

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(response=self)


# --- Sample CTIS search payload (matches the real /search envelope) ---
_CTIS_PAYLOAD = {
    "pagination": {
        "totalRecords": 30,
        "currentPage": 1,
        "totalPages": 10,
    },
    "data": [
        {
            "ctNumber": "2024-516282-37-00",
            "ctStatus": 3,
            "ctTitle": "Preservation of Fertility (PRESAGE)",
            "conditions": "Breast cancer",
            "therapeuticAreas": ["Diseases [C] - Neoplasms [C04]"],
            "trialPhase": "Therapeutic exploratory (Phase II)",
            "sponsor": "Institut De Cancerologie De L Ouest",
            "sponsorType": "Hospital/Clinic/Other health care facility",
            "trialCountries": ["France:3"],
            "ageGroup": "18-64 years",
            "gender": "Female",
            "trialRegion": 1,
            "totalNumberEnrolled": "100",
            "resultsFirstReceived": "No",
            "startDateEU": "18/02/2025",
            "lastUpdated": "09/08/2024",
        }
    ],
}


# --- Sample ISRCTN XML (full <trial> with the enriched detail tags) ---
_ISRCTN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<allTrials xmlns="http://www.67bricks.com/isrctn" totalCount="1106">
  <fullTrial>
    <trial>
      <isrctn>12336055</isrctn>
      <trialDescription>
        <title>CGM in type 2 diabetes</title>
        <scientificTitle>A study of CGM systems</scientificTitle>
        <acronym>CGM2D</acronym>
        <studyHypothesis>CGM improves control.</studyHypothesis>
        <plainEnglishSummary>People with type 2 diabetes may benefit.</plainEnglishSummary>
        <primaryOutcomes>
          <outcomeMeasure>
            <variable>HbA1c change</variable>
            <method>blood test</method>
            <timepoints>6 months</timepoints>
          </outcomeMeasure>
        </primaryOutcomes>
        <secondaryOutcomes>
          <outcomeMeasure>
            <variable>Quality of life</variable>
            <method>questionnaire</method>
            <timepoints>12 months</timepoints>
          </outcomeMeasure>
        </secondaryOutcomes>
      </trialDescription>
      <externalRefs>
        <doi>10.1186/ISRCTN12336055</doi>
        <eudraCTNumber>2023-000001-01</eudraCTNumber>
        <clinicalTrialsGovNumber>NCT00000001</clinicalTrialsGovNumber>
      </externalRefs>
      <trialDesign>
        <primaryStudyDesign>Interventional</primaryStudyDesign>
        <secondaryStudyDesign>Randomised controlled trial</secondaryStudyDesign>
        <overallEndDate>2027-01-31T00:00:00.000Z</overallEndDate>
      </trialDesign>
      <participants>
        <recruitmentCountries>
          <country>United Kingdom</country>
          <country>Ireland</country>
        </recruitmentCountries>
        <healthyVolunteersAllowed>false</healthyVolunteersAllowed>
        <inclusion>Age at least 18 years.</inclusion>
        <exclusion>Type 1 diabetes.</exclusion>
        <ageRange>Mixed</ageRange>
        <lowerAgeLimit>18 Years</lowerAgeLimit>
        <upperAgeLimit>100 Years</upperAgeLimit>
        <gender>All</gender>
        <targetEnrolment>232</targetEnrolment>
        <totalFinalEnrolment>0</totalFinalEnrolment>
        <recruitmentStart>2026-03-12T00:00:00.000Z</recruitmentStart>
        <recruitmentEnd>2027-01-31T00:00:00.000Z</recruitmentEnd>
      </participants>
      <conditions>
        <condition>
          <description>Type 2 Diabetes Mellitus</description>
          <diseaseClass1>Nutritional, Metabolic, Endocrine</diseaseClass1>
        </condition>
      </conditions>
      <interventions>
        <intervention>
          <interventionType>Device</interventionType>
          <phase>Phase IV</phase>
          <drugNames>Dexcom ONE + CGM System</drugNames>
          <description>CGM device cohort.</description>
        </intervention>
      </interventions>
      <results>
        <dataPolicies>
          <dataPolicy>Not expected to be made available</dataPolicy>
        </dataPolicies>
      </results>
      <miscellaneous>
        <ipdSharingPlan>No</ipdSharingPlan>
      </miscellaneous>
    </trial>
    <contact>
      <forename>Samuel</forename>
      <surname>Seidu</surname>
    </contact>
    <sponsor>
      <organisation>Dexcom (United States)</organisation>
      <sponsorType></sponsorType>
      <commercialStatus>Commercial</commercialStatus>
      <rorId>https://ror.org/03ra42c27</rorId>
    </sponsor>
    <funder>
      <name>Dexcom</name>
      <fundRef>http://dx.doi.org/10.13039/100015769</fundRef>
    </funder>
  </fullTrial>
</allTrials>
"""

_ISRCTN_EMPTY_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<allTrials xmlns="http://www.67bricks.com/isrctn" totalCount="0"/>'
)


# ===================== CTIS filtered search =====================


def test_ctis_filtered_builds_criteria_and_parses(monkeypatch):
    """Structured filters compile into searchCriteria and results parse."""
    cfg = _load_tool_config("ctis_tools.json", "CTIS_search_trials_filtered")
    tool = CTISSearchTrialsTool(cfg)

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["body"] = json
        return _FakeResponse(json_data=_CTIS_PAYLOAD)

    monkeypatch.setattr(requests, "post", fake_post)

    out = tool.run(
        {
            "medical_condition": "breast cancer",
            "status": [3],
            "trial_phase_code": "3",
            "limit": 3,
        }
    )

    assert out["status"] == "success"
    # The structured filters must be assembled into searchCriteria.
    criteria = captured["body"]["searchCriteria"]
    assert criteria["medicalCondition"] == "breast cancer"
    assert criteria["status"] == [3]  # status codes coerced to int
    assert criteria["trialPhaseCode"] == ["3"]  # scalar wrapped into a list
    assert captured["body"]["pagination"]["size"] == 3

    assert out["metadata"]["total_records"] == 30
    assert out["metadata"]["search_criteria"] == criteria
    record = out["data"][0]
    assert record["ct_number"] == "2024-516282-37-00"
    assert record["status"] == 3
    assert record["gender"] == "Female"
    assert record["results_first_received"] == "No"


def test_ctis_filtered_country_aliases_to_msc(monkeypatch):
    """The country argument is an alias for the CTIS msc filter."""
    cfg = _load_tool_config("ctis_tools.json", "CTIS_search_trials_filtered")
    tool = CTISSearchTrialsTool(cfg)
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["body"] = json
        return _FakeResponse(json_data=_CTIS_PAYLOAD)

    monkeypatch.setattr(requests, "post", fake_post)
    tool.run({"query": "cancer", "country": "DE"})
    criteria = captured["body"]["searchCriteria"]
    assert criteria["containAll"] == "cancer"
    assert criteria["msc"] == ["DE"]


def test_ctis_filtered_requires_a_filter():
    """Calling with no filters returns a status=error envelope."""
    cfg = _load_tool_config("ctis_tools.json", "CTIS_search_trials_filtered")
    tool = CTISSearchTrialsTool(cfg)
    out = tool.run({})
    assert out["status"] == "error"
    assert "filter" in out["error"].lower()


def test_ctis_filtered_network_error_returns_error(monkeypatch):
    """A connection failure is returned as a status=error envelope, not raised."""
    cfg = _load_tool_config("ctis_tools.json", "CTIS_search_trials_filtered")
    tool = CTISSearchTrialsTool(cfg)

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(requests, "post", boom)
    out = tool.run({"medical_condition": "breast cancer"})
    assert out["status"] == "error"
    assert "CTIS request failed" in out["error"]


# ===================== ISRCTN fielded search =====================


def test_isrctn_fielded_forwards_raw_dsl(monkeypatch):
    """A raw field-scoped DSL query passes through verbatim with detailed records."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_search_trials_fielded")
    tool = ISRCTNSearchTool(cfg)
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return _FakeResponse(text=_ISRCTN_XML)

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run({"q": "gender:Female AND condition:asthma", "limit": 2})

    assert out["status"] == "success"
    # The field-scoped DSL must pass through verbatim.
    assert captured["params"]["q"] == "gender:Female AND condition:asthma"
    assert out["metadata"]["total_available"] == "1106"
    # Fielded results are detailed records.
    assert out["data"][0]["interventions"][0]["drug_names"] == (
        "Dexcom ONE + CGM System"
    )


def test_isrctn_fielded_compiles_field_helpers(monkeypatch):
    """Field helpers are quoted and AND-joined into a DSL query."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_search_trials_fielded")
    tool = ISRCTNSearchTool(cfg)
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return _FakeResponse(text=_ISRCTN_XML)

    monkeypatch.setattr(requests, "get", fake_get)
    tool.run({"phase": "Phase III", "condition": "diabetes"})
    # Multi-word values are quoted; helpers are AND-joined in helper order.
    assert captured["params"]["q"] == 'condition:diabetes AND phase:"Phase III"'


def test_isrctn_fielded_requires_query():
    """Calling with no query or helpers returns a status=error envelope."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_search_trials_fielded")
    tool = ISRCTNSearchTool(cfg)
    out = tool.run({})
    assert out["status"] == "error"
    assert "field-scoped" in out["error"]


def test_isrctn_fielded_network_error(monkeypatch):
    """A timeout is returned as a status=error envelope, not raised."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_search_trials_fielded")
    tool = ISRCTNSearchTool(cfg)

    def boom(*args, **kwargs):
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(requests, "get", boom)
    out = tool.run({"q": "condition:diabetes"})
    assert out["status"] == "error"
    assert "timed out" in out["error"]


# ===================== ISRCTN enriched get_trial =====================


def test_isrctn_get_trial_enriched_fields(monkeypatch):
    """The enriched parser extracts the full detail field set."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_get_trial")
    tool = ISRCTNGetTrialTool(cfg)

    def fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(text=_ISRCTN_XML)

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run({"isrctn_id": "ISRCTN12336055"})

    assert out["status"] == "success"
    data = out["data"]
    assert data["isrctn_id"] == "ISRCTN12336055"

    # Interventions + drug names.
    assert data["interventions"][0]["intervention_type"] == "Device"
    assert data["drug_names"] == ["Dexcom ONE + CGM System"]
    assert data["phase"] == "Phase IV"

    # Outcomes parsed from trialDescription/<group>/outcomeMeasure.
    assert data["primary_outcomes"][0]["measure"] == "HbA1c change"
    assert data["secondary_outcomes"][0]["measure"] == "Quality of life"

    # Eligibility.
    assert data["eligibility"]["inclusion"] == "Age at least 18 years."
    assert data["eligibility"]["exclusion"] == "Type 1 diabetes."
    assert data["eligibility"]["gender"] == "All"

    # Recruitment + enrolment.
    assert data["recruitment_countries"] == ["United Kingdom", "Ireland"]
    assert data["recruitment_start"].startswith("2026-03-12")
    assert data["target_enrolment"] == "232"
    assert data["total_final_enrolment"] == "0"

    # Sponsors / funders live at the fullTrial level.
    assert data["sponsors"][0]["organisation"] == "Dexcom (United States)"
    assert data["funders"][0]["name"] == "Dexcom"
    assert data["contacts"][0]["name"] == "Samuel Seidu"

    # IPD + summary + conditions.
    assert data["ipd_sharing_statement"] == "No"
    assert data["plain_english_summary"].startswith("People with type 2 diabetes")
    assert data["conditions"] == ["Type 2 Diabetes Mellitus"]


def test_isrctn_get_trial_not_found(monkeypatch):
    """An empty result set returns success with an empty data dict + note."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_get_trial")
    tool = ISRCTNGetTrialTool(cfg)

    def fake_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(text=_ISRCTN_EMPTY_XML)

    monkeypatch.setattr(requests, "get", fake_get)
    out = tool.run({"isrctn_id": "ISRCTN99999999"})
    assert out["status"] == "success"
    assert out["data"] == {}
    assert "No ISRCTN trial" in out["metadata"]["note"]


def test_isrctn_get_trial_network_error(monkeypatch):
    """A connection failure is returned as a status=error envelope, not raised."""
    cfg = _load_tool_config("isrctn_tools.json", "ISRCTN_get_trial")
    tool = ISRCTNGetTrialTool(cfg)

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    out = tool.run({"isrctn_id": "ISRCTN12336055"})
    assert out["status"] == "error"
    assert "ISRCTN request failed" in out["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
