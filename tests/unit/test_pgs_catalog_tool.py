"""PGS Catalog tool (published polygenic scores, EMBL-EBI).

Mocked unit tests for the three operations + normalization + error paths
(no live pgscatalog.org calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool(operation):
    from tooluniverse.pgs_catalog_tool import PGSCatalogTool

    return PGSCatalogTool(
        {"name": f"PGSCatalog_{operation}", "type": "PGSCatalogTool", "fields": {"operation": operation}}
    )


def _resp(status_code, body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    return r


_SCORE = {
    "id": "PGS000001",
    "name": "PGS000001",
    "trait_reported": "Breast cancer",
    "variants_number": 77,
    "method_name": "SNPs passing genome-wide significance",
    "variants_genomebuild": "GRCh37",
    "trait_efo": [{"id": "MONDO_0004989", "label": "breast carcinoma"}],
    "publication": {"firstauthor": "Mavaddat N", "journal": "AJHG", "date_publication": "2019-01-01", "PMID": 30554720},
    "ftp_scoring_file": "https://ftp/PGS000001.txt.gz",
}


class TestSearchTraits(unittest.TestCase):
    def test_missing_query_rejected(self):
        result = _make_tool("search_traits").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("query", result["error"])

    def test_trait_search_counts_scores(self):
        tool = _make_tool("search_traits")
        body = {"results": [{"id": "MONDO_0004989", "label": "breast carcinoma", "associated_pgs_ids": ["PGS1", "PGS2"]}]}
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(200, body)
            result = tool.run({"query": "breast cancer"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["trait_id"], "MONDO_0004989")
        self.assertEqual(result["data"][0]["n_scores"], 2)
        self.assertEqual(get.call_args.kwargs["params"]["term"], "breast cancer")


class TestScoresByTrait(unittest.TestCase):
    def test_missing_trait_id_rejected(self):
        result = _make_tool("get_scores_by_trait").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("trait_id", result["error"])

    def test_scores_summarized(self):
        tool = _make_tool("get_scores_by_trait")
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(200, {"count": 1, "results": [_SCORE]})
            result = tool.run({"trait_id": "MONDO_0004989"})
        s = result["data"][0]
        self.assertEqual(s["pgs_id"], "PGS000001")
        self.assertEqual(s["variants_number"], 77)
        self.assertEqual(s["publication"]["first_author"], "Mavaddat N")
        self.assertEqual(s["publication"]["year"], "2019")  # parsed from date
        self.assertEqual(result["metadata"]["total"], 1)


class TestGetScore(unittest.TestCase):
    def test_get_score_adds_efo_and_ancestry(self):
        tool = _make_tool("get_score")
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(200, _SCORE)
            result = tool.run({"pgs_id": "pgs000001"})  # lowercased -> normalized
        d = result["data"]
        self.assertEqual(d["pgs_id"], "PGS000001")
        self.assertEqual(d["trait_efo"][0]["label"], "breast carcinoma")
        self.assertTrue(get.call_args.args[0].endswith("/score/PGS000001"))  # upper-cased

    def test_404_is_clear_error(self):
        tool = _make_tool("get_score")
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(404, {})
            result = tool.run({"pgs_id": "PGS999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Not found", result["error"])

    def test_unknown_operation(self):
        from tooluniverse.pgs_catalog_tool import PGSCatalogTool

        tool = PGSCatalogTool({"name": "x", "type": "PGSCatalogTool", "fields": {}})
        result = tool.run({"operation": "bogus"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown operation", result["error"])


if __name__ == "__main__":
    unittest.main()
