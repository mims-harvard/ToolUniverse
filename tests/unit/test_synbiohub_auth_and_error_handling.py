"""Regression guard for Fix-R22C-1/2: SynBioHubTool had 3 related bugs
confirmed live:

1. SynBioHub_get_part crashed with an opaque
   "Unexpected error querying SynBioHub: mismatched tag: line N, column M"
   whenever the /sbol endpoint returned non-XML content -- which is exactly
   what happens now, since synbiohub.org 200-OKs an HTML login page for
   unauthenticated requests instead of raising an HTTP error status.
2. SynBioHub_search_parts/get_collections's generic 401 handler gave no
   indication of *why* (login now required upstream) or what to do about
   it.
3. The tool's own JSON description already promised "users with a
   SynBioHub account can supply the auth token via SYNBIOHUB_API_TOKEN",
   but nothing in the implementation ever read that environment variable
   -- the documented capability didn't exist in code.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.synbiohub_tool import SynBioHubTool

pytestmark = pytest.mark.unit

_LOGIN_PAGE_HTML = (
    "<!DOCTYPE html><html><head><title>SynBioHub</title></head>"
    "<body><form>Login required</form></body></html>"
)

_REAL_SBOL_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
    'xmlns:sbol="http://sbols.org/v2#" '
    'xmlns:dcterms="http://purl.org/dc/terms/">'
    '<sbol:ComponentDefinition rdf:about="https://synbiohub.org/public/igem/BBa_E0040/1">'
    "<sbol:displayId>BBa_E0040</sbol:displayId>"
    "<dcterms:title>GFP</dcterms:title>"
    "</sbol:ComponentDefinition>"
    "</rdf:RDF>"
)


def _tool(endpoint):
    return SynBioHubTool({"name": "synbiohub_test", "fields": {"endpoint": endpoint}})


def _resp(status_code=200, text="", json_body=None, content_type="application/json"):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.headers = {"Content-Type": content_type}
    if status_code >= 400:
        r.raise_for_status = MagicMock(
            side_effect=requests.exceptions.HTTPError(response=r)
        )
    else:
        r.raise_for_status = MagicMock()
    if json_body is not None:
        r.json.return_value = json_body
    return r


class TestGetPartNonXmlResponse:
    def test_html_login_page_gives_clear_error_not_xml_parse_crash(self, monkeypatch):
        monkeypatch.delenv("SYNBIOHUB_API_TOKEN", raising=False)
        tool = _tool("get_part")
        resp = _resp(200, text=_LOGIN_PAGE_HTML, content_type="text/html")

        with patch("tooluniverse.synbiohub_tool.requests.get", return_value=resp):
            result = tool.run({"display_id": "BBa_E0040"})

        assert result["status"] == "error"
        assert "non-XML content" in result["error"]
        assert "mismatched tag" not in result["error"]

    def test_real_sbol_xml_still_parses_correctly(self, monkeypatch):
        monkeypatch.delenv("SYNBIOHUB_API_TOKEN", raising=False)
        tool = _tool("get_part")
        resp = _resp(200, text=_REAL_SBOL_XML, content_type="application/rdf+xml")

        with patch("tooluniverse.synbiohub_tool.requests.get", return_value=resp):
            result = tool.run({"display_id": "BBa_E0040"})

        assert result["status"] == "success"
        assert result["data"]["display_id"] == "BBa_E0040"
        assert result["data"]["title"] == "GFP"

    def test_malformed_xml_with_xml_content_type_gives_clear_parse_error(
        self, monkeypatch
    ):
        monkeypatch.delenv("SYNBIOHUB_API_TOKEN", raising=False)
        tool = _tool("get_part")
        resp = _resp(
            200, text="<?xml version='1.0'?><rdf:RDF><unterminated>",
            content_type="application/rdf+xml",
        )

        with patch("tooluniverse.synbiohub_tool.requests.get", return_value=resp):
            result = tool.run({"display_id": "BBa_E0040"})

        assert result["status"] == "error"
        assert "Failed to parse SBOL/XML response" in result["error"]


class Test401ErrorMessage:
    def test_401_without_token_hints_at_missing_token(self, monkeypatch):
        monkeypatch.delenv("SYNBIOHUB_API_TOKEN", raising=False)
        tool = _tool("search")
        resp = _resp(401)

        with patch("tooluniverse.synbiohub_tool.requests.get", return_value=resp):
            result = tool.run({"query": "GFP"})

        assert result["status"] == "error"
        assert "login required" in result["error"].lower()
        assert "no SYNBIOHUB_API_TOKEN is set" in result["error"]

    def test_401_with_token_hints_token_may_be_invalid(self, monkeypatch):
        monkeypatch.setenv("SYNBIOHUB_API_TOKEN", "sometoken")
        tool = _tool("search")
        resp = _resp(401)

        with patch("tooluniverse.synbiohub_tool.requests.get", return_value=resp):
            result = tool.run({"query": "GFP"})

        assert result["status"] == "error"
        assert "may be invalid or expired" in result["error"]


class TestApiTokenWiring:
    def test_search_sends_x_authorization_header_when_token_set(self, monkeypatch):
        monkeypatch.setenv("SYNBIOHUB_API_TOKEN", "mytoken123")
        tool = _tool("search")
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured["headers"] = headers
            return _resp(200, json_body=[])

        with patch("tooluniverse.synbiohub_tool.requests.get", side_effect=fake_get):
            tool.run({"query": "GFP"})

        assert captured["headers"]["X-authorization"] == "mytoken123"

    def test_search_no_auth_header_when_token_unset(self, monkeypatch):
        monkeypatch.delenv("SYNBIOHUB_API_TOKEN", raising=False)
        tool = _tool("search")
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured["headers"] = headers
            return _resp(200, json_body=[])

        with patch("tooluniverse.synbiohub_tool.requests.get", side_effect=fake_get):
            tool.run({"query": "GFP"})

        assert "X-authorization" not in captured["headers"]

    def test_get_collections_sends_token(self, monkeypatch):
        monkeypatch.setenv("SYNBIOHUB_API_TOKEN", "mytoken123")
        tool = _tool("get_collections")
        captured = {}

        def fake_get(url, headers=None, timeout=None):
            captured["headers"] = headers
            return _resp(200, json_body=[])

        with patch("tooluniverse.synbiohub_tool.requests.get", side_effect=fake_get):
            tool.run({})

        assert captured["headers"]["X-authorization"] == "mytoken123"

    def test_get_part_sends_token(self, monkeypatch):
        monkeypatch.setenv("SYNBIOHUB_API_TOKEN", "mytoken123")
        tool = _tool("get_part")
        captured = {}

        def fake_get(url, headers=None, timeout=None):
            captured["headers"] = headers
            return _resp(200, text=_REAL_SBOL_XML, content_type="application/rdf+xml")

        with patch("tooluniverse.synbiohub_tool.requests.get", side_effect=fake_get):
            tool.run({"display_id": "BBa_E0040"})

        assert captured["headers"]["X-authorization"] == "mytoken123"
