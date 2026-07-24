"""PathwayCommons_paths_between (multi-gene mechanistic path-finding).

Closes the gap where the PathwayCommons family could fetch a single gene's
interaction neighborhood but not the mechanistic paths connecting a *set* of
genes. The new ``paths_between`` operation calls the PC2 /graph endpoint with
kind=PATHSBETWEEN, format=SIF, one source= per gene, and parses the
tab-separated SIF triples "ENTITY_A <relation> ENTITY_B" into
{source, relation, target} edges.

These tests mock the HTTP layer so they run offline. They cover:
  - SIF parsing into edges + relation_counts + entity_count,
  - empty-body handling (200 with no paths -> success with a note),
  - the <2-genes validation error,
  - the bad-input (no genes) validation error,
  - the HTTP-error path,
  - that run() returns an error dict instead of raising on network failure,
  - that one source= is sent per gene with kind=PATHSBETWEEN & format=SIF.
"""

import unittest
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


# Realistic SIF snippet (tab-separated triples, no header) as the PC2 /graph
# endpoint returns for kind=PATHSBETWEEN&format=SIF on a BRCA1/BRCA2/TP53 set.
SAMPLE_SIF = "\n".join(
    [
        "BRCA1\tin-complex-with\tBARD1",
        "BRCA1\tin-complex-with\tBRCA2",
        "BRCA2\tin-complex-with\tRAD51",
        "ATM\tcontrols-phosphorylation-of\tTP53",
        "TP53\tcontrols-expression-of\tCDKN1A",
        "",  # blank line should be skipped
        "MALFORMED_LINE_ONLY_TWO\tcols",  # <3 fields -> skipped
    ]
)


def _make_tool():
    from tooluniverse.pathwaycommons_tool import PathwayCommonsTool

    return PathwayCommonsTool(
        {
            "name": "PathwayCommons_paths_between",
            "type": "PathwayCommonsTool",
            "fields": {"operation": "paths_between"},
            "parameter": {"type": "object", "properties": {}, "required": ["genes"]},
        }
    )


