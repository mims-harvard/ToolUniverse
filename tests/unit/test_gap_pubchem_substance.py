"""PubChem SUBSTANCE (SID) record lookup — PubChem_get_substance_by_SID.

TU's other PubChem tools are all compound/CID-keyed. This closes that gap by
adding a depositor-level SUBSTANCE lookup over PUG
(``/substance/sid/{SID}/JSON`` plus ``/substance/sid/{SID}/cids/JSON``).

These tests mock the HTTP layer so they run offline and assert:
  * a real PC_Substances payload is flattened into the summary record and
    merged with linked compound CIDs,
  * a 404 yields a clean found=false (not an error),
  * an empty PC_Substances list yields found=false,
  * an upstream non-200/non-404 yields status=error,
  * invalid / missing sid is rejected before any HTTP call.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.pubchem_tool import PubChemRESTTool

    return PubChemRESTTool(
        {
            "name": "PubChem_get_substance_by_SID",
            "type": "PubChemRESTTool",
            "fields": {
                "endpoint": "/substance/sid/{sid}/JSON",
                "substance_record": True,
            },
            "parameter": {"properties": {"sid": {}}, "required": ["sid"]},
        }
    )


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


# A trimmed but realistic SID 223766453 (aspirin) substance payload.
_SUBSTANCE_PAYLOAD = {
    "PC_Substances": [
        {
            "sid": {"id": 223766453, "version": 2},
            "source": {
                "db": {
                    "name": "10590",
                    "source_id": {"str": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"},
                }
            },
            "synonyms": ["aspirin", "acetylsalicylic acid"],
            "comment": ["SMILES: CC(=O)OC1=CC=CC=C1C(=O)O"],
            "xref": [
                {"regid": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"},
                {"patent": "US03953464"},
            ],
        }
    ]
}

_CIDS_PAYLOAD = {
    "InformationList": {"Information": [{"SID": 223766453, "CID": [2244]}]}
}


def _route(url, **_kwargs):
    """Dispatch mocked GETs by URL suffix."""
    if url.endswith("/cids/JSON"):
        return _FakeResponse(200, _CIDS_PAYLOAD)
    return _FakeResponse(200, _SUBSTANCE_PAYLOAD)


class TestSubstanceLookup(unittest.TestCase):
    def test_parses_record_and_merges_linked_cids(self):
        tool = _make_tool()
        with patch("tooluniverse.pubchem_tool.requests.get", side_effect=_route):
            result = tool.run({"sid": 223766453})

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["found"])
        data = result["data"]
        self.assertEqual(data["sid"], 223766453)
        self.assertEqual(data["source_name"], "10590")
        self.assertEqual(data["source_id"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        self.assertIn("aspirin", data["synonyms"])
        self.assertIn("BSYNRYMUTXBXSQ-UHFFFAOYSA-N", data["registry_ids"])
        # linked compound CID merged from the /cids/JSON call
        self.assertEqual(data["linked_cids"], [2244])
        self.assertEqual(result["metadata"]["linked_cid_count"], 1)

    def test_404_returns_found_false(self):
        tool = _make_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(404, text="Not Found"),
        ):
            result = tool.run({"sid": 1})
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["found"])

    def test_empty_pc_substances_returns_found_false(self):
        tool = _make_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(200, {"PC_Substances": []}),
        ):
            result = tool.run({"sid": 12345})
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["found"])

    def test_upstream_error_returns_status_error(self):
        tool = _make_tool()
        with patch(
            "tooluniverse.pubchem_tool.requests.get",
            return_value=_FakeResponse(
                400, {"Fault": {"Message": "SID out of range"}}, text="bad"
            ),
        ):
            result = tool.run({"sid": 999999999999})
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP 400", result["error"])
        self.assertEqual(result["detail"], "SID out of range")

    def test_missing_sid_rejected_before_http(self):
        tool = _make_tool()
        with patch("tooluniverse.pubchem_tool.requests.get") as mock_get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("sid", result["error"])
        mock_get.assert_not_called()

    def test_non_numeric_sid_rejected_before_http(self):
        tool = _make_tool()
        with patch("tooluniverse.pubchem_tool.requests.get") as mock_get:
            result = tool.run({"sid": "abc"})
        self.assertEqual(result["status"], "error")
        mock_get.assert_not_called()

    def test_string_sid_accepted(self):
        tool = _make_tool()
        with patch("tooluniverse.pubchem_tool.requests.get", side_effect=_route):
            result = tool.run({"sid": "223766453"})
        self.assertTrue(result["found"])
        self.assertEqual(result["metadata"]["sid"], 223766453)

    def test_linked_cid_failure_does_not_break_call(self):
        """If the /cids call fails, the record still returns with empty CIDs."""
        tool = _make_tool()

        def _route_cids_fail(url, **_kwargs):
            if url.endswith("/cids/JSON"):
                raise RuntimeError("network blip")
            return _FakeResponse(200, _SUBSTANCE_PAYLOAD)

        with patch(
            "tooluniverse.pubchem_tool.requests.get", side_effect=_route_cids_fail
        ):
            result = tool.run({"sid": 223766453})
        self.assertTrue(result["found"])
        self.assertEqual(result["data"]["linked_cids"], [])


if __name__ == "__main__":
    unittest.main()
