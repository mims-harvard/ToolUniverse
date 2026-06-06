"""ENCORI_get_miRNA_targets parses the starBase TSV and ranks by CLIP support.

Fills the gap where TU had no miRNA target-lookup tool (skills fell back to bulk
TargetScan/miRTarBase downloads). ENCORI's REST API returns CLIP-supported +
predicted interactions as a #-commented TSV.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

_TSV = (
    "#cite...\n"
    "miRNAid\tmiRNAname\tgeneID\tgeneName\tgeneType\tchromosome\tnarrowStart\tnarrowEnd\t"
    "broadStart\tbroadEnd\tstrand\tclipExpNum\tdegraExpNum\tRBP\tPITA\tRNA22\tmiRmap\t"
    "microT\tmiRanda\tPicTar\tTargetScan\tTDMDScore\tphyloP\tpancancerNum\tcellline/tissue\n"
    "M1\thsa-miR-21-5p\tENSG1\tWEAK\tprotein_coding\tchr1\t1\t2\t1\t2\t-\t2\t0\tAGO2\t0\t0\t0\t0\t0\t0\t1\t0\t0\t1\tA\n"
    "M1\thsa-miR-21-5p\tENSG2\tSTRONG\tprotein_coding\tchr1\t1\t2\t1\t2\t-\t103\t0\tAGO2\t1\t0\t1\t1\t1\t1\t1\t0\t0\t8\tB\n"
)


def _tool():
    from tooluniverse.encori_tool import ENCORITool

    return ENCORITool({"name": "ENCORI_get_miRNA_targets", "type": "ENCORITool"})


class TestENCORI(unittest.TestCase):
    def test_targets_ranked_by_clip(self):
        tool = _tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = _TSV
        with patch("tooluniverse.encori_tool.requests.get", return_value=resp) as get:
            result = tool.run({"mirna": "hsa-miR-21-5p", "limit": 10})
        # query sent miRNA=name, target=all
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["miRNA"], "hsa-miR-21-5p")
        self.assertEqual(params["target"], "all")
        self.assertEqual(result["status"], "success")
        # strongest CLIP support first
        self.assertEqual(result["data"][0]["gene"], "STRONG")
        self.assertEqual(result["data"][0]["clip_experiments"], 103)
        self.assertEqual(result["data"][0]["n_programs"], 6)
        self.assertEqual(result["metadata"]["direction"], "miRNA->targets")

    def test_requires_mirna_or_gene(self):
        tool = _tool()
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