def _mock_response(status_code=200, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestPathsBetweenParsing(unittest.TestCase):
    def test_sif_parsed_into_edges(self):
        """SIF triples become {source, relation, target} edges."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(200, SAMPLE_SIF))

        result = tool.run({"genes": ["BRCA1", "BRCA2", "TP53"]})

        self.assertEqual(result["status"], "success")
        edges = result["data"]["edges"]
        # 5 valid triples; blank line + 2-col malformed line dropped.
        self.assertEqual(len(edges), 5)
        self.assertEqual(
            edges[0],
            {"source": "BRCA1", "relation": "in-complex-with", "target": "BARD1"},
        )
        self.assertEqual(result["metadata"]["total_edges"], 5)

    def test_relation_counts_and_entity_count(self):
        """relation_counts aggregates per relation; entity_count is distinct nodes."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(200, SAMPLE_SIF))

        data = tool.run({"genes": ["BRCA1", "BRCA2", "TP53"]})["data"]

        self.assertEqual(data["relation_counts"]["in-complex-with"], 3)
        self.assertEqual(data["relation_counts"]["controls-phosphorylation-of"], 1)
        self.assertEqual(data["relation_counts"]["controls-expression-of"], 1)
        # Distinct entities: BRCA1, BARD1, BRCA2, RAD51, ATM, TP53, CDKN1A = 7
        self.assertEqual(data["entity_count"], 7)
        self.assertIsNone(data["note"])

    def test_max_results_truncates_edges(self):
        """max_results limits returned edges but total_edges reflects full count."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(200, SAMPLE_SIF))

        result = tool.run({"genes": ["BRCA1", "BRCA2", "TP53"], "max_results": 2})

        self.assertEqual(len(result["data"]["edges"]), 2)
        self.assertEqual(result["metadata"]["total_edges"], 5)
        self.assertEqual(result["metadata"]["returned"], 2)

    def test_comma_separated_string_accepted(self):
        """A comma-separated genes string is split into a list."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(200, SAMPLE_SIF))

        result = tool.run({"genes": "BRCA1, BRCA2 , TP53"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["genes"], ["BRCA1", "BRCA2", "TP53"])

    def test_request_sends_one_source_per_gene(self):
        """Verify kind=PATHSBETWEEN, format=SIF, and one source= per gene."""
        tool = _make_tool()
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured["url"] = url
            captured["params"] = params
            captured["timeout"] = timeout
            return _mock_response(200, SAMPLE_SIF)

        tool.session.get = fake_get
        tool.run({"genes": ["BRCA1", "BRCA2", "TP53"]})

        self.assertTrue(captured["url"].endswith("/graph"))
        self.assertEqual(captured["params"]["kind"], "PATHSBETWEEN")
        self.assertEqual(captured["params"]["format"], "SIF")
        # source must be the full list (requests serializes -> repeated source=).
        self.assertEqual(captured["params"]["source"], ["BRCA1", "BRCA2", "TP53"])
        self.assertEqual(captured["timeout"], 30)

    def test_duplicate_genes_deduplicated(self):
        """Case-insensitive de-duplication while preserving order."""
        tool = _make_tool()
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured["params"] = params
            return _mock_response(200, SAMPLE_SIF)

        tool.session.get = fake_get
        tool.run({"genes": ["BRCA1", "brca1", "TP53"]})

        self.assertEqual(captured["params"]["source"], ["BRCA1", "TP53"])


class TestPathsBetweenEdgeCases(unittest.TestCase):
    def test_empty_body_returns_success_with_note(self):
        """HTTP 200 with empty body (no paths) -> success with explanatory note."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(200, ""))

        result = tool.run({"genes": ["ZZZFAKE1", "ZZZFAKE2"]})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["edges"], [])
        self.assertEqual(result["metadata"]["total_edges"], 0)
        self.assertIsNotNone(result["data"]["note"])

    def test_single_gene_is_error(self):
        """paths_between requires >=2 distinct genes."""
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=AssertionError("network must not be called")
        )

        result = tool.run({"genes": ["BRCA1"]})

        self.assertEqual(result["status"], "error")
        self.assertIn("at least 2", result["error"])

    def test_missing_genes_is_error(self):
        """No genes parameter -> error, no exception."""
        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=AssertionError("network must not be called")
        )

        result = tool.run({})

        self.assertEqual(result["status"], "error")
        self.assertIn("genes", result["error"])

    def test_http_error_returns_error_dict(self):
        """Non-200 HTTP status -> error dict, never raises."""
        tool = _make_tool()
        tool.session.get = MagicMock(return_value=_mock_response(500, ""))

        result = tool.run({"genes": ["BRCA1", "TP53"]})

        self.assertEqual(result["status"], "error")
        self.assertIn("500", result["error"])

    def test_network_exception_caught(self):
        """A raised requests exception is caught and returned as an error dict."""
        import requests

        tool = _make_tool()
        tool.session.get = MagicMock(
            side_effect=requests.exceptions.ConnectionError("boom")
        )

        result = tool.run({"genes": ["BRCA1", "TP53"]})

        self.assertEqual(result["status"], "error")
        self.assertIn("connect", result["error"].lower())

    def test_timeout_exception_caught(self):
        """A request timeout is caught and returned as an error dict."""
        import requests

        tool = _make_tool()
        tool.session.get = MagicMock(side_effect=requests.exceptions.Timeout("slow"))

        result = tool.run({"genes": ["BRCA1", "TP53"]})

        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"].lower())


class TestParseSifHelper(unittest.TestCase):
    def test_parse_skips_blank_and_short_lines(self):
        """_parse_sif_edges drops blank lines and lines with <3 fields."""
        from tooluniverse.pathwaycommons_tool import PathwayCommonsTool

        edges = PathwayCommonsTool._parse_sif_edges(SAMPLE_SIF)
        self.assertEqual(len(edges), 5)
        self.assertTrue(all({"source", "relation", "target"} <= set(e) for e in edges))


if __name__ == "__main__":
    unittest.main()
