"""Chemistry vendor / procurement depth — reverse-sourcing + source directory.

TU's existing PubChem coverage only does the forward direction
(CID -> vendor names/URLs via PubChem_get_compound_xrefs_by_CID). These two
tools close the reverse-sourcing gap by reusing the generic ``PubChemRESTTool``
class (no new @register_tool class, no registration changes):

  * ``PubChem_get_substances_by_source`` — GET
    ``/substance/sourceall/{source}/sids/JSON``: every substance SID a given
    vendor deposits/offers. Answers "what does vendor X actually stock".
  * ``PubChem_list_substance_sources`` — GET ``/sources/substance/JSON``: the
    master directory (~919) of registered substance sources/vendors, used to
    validate a vendor name before a reverse-sourcing query.

These tests mock the HTTP layer so they run offline and assert the success
parse path and the error path for each tool, plus the ``vendor`` -> ``source``
alias resolution.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def _make_sourceall_tool():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool(
        {
            "name": "PubChem_get_substances_by_source",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/substance/sourceall/{source}/sids/JSON",
                "use_pugview": False,
            },
            "parameter": {
                "properties": {"source": {}, "vendor": {}},
                "required": [],
            },
        }
    )


def _make_sources_tool():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool(
        {
            "name": "PubChem_list_substance_sources",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/sources/substance/JSON",
                "use_pugview": False,
            },
            "parameter": {"properties": {}, "required": []},
        }
    )


# Trimmed but realistic sourceall payload for Combi-Blocks.
_SOURCEALL_PAYLOAD = {
    "IdentifierList": {"SID": [374001172, 374001173, 374001174, 374001175, 374001176]}
}

# Trimmed but realistic substance-source directory payload.
_SOURCES_PAYLOAD = {
    "InformationList": {
        "SourceName": [
            "001Chemical",
            "AA BLOCKS",
            "Aaron Chemicals LLC",
            "AbaChemScene",
            "Combi-Blocks",
            "Enamine",
            "Sigma-Aldrich",
            "TCI (Tokyo Chemical Industry)",
        ]
    }
}


class TestSubstancesBySource(unittest.TestCase):
    def test_parses_sid_list(self):
        """Parses the SID list from a sourceall payload and substitutes the vendor into the URL."""
        tool = _make_sourceall_tool()
        captured = {}

        def _route(url, **_kwargs):
            captured["url"] = url
            return _FakeResponse(200, _SOURCEALL_PAYLOAD)

        with patch("tooluniverse.pubchem_tool.requests.get", side_effect=_route):
            result = tool.run({"source": "Combi-Blocks"})

        self.assertEqual(result["status"], "success")
        sids = result["data"]["IdentifierList"]["SID"]
        self.assertEqual(len(sids), 5)
        self.assertEqual(sids[0], 374001172)
        # The vendor name is substituted into the sourceall URL path.
        self.assertIn("/substance/sourceall/Combi-Blocks/sids/JSON", captured["url"])

    def test_vendor_alias_resolves_to_source(self):
        """The 'vendor' argument is resolved to the {source} URL placeholder."""
        tool = _make_sourceall_tool()
        captured = {}

        def _route(url, **_kwargs):
            captured["url"] = url
            return _FakeResponse(200, _SOURCEALL_PAYLOAD)

        with patch("tooluniverse.pubchem_tool.requests.get", side_effect=_route):
            result = tool.run({"vendor": "Sigma-Aldrich"})

        self.assertEqual(result["status"], "success")
        self.assertIn("/substance/sourceall/Sigma-Aldrich/sids/JSON", captured["url"])

    def test_unknown_source_404_returns_status_error(self):
        """An unknown vendor name (HTTP 404) is surfaced as status:error."""
        tool = _make_sourceall_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(
                404,
                {"Fault": {"Message": "No SIDs found for source"}},
                text="Not Found",
            ),
        ):
            result = tool.run({"source": "NotARealVendor"})

        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP 404", result["error"])
        self.assertEqual(result["detail"], "No SIDs found for source")

    def test_missing_source_placeholder_returns_error_not_raise(self):
        """Missing source/vendor returns a clean status:error and never raises."""
        tool = _make_sourceall_tool()
        with patch("tooluniverse.pubchem_tool.requests.get") as mock_get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("source", result["error"])
        mock_get.assert_not_called()

    def test_network_error_returns_status_error(self):
        """A network exception is caught and returned as status:error."""
        tool = _make_sourceall_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            side_effect=RuntimeError("network blip"),
        ):
            result = tool.run({"source": "Combi-Blocks"})
        self.assertEqual(result["status"], "error")
        self.assertIn("network blip", result["error"])


class TestListSubstanceSources(unittest.TestCase):
    def test_parses_source_directory(self):
        """Parses the full substance-source directory listing."""
        tool = _make_sources_tool()
        captured = {}

        def _route(url, **_kwargs):
            captured["url"] = url
            return _FakeResponse(200, _SOURCES_PAYLOAD)

        with patch("tooluniverse.pubchem_tool.requests.get", side_effect=_route):
            result = tool.run({})

        self.assertEqual(result["status"], "success")
        names = result["data"]["InformationList"]["SourceName"]
        self.assertIn("Combi-Blocks", names)
        self.assertIn("Sigma-Aldrich", names)
        self.assertIn("Enamine", names)
        self.assertTrue(captured["url"].endswith("/sources/substance/JSON"))

    def test_upstream_error_returns_status_error(self):
        """An upstream HTTP 500 is surfaced as status:error."""
        tool = _make_sources_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(
                500, {"Fault": {"Message": "server error"}}, text="oops"
            ),
        ):
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP 500", result["error"])
        self.assertEqual(result["detail"], "server error")

    def test_non_json_response_returns_status_error(self):
        """A non-JSON (HTML) response is surfaced as status:error."""
        tool = _make_sources_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(
                200,
                None,
                text="<html>oops</html>",
                headers={"content-type": "text/html"},
            ),
        ):
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("JSON", result["error"])


if __name__ == "__main__":
    unittest.main()
