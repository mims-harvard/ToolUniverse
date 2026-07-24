"""Gene-regulation depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed gene-regulation capability gaps:

* ``ReMap_get_peaks_in_region`` (ReMapRESTTool) — region-based ChIP-seq
  TR-binding peak retrieval from the real ReMap REST catalog. The legacy
  ReMap tool only queried the ENCODE portal; this adds the defining ReMap
  "region in -> all overlapping TR peaks out" capability.
* ``ChIPAtlas_get_colocalization`` (ChIPAtlasTool) — co-binding partner
  proteins for an antigen in a tissue class, ranked by overlap score.
* ``ChIPAtlas_get_target_genes`` (ChIPAtlasTool) — ranked potential target
  genes for a TF at a chosen TSS distance.
* ``ChIPAtlas_get_experiment_metadata`` (ChIPAtlasTool) — structured
  single-experiment metadata for an SRX/DRX/ERX accession.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _mock_response(*, status_code=200, json_data=None, text=None, url=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text

    def _raise():
        if status_code >= 400:
            raise Exception(f"HTTP {status_code}")

    resp.raise_for_status.side_effect = _raise
    return resp


# ---------------------------------------------------------------------------
# ReMap_get_peaks_in_region
# ---------------------------------------------------------------------------


def _remap_tool():
    from tooluniverse.remap_tool import ReMapRESTTool

    return ReMapRESTTool(
        {
            "name": "ReMap_get_peaks_in_region",
            "fields": {"operation": "get_peaks_in_region"},
        }
    )


_REMAP_FAKE = {
    "region": "chr1:1000000-1010000",
    "size": 7270,
    "datatype": "all",
    "assembly": "hg38",
    "version": "2022",
    "peaks": [
        {
            "peakValues": {
                "chrom": "chr1",
                "chromStart": "998831",
                "chromEnd": "1000050",
                "name": {
                    "Experiment": "GSE121798",
                    "TF": "MED1",
                    "Biotype": "HCT-116",
                    "Treatments": {"size": 2, "data": ["shLuc", "thaps"]},
                },
            }
        },
        {
            "peakValues": {
                "chrom": "chr1",
                "chromStart": "998851",
                "chromEnd": "1000280",
                "name": {
                    "Experiment": "ENCSR000ARO",
                    "TF": "EZH2",
                    "Biotype": "fibroblast",
                    "Treatments": {"size": 1, "data": ["LUNG"]},
                },
            }
        },
    ],
}


class TestReMapGetPeaksInRegion(unittest.TestCase):
    def test_parses_peaks_with_tf_biotype_experiment(self):
        """Parses peaks with tf biotype experiment."""
        tool = _remap_tool()
        with patch.object(tool.session, "get") as get:
            get.return_value = _mock_response(json_data=_REMAP_FAKE)
            result = tool.run(
                {
                    "operation": "get_peaks_in_region",
                    "region": "chr1:1000000-1010000",
                }
            )
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["peak_count"], 2)
        self.assertEqual(data["unique_tf_count"], 2)
        self.assertEqual(data["unique_tfs"], ["EZH2", "MED1"])
        first = data["peaks"][0]
        self.assertEqual(first["tf"], "MED1")
        self.assertEqual(first["biotype"], "HCT-116")
        self.assertEqual(first["experiment"], "GSE121798")
        self.assertEqual(first["treatments"], ["shLuc", "thaps"])

    def test_limit_caps_returned_peaks(self):
        """Limit caps returned peaks."""
        tool = _remap_tool()
        with patch.object(tool.session, "get") as get:
            get.return_value = _mock_response(json_data=_REMAP_FAKE)
            result = tool.run({"region": "chr1:1000000-1010000", "limit": 1})
        self.assertEqual(result["status"], "success")
        # returned_count is capped, peak_count keeps the true total.
        self.assertEqual(result["data"]["returned_count"], 1)
        self.assertEqual(result["data"]["peak_count"], 2)

    def test_invalid_region_format_errors(self):
        """Invalid region format errors."""
        tool = _remap_tool()
        result = tool.run({"region": "not-a-region"})
        self.assertEqual(result["status"], "error")
        self.assertIn("region", result["error"].lower())

    def test_missing_region_errors(self):
        """Missing region errors."""
        tool = _remap_tool()
        result = tool.run({"operation": "get_peaks_in_region"})
        self.assertEqual(result["status"], "error")

    def test_network_failure_returns_error_envelope(self):
        """Network failure returns error envelope."""
        tool = _remap_tool()
        with patch.object(tool.session, "get", side_effect=Exception("boom")):
            result = tool.run({"region": "chr1:1000000-1010000"})
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_legacy_encode_path_still_dispatches(self):
        """Without get_peaks_in_region operation, the legacy ENCODE search runs."""
        tool = _remap_tool()
        # No operation override -> defaults to config's get_peaks_in_region,
        # so explicitly request the legacy behavior with a different op value.
        with patch.object(tool.session, "get") as get:
            get.return_value = _mock_response(json_data={"@graph": []})
            result = tool.run({"operation": "tf_binding", "gene_name": "TP53"})
        self.assertEqual(result["status"], "success")
        self.assertIn("experiments", result["data"])


# ---------------------------------------------------------------------------
# ChIP-Atlas tools (shared class ChIPAtlasTool)
# ---------------------------------------------------------------------------


def _chipatlas_tool():
    from tooluniverse.chipatlas_tool import ChIPAtlasTool

    return ChIPAtlasTool({"name": "ChIPAtlas", "parameter": {"properties": {}}})


_COLO_TSV = (
    "Experiment\tCell_subclass\tProtein\tCTCF|Average\tSRX1|697\tSRX2|697\n"
    "SRX8841617\tLymphoblasts\tCTCF\t7.627306\t0\t9\n"
    "SRXa\tK562\tRAD21\t7.353591\t0\t0\n"
    "SRXb\tK562\tRAD21\t5.000000\t0\t0\n"
    "SRXc\tJurkat\tSTAG1\t6.624309\t0\t0\n"
)


class TestChIPAtlasColocalization(unittest.TestCase):
    def test_ranks_partners_by_best_overlap_score(self):
        """Ranks partners by best overlap score."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(text=_COLO_TSV)
            result = tool.run(
                {
                    "operation": "get_colocalization",
                    "antigen": "CTCF",
                    "cell_type_class": "Blood",
                    "genome": "hg38",
                }
            )
        self.assertEqual(result["status"], "success")
        partners = result["data"]["partners"]
        # CTCF (self) ranks first, RAD21 deduped to its best (7.35), then STAG1.
        self.assertEqual([p["protein"] for p in partners], ["CTCF", "RAD21", "STAG1"])
        rad21 = next(p for p in partners if p["protein"] == "RAD21")
        self.assertAlmostEqual(rad21["best_overlap_score"], 7.353591, places=4)
        self.assertEqual(rad21["best_experiment"], "SRXa")

    def test_missing_cell_type_class_errors(self):
        """Missing cell type class errors."""
        tool = _chipatlas_tool()
        result = tool.run({"operation": "get_colocalization", "antigen": "CTCF"})
        self.assertEqual(result["status"], "error")
        self.assertIn("cell_type_class", result["data"]["error"])

    def test_404_returns_error_envelope(self):
        """404 returns error envelope."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(status_code=404, text="")
            result = tool.run(
                {
                    "operation": "get_colocalization",
                    "antigen": "NOPE",
                    "cell_type_class": "Blood",
                }
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("No colocalization data", result["data"]["error"])

    def test_tissue_class_spaces_become_underscores(self):
        """Tissue class spaces become underscores."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(text=_COLO_TSV)
            tool.run(
                {
                    "operation": "get_colocalization",
                    "antigen": "CTCF",
                    "cell_type_class": "Digestive tract",
                }
            )
            called_url = get.call_args[0][0]
        self.assertIn("CTCF.Digestive_tract.tsv", called_url)


