"""OMA_get_hog handles retired HOG IDs with actionable guidance.

Regression: OMA reassigns HOG IDs between releases. Retired IDs (e.g. the old
'HOG:E0739094' p53 group) now return HTTP 410, which the tool surfaced as a
bare "OMA API HTTP error: 410". The tool should explain the ID was retired and
point the caller at OMA_get_protein's 'oma_hog_id' field. The current p53 HOG is
'HOG:F0782425'.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _hog_tool():
    from tooluniverse.oma_tool import OMATool

    return OMATool(
        {"name": "OMA_get_hog", "type": "OMATool", "fields": {"endpoint": "hog"}}
    )


class TestOMAHog(unittest.TestCase):
    def test_retired_id_returns_actionable_message(self):
        tool = _hog_tool()
        with patch("tooluniverse.oma_tool.requests.get") as get:
            resp = MagicMock()
            resp.status_code = 410
            get.return_value = resp
            result = tool.run({"hog_id": "HOG:E0739094"})
        self.assertEqual(result["status"], "error")
        self.assertIn("no longer valid", result["error"])
        self.assertIn("OMA_get_protein", result["error"])
        # must not raise_for_status -> no generic "HTTP error" path
        self.assertNotIn("HTTP error", result["error"])

    def test_valid_hog_parsed(self):
        tool = _hog_tool()
        with patch("tooluniverse.oma_tool.requests.get") as get:
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = [
                {
                    "hog_id": "HOG:F0782425",
                    "level": "Euteleostomi",
                    "roothog_id": 782425,
                    "completeness_score": 0.61,
                    "description": "Cellular tumor antigen p53",
                    "children_hogs": [],
                }
            ]
            get.return_value = resp
            result = tool.run({"hog_id": "HOG:F0782425"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["description"], "Cellular tumor antigen p53")


if __name__ == "__main__":
    unittest.main()
