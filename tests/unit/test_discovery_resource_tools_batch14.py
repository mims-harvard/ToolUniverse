"""Unit tests for the NCBI Clinical Tables tool (RxTerms, conditions, disease_names).

Network is mocked so these run in CI. They cover the deterministic parsing logic
the live API cannot exercise repeatably:
  - df + ef hash merge (RxTerms strengths/forms + RXCUIS)
  - conditions ICD crosswalk alignment
  - disease_names default-display column (df omitted) mapping to primary_name
  - empty terms input validation
  - malformed response handling
"""

from unittest.mock import MagicMock, patch

from tooluniverse.clinical_tables_tool import ClinicalTablesTool


def _tool(name):
    return ClinicalTablesTool(
        {
            "name": name,
            "type": "ClinicalTablesTool",
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def test_rxterms_merges_display_and_extra_fields():
    body = [
        2,
        ["metFORMIN (Oral Pill)", "metFORMIN XR (Oral Pill)"],
        {
            "STRENGTHS_AND_FORMS": [["500 mg Tab"], ["500 mg 24 HR XR Tab"]],
            "RXCUIS": [["861007"], ["860975"]],
        },
        [
            ["metFORMIN (Oral Pill)", "500 mg Tab"],
            ["metFORMIN XR (Oral Pill)", "500 mg 24 HR XR Tab"],
        ],
    ]
    with patch("tooluniverse.clinical_tables_tool.requests.get", return_value=_resp(body)):
        out = _tool("RxTerms_search_drugs").run({"terms": "metformin"})
    assert out["count"] == 2
    first = out["results"][0]
    assert first["DISPLAY_NAME"] == "metFORMIN (Oral Pill)"
    assert first["RXCUIS"] == ["861007"]
    assert first["STRENGTHS_AND_FORMS"] == ["500 mg Tab"]


def test_conditions_aligns_icd_crosswalk():
    body = [
        1,
        ["2143"],
        {"icd10cm_codes": ["E11.9"], "term_icd9_code": ["250.00"]},
        [["Diabetes mellitus", "Diabetes mellitus (DM)"]],
    ]
    with patch("tooluniverse.clinical_tables_tool.requests.get", return_value=_resp(body)):
        out = _tool("HealthConditions_search").run({"terms": "diabetes"})
    row = out["results"][0]
    assert row["primary_name"] == "Diabetes mellitus"
    assert row["consumer_name"] == "Diabetes mellitus (DM)"
    assert row["icd10cm_codes"] == "E11.9"
    assert row["term_icd9_code"] == "250.00"


def test_disease_names_uses_default_display_column():
    # disease_names returns its name only via the default column (df omitted).
    body = [2, ["C0010674", "CN381012"], None, [["Cystic fibrosis"], ["CF-related diabetes"]]]
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured.update(params or {})
        return _resp(body)

    with patch("tooluniverse.clinical_tables_tool.requests.get", side_effect=fake_get):
        out = _tool("DiseaseNames_search").run({"terms": "cystic fibrosis"})
    assert "df" not in captured  # df must be omitted for disease_names
    assert out["results"][0]["code"] == "C0010674"
    assert out["results"][0]["primary_name"] == "Cystic fibrosis"


def test_empty_terms_is_validation_error():
    out = _tool("RxTerms_search_drugs").run({"terms": "   "})
    assert out["status"] == "error"
    assert "terms" in out["error"]


def test_malformed_response_is_error():
    with patch(
        "tooluniverse.clinical_tables_tool.requests.get",
        return_value=_resp({"unexpected": "shape"}),
    ):
        out = _tool("HealthConditions_search").run({"terms": "asthma"})
    assert out["status"] == "error"


def test_unknown_tool_name_is_error():
    out = _tool("ClinicalTables_bogus").run({"terms": "x"})
    assert out["status"] == "error"
    assert "Unknown operation" in out["error"]
