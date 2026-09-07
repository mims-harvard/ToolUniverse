"""FAERS count tools must never present a truncated ranking as the complete set.

openFDA answers a ``count=`` aggregation with only its most frequent values --
100 rows when no ``limit`` is sent -- and its ``meta`` block carries no total, so
a caller has no way to tell a complete ranking from a clipped one. The tools
used to return that bare 100-row list while their descriptions promised "all"
adverse reactions, which turns any term ranked below 100th into a confident
false negative ("not reported for this drug").

The contract pinned here:
  * the response is an object with a top-level ``truncated`` flag,
    ``result_count`` matching ``len(results)`` and the applied ``limit``;
  * ``truncation_note`` appears only when the ranking really is clipped, and
    names the parameter that retrieves more;
  * a query whose full ranking fits inside the limit is NOT flagged.

No network: the openFDA HTTP call is mocked throughout.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit

_JSON_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "fda_drug_adverse_event_tools.json",
)


def _load_config(tool_name):
    with open(_JSON_PATH) as fh:
        configs = json.load(fh)
    for cfg in configs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"tool config not found: {tool_name}")


@pytest.fixture(autouse=True)
def _stub_denominator_probe():
    """Keep the coverage-disclosure probe off the network.

    Every FAERS count tool now fetches its own denominator, and that request
    goes through `request_with_retry` rather than `requests.get` -- so it slips
    past the `requests.get` mocks in this file and would really call
    api.fda.gov. The disclosure itself is pinned in
    test_faers_count_facet_coverage.py; here it is stubbed with a fixed total so
    these truncation tests stay hermetic.
    """
    probe = MagicMock()
    probe.status_code = 200
    probe.json.return_value = {"meta": {"results": {"total": 4741}}}
    with patch("tooluniverse.openfda_adv_tool.request_with_retry", return_value=probe):
        yield


def _make_tool(tool_name="FAERS_count_reactions_by_drug_event"):
    from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool

    # api_key is passed explicitly so a developer's FDA_API_KEY does not change
    # the anonymous ceiling these tests assert against.
    return FDADrugAdverseEventTool(_load_config(tool_name), api_key=None)


def _make_additive_tool(tool_name="FAERS_count_additive_adverse_reactions"):
    from tooluniverse.openfda_adv_tool import FDACountAdditiveReactionsTool

    return FDACountAdditiveReactionsTool(_load_config(tool_name))


def _rows(n, start=1000):
    """n synthetic term/count rows in descending-count order."""
    return [{"term": f"REACTION {i}", "count": start - i} for i in range(n)]


def _response(rows):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": rows}
    resp.raise_for_status.return_value = None
    return resp


class TestTruncationDisclosure(unittest.TestCase):
    def test_clipped_ranking_is_flagged_and_explains_how_to_get_more(self):
        """More terms than the limit -> truncated flag + actionable note."""
        tool = _make_tool()
        # openFDA is asked for limit+1 rows; getting all 101 back proves there
        # is at least one term past the caller's page.
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(101)),
        ) as get:
            out = tool.run({"medicinalproduct": "TACROLIMUS"})
            url = get.call_args.args[0]

        self.assertIsInstance(out, dict)
        self.assertTrue(out["truncated"])
        self.assertEqual(out["limit"], 100)
        self.assertEqual(out["result_count"], 100)
        self.assertEqual(out["result_count"], len(out["results"]))
        # The probe row must not leak into the caller's page.
        self.assertEqual(out["results"][-1]["term"], "REACTION 99")

        note = out["truncation_note"]
        self.assertIn("limit", note)
        self.assertIn("100", note)
        self.assertIn("1000", note)  # the documented maximum
        self.assertIn("NOT evidence", note)

        # limit rides after count= so it can never be read as a search clause.
        self.assertIn("&limit=101", url)
        self.assertNotIn("limit", url.split("count=")[0])

    def test_complete_ranking_is_not_flagged(self):
        """Fewer terms than the limit -> no truncation flag, no note."""
        tool = _make_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(12)),
        ):
            out = tool.run({"medicinalproduct": "SOME RARE DRUG"})

        self.assertFalse(out["truncated"])
        self.assertNotIn("truncation_note", out)
        self.assertEqual(out["result_count"], 12)
        self.assertEqual(out["result_count"], len(out["results"]))

    def test_exactly_limit_terms_is_not_flagged(self):
        """A ranking that exactly fills the page is complete, not truncated.

        The probe row is what makes this exact: 100 rows come back from a
        request for 101, so there is nothing beyond the page.
        """
        tool = _make_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(100)),
        ):
            out = tool.run({"medicinalproduct": "SOME DRUG"})

        self.assertFalse(out["truncated"])
        self.assertNotIn("truncation_note", out)
        self.assertEqual(out["result_count"], 100)

    def test_empty_result_is_not_flagged_as_truncated(self):
        """No matching reports is a complete answer, not a clipped one."""
        tool = _make_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response([]),
        ):
            out = tool.run({"medicinalproduct": "NOT A DRUG"})

        self.assertEqual(out["results"], [])
        self.assertEqual(out["result_count"], 0)
        self.assertFalse(out["truncated"])


class TestLimitParameter(unittest.TestCase):
    def test_limit_is_forwarded_and_widens_the_page(self):
        tool = _make_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(250)),
        ) as get:
            out = tool.run({"medicinalproduct": "TACROLIMUS", "limit": 250})
            url = get.call_args.args[0]

        self.assertIn("&limit=251", url)
        self.assertEqual(out["limit"], 250)
        self.assertEqual(out["result_count"], 250)
        self.assertFalse(out["truncated"])

    def test_limit_is_declared_in_the_shipped_config(self):
        """Every FAERS count tool advertises the pagination parameter."""
        with open(_JSON_PATH) as fh:
            configs = json.load(fh)
        count_tools = [
            c
            for c in configs
            if c.get("type")
            in {"FDADrugAdverseEventTool", "FDACountAdditiveReactionsTool"}
        ]
        self.assertTrue(count_tools)
        for cfg in count_tools:
            prop = cfg["parameter"]["properties"].get("limit")
            self.assertIsNotNone(prop, cfg["name"])
            self.assertEqual(prop["type"], "integer", cfg["name"])
            self.assertEqual(prop["default"], 100, cfg["name"])
            self.assertEqual(prop["maximum"], 1000, cfg["name"])
            self.assertNotIn("limit", cfg["parameter"].get("required", []))

    def test_description_no_longer_promises_every_reaction(self):
        cfg = _load_config("FAERS_count_reactions_by_drug_event")
        self.assertNotIn("returns all adverse reactions", cfg["description"])
        self.assertIn("truncated", cfg["description"])
        self.assertIn("ranked by descending report count", cfg["description"])

    def test_limit_beyond_documented_maximum_is_rejected(self):
        tool = _make_tool()
        with patch("tooluniverse.openfda_adv_tool.requests.get") as get:
            out = tool.run({"medicinalproduct": "TACROLIMUS", "limit": 1001})
        get.assert_not_called()
        self.assertEqual(out["status"], "error")
        self.assertIn("1000", out["error"])

    def test_limit_at_documented_maximum_requires_an_api_key(self):
        """Anonymous callers are capped one below openFDA's documented ceiling.

        Measured live: limit=1000 without a key answers HTTP 403
        API_KEY_MISSING, so the tool rejects it up front with the fix rather
        than letting the caller discover it as an opaque request failure.
        """
        tool = _make_tool()
        with patch("tooluniverse.openfda_adv_tool.requests.get") as get:
            out = tool.run({"medicinalproduct": "TACROLIMUS", "limit": 1000})
        get.assert_not_called()
        self.assertEqual(out["status"], "error")
        self.assertIn("FDA_API_KEY", out["error"])

        keyed = _make_tool()
        keyed.api_key = "test-key"
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(1000)),
        ) as get:
            out = keyed.run({"medicinalproduct": "TACROLIMUS", "limit": 1000})
            url = get.call_args.args[0]
        # At the ceiling there is no probe row, so a full page can only be
        # reported as possibly-incomplete -- never as complete.
        self.assertIn("&limit=1000", url)
        self.assertTrue(out["truncated"])
        self.assertIn("may exist", out["truncation_note"])

    def test_non_integer_limit_is_rejected(self):
        tool = _make_tool()
        with patch("tooluniverse.openfda_adv_tool.requests.get") as get:
            out = tool.run({"medicinalproduct": "TACROLIMUS", "limit": "many"})
        get.assert_not_called()
        self.assertEqual(out["status"], "error")


class TestFilteredAndErrorPaths(unittest.TestCase):
    def test_reaction_filter_still_narrows_to_the_requested_term(self):
        tool = _make_tool()
        rows = _rows(50) + [
            {"term": "PROGRESSIVE MULTIFOCAL LEUKOENCEPHALOPATHY", "count": 561}
        ]
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(rows),
        ):
            out = tool.run(
                {
                    "medicinalproduct": "TACROLIMUS",
                    "reactionmeddraverse": "progressive multifocal leukoencephalopathy",
                }
            )

        self.assertEqual(out["results"], [rows[-1]])
        self.assertEqual(out["result_count"], 1)
        self.assertFalse(out["truncated"])

    def test_filtered_note_says_truncation_applies_to_the_ranking(self):
        tool = _make_tool()
        rows = _rows(100) + [
            {"term": "PROGRESSIVE MULTIFOCAL LEUKOENCEPHALOPATHY", "count": 561}
        ]
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(rows),
        ):
            out = tool.run(
                {
                    "medicinalproduct": "TACROLIMUS",
                    "reactionmeddraverse": "progressive multifocal leukoencephalopathy",
                }
            )
        self.assertTrue(out["truncated"])
        self.assertIn("narrowed to the requested term", out["truncation_note"])

    def test_api_failure_still_surfaces_an_error_not_a_clean_envelope(self):
        """A transport failure must never look like an empty, complete result."""
        tool = _make_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            out = tool.run({"medicinalproduct": "TACROLIMUS"})

        self.assertIsInstance(out, list)
        self.assertIn("error", out[0])
        self.assertIn("API request failed", out[0]["error"])


class TestAdditiveCountTool(unittest.TestCase):
    def test_multi_drug_counts_carry_the_same_disclosure(self):
        tool = _make_additive_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(101)),
        ) as get:
            out = tool.run({"medicinalproducts": ["TACROLIMUS", "CYCLOSPORINE"]})
            url = get.call_args.args[0]

        self.assertIn("&limit=101", url)
        self.assertTrue(out["truncated"])
        self.assertEqual(out["result_count"], 100)
        self.assertIn("truncation_note", out)

    def test_multi_drug_complete_ranking_is_not_flagged(self):
        tool = _make_additive_tool()
        with patch(
            "tooluniverse.openfda_adv_tool.requests.get",
            return_value=_response(_rows(7)),
        ):
            out = tool.run(
                {"medicinalproducts": ["TACROLIMUS", "CYCLOSPORINE"], "limit": 20}
            )

        self.assertFalse(out["truncated"])
        self.assertNotIn("truncation_note", out)
        self.assertEqual(out["result_count"], 7)
        self.assertEqual(out["limit"], 20)


if __name__ == "__main__":
    unittest.main()
