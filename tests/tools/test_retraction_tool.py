"""Publication retraction-status tool (Crossref update metadata).

Covers retracted / clean / correction-only classification, DOI normalization,
deduplication, and error paths with mocks (no live Crossref calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.retraction_tool import RetractionCheckTool

    return RetractionCheckTool(
        {"name": "Crossref_check_retraction", "type": "RetractionCheckTool", "fields": {}}
    )


def _resp(status_code, message=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = {"message": message or {}}
    return r


def _update(utype, doi):
    return {
        "type": utype,
        "label": utype.title(),
        "DOI": doi,
        "source": "retraction-watch",
        "updated": {"date-parts": [[2010, 2, 6]]},
    }


class TestRetractionCheck(unittest.TestCase):
    def test_missing_doi_rejected(self):
        result = _make_tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("doi", result["error"])

    def test_retracted_paper_flagged(self):
        tool = _make_tool()
        msg = {
            "title": ["A retracted study"],
            "updated-by": [
                _update("correction", "10.x/corr"),
                _update("retraction", "10.x/retr"),
            ],
        }
        with patch("tooluniverse.retraction_tool.requests.get") as get:
            get.return_value = _resp(200, msg)
            result = tool.run({"doi": "10.1016/S0140-6736(97)11096-0"})

        d = result["data"]
        self.assertTrue(d["is_retracted"])
        self.assertTrue(d["has_correction"])
        self.assertEqual(len(d["notices"]), 2)
        self.assertEqual(d["notices"][0]["date"], "2010-02-06")

    def test_clean_paper_not_retracted(self):
        tool = _make_tool()
        with patch("tooluniverse.retraction_tool.requests.get") as get:
            get.return_value = _resp(200, {"title": ["Fine"], "updated-by": []})
            result = tool.run({"doi": "10.1038/x"})
        self.assertFalse(result["data"]["is_retracted"])
        self.assertEqual(result["data"]["notices"], [])

    def test_duplicate_notices_deduped(self):
        tool = _make_tool()
        msg = {"updated-by": [_update("retraction", "10.x/r"), _update("retraction", "10.x/r")]}
        with patch("tooluniverse.retraction_tool.requests.get") as get:
            get.return_value = _resp(200, msg)
            result = tool.run({"doi": "10.1038/nature12968"})
        self.assertEqual(len(result["data"]["notices"]), 1)

    def test_doi_url_and_prefix_normalized(self):
        tool = _make_tool()
        with patch("tooluniverse.retraction_tool.requests.get") as get:
            get.return_value = _resp(200, {"updated-by": []})
            tool.run({"doi": "https://doi.org/10.1038/x"})
        self.assertTrue(get.call_args.args[0].endswith("/works/10.1038/x"))

    def test_404_is_clear_error(self):
        tool = _make_tool()
        with patch("tooluniverse.retraction_tool.requests.get") as get:
            get.return_value = _resp(404)
            result = tool.run({"doi": "10.9999/nope"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["error"])


if __name__ == "__main__":
    unittest.main()
