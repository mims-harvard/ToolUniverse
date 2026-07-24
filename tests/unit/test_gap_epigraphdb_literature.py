"""EpiGraphDB literature/support-path evidence (SemMedDB triples).

Closes the gap where EpiGraphDB tools covered MR and gene-drug evidence
but not the literature/support-path evidence. The new
EpiGraphDB_get_literature_evidence tool calls /literature/gwas and parses
SemMedDB subject-predicate-object triples plus their PubMed citations.

These tests mock the HTTP layer to cover: results[] parsing (including the
subject/object split from the triple 'name' field), empty handling, and the
error path.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.epigraphdb_tool import EpiGraphDBTool

    return EpiGraphDBTool(
        {
            "name": "EpiGraphDB_get_literature_evidence",
            "type": "EpiGraphDBTool",
            "fields": {"operation": "literature_evidence"},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _record(name, predicate, pubmed_id):
    """Shape one /literature/gwas result row as the upstream API returns it."""
    return {
        "gwas": {"id": "ieu-a-1089", "trait": "Body mass index"},
        "gs": {"pval": 9.7e-09, "localCount": 6},
        "triple": {
            "id": "C0245514:INHIBITS:3952",
            "name": name,
            "predicate": predicate,
        },
        "lit": {"id": pubmed_id},
    }


class TestLiteratureEvidenceParsing(unittest.TestCase):
    def test_results_parsed_into_triple_rows(self):
        """results[] rows become {subject,predicate,object,pubmed_id,gwas_trait}."""
        tool = _make_tool()
        results = [
            _record("troglitazone INHIBITS Leptin|LEP", "INHIBITS", "9727893"),
            _record(
                "Leptin|LEP ASSOCIATED_WITH Liver Cirrhosis",
                "ASSOCIATED_WITH",
                "9877260",
            ),
        ]

        def fake_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": results}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "body mass index"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_count"], 2)

        rows = result["data"]["literature_triples"]
        self.assertEqual(rows[0]["triple_subject"], "troglitazone")
        self.assertEqual(rows[0]["triple_predicate"], "INHIBITS")
        self.assertEqual(rows[0]["triple_object"], "Leptin|LEP")
        self.assertEqual(rows[0]["pubmed_id"], "9727893")
        self.assertEqual(rows[0]["gwas_trait"], "Body mass index")

        # Object containing a multi-word phrase splits correctly.
        self.assertEqual(rows[1]["triple_subject"], "Leptin|LEP")
        self.assertEqual(rows[1]["triple_predicate"], "ASSOCIATED_WITH")
        self.assertEqual(rows[1]["triple_object"], "Liver Cirrhosis")

        self.assertEqual(result["metadata"]["source"], "EpiGraphDB / SemMedDB")
        self.assertNotIn("note", result["metadata"])

    def test_default_pval_threshold_forwarded(self):
        """Default pval_threshold (1e-8) is sent to the API and echoed in metadata."""
        tool = _make_tool()
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured.update(params)
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": []}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "body mass index"})

        self.assertEqual(captured["pval_threshold"], 1e-8)
        self.assertEqual(captured["trait"], "body mass index")
        self.assertEqual(result["metadata"]["pval_threshold"], 1e-8)

    def test_malformed_triple_falls_back_to_name_as_subject(self):
        """A triple whose name lacks the predicate token keeps name as subject."""
        tool = _make_tool()
        results = [_record("some opaque label", "INHIBITS", "111")]

        def fake_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": results}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "body mass index"})

        row = result["data"]["literature_triples"][0]
        self.assertEqual(row["triple_subject"], "some opaque label")
        self.assertIsNone(row["triple_object"])
        self.assertEqual(row["triple_predicate"], "INHIBITS")


class TestLiteratureEvidenceEmpty(unittest.TestCase):
    def test_empty_results_carry_actionable_note(self):
        """An empty result set is success with an actionable note, not silent."""
        tool = _make_tool()

        def fake_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": []}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "made up trait"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_count"], 0)
        self.assertEqual(result["data"]["literature_triples"], [])
        self.assertIn("note", result["metadata"])


class TestLiteratureEvidenceErrors(unittest.TestCase):
    def test_missing_trait_returns_error(self):
        """Missing trait short-circuits to a status:error envelope."""
        tool = _make_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("trait", result["error"])

    def test_http_error_returns_error_envelope(self):
        """An upstream HTTP error is caught and shaped as status:error."""
        import requests

        tool = _make_tool()

        def fake_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            err = requests.exceptions.HTTPError(response=MagicMock(status_code=500))
            err.response.text = "server error"
            resp.raise_for_status.side_effect = err
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "body mass index"})

        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP error", result["error"])


if __name__ == "__main__":
    unittest.main()