_TARGET_TSV = (
    "Target_genes\tGATA1|Average\tSRX1|CD34\tSRX2|CD34\n"
    "NFE2\t1526.270677\t1000\t900\n"
    "TAL1\t1276.240602\t800\t700\n"
    "LOWGENE\t5.0\t1\t1\n"
)


class TestChIPAtlasTargetGenes(unittest.TestCase):
    def test_parses_and_ranks_target_genes(self):
        """Parses and ranks target genes."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(text=_TARGET_TSV)
            result = tool.run(
                {
                    "operation": "get_target_genes",
                    "antigen": "GATA1",
                    "distance": "5",
                }
            )
        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["gene_count"], 3)
        self.assertEqual(data["target_genes"][0]["gene"], "NFE2")
        self.assertAlmostEqual(
            data["target_genes"][0]["average_binding_score"], 1526.270677, places=3
        )
        # ranked descending
        scores = [g["average_binding_score"] for g in data["target_genes"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_header_only_file_returns_note(self):
        """Header only file returns note."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(
                text="Target_genes\tCTCF|Average\tSRX1|293\n"
            )
            result = tool.run(
                {"operation": "get_target_genes", "antigen": "CTCF"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["gene_count"], 0)
        self.assertIn("note", result["data"])

    def test_invalid_distance_errors(self):
        """Invalid distance errors."""
        tool = _chipatlas_tool()
        result = tool.run(
            {"operation": "get_target_genes", "antigen": "GATA1", "distance": "7"}
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("distance", result["data"]["error"])

    def test_missing_antigen_errors(self):
        """Missing antigen errors."""
        tool = _chipatlas_tool()
        result = tool.run({"operation": "get_target_genes"})
        self.assertEqual(result["status"], "error")


_META_JSON = [
    {
        "expid": "SRX080331",
        "genome": "hg38",
        "agClass": "TFs and others",
        "agSubClass": "CTCF",
        "clClass": "Kidney",
        "clSubClass": "293",
        "title": "GSM749668: Stam HEK293 CTCF 1",
        "attributes": "source_name=HEK293\tcell=HEK293\tantibody=CTCF",
    },
    {
        "expid": "SRX080331",
        "genome": "hg19",
        "agClass": "TFs and others",
        "agSubClass": "CTCF",
        "clClass": "Kidney",
        "clSubClass": "293",
        "title": "GSM749668: Stam HEK293 CTCF 1",
        "attributes": "source_name=HEK293\tantibody=CTCF",
    },
]


class TestChIPAtlasExperimentMetadata(unittest.TestCase):
    def test_parses_structured_metadata_and_attributes(self):
        """Parses structured metadata and attributes."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(
                json_data=_META_JSON, url="https://chip-atlas.org/data/exp_metadata.json?expid=SRX080331"
            )
            result = tool.run(
                {
                    "operation": "get_experiment_metadata",
                    "experiment_id": "SRX080331",
                }
            )
        self.assertEqual(result["status"], "success")
        # both genome records returned when no genome filter
        self.assertEqual(result["data"]["count"], 2)
        exp = result["data"]["experiments"][0]
        self.assertEqual(exp["antigen"], "CTCF")
        self.assertEqual(exp["antigen_class"], "TFs and others")
        self.assertEqual(exp["cell_type"], "293")
        self.assertEqual(exp["cell_type_class"], "Kidney")
        self.assertEqual(exp["attributes"]["antibody"], "CTCF")
        self.assertEqual(exp["attributes"]["cell"], "HEK293")

    def test_genome_filter_narrows_records(self):
        """Genome filter narrows records."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(json_data=_META_JSON)
            result = tool.run(
                {
                    "operation": "get_experiment_metadata",
                    "experiment_id": "SRX080331",
                    "genome": "hg38",
                }
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["experiments"][0]["genome"], "hg38")

    def test_empty_records_error(self):
        """Empty records error."""
        tool = _chipatlas_tool()
        with patch("tooluniverse.chipatlas_tool.requests.get") as get:
            get.return_value = _mock_response(json_data=[])
            result = tool.run(
                {
                    "operation": "get_experiment_metadata",
                    "experiment_id": "SRX_BOGUS",
                }
            )
        self.assertEqual(result["status"], "error")

    def test_missing_experiment_id_errors(self):
        """Missing experiment id errors."""
        tool = _chipatlas_tool()
        result = tool.run({"operation": "get_experiment_metadata"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
