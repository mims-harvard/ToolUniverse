"""SwissLipids tool (SIB lipid database).

Covers search, entity normalization (formula/mass/adducts/xrefs), id-prefix
handling, and error paths with mocks (no live SwissLipids calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool(operation):
    from tooluniverse.swisslipids_tool import SwissLipidsTool

    return SwissLipidsTool(
        {"name": f"SwissLipids_{operation}", "type": "SwissLipidsTool", "fields": {"operation": operation}}
    )


def _resp(status_code, body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.text = ""
    return r


class TestSearch(unittest.TestCase):
    def test_missing_query_rejected(self):
        result = _make_tool("search").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("query", result["error"])

    def test_search_returns_hits(self):
        tool = _make_tool("search")
        hits = [
            {"entity_id": "SLM:1", "entity_name": "PC(16:0/18:1)", "classification_level": "Structural subspecies"},
            {"entity_id": "SLM:2", "entity_name": "x"},
        ]
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _resp(200, hits)
            result = tool.run({"query": "PC(16:0/18:1)", "limit": 1})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)  # limit honored
        self.assertEqual(result["metadata"]["total_matches"], 2)
        self.assertEqual(get.call_args.kwargs["params"]["term"], "PC(16:0/18:1)")


class TestGetLipid(unittest.TestCase):
    _ENTRY = {
        "entity_id": "SLM:000000510",
        "entity_name": "hexadecanoate",
        "chemical_data": {"formula": "C16H31O2", "mass": 255.4167, "charge": -1, "mz": {"[M-H]-": 255.23}},
        "xrefs": [
            {"source": "ChEBI", "id": "CHEBI:7896", "url": ""},
            {"source": "HMDB", "id": "HMDB00220", "url": "http://x"},
            {"source": "NoId"},
        ],
        "synonyms": [{"name": "hexadecanoate"}, {"name": "palmitate"}],
    }

    def test_missing_id_rejected(self):
        result = _make_tool("get_lipid").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("entity_id", result["error"])

    def test_entity_normalized(self):
        tool = _make_tool("get_lipid")
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _resp(200, [self._ENTRY])
            result = tool.run({"entity_id": "SLM:000000510"})
        d = result["data"]
        self.assertEqual(d["formula"], "C16H31O2")
        self.assertEqual(d["adduct_mz"], {"[M-H]-": 255.23})
        self.assertEqual(d["synonyms"], ["hexadecanoate", "palmitate"])
        # xref without an id is dropped.
        self.assertEqual([x["source"] for x in d["xrefs"]], ["ChEBI", "HMDB"])

    def test_bare_number_gets_slm_prefix(self):
        tool = _make_tool("get_lipid")
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _resp(200, [self._ENTRY])
            tool.run({"entity_id": "000000510"})
        self.assertTrue(get.call_args.args[0].endswith("/entity/SLM:000000510"))

    def test_empty_entry_is_error(self):
        tool = _make_tool("get_lipid")
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _resp(200, [])
            result = tool.run({"entity_id": "SLM:999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No SwissLipids entry", result["error"])

    def test_http_500_becomes_friendly_not_found(self):
        # the SwissLipids entity endpoint returns HTTP 500 for non-existent /
        # malformed ids -> translate to an actionable not-found, not "HTTP 500".
        tool = _make_tool("get_lipid")
        with patch("tooluniverse.swisslipids_tool.requests.get") as get:
            get.return_value = _resp(500, {})
            result = tool.run({"entity_id": "SLM:999999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No SwissLipids entry", result["error"])
        self.assertIn("SwissLipids_search", result["error"])  # points to the fix
        self.assertNotIn("HTTP 500", result["error"])


if __name__ == "__main__":
    unittest.main()
