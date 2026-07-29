"""Regressions found while validating hosted BYOK scientific tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import validate

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.http_utils import redact_url_secrets
from tooluniverse.openalex_tool import OpenAlexRESTTool
from tooluniverse.pubmed_tool import PubMedRESTTool


DATA_DIR = Path(__file__).parents[2] / "src" / "tooluniverse" / "data"


def _tool_config(filename: str, name: str) -> dict:
    configs = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    return next(config for config in configs if config["name"] == name)


@pytest.mark.unit
def test_census_builds_dataset_path_and_injects_key(monkeypatch):
    """The saved CENSUS_API_KEY must actually reach the upstream query."""
    tool = BaseRESTTool(_tool_config("uscensus_tools.json", "USCensus_get_population"))
    monkeypatch.setenv("CENSUS_API_KEY", "census-secret-sentinel")

    captured = {}

    def fake_request(session, method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = [
            ["NAME", "B01003_001E", "state"],
            ["Massachusetts", "6984205", "25"],
            ["California", "39029342", "06"],
        ]
        response.headers = {"content-type": "application/json"}
        response.text = "[]"
        return response

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        result = tool.run(
            {
                "get": "NAME,B01003_001E",
                "for": "state:25",
                "dataset": "2022/acs/acs5",
                "limit": 1,
            }
        )

    assert captured["url"] == "https://api.census.gov/data/2022/acs/acs5"
    assert captured["params"] == {
        "get": "NAME,B01003_001E",
        "for": "state:25",
        "key": "census-secret-sentinel",
    }
    assert result["status"] == "success"
    assert result["count"] == 1
    assert len(result["data"]) == 2
    assert result["data"][0] == ["NAME", "B01003_001E", "state"]
    assert result["data"][1][0] == "Massachusetts"
    assert result["total_before_limit"] == 2
    validate(instance=result, schema=tool.tool_config["return_schema"])


@pytest.mark.unit
def test_census_uses_default_dataset_without_sending_dataset_as_query(monkeypatch):
    tool = BaseRESTTool(_tool_config("uscensus_tools.json", "USCensus_get_population"))
    monkeypatch.setenv("CENSUS_API_KEY", "census-secret-sentinel")
    args = {"get": "NAME,B01003_001E", "for": "state:25"}

    url = tool._build_url(args)
    params = tool._build_params(args)

    assert url == "https://api.census.gov/data/2022/acs/acs5"
    assert "dataset" not in params
    assert params["key"] == "census-secret-sentinel"


@pytest.mark.unit
def test_census_count_never_includes_header_row(monkeypatch):
    tool = BaseRESTTool(_tool_config("uscensus_tools.json", "USCensus_get_population"))
    monkeypatch.setenv("CENSUS_API_KEY", "census-secret-sentinel")
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = [
        ["NAME", "B01003_001E", "state"],
        ["Massachusetts", "6984205", "25"],
        ["California", "39029342", "06"],
    ]
    response.headers = {"content-type": "application/json"}
    response.text = "[]"

    with patch("tooluniverse.base_rest_tool.request_with_retry", return_value=response):
        result = tool.run({"get": "NAME,B01003_001E", "for": "state:*"})

    assert result["count"] == 2
    assert len(result["data"]) == 3


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "https://example.test/path?q=gene&api_key=top-secret&limit=1",
        "request failed for /path?key=top-secret&keyword=monkey",
        "https://example.test/?access_token=top-secret",
        "https://example.test/?client-secret=top-secret",
    ],
)
def test_redact_url_secrets_removes_secret_values(text):
    redacted = redact_url_secrets(text)
    assert "top-secret" not in redacted
    assert "[REDACTED]" in redacted
    if "keyword=monkey" in text:
        assert "keyword=monkey" in redacted


@pytest.mark.unit
def test_openalex_never_returns_api_key_in_response_url(monkeypatch):
    config = {
        "name": "openalex_search_authors",
        "type": "OpenAlexRESTTool",
        "fields": {
            "path": "/authors",
            "path_params": [],
            "param_map": {"per_page": "per-page"},
            "default_params": {},
        },
        "parameter": {"type": "object", "properties": {}},
    }
    tool = OpenAlexRESTTool(config)
    monkeypatch.setenv("OPENALEX_API_KEY", "openalex-secret-sentinel")

    response = MagicMock()
    response.status_code = 200
    response.url = (
        "https://api.openalex.org/authors?search=Harvard"
        "&api_key=openalex-secret-sentinel"
    )
    response.json.return_value = {"results": []}

    with patch("tooluniverse.openalex_tool.request_with_retry", return_value=response):
        result = tool.run({"search": "Harvard", "per_page": 1})

    assert result["status"] == "success"
    assert "openalex-secret-sentinel" not in result["url"]
    assert "api_key=[REDACTED]" in result["url"]


@pytest.mark.unit
def test_pubmed_xml_fallback_never_returns_api_key_in_url():
    config = {
        "name": "PubMed_get_article",
        "type": "PubMedRESTTool",
        "fields": {"endpoint": "https://eutils.ncbi.nlm.nih.gov/efetch.fcgi"},
        "parameter": {"type": "object", "properties": {}},
    }
    tool = PubMedRESTTool(config)
    response = MagicMock()
    response.text = "not XML"
    response.url = "https://example.test/efetch?api_key=ncbi-secret-sentinel"

    result = tool._parse_efetch_xml(response)

    assert "ncbi-secret-sentinel" not in result["url"]
    assert "api_key=[REDACTED]" in result["url"]
