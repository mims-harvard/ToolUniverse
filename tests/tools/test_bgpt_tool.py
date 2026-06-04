"""BGPT structured-evidence tool (issue #204).

Covers the request-building, the success envelope, and the error paths
(missing query, free-tier 402, non-JSON) with mocks — no live BGPT calls.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.bgpt_tool import BGPTPaperEvidenceTool

    return BGPTPaperEvidenceTool(
        {"name": "BGPT_search_paper_evidence", "type": "BGPTPaperEvidenceTool", "fields": {}}
    )


def _resp(status_code, json_body=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    if json_body is None:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_body
    return r


class TestBGPTTool(unittest.TestCase):
    def test_missing_query_is_rejected(self):
        result = _make_tool().run({"num_results": 5})
        self.assertEqual(result["status"], "error")
        self.assertIn("query", result["error"])

    def test_success_returns_results_and_metadata(self):
        tool = _make_tool()
        papers = [{"doi": "10.3390/medsci13030136", "title": "GLP-1 and craving"}]
        with patch("tooluniverse.bgpt_tool.requests.post") as post:
            post.return_value = _resp(200, {"results": papers})
            result = tool.run({"query": "GLP-1 alcohol craving", "num_results": 2})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], papers)
        self.assertEqual(result["metadata"]["returned"], 1)
        # num_results is forwarded in the POST body.
        self.assertEqual(post.call_args.kwargs["json"]["num_results"], 2)

    def test_free_tier_exhausted_gives_actionable_error(self):
        tool = _make_tool()
        with patch("tooluniverse.bgpt_tool.requests.post") as post:
            post.return_value = _resp(402, text="payment required")
            result = tool.run({"query": "semaglutide"})
        self.assertEqual(result["status"], "error")
        self.assertIn("BGPT_API_KEY", result["error"])

    def test_env_api_key_is_attached(self):
        tool = _make_tool()
        with patch.dict("os.environ", {"BGPT_API_KEY": "sk-test"}):
            with patch("tooluniverse.bgpt_tool.requests.post") as post:
                post.return_value = _resp(200, {"results": []})
                tool.run({"query": "x"})
        self.assertEqual(post.call_args.kwargs["json"]["api_key"], "sk-test")

    def test_non_json_response_is_handled(self):
        tool = _make_tool()
        with patch("tooluniverse.bgpt_tool.requests.post") as post:
            post.return_value = _resp(200, json_body=None, text="<html>down</html>")
            result = tool.run({"query": "x"})
        self.assertEqual(result["status"], "error")
        self.assertIn("non-JSON", result["error"])


if __name__ == "__main__":
    unittest.main()
