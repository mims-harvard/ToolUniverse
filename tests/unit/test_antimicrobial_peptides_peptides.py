"""Offline, mocked unit tests for DBAASP antimicrobial-peptide tools.

Covers DBAASPGetPeptideTool (DBAASP_get_peptide) and
DBAASPSearchPeptidesTool (DBAASP_search_peptides): a success-parse path and an
error path for each. The HTTP layer (requests.get) is mocked so the tests are
deterministic and run without network access.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.dbaasp_tool import (  # noqa: E402
    DBAASPGetPeptideTool,
    DBAASPSearchPeptidesTool,
)


_PEPTIDE_107 = {
    "id": 107,
    "dbaaspId": "DBAASPR_107",
    "name": "Dermaseptin S4 (1-16)[M4K]",
    "sequence": "ALWKTLLKKVLKAAAK",
    "sequenceLength": 16,
    "nTerminus": None,
    "cTerminus": None,
    "synthesisType": "Synthetic",
    "complexity": "monomer",
    "pdbs": [],
    "structureModel": None,
    "targetGroups": [],
    "targetActivities": [
        {
            "targetSpecies": {"name": "Staphylococcus aureus"},
            "activityMeasureGroup": {"name": "MIC"},
            "concentration": "0.5-8",
            "unit": {"name": "µg/ml"},
            "medium": {"name": "TYE"},
            "cfu": "1E6",
            "activity": 8.0,
        }
    ],
    "hemoliticCytotoxicActivities": [],
    "antibiofilmActivities": [],
    "uniprots": [],
    "sourceGenes": [],
    "smiles": None,
    "articles": [],
}

_SEARCH_RESULT = {
    "totalCount": 1,
    "data": [
        {
            "id": 2975,
            "dbaaspId": "DBAASPR_2975",
            "name": "Aurein-2.2",
            "sequence": "GLFDIVKKVVGALGSL",
            "sequenceLength": 16,
            "nTerminus": None,
            "cTerminus": "AMD",
            "complexity": "monomer",
            "synthesisType": "Ribosomal",
            "pdb": "",
            "pubchemCid": None,
        }
    ],
}


def _mock_response(json_value=None, status_code=200, raise_json=False, url="https://dbaasp.org/peptides"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.text = "" if json_value is not None else "<html>error</html>"
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_value
    return resp


class TestDBAASPGetPeptide(unittest.TestCase):
    def test_success_parse(self):
        """Parses the mocked record/list and forwards exact DBAASP params."""
        tool = DBAASPGetPeptideTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(_PEPTIDE_107, url="https://dbaasp.org/peptides/107")
            result = tool.run({"peptideId": 107})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["sequence"], "ALWKTLLKKVLKAAAK")
        self.assertEqual(result["metadata"]["name"], "Dermaseptin S4 (1-16)[M4K]")
        self.assertEqual(result["metadata"]["target_activity_count"], 1)
        # URL is built from the digits of the ID
        called_url = get.call_args.args[0]
        self.assertTrue(called_url.endswith("/peptides/107"))

    def test_id_string_with_prefix_extracts_digits(self):
        """A 'DBAASPR_107' string ID yields the /peptides/107 URL."""
        tool = DBAASPGetPeptideTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(_PEPTIDE_107)
            tool.run({"peptideId": "DBAASPR_107"})
        self.assertTrue(get.call_args.args[0].endswith("/peptides/107"))

    def test_missing_id_error(self):
        """Missing peptideId returns an error envelope without raising."""
        tool = DBAASPGetPeptideTool({})
        # No HTTP call should be needed; assert tool does not raise.
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("peptideId", result["error"])

    def test_http_404_error(self):
        """HTTP 404 maps to a not-found error envelope."""
        tool = DBAASPGetPeptideTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(None, status_code=404)
            result = tool.run({"peptideId": 99999999})
        self.assertEqual(result["status"], "error")
        self.assertIn("No DBAASP peptide", result["error"])

    def test_network_exception_returns_error(self):
        """A requests exception is caught and returned as an error."""
        import requests

        tool = DBAASPGetPeptideTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            result = tool.run({"peptideId": 107})
        self.assertEqual(result["status"], "error")
        self.assertIn("failed", result["error"])


class TestDBAASPSearchPeptides(unittest.TestCase):
    def test_success_parse(self):
        """Parses the mocked record/list and forwards exact DBAASP params."""
        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(_SEARCH_RESULT)
            result = tool.run(
                {"sequence": "GLFDIVKKVVGALGSL", "sequence_option": "full", "limit": 3}
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_count"], 1)
        self.assertEqual(result["metadata"]["returned_count"], 1)
        self.assertEqual(result["data"][0]["name"], "Aurein-2.2")

        # The DBAASP-exact param names must be forwarded.
        sent_params = get.call_args.kwargs["params"]
        self.assertEqual(sent_params["sequence.value"], "GLFDIVKKVVGALGSL")
        self.assertEqual(sent_params["sequence.option"], "full")
        self.assertEqual(sent_params["limit"], 3)
        self.assertEqual(sent_params["offset"], 0)

    def test_sequence_option_defaults_to_full(self):
        """sequence.option defaults to 'full' when a sequence is given."""
        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(_SEARCH_RESULT)
            tool.run({"sequence": "GLFDIVKKVVGALGSL"})
        self.assertEqual(get.call_args.kwargs["params"]["sequence.option"], "full")

    def test_target_species_param_mapped(self):
        """target_species maps to targetSpecies.value; no sequence.option injected."""
        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response({"totalCount": 2893, "data": []})
            tool.run({"target_species": "Staphylococcus aureus", "limit": 2})
        sent_params = get.call_args.kwargs["params"]
        self.assertEqual(sent_params["targetSpecies.value"], "Staphylococcus aureus")
        # sequence.option should NOT be injected when no sequence was provided
        self.assertNotIn("sequence.option", sent_params)

    def test_no_filter_error_no_http(self):
        """No filter returns an error and makes no HTTP call."""
        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            result = tool.run({"limit": 5})
            get.assert_not_called()
        self.assertEqual(result["status"], "error")
        self.assertIn("filter", result["error"])

    def test_non_json_response_error(self):
        """A non-JSON body returns an error envelope."""
        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.return_value = _mock_response(None, raise_json=True)
            result = tool.run({"name": "Magainin"})
        self.assertEqual(result["status"], "error")
        self.assertIn("non-JSON", result["error"])

    def test_network_exception_returns_error(self):
        """A requests exception is caught and returned as an error."""
        import requests

        tool = DBAASPSearchPeptidesTool({})
        with patch("tooluniverse.dbaasp_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout("slow")
            result = tool.run({"name": "Magainin"})
        self.assertEqual(result["status"], "error")
        self.assertIn("failed", result["error"])


if __name__ == "__main__":
    unittest.main()
