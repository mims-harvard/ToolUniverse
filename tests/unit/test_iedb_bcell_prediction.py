"""IEDB_predict_bcell_epitopes collapses per-residue scores into epitope regions.

Fills a real gap: TU had MHC-I/II epitope prediction but no B-cell (antibody)
epitope *prediction* (only search of known epitopes). The new endpoint posts to
the IEDB B-cell tool and turns the per-residue 'E'/'.' assignment into contiguous
predicted epitope regions.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# IEDB bcell TSV: position, residue, score, assignment ('E' = epitope)
_TSV = "Position\tResidue\tScore\tAssignment\n" + "\n".join(
    f"{i}\t{aa}\t{sc}\t{asg}"
    for i, (aa, sc, asg) in enumerate(
        [("S", -0.3, "."), ("A", 0.6, "E"), ("K", 0.8, "E"), ("M", 0.7, "E"), ("L", -0.2, ".")],
        start=1,
    )
)


def _tool():
    from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

    return IEDBPredictionTool(
        {"name": "IEDB_predict_bcell_epitopes", "type": "IEDBPredictionTool", "fields": {"endpoint_type": "predict_bcell"}}
    )


class TestIEDBBcell(unittest.TestCase):
    def test_regions_collapsed(self):
        tool = _tool()
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.text = _TSV
        with patch("tooluniverse.iedb_prediction_tool.requests.post", return_value=resp):
            result = tool.run({"sequence": "SAKML"})
        self.assertEqual(result["status"], "success")
        regions = result["data"]["epitope_regions"]
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["peptide"], "AKM")
        self.assertEqual(regions[0]["start"], "2")
        self.assertEqual(regions[0]["end"], "4")
        self.assertEqual(len(result["data"]["per_residue"]), 5)

    def test_requires_sequence(self):
        tool = _tool()
        with patch("tooluniverse.iedb_prediction_tool.requests.post") as post:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
