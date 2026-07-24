"""Unit tests for ClinVarSubmittedRecordsTool (mocked XML).

Run with:
    python3 -m pytest tests/unit/test_clinvar_submitted.py -o addopts="" -q
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_submitted_tool import (
    ClinVarSubmittedRecordsTool,
    _normalize_variant_id,
)

pytestmark = pytest.mark.unit


TOOL_CONFIG = {
    "type": "ClinVarSubmittedRecordsTool",
    "name": "ClinVar_get_submitted_records",
    "description": "test",
    "parameter": {
        "type": "object",
        "properties": {"variant_id": {"type": "string"}},
        "required": ["variant_id"],
    },
}


# --- Mock XML payloads -------------------------------------------------------

XML_TWO_SCVS = b"""<?xml version="1.0" encoding="UTF-8" ?>
<ClinVarResult-Set>
  <VariationArchive VariationID="13961" VariationName="NM_004333.6(BRAF):c.1799T&gt;A (p.Val600Glu)"
      Accession="VCV000013961" RecordType="classified"
      NumberOfSubmissions="2" NumberOfSubmitters="2" DateLastUpdated="2026-06-06">
    <ClassifiedRecord>
      <Classifications>
        <GermlineClassification>
          <ReviewStatus>criteria provided, conflicting classifications</ReviewStatus>
          <Description>Conflicting classifications of pathogenicity</Description>
        </GermlineClassification>
      </Classifications>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <ClinVarAccession Accession="SCV001450230" Version="1" Type="SCV"
              SubmitterName="Karolinska University Hospital" />
          <Classification DateLastEvaluated="2014-07-11">
            <ReviewStatus>criteria provided, single submitter</ReviewStatus>
            <GermlineClassification>Pathogenic</GermlineClassification>
          </Classification>
          <TraitSet Type="Disease">
            <Trait Type="Disease">
              <Name><ElementValue Type="Preferred">not provided</ElementValue></Name>
            </Trait>
          </TraitSet>
        </ClinicalAssertion>
        <ClinicalAssertion>
          <ClinVarAccession Accession="SCV001132084" Version="3" Type="SCV"
              SubmitterName="Memorial Sloan Kettering Cancer Center" />
          <Classification DateLastEvaluated="2019-08-31">
            <ReviewStatus>no assertion criteria provided</ReviewStatus>
            <GermlineClassification>Likely pathogenic</GermlineClassification>
          </Classification>
          <TraitSet Type="Disease">
            <Trait Type="Disease">
              <Name><ElementValue Type="Preferred">Multiple myeloma</ElementValue></Name>
            </Trait>
          </TraitSet>
        </ClinicalAssertion>
        <ClinicalAssertion>
          <ClinVarAccession Accession="SCV004565360" Version="1" Type="SCV"
              SubmitterName="Some Somatic Lab" />
          <Classification>
            <ReviewStatus>no assertion criteria provided</ReviewStatus>
            <SomaticClinicalImpact ClinicalImpactAssertionType="therapeutic"
                DrugForTherapeuticAssertion="Dabrafenib;Trametinib">Tier I - Strong</SomaticClinicalImpact>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>
"""

# Record with no ClinicalAssertionList at all.
XML_NO_ASSERTIONS = b"""<?xml version="1.0" encoding="UTF-8" ?>
<ClinVarResult-Set>
  <VariationArchive VariationID="99999" VariationName="some variant"
      Accession="VCV000099999" RecordType="classified" NumberOfSubmissions="0">
    <ClassifiedRecord>
      <Classifications>
        <GermlineClassification>
          <ReviewStatus>no classification provided</ReviewStatus>
          <Description>not provided</Description>
        </GermlineClassification>
      </Classifications>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>
