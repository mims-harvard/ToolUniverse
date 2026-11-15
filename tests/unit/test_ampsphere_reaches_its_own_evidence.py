"""AMPSphere's co-prediction scores, its samples, and a page it called a total.

arXiv 2609.26836 reports two AMPSphere gaps. Measured live 2026-11-12 and
2026-11-13 against the API's own openapi.json:

- `/v1/amps/{accession}/coprediction` is a real endpoint that no tool
  reached. It is how each of seven independent predictors scored the peptide,
  and they disagree: AMP10.000_000 reads APIN 1.0, AI4AMP 0.989,
  AMPScanner2 0.988, AMPlify 0.979, ampir 0.928, Macrel 0.604, amPEPpy 0.601.
  Whether a peptide IS antimicrobial is the question the resource exists to
  answer, and the spread of the answers was unreachable.

- `/v1/search/mmseqs` and `/v1/search/hmmer`, the homology endpoints the
  sequence-match tool's description pointed at as the alternative to its own
  exact match, both answer HTTP 500 -- for the API's own default query and
  for others. That claim is an upstream outage, not a wrapper gap, and the
  description no longer sends anyone there.

And one found beside them: `AMPSphere_get_amp` reported
`metadata.gene_count: 5` for a peptide with 15,523 gene/sample rows. The
record embeds page zero of a paged connection and the handler took the length
of that page as the count, with the page info sitting in the same response.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
RECORD_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "ampsphere_record_tool.py"
).read_text()


def _tools():
    out = {}
    for name in ("ampsphere_tools.json", "ampsphere_record_tools.json"):
        for tool in json.loads((DATA / name).read_text()):
            out[tool["name"]] = tool
    return out


def test_the_coprediction_endpoint_has_a_tool():
    tools = _tools()
    assert "AMPSphere_get_amp_coprediction" in tools
    config = tools["AMPSphere_get_amp_coprediction"]
    assert "accession" in config["parameter"]["properties"]
    success = config["return_schema"]["oneOf"][0]["properties"]
    assert "predictions" in success
    # The denominator travels with the count, or the count is a number
    # without a question attached to it.
    assert "predictors_total" in success
    assert "predictors_agreeing" in success


def test_the_coprediction_tool_warns_against_averaging():
    from tooluniverse.ampsphere_tool import AMPSphereCopredictionTool

    config = _tools()["AMPSphere_get_amp_coprediction"]
    tool = AMPSphereCopredictionTool(config)
    rows = [
        {"predictor": "APIN", "value": 1.0},
        {"predictor": "Macrel", "value": 0.604},
        {"predictor": "amPEPpy", "value": 0.4},
    ]
    import tooluniverse.ampsphere_tool as module

    original = module._get
    module._get = lambda path, params=None: (rows, None)
    try:
        result = tool.run({"accession": "AMP10.000_000"})
    finally:
        module._get = original

    assert result["status"] == "success"
    data = result["data"]
    assert data["predictors_total"] == 3
    assert data["predictors_agreeing"] == 2
    assert data["score_range"] == [0.4, 1.0]
    # Seven models on seven scales do not average into a probability.
    assert "not average" in result["metadata"]["note"].lower()


def test_the_sample_metadata_endpoint_has_a_tool_and_reports_the_total():
    from tooluniverse.ampsphere_tool import AMPSphereAmpMetadataTool

    config = _tools()["AMPSphere_get_amp_metadata"]
    tool = AMPSphereAmpMetadataTool(config)
    payload = {
        "info": {
            "currentPage": 0,
            "pageSize": 3,
            "totalPage": 5175,
            "totalItem": 15523,
        },
        "data": [{"AMP": "AMP10.000_000"}] * 3,
    }
    import tooluniverse.ampsphere_tool as module

    original = module._get
    module._get = lambda path, params=None: (payload, None)
    try:
        result = tool.run({"accession": "AMP10.000_000", "page_size": 3})
    finally:
        module._get = original

    data = result["data"]
    assert data["returned"] == 3
    assert data["total_samples"] == 15523
    assert data["has_more"] is True
    assert data["next_page"] == 1


def test_get_amp_does_not_report_its_page_as_the_gene_count():
    from tooluniverse.ampsphere_record_tool import AMPSphereGetAmpTool

    config = _tools()["AMPSphere_get_amp"]
    tool = AMPSphereGetAmpTool(config)
    payload = {
        "accession": "AMP10.000_000",
        "family": "SPHERE-III.001_493",
        "length": 27,
        "metadata": {
            "info": {
                "currentPage": 0,
                "pageSize": 5,
                "totalPage": 3105,
                "totalItem": 15523,
            },
            "data": [{"AMP": "AMP10.000_000"}] * 5,
        },
    }
    import tooluniverse.ampsphere_record_tool as module

    original = module._request
    module._request = lambda url, params=None: (payload, None)
    try:
        result = tool.run({"accession": "AMP10.000_000"})
    finally:
        module._request = original

    meta = result["metadata"]
    assert meta["gene_count"] == 15523, "the page length was reported as the total"
    assert meta["gene_rows_returned"] == 5
    assert meta["truncated"] is True
    assert "AMPSphere_get_amp_metadata" in meta["note"]


def test_the_homology_endpoints_are_not_recommended_as_a_fallback():
    # Both answer HTTP 500, measured for the API's own default query.
    assert "/search/mmseqs or /search/hmmer endpoints" not in RECORD_SOURCE
    assert "HTTP 500 for every query" in RECORD_SOURCE
