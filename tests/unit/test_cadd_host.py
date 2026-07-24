"""CADD tool uses the canonical washington host (not the broken bihealth mirror).

Regression: the cadd.bihealth.org mirror returns an empty list (HTTP 200) for
GRCh38-v1.7 queries, so scored variants (e.g. BRAF V600E) silently reported
"No CADD score found". The tool must query cadd.gs.washington.edu and parse
the returned row.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.cadd_tool import CADDTool

    return CADDTool(
        {"name": "CADD_get_variant_score", "type": "CADDTool", "fields": {"operation": "get_variant_score"}}
    )


class TestCADDHost(unittest.TestCase):
    def test_base_url_is_washington(self):
        import tooluniverse.cadd_tool as mod

        self.assertIn("cadd.gs.washington.edu", mod.CADD_BASE_URL)
        self.assertNotIn("bihealth", mod.CADD_BASE_URL)

    def test_variant_score_parsed_from_washington_response(self):
        tool = _make_tool()
        with patch("tooluniverse.cadd_tool.requests.get") as get:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = [
                {"Alt": "T", "Chrom": "7", "PHRED": "29.8", "Pos": "140753336", "RawScore": "5.298463", "Ref": "A"}
            ]
            get.return_value = resp
            result = tool.run(
                {"operation": "get_variant_score", "chrom": "7", "pos": 140753336, "ref": "A", "alt": "T"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["phred_score"], 29.8)
        # the request must go to the washington host
        self.assertIn("cadd.gs.washington.edu", get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