"""

# efetch returns an empty set when the id does not resolve.
XML_EMPTY = b"""<?xml version="1.0" encoding="UTF-8" ?>
<ClinVarResult-Set><set/></ClinVarResult-Set>
"""


class _FakeResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def _make_tool():
    return ClinVarSubmittedRecordsTool(TOOL_CONFIG)


# --- _normalize_variant_id ---------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("VCV000013961", "VCV000013961"),
        ("13961", "VCV000013961"),
        (13961, "VCV000013961"),
        ("vcv13961", "VCV000013961"),
        ("VCV13961", "VCV000013961"),
        ("  13961  ", "VCV000013961"),
    ],
)
def test_normalize_variant_id_valid(raw, expected):
    assert _normalize_variant_id(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None, "not-an-id", "VCVabc", "rs113488022"])
def test_normalize_variant_id_invalid(raw):
    assert _normalize_variant_id(raw) is None


# --- run(): parsing multiple SCVs -------------------------------------------


def test_run_parses_multiple_scvs():
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(XML_TWO_SCVS),
    ):
        result = tool.run({"variant_id": "VCV000013961"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["variation_id"] == "13961"
    assert data["vcv_accession"] == "VCV000013961"
    assert data["aggregate_classification"] == (
        "Conflicting classifications of pathogenicity"
    )
    assert data["total_submissions"] == 3

    subs = data["submissions"]
    assert subs[0]["scv_accession"] == "SCV001450230.1"
    assert subs[0]["classification"] == "Pathogenic"
    assert subs[0]["classification_type"] == "germline"
    assert subs[0]["review_status"] == "criteria provided, single submitter"
    assert subs[0]["submitter"] == "Karolinska University Hospital"
    assert subs[0]["condition"] == "not provided"
    assert subs[0]["last_evaluated"] == "2014-07-11"

    assert subs[1]["scv_accession"] == "SCV001132084.3"
    assert subs[1]["classification"] == "Likely pathogenic"
    assert subs[1]["classification_type"] == "germline"
    assert subs[1]["condition"] == "Multiple myeloma"

    # SCV-level somatic uses the <SomaticClinicalImpact> tag, not
    # <SomaticClinicalImpactClassification> (which is the aggregate-level tag).
    assert subs[2]["scv_accession"] == "SCV004565360.1"
    assert subs[2]["classification"] == "Tier I - Strong"
    assert subs[2]["classification_type"] == "somatic_clinical_impact"
    assert subs[2]["condition"] is None

    assert result["metadata"]["number_of_submissions_reported"] == "2"
    assert result["metadata"]["queried_id"] == "VCV000013961"


def test_run_normalizes_bare_numeric_id():
    """A bare numeric id must be normalized to VCV%09d before the request."""
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(XML_TWO_SCVS),
    ) as mock_get:
        result = tool.run({"variant_id": "13961"})

    assert result["status"] == "success"
    # Verify the normalized id was passed in the request params.
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["id"] == "VCV000013961"


def test_run_handles_no_assertions():
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(XML_NO_ASSERTIONS),
    ):
        result = tool.run({"variant_id": "99999"})

    assert result["status"] == "success"
    assert result["data"]["total_submissions"] == 0
    assert result["data"]["submissions"] == []
    assert result["data"]["aggregate_classification"] == "not provided"


def test_run_empty_result_set_is_error():
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(XML_EMPTY),
    ):
        result = tool.run({"variant_id": "VCV000000001"})

    assert result["status"] == "error"
    assert "VariationArchive" in result["error"]


# --- run(): error paths ------------------------------------------------------


def test_run_missing_variant_id():
    tool = _make_tool()
    result = tool.run({})
    assert result["status"] == "error"
    assert "variant_id" in result["error"]


def test_run_unparseable_variant_id():
    tool = _make_tool()
    result = tool.run({"variant_id": "not-a-valid-id"})
    assert result["status"] == "error"
    assert "Could not interpret" in result["error"]


def test_run_http_error():
    """A non-200 HTTP status returns an error envelope, not an exception."""
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(b"", status_code=500),
    ):
        result = tool.run({"variant_id": "13961"})
    assert result["status"] == "error"
    assert "500" in result["error"]


def test_run_request_exception_does_not_raise():
    """A network exception is caught and returned as an error envelope."""
    import requests

    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        result = tool.run({"variant_id": "13961"})
    assert result["status"] == "error"
    assert "failed" in result["error"].lower()


def test_run_bad_xml_does_not_raise():
    """Malformed XML is caught and returned as an error envelope."""
    tool = _make_tool()
    with patch(
        "tooluniverse.clinvar_submitted_tool.requests.get",
        return_value=_FakeResponse(b"<not><valid xml"),
    ):
        result = tool.run({"variant_id": "13961"})
    assert result["status"] == "error"
    assert "parse" in result["error"].lower()
