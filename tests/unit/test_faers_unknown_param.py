"""FAERS / openFDA adverse-event tools: unrecognized params must not corrupt the query.

Regression for a silent-failure bug: an unknown argument (e.g. a stray 'limit')
was forwarded into the openFDA search query as a bogus filter ('limit:2'),
which matches nothing and returns a silent empty result. The tool must now
ignore params not in its search-field map.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.openfda_adv_tool import FDADrugAdverseEventTool

    return FDADrugAdverseEventTool(
        {
            "name": "FAERS_count_reactions_by_drug_event",
            "type": "FDADrugAdverseEventTool",
            "count_field": "patient.reaction.reactionmeddrapt.exact",
            "fields": {
                "search_fields": {"medicinalproduct": ["patient.drug.medicinalproduct"]},
            },
        }
    )


class TestUnknownParam(unittest.TestCase):
    def _run_and_capture_url(self, arguments):
        tool = _make_tool()
        with patch("tooluniverse.openfda_adv_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = {"results": [{"term": "FATIGUE", "count": 100}]}
            resp.status_code = 200
            get.return_value = resp
            tool.run(arguments)
            return get.call_args.args[0] if get.call_args.args else get.call_args.kwargs.get("url", "")

    def test_known_param_is_in_query(self):
        url = self._run_and_capture_url({"medicinalproduct": "SIMVASTATIN"})
        self.assertIn("patient.drug.medicinalproduct", url)
        self.assertIn("SIMVASTATIN", url)

    def test_unknown_param_is_ignored_not_forwarded(self):
        # 'limit' is not in search_fields -> must NOT appear as a bogus filter
        url = self._run_and_capture_url({"medicinalproduct": "SIMVASTATIN", "limit": 2})
        self.assertIn("patient.drug.medicinalproduct", url)  # the real query survives
        self.assertNotIn("limit:2", url)  # the stray param is dropped
        self.assertNotIn("limit", url.split("count=")[0])  # not in the search clause


if __name__ == "__main__":
    unittest.main()
