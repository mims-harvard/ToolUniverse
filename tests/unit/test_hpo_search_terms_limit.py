"""Regression tests for HPO_search_terms result-count handling (mocked HTTP).

The JAX ontology search endpoint (ontology.jax.org/api/hp/search) sizes the
returned page with the ``limit`` query parameter. The tool previously sent
``max``, which the API silently ignores, so every result set was capped at the
API default of 10 regardless of the requested ``max_results`` -- a valid input
silently returning truncated data wrapped in ``status: success``. These tests
lock in that ``max_results`` is honored (sent as ``limit``), bounded safely,
and that the true total match count is surfaced.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _hpo_search_tool():
    from tooluniverse.hpo_tool import HPOTool

    return HPOTool(
        {
            "name": "HPO_search_terms",
            "type": "HPOTool",
            "fields": {"endpoint": "search_terms"},
        }
    )


def _search_resp(n_terms, total_count):
    """Mock a JAX /hp/search response carrying ``n_terms`` rows."""
    terms = [
        {
            "id": f"HP:{i:07d}",
            "name": f"term {i}",
            "definition": f"def {i}",
            "descendantCount": i,
            "synonyms": [],
        }
        for i in range(n_terms)
    ]
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = {"terms": terms, "totalCount": total_count}
    return r


class TestHPOSearchTermsLimit(unittest.TestCase):
    def test_max_results_sent_as_limit_not_max(self):
        """max_results must reach the API as ``limit`` (never the ignored ``max``)."""
        tool = _hpo_search_tool()
        with patch(
            "tooluniverse.hpo_tool.requests.get",
            return_value=_search_resp(25, 100),
        ) as get:
            result = tool.run({"query": "seizure", "max_results": 25})

        params = get.call_args.kwargs["params"]
        self.assertEqual(params.get("limit"), 25)
        self.assertNotIn("max", params)
        self.assertEqual(params.get("q"), "seizure")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 25)

    def test_total_available_surfaces_true_total(self):
        """metadata exposes the API totalCount, not just the returned page size."""
        tool = _hpo_search_tool()
        with patch(
            "tooluniverse.hpo_tool.requests.get",
            return_value=_search_resp(10, 100),
        ):
            result = tool.run({"query": "seizure", "max_results": 10})

        meta = result["metadata"]
        self.assertEqual(meta["total_results"], 10)
        self.assertEqual(meta["total_available"], 100)

    def test_response_truncated_defensively(self):
        """If upstream ever over-returns, the tool truncates to max_results."""
        tool = _hpo_search_tool()
        with patch(
            "tooluniverse.hpo_tool.requests.get",
            return_value=_search_resp(40, 100),
        ):
            result = tool.run({"query": "seizure", "max_results": 5})
        self.assertEqual(len(result["data"]), 5)

    def test_null_max_results_defaults_without_crashing(self):
        """max_results=null (schema allows integer|null) must default, not crash."""
        tool = _hpo_search_tool()
        with patch(
            "tooluniverse.hpo_tool.requests.get",
            return_value=_search_resp(10, 100),
        ) as get:
            result = tool.run({"query": "seizure", "max_results": None})
        self.assertEqual(result["status"], "success")
        self.assertEqual(get.call_args.kwargs["params"]["limit"], 10)

    def test_max_results_clamped_to_bounds(self):
        """Over-max clamps to 50; zero/negative clamps up to 1."""
        for requested, expected_limit in [(999, 50), (0, 10), (-5, 1)]:
            tool = _hpo_search_tool()
            with patch(
                "tooluniverse.hpo_tool.requests.get",
                return_value=_search_resp(1, 100),
            ) as get:
                tool.run({"query": "seizure", "max_results": requested})
            self.assertEqual(
                get.call_args.kwargs["params"]["limit"],
                expected_limit,
                msg=f"max_results={requested}",
            )


if __name__ == "__main__":
    unittest.main()
