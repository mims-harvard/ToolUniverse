"""ProtVar_get_function tolerates null list fields in the UniProt payload.

Regression: a comment with an explicit ``"text": null`` (or a null
features/comments list) made the tool do ``for t in None`` -> TypeError, which
then surfaced as a confusing 'object has no attribute handle_error'. The tool
must treat null lists as empty.
"""

import unittest
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.protvar_tool import ProtVarFunctionTool

    return ProtVarFunctionTool(
        {"name": "ProtVar_get_function", "type": "ProtVarFunctionTool"}
    )


class TestProtVarNullFields(unittest.TestCase):
    def test_null_text_does_not_crash(self):
        tool = _tool()
        payload = {
            "accession": "P04637",
            "position": 175,
            "name": "Cellular tumor antigen p53",
            "features": None,  # explicit null list
            "comments": [
                {"type": "FUNCTION", "text": None},  # explicit null list
                {"type": "DISEASE", "text": [{"value": "Li-Fraumeni syndrome"}]},
            ],
        }
        with patch("tooluniverse.protvar_tool._get_json", return_value=payload):
            result = tool.run({"accession": "P04637", "position": 175})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["features"], [])
        self.assertEqual(
            result["data"]["comments"],
            [{"type": "DISEASE", "value": "Li-Fraumeni syndrome"}],
        )

    def test_non_dict_result_is_clean_error(self):
        tool = _tool()
        with patch("tooluniverse.protvar_tool._get_json", return_value=None):
            result = tool.run({"accession": "P04637", "position": 175})
        self.assertEqual(result["status"], "error")
        self.assertIn("No ProtVar function annotation", result["error"])


if __name__ == "__main__":
    unittest.main()
