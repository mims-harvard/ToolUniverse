"""CIViC searches must return a denominator, not just a page.

Every CIViC tool asked GraphQL for ``nodes`` only. A caller therefore saw N
records and had no way to tell whether N was the whole answer or the first page
of a much larger set -- so summaries read "50 evidence items across these
diseases" when 50 was the page size and the disease list was truncated.

CIViC's GraphQL connections expose the denominator; nothing requested it.
Verified against the live API (https://civicdb.org/api/graphql):

    evidenceItems(diseaseName:"melanoma")                  totalCount 370
    evidenceItems(diseaseName:"melanoma", status:ACCEPTED) totalCount 218
    gene(id:5).variants                                    totalCount 114

The tools default to ``status: ACCEPTED``, and the tool now reports 218 for
melanoma -- the denominator for its own filters, not the wider 370. Getting that
wrong is the mismatched-denominator trap this change exists to close.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "civic_tools.json"
)


def _load_configs():
    with open(CONFIG) as fh:
        return json.load(fh)


def _make_tool(name):
    from tooluniverse.civic_tool import CIViCTool

    for cfg in _load_configs():
        if cfg["name"] == name:
            return CIViCTool(cfg)
    raise AssertionError(f"{name} not in civic_tools.json")


def _post(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


# browseDiseases/browseTherapies report the size of the whole browse table
# regardless of the name filter -- 653 therapies for "imatinib", for
# "zzzzznotatherapy", and for no filter at all (verified live). A denominator
# that ignores the query is worse than none, so these two select pageInfo only.
_NO_FILTER_AWARE_TOTAL = {"civic_search_diseases", "civic_search_therapies"}


class TestCivicQueriesRequestTotalCount(unittest.TestCase):
    def test_every_filter_aware_connection_requests_the_denominator(self):
        """Config invariant: no CIViC connection may ship without totalCount."""
        missing = []
        for cfg in _load_configs():
            if cfg["name"] in _NO_FILTER_AWARE_TOTAL:
                continue
            query = (cfg.get("fields") or {}).get("query", "")
            if "nodes" in query and "totalCount" not in query:
                missing.append(cfg["name"])
        self.assertEqual(
            missing,
            [],
            f"CIViC connection queries return a page with no denominator: {missing}",
        )

    def test_browse_connections_do_not_publish_an_unfiltered_total(self):
        """The exemption is asserted, not just commented.

        Whoever adds totalCount back to these two must first confirm upstream
        made them filter-aware -- otherwise a search matching nothing reports
        653, under a description telling the caller to divide by it.
        """
        for cfg in _load_configs():
            if cfg["name"] not in _NO_FILTER_AWARE_TOTAL:
                continue
            query = (cfg.get("fields") or {}).get("query", "")
            self.assertNotIn("totalCount", query, cfg["name"])
            self.assertIn("pageInfo", query, cfg["name"])
            self.assertNotIn(
                "totalCount", json.dumps(cfg.get("return_schema", {})), cfg["name"]
            )

    def test_paginated_variants_query_actually_sent_requests_total_count(self):
        """The gene-variants path builds its query in Python, not in JSON.

        Asserted against the query put on the wire, not against the method
        source: the source also contains the word in a comment, so a
        source-scanning assertion would pass even if the GraphQL selection
        lost the field.
        """
        tool = _make_tool("civic_get_variants_by_gene")
        payload = {
            "data": {
                "gene": {
                    "id": 5,
                    "name": "BRAF",
                    "variants": {
                        "totalCount": 114,
                        "nodes": [{"id": 1, "name": "V600E"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    },
                }
            }
        }
        post = MagicMock(return_value=_post(payload))
        with patch("tooluniverse.civic_tool.requests.post", post):
            tool._get_variants_for_gene_id(5, 10)

        sent = post.call_args.kwargs["json"]["query"]
        self.assertIn("totalCount", sent)
        # It must be selected on the variants connection, not anywhere.
        self.assertRegex(sent, r"variants\([^)]*\)\s*\{\s*totalCount")


class TestEvidenceItemsDenominator(unittest.TestCase):
    def test_query_sent_selects_the_denominator_and_it_is_passed_through(self):
        """Asserts the query on the wire, not just the mocked response.

        CIViCTool returns GraphQL `data` verbatim, so a fixture that already
        contains totalCount proves nothing about the shipped query: strip
        totalCount from civic_tools.json and a response-only assertion still
        passes. The wire assertion is what discriminates.
        """
        tool = _make_tool("civic_search_evidence_items")
        payload = {
            "data": {
                "evidenceItems": {
                    "totalCount": 218,
                    "pageInfo": {"hasNextPage": True},
                    "nodes": [{"id": 1409}, {"id": 1411}],
                }
            }
        }
        post = MagicMock(return_value=_post(payload))
        with patch("tooluniverse.civic_tool.requests.post", post):
            result = tool.run({"disease": "melanoma", "limit": 2})

        sent = post.call_args.kwargs["json"]["query"]
        self.assertRegex(sent, r"evidenceItems\([^)]*\)\s*\{\s*totalCount")
        self.assertIn("pageInfo { hasNextPage }", sent)

        block = result["data"]["evidenceItems"]
        self.assertEqual(block["totalCount"], 218)
        self.assertTrue(block["pageInfo"]["hasNextPage"])
        self.assertEqual(len(block["nodes"]), 2)


class TestVariantsByGeneDenominator(unittest.TestCase):
    """The paginated path rebuilds the block itself, so it can drop the count."""

    def _run(self, limit, total_count=114, page_nodes=None):
        tool = _make_tool("civic_get_variants_by_gene")
        nodes = (
            page_nodes
            if page_nodes is not None
            else [{"id": i, "name": f"V{i}"} for i in range(1, 6)]
        )
        variants = {
            "nodes": nodes,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
        if total_count is not None:
            variants["totalCount"] = total_count
        payload = {"data": {"gene": {"id": 5, "name": "BRAF", "variants": variants}}}
        with patch(
            "tooluniverse.civic_tool.requests.post", return_value=_post(payload)
        ):
            return tool._get_variants_for_gene_id(5, limit)

    def test_total_count_survives_the_pagination_rebuild(self):
        result = self._run(limit=3)
        variants = result["data"]["gene"]["variants"]
        self.assertEqual(variants["totalCount"], 114)
        self.assertEqual(len(variants["nodes"]), 3)
        self.assertTrue(
            variants["pageInfo"]["hasNextPage"],
            "3 of 114 returned but the response claimed the page was complete",
        )

    def test_has_next_page_is_false_when_everything_was_returned(self):
        result = self._run(limit=50, total_count=5)
        variants = result["data"]["gene"]["variants"]
        self.assertEqual(variants["totalCount"], 5)
        self.assertEqual(len(variants["nodes"]), 5)
        self.assertFalse(variants["pageInfo"]["hasNextPage"])

    def test_absent_upstream_total_count_is_not_invented(self):
        """No denominator is better than a fabricated one."""
        result = self._run(
            limit=10, total_count=None, page_nodes=[{"id": 1, "name": "V600E"}]
        )
        variants = result["data"]["gene"]["variants"]
        self.assertNotIn("totalCount", variants)
        self.assertEqual(len(variants["nodes"]), 1)


if __name__ == "__main__":
    unittest.main()
