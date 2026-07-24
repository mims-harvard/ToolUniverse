"""EpiGraphDB MR trait-label casing fallback (discovery harness, MR build).

EpiGraphDB's /mr endpoint matches GWAS trait labels exactly and
case-sensitively. A lowercase input previously returned an empty
status:success (silent failure). The tool now retries sentence-case
variants and annotates the match with a note.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.epigraphdb_tool import EpiGraphDBTool

    return EpiGraphDBTool(
        {
            "name": "EpiGraphDB_get_mendelian_randomization",
            "type": "EpiGraphDBTool",
            "fields": {"operation": "mr"},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


def _mr_record():
    return {
        "exposure": {"id": "ieu-a-300", "trait": "LDL cholesterol"},
        "outcome": {"id": "ieu-a-7", "trait": "Coronary heart disease"},
        "mr": {"b": 0.45, "se": 0.05, "pval": 1e-20, "method": "IVW", "moescore": 0.95},
    }


class TestMRCasingFallback(unittest.TestCase):
    def test_lowercase_outcome_resolves_via_capitalized_variant(self):
        """Lowercase outcome label falls back to the sentence-case match."""
        tool = _make_tool()

        def fake_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            # Only the exact sentence-case outcome label returns results.
            if params.get("outcome_trait") == "Coronary heart disease":
                resp.json.return_value = {"results": [_mr_record()]}
            else:
                resp.json.return_value = {"results": []}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {
                    "exposure_trait": "LDL cholesterol",
                    "outcome_trait": "coronary heart disease",
                }
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_count"], 1)
        self.assertEqual(result["metadata"]["outcome_trait"], "Coronary heart disease")
        self.assertIn("note", result["metadata"])
        self.assertIn("case normalization", result["metadata"]["note"])

    def test_no_match_returns_actionable_note_not_silent_empty(self):
        """A genuine miss carries a note pointing at search_opengwas."""
        tool = _make_tool()

        def fake_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": []}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {"exposure_trait": "made up trait", "outcome_trait": "another fake"}
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_count"], 0)
        self.assertIn("note", result["metadata"])
        self.assertIn("EpiGraphDB_search_opengwas", result["metadata"]["note"])

    def test_exact_match_no_note(self):
        """An exact first-try match adds no normalization note."""
        tool = _make_tool()

        def fake_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": [_mr_record()]}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run(
                {
                    "exposure_trait": "LDL cholesterol",
                    "outcome_trait": "Coronary heart disease",
                }
            )

        self.assertEqual(result["data"]["total_count"], 1)
        self.assertNotIn("note", result["metadata"])


def _make_gencor_tool():
    from tooluniverse.epigraphdb_tool import EpiGraphDBTool

    return EpiGraphDBTool(
        {
            "name": "EpiGraphDB_get_genetic_correlations",
            "type": "EpiGraphDBTool",
            "fields": {"operation": "genetic_cor"},
            "parameter": {"type": "object", "properties": {}, "required": []},
        }
    )


class TestGeneticCorEmptyNote(unittest.TestCase):
    """Genetic-correlation empty results must carry an actionable note."""

    def test_empty_result_has_actionable_note(self):
        tool = _make_gencor_tool()

        def fake_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": []}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "Body mass index"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["total_count"], 0)
        self.assertIn("note", result["metadata"])
        self.assertIn("|rg| > 0.8", result["metadata"]["note"])

    def test_populated_result_no_note(self):
        """A non-empty genetic-correlation result adds no note."""
        tool = _make_gencor_tool()
        record = {
            "trait1": {"id": "ieu-a-61", "trait": "Waist circumference"},
            "trait2": {"id": "ieu-a-2", "trait": "Body mass index"},
            "cor": {"rg": 0.91, "rg_se": 0.02, "rg_pval": 1e-50},
        }

        def fake_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"results": [record]}
            return resp

        with patch("tooluniverse.epigraphdb_tool.requests.get", side_effect=fake_get):
            result = tool.run({"trait": "Waist circumference"})

        self.assertEqual(result["data"]["total_count"], 1)
        self.assertNotIn("note", result["metadata"])


if __name__ == "__main__":
    unittest.main()
