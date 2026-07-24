"""Dfam_get_annotations gives an actionable message on the server-side 405.

Regression: Dfam's genome-annotation endpoint currently returns HTTP 405
"Invalid Input - 101 - undefined" for every well-formed region query (parameter
validation itself passes). The tool used to surface a bare "Dfam API HTTP 405".
It should explain the failure is a transient Dfam infrastructure issue and point
at the endpoints that still work, without disabling anything.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.dfam_tool import DfamTool

    return DfamTool(
        {"name": "Dfam_get_annotations", "type": "DfamTool", "fields": {"endpoint": "get_annotations"}}
    )


class TestDfamAnnotations(unittest.TestCase):
    def test_server_405_returns_actionable_message(self):
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 405
        resp.text = "Invalid Input - 101 - undefined"
        with patch("tooluniverse.dfam_tool.requests.get", return_value=resp):
            result = tool.run(
                {"assembly": "hg38", "chrom": "chr1", "start": 168100000, "end": 168120000}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("transient", result["error"])
        self.assertIn("Dfam_search_families", result["error"])
        self.assertNotIn("HTTP error", result["error"])

    def test_missing_region_is_validation_error(self):
        tool = _tool()
        # no network call should be needed for a missing-arg validation error
        with patch("tooluniverse.dfam_tool.requests.get") as get:
            result = tool.run({"assembly": "hg38", "chrom": "chr1"})
        self.assertEqual(result["status"], "error")
        self.assertIn("required", result["error"])
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
