"""Antibody Registry tool (RRID search + resolve).

Covers the request building, RRID normalization, and error paths with mocks
(no live antibodyregistry.org calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool(operation):
    from tooluniverse.antibody_registry_tool import AntibodyRegistryTool

    return AntibodyRegistryTool(
        {
            "name": f"AntibodyRegistry_{operation}",
            "type": "AntibodyRegistryTool",
            "fields": {"operation": operation},
        }
    )


def _resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    r.text = ""
    return r


class TestAntibodySearch(unittest.TestCase):
    def test_missing_query_rejected(self):
        result = _make_tool("search").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("query", result["error"])

    def test_search_normalizes_rrid_and_forwards_q(self):
        tool = _make_tool("search")
        body = {
            "totalElements": 2348,
            "items": [{"abId": 3750875, "abName": "GFAP mAb", "abTarget": "GFAP"}],
        }
        with patch("tooluniverse.antibody_registry_tool.requests.get") as get:
            get.return_value = _resp(200, body)
            result = tool.run({"query": "GFAP", "size": 2})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["rrid"], "AB_3750875")
        self.assertEqual(result["metadata"]["total_matches"], 2348)
        # full-text endpoint + q param (not the unfiltered /antibodies list)
        self.assertIn("fts-antibodies", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["params"]["q"], "GFAP")


class TestAntibodyResolve(unittest.TestCase):
    def test_rrid_prefix_is_stripped(self):
        tool = _make_tool("get_by_rrid")
        with patch("tooluniverse.antibody_registry_tool.requests.get") as get:
            get.return_value = _resp(200, [{"abId": 10000343, "abName": "anti-PV"}])
            result = tool.run({"rrid": "RRID:AB_10000343"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["rrid"], "AB_10000343")
        # URL resolves the bare numeric id.
        self.assertTrue(get.call_args.args[0].endswith("/antibodies/10000343"))

    def test_bare_numeric_id_accepted(self):
        tool = _make_tool("get_by_rrid")
        with patch("tooluniverse.antibody_registry_tool.requests.get") as get:
            get.return_value = _resp(200, [{"abId": 10000343}])
            result = tool.run({"rrid": "10000343"})
        self.assertEqual(result["status"], "success")

    def test_non_numeric_rrid_rejected(self):
        result = _make_tool("get_by_rrid").run({"rrid": "AB_notanumber"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid RRID", result["error"])

    def test_empty_result_is_a_clear_error(self):
        tool = _make_tool("get_by_rrid")
        with patch("tooluniverse.antibody_registry_tool.requests.get") as get:
            get.return_value = _resp(200, [])
            result = tool.run({"rrid": "AB_999999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No antibody found", result["error"])


if __name__ == "__main__":
    unittest.main()
