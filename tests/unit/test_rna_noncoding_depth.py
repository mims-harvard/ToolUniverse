"""Depth tests for the rna-noncoding cluster: ENCORI (starBase) RNA-interactome
modules and the RNAcentral genome-region overlap tool.

These add coverage for capability gaps:
  * ENCORI_get_RBP_targets        (RBPTarget/)
  * ENCORI_get_ceRNA_network      (ceRNA/)
  * ENCORI_get_RNA_RNA_interactions (RNARNA/)
  * ENCORI_get_degradome_cleavage (degradomeRNA/)
  * ENCORI_get_RBP_disease        (RBPDisease/)
  * ENCORI_scan_RBP_motifs        (RBPMotifScan/)
  * RNAcentral_get_region_ncRNAs  (overlap/region/...)

All ENCORI modules return a #-commented TSV; a bad parameter is reported as a
single plain-language line instead of a table. The RNAcentral overlap endpoint
returns a JSON array of transcript/exon feature dicts. Tests mock HTTP and check
both the parse path and the error path.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _encori_tool(endpoint, name):
    from tooluniverse.encori_tool import ENCORITool

    return ENCORITool(
        {"name": name, "type": "ENCORITool", "fields": {"encori_endpoint": endpoint}}
    )


def _resp(text, status=200):
    r = MagicMock()
    r.status_code = status
    r.text = text
    return r


# --------------------------------------------------------------------------
# 1. RBPTarget/
# --------------------------------------------------------------------------
_RBP_TARGET_TSV = (
    "#cite...\n"
    "RBP\tgeneID\tgeneName\tgeneType\tclusterNum\ttotalClipExpNum\ttotalClipSiteNum\t"
    "clusterID\tchromosome\tnarrowStart\tnarrowEnd\tbroadStart\tbroadEnd\tstrand\t"
    "clipExpNum\tHepG2(shRNA)\tK562(shRNA)\tHepG2(CRISPR)\tK562(CRISPR)\tpancancerNum\t"
    "cellline/tissue\n"
    "WEAKRBP\tENSG1\tTP53\tprotein_coding\t1\t2\t3\tC1\tchr17\t1\t2\t1\t2\t-\t1\t"
    "NA\tNA\tNA\tNA\t0\tHeLa\n"
    "STRONGRBP\tENSG1\tTP53\tprotein_coding\t6\t31\t130\tC2\tchr17\t10\t20\t10\t20\t-\t1\t"
    "NA\tNA\tNA\tNA\t22\tMCF7\n"
)


class TestRBPTarget(unittest.TestCase):
    def test_parses_and_ranks_by_clip_support(self):
        """RBPTarget TSV parses; rows ranked by total CLIP-experiment support."""
        tool = _encori_tool("RBPTarget/", "ENCORI_get_RBP_targets")
        with patch(
            "tooluniverse.encori_tool.requests.get",
            return_value=_resp(_RBP_TARGET_TSV),
        ) as get:
            result = tool.run({"gene": "TP53", "clip_min": 5, "limit": 10})
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["target"], "TP53")
        self.assertEqual(params["RBP"], "all")
        self.assertEqual(result["status"], "success")
        # ranked by total_clip_experiments desc
        self.assertEqual(result["data"][0]["rbp"], "STRONGRBP")
        self.assertEqual(result["data"][0]["total_clip_experiments"], 31)
        self.assertEqual(result["data"][0]["total_clip_sites"], 130)
        self.assertEqual(result["metadata"]["direction"], "gene->RBPs")

    def test_requires_rbp_or_gene(self):
        """RBPTarget requires 'rbp' or 'gene'; no HTTP call otherwise."""
        tool = _encori_tool("RBPTarget/", "ENCORI_get_RBP_targets")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# 2. ceRNA/
# --------------------------------------------------------------------------
_CERNA_TSV = (
    "#cite...\n"
    "geneID\tgeneName\tgeneType\tceRNAid\tceRNAname\tceRNAgeneType\t"
    "hitMiRNAFamilyNum\thitMiRNAFamily\tpval\tfdr\n"
    "ENSG1\tPTEN\tprotein_coding\tENSG2\tFEW\tprotein_coding\t5\t\t1e-3\t1e-2\n"
    "ENSG1\tPTEN\tprotein_coding\tENSG3\tMANY\tprotein_coding\t129\t\t5.4e-09\t1.5e-07\n"
)


class TestCeRNA(unittest.TestCase):
    def test_parses_and_ranks_by_shared_families(self):
        """ceRNA TSV parses; rows ranked by shared miRNA-family count."""
        tool = _encori_tool("ceRNA/", "ENCORI_get_ceRNA_network")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_CERNA_TSV)
        ) as get:
            result = tool.run({"gene": "PTEN", "shared_mirna_min": 5, "limit": 10})
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["ceRNA"], "PTEN")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["partner"], "MANY")
        self.assertEqual(result["data"][0]["shared_mirna_families"], 129)
        self.assertEqual(result["data"][0]["pval"], 5.4e-09)

    def test_requires_gene(self):
        """ceRNA requires a query gene; no HTTP call otherwise."""
        tool = _encori_tool("ceRNA/", "ENCORI_get_ceRNA_network")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# 3. RNARNA/  (also tests the "bad parameter -> single-line body" error path)
# --------------------------------------------------------------------------
_RNARNA_TSV = (
    "#cite...\n"
    "geneID\tgeneName\tgeneType\tpairGeneID\tpairGeneName\tpairGeneType\t"
    "interactionNum\ttotalExpNum\ttotalSeqTypeNum\ttotalReadsNum\tinteractionLocus\t"
    "alignment\texpNum\tseqTypeNum\treadsNum\tFreeEnergy\tAlignScore(Smith-Waterman)\t"
    "CellLine/Tissue\n"
    "ENSG1\tMALAT1\tlncRNA\tENSG2\tSCYL3\tprotein_coding\t1\t1\t1\t1\tloc\taln\t1\t1\t1\t"
    "-33.7\t18.0\tHeLa\n"
    "ENSG1\tMALAT1\tlncRNA\tENSG3\tRNU1-1\tsnRNA\t371\t20\t1\t506\tloc\taln\t20\t1\t506\t"
    "-33.6\t16.0\tLymphoblastoid\n"
)
_RNARNA_BAD = (
    "#cite...\n"
    'The "RNA" parameter haven\'t been set correctly! Or the input of "RNA"'
    " parameter is not available!\n"
)


class TestRNARNA(unittest.TestCase):
    def test_parses_and_ranks_by_experiment_support(self):
        """RNARNA TSV parses; ranked by supporting-experiment count."""
        tool = _encori_tool("RNARNA/", "ENCORI_get_RNA_RNA_interactions")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_RNARNA_TSV)
        ) as get:
            result = tool.run({"rna": "MALAT1", "gene_type": "lncRNA", "limit": 10})
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["RNA"], "MALAT1")
        self.assertEqual(params["geneType"], "lncRNA")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["partner"], "RNU1-1")
        self.assertEqual(result["data"][0]["total_experiments"], 20)
        self.assertEqual(result["data"][0]["free_energy"], -33.6)

    def test_bad_parameter_single_line_is_error(self):
        """RNARNA single-line error body is surfaced as status=error."""
        tool = _encori_tool("RNARNA/", "ENCORI_get_RNA_RNA_interactions")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_RNARNA_BAD)
        ):
            result = tool.run({"rna": "BADRNA"})
        self.assertEqual(result["status"], "error")
        self.assertIn("RNA", result["error"])

    def test_requires_rna(self):
        """RNARNA requires an 'rna'; no HTTP call otherwise."""
        tool = _encori_tool("RNARNA/", "ENCORI_get_RNA_RNA_interactions")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# 4. degradomeRNA/
# --------------------------------------------------------------------------
_DEGRADOME_TSV = (
    "#cite...\n"
    "miRNAid\tmiRNAname\tgeneName\tgeneType\tcleaveEventNum\tdegraExpNum\t"
    "degraSiteNum\ttotalReads\tcategory\n"
    "MIMAT2\thsa-miR-6831-3p\tTP53\tprotein_coding\t1\t2\t2\t4\tII\n"
    "MIMAT1\thsa-miR-1-3p\tTP53\tprotein_coding\t3\t7\t8\t17\tII\n"
)


class TestDegradome(unittest.TestCase):
    def test_parses_and_ranks_by_degradome_support(self):
        """degradome TSV parses; ranked by degradome-experiment count."""
        tool = _encori_tool("degradomeRNA/", "ENCORI_get_degradome_cleavage")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_DEGRADOME_TSV)
        ) as get:
            result = tool.run({"gene": "TP53", "assembly": "hg19", "limit": 10})
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["target"], "TP53")
        self.assertEqual(params["assembly"], "hg19")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["mirna"], "hsa-miR-1-3p")
        self.assertEqual(result["data"][0]["degradome_experiments"], 7)
        self.assertEqual(result["data"][0]["cleave_event_num"], 3)
        self.assertEqual(result["metadata"]["assembly"], "hg19")

    def test_defaults_to_hg19_assembly(self):
        """degradome defaults to assembly hg19 (only built assembly)."""
        tool = _encori_tool("degradomeRNA/", "ENCORI_get_degradome_cleavage")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_DEGRADOME_TSV)
        ) as get:
            tool.run({"gene": "TP53"})
        self.assertEqual(get.call_args.kwargs["params"]["assembly"], "hg19")

    def test_requires_gene_or_mirna(self):
        """degradome requires 'gene' or 'mirna'; no HTTP call otherwise."""
        tool = _encori_tool("degradomeRNA/", "ENCORI_get_degradome_cleavage")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# 5. RBPDisease/
# --------------------------------------------------------------------------
_RBP_DISEASE_TSV = (
    "#cite...\n"
    "RBP\tgeneID\tgeneName\ttissue\tdiseaseNum\tdiseases\tdiseaseCosmicID\t"
    "cosmicNum\tsampleNum\tmutTypeNum\tclipExpNum\tclipSiteNum\n"
    "ACIN1\tENSG1\tMYC\tbreast\t2\tcarcinoma,metaplastic carcinoma\t"
    "COSM5965505,COSM6193792\t2\t2\t2\t5\t7\n"
    "EIF4A3\tENSG1\tMYC\tbreast\t3\tcarcinoma,ductal carcinoma,lobular carcinoma\t"
    "COSM6502365,COSM5798874,COSM6947109\t3\t3\t2\t2\t2\n"
)


class TestRBPDisease(unittest.TestCase):
    def test_parses_and_ranks_by_cosmic_count(self):
        """RBPDisease TSV parses; ranked by COSMIC mutation count."""
        tool = _encori_tool("RBPDisease/", "ENCORI_get_RBP_disease")
        with patch(
            "tooluniverse.encori_tool.requests.get",
            return_value=_resp(_RBP_DISEASE_TSV),
        ) as get:
            result = tool.run(
                {"gene": "MYC", "tissue": "breast", "disease": "carcinoma", "limit": 10}
            )
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["target"], "MYC")
        self.assertEqual(params["tissue"], "breast")
        self.assertEqual(params["disease"], "carcinoma")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["rbp"], "EIF4A3")
        self.assertEqual(result["data"][0]["cosmic_num"], 3)
        self.assertIn("COSM5965505", _RBP_DISEASE_TSV)

    def test_requires_some_filter(self):
        """RBPDisease requires at least one filter; no HTTP call otherwise."""
        tool = _encori_tool("RBPDisease/", "ENCORI_get_RBP_disease")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# 6. RBPMotifScan/
# --------------------------------------------------------------------------
_MOTIF_TSV = (
    "#cite...\n"
    "RBP\tDatasetID\tMotifRank\tIdentifiedMotif\tQueryMotif\ttargetPeakNum\t"
    "TargetPercentage(%)\tp-value\tp-value(ln)\tMotifMatrix\tRegion\tCellLine/Tissue\t"
    "Properties\tMainAccession\tSubAccession\tCitation\n"
    "MBNL2\tSBDH1117\t1\tTGCATG\tUGCAUG\t774\t0\t1e-58\t-58\thttp://m1\thttp://b1\t"
    "brain\trep3\tGSE68890\tGSM1685416\tGoodwin M et al. Cell Rep 2015.\n"
    "RBFOX2\tSBDH1753\t1\tTGCATG\tUGCAUG\t11554\t0\t0\t-8551\thttp://m2\thttp://b2\t"
    "HEK293T\trep1\tSRP239057\tSRX\tNye C et al.\n"
)


class TestMotifScan(unittest.TestCase):
    def test_parses_and_ranks_by_target_peaks(self):
        """RBPMotifScan TSV parses; ranked by target-peak count."""
        tool = _encori_tool("RBPMotifScan/", "ENCORI_scan_RBP_motifs")
        with patch(
            "tooluniverse.encori_tool.requests.get", return_value=_resp(_MOTIF_TSV)
        ) as get:
            result = tool.run({"motif": "UGCAUG", "rank_limit": 10, "limit": 10})
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["motif"], "UGCAUG")
        self.assertEqual(params["rankLimit"], 10)
        self.assertEqual(result["status"], "success")
        # ranked by target_peak_num desc
        self.assertEqual(result["data"][0]["rbp"], "RBFOX2")
        self.assertEqual(result["data"][0]["target_peak_num"], 11554)
        self.assertEqual(result["data"][0]["identified_motif"], "TGCATG")

    def test_requires_motif_or_rbp(self):
        """RBPMotifScan requires 'motif' or 'rbp'; no HTTP call otherwise."""
        tool = _encori_tool("RBPMotifScan/", "ENCORI_scan_RBP_motifs")
        with patch("tooluniverse.encori_tool.requests.get") as get:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get.assert_not_called()


# --------------------------------------------------------------------------
# ENCORI shared HTTP error path
# --------------------------------------------------------------------------
class TestEncoriHttpError(unittest.TestCase):
    def test_non_200_is_error(self):
        """Non-200 ENCORI response becomes status=error."""
        tool = _encori_tool("RBPTarget/", "ENCORI_get_RBP_targets")
        with patch(
            "tooluniverse.encori_tool.requests.get",
            return_value=_resp("oops", status=500),
        ):
            result = tool.run({"gene": "TP53"})
        self.assertEqual(result["status"], "error")
        self.assertIn("500", result["error"])

    def test_request_exception_does_not_raise(self):
        """A requests exception is caught and returned as status=error."""
        import requests as _rq

        tool = _encori_tool("ceRNA/", "ENCORI_get_ceRNA_network")
        with patch(
            "tooluniverse.encori_tool.requests.get",
            side_effect=_rq.exceptions.ConnectionError("boom"),
        ):
            result = tool.run({"gene": "PTEN"})
        self.assertEqual(result["status"], "error")


# --------------------------------------------------------------------------
# 7. RNAcentral region overlap
# --------------------------------------------------------------------------
_OVERLAP_JSON = [
    {
        "ID": "URS0000220C5A_9606@2/39767323-39767440:+",
        "external_name": "URS0000220C5A",
        "taxid": 9606,
        "feature_type": "transcript",
        "biotype": "misc_RNA",
        "seq_region_name": "2",
        "strand": 1,
        "start": 39767323,
        "end": 39767440,
    },
    {
        "ID": 34931607,
        "feature_type": "exon",
        "Parent": "URS0000220C5A_9606@2/39767323-39767440:+",
        "biotype": "misc_RNA",
        "seq_region_name": "2",
        "strand": 1,
        "start": 39767323,
        "end": 39767440,
    },
]


def _region_tool():
    from tooluniverse.rnacentral_tool import RNAcentralGetTool

    return RNAcentralGetTool(
        {
            "name": "RNAcentral_get_region_ncRNAs",
            "type": "RNAcentralGetTool",
            "fields": {"region_overlap": True},
            "settings": {"base_url": "https://rnacentral.org/api/v1", "timeout": 30},
        }
    )


class TestRNAcentralRegion(unittest.TestCase):
    def test_parses_region_string(self):
        """Region overlap parses a 'chr:start-end' string into transcripts/exons."""
        tool = _region_tool()
        with patch(
            "tooluniverse.rnacentral_tool._http_get", return_value=_OVERLAP_JSON
        ) as g:
            result = tool.run(
                {"region": "2:39745816-39826679", "species": "homo_sapiens"}
            )
        url = g.call_args.args[0]
        self.assertIn(
            "overlap/region/homo_sapiens/2:39745816-39826679",
            url,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["transcript_count"], 1)
        self.assertEqual(result["data"]["exon_count"], 1)
        self.assertEqual(
            result["data"]["transcripts"][0]["external_name"], "URS0000220C5A"
        )

    def test_builds_region_from_discrete_coords(self):
        """Region overlap builds the locus from chromosome/start/end."""
        tool = _region_tool()
        with patch(
            "tooluniverse.rnacentral_tool._http_get", return_value=_OVERLAP_JSON
        ) as g:
            result = tool.run({"chromosome": "2", "start": 39745816, "end": 39826679})
        self.assertIn("2:39745816-39826679", g.call_args.args[0])
        self.assertEqual(result["status"], "success")

    def test_missing_region_and_coords_is_error(self):
        """Region overlap errors when neither region nor coords are given."""
        tool = _region_tool()
        with patch("tooluniverse.rnacentral_tool._http_get") as g:
            result = tool.run({"species": "homo_sapiens"})
        self.assertEqual(result["status"], "error")
        g.assert_not_called()

    def test_non_list_payload_is_error(self):
        """A non-list overlap payload (server error) becomes status=error."""
        tool = _region_tool()
        with patch(
            "tooluniverse.rnacentral_tool._http_get",
            return_value={"message": "Internal Server Error"},
        ):
            result = tool.run({"region": "2:1-2"})
        self.assertEqual(result["status"], "error")

    def test_http_exception_does_not_raise(self):
        """An overlap HTTP exception is caught and returned as status=error."""
        tool = _region_tool()
        with patch(
            "tooluniverse.rnacentral_tool._http_get", side_effect=RuntimeError("boom")
        ):
            result = tool.run({"region": "2:1-2"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
