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

    def test_ranked_results_have_recoverable_offsets(self):
        tool = _tool()
        comment, column_header, template, _ = _TSV.splitlines()
        rows = []
        for i in range(7):
            fields = template.split("\t")
            fields[2] = f"ENSG{i}"
            fields[3] = f"GENE{i}"
            fields[11] = str(100 - i)
            rows.append("\t".join(fields))
        resp = MagicMock(
            status_code=200, text="\n".join([comment, column_header, *rows])
        )

        with patch("tooluniverse.encori_tool.requests.get", return_value=resp):
            page1 = tool.run({"mirna": "hsa-miR-21-5p", "limit": 3, "offset": 0})
            page2 = tool.run({"mirna": "hsa-miR-21-5p", "limit": 3, "offset": 3})
            tail = tool.run({"mirna": "hsa-miR-21-5p", "limit": 3, "offset": 6})

        self.assertEqual([r["gene"] for r in page1["data"]], ["GENE0", "GENE1", "GENE2"])
        self.assertEqual([r["gene"] for r in page2["data"]], ["GENE3", "GENE4", "GENE5"])
        self.assertEqual([r["gene"] for r in tail["data"]], ["GENE6"])
        self.assertEqual(page1["metadata"]["next_offset"], 3)
        self.assertTrue(page1["metadata"]["has_more"])
        self.assertIsNone(tail["metadata"]["next_offset"])
        self.assertFalse(tail["metadata"]["has_more"])


if __name__ == "__main__":
    unittest.main()
