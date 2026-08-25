"""Immunology depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed antibody / immunogenetics
capability gaps. All four reuse an existing registered tool class (no new
@register_tool), so they need no registration:

* ``SAbDab_get_structure_summary`` (SAbDabTool, operation
  ``get_structure_summary``) — per-structure curated antibody annotations
  (antigen, species, resolution, R-free, V-gene subclass, scFv/engineered
  flags, affinity) from the SAbDab summary TSV.
* ``TheraSAbDab_get_therapeutic_sequences`` (TheraSAbDabTool, operation
  ``get_therapeutic_sequences``) — therapeutic antibody VH/VL sequences,
  isotype, PDB coverage, companies and conditions parsed from the
  Thera-SAbDab ``?all=true`` summary hrefs.
* ``IMGT_get_germline_gene_fasta`` (IMGTTool, operation
  ``get_germline_fasta``) — IMGT/GENE-DB germline IG/TR FASTA, following the
  GENElect redirect chain and extracting the FASTA <pre> block.
* ``IEDB_predict_antigen_processing`` (IEDBPredictionTool, endpoint
  ``predict_processing``) — combined cleavage + TAP + MHC-I processing scores
  from IEDB's next-generation tools pipeline (Fix-R29A-1 moved this off the
  retired synchronous ``tools_api/processing/`` endpoint, which accepts a
  POST and then never answers, stalling every call for the full timeout).

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SAbDab_get_structure_summary
# ---------------------------------------------------------------------------

_SABDAB_TSV = (
    "pdb\tHchain\tLchain\tmodel\tantigen_chain\tantigen_type\tantigen_het_name\t"
    "antigen_name\tshort_header\tdate\tcompound\torganism\theavy_species\t"
    "light_species\tantigen_species\tauthors\tresolution\tmethod\tr_free\t"
    "r_factor\tscfv\tengineered\theavy_subclass\tlight_subclass\tlight_ctype\t"
    "affinity\tdelta_g\taffinity_method\ttemperature\tpmid\n"
    "7d6i\tB\tC\t0\tA\tprotein\tNA\tsars-cov-2 receptor binding domain\t"
    "ANTIVIRAL PROTEIN,IMMUNE SYSTEM\t09/30/20\tA neutralizing MAb\t"
    "SARS-CoV-2; HOMO SAPIENS\thomo sapiens\thomo sapiens\t"
    "severe acute respiratory syndrome-relatedcoronavirus\tShi, R.\t3.41\t"
    "X-RAY DIFFRACTION\t0.255\t0.226\tFalse\tTrue\tIGHV3\tIGLV6\tLambda\t"
    "None\tNone\tNone\tNone\tNone\n"
)


def _sabdab_tool():
    from tooluniverse.sabdab_tool import SAbDabTool

    return SAbDabTool({"name": "SAbDab_get_structure_summary", "timeout": 30})


class TestSAbDabStructureSummary(unittest.TestCase):
    def test_parses_summary_row_with_typed_fields(self):
        """SAbDab TSV row is parsed with numeric/boolean/None coercion."""
        tool = _sabdab_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "text/tab-separated-values; charset=utf-8"}
        resp.text = _SABDAB_TSV
        resp.raise_for_status.return_value = None

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_structure_summary", "pdb_id": "7d6i"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["pdb_id"], "7d6i")
        self.assertEqual(data["antigen_name"], "sars-cov-2 receptor binding domain")
        self.assertEqual(data["heavy_species"], "homo sapiens")
        self.assertEqual(data["light_species"], "homo sapiens")
        # Numeric coercion
        self.assertEqual(data["resolution"], 3.41)
        self.assertEqual(data["r_free"], 0.255)
        # Boolean coercion
        self.assertIs(data["scfv"], False)
        self.assertIs(data["engineered"], True)
        self.assertEqual(data["heavy_subclass"], "IGHV3")
        self.assertEqual(data["light_subclass"], "IGLV6")
        # "None" string -> None
        self.assertIsNone(data["affinity"])
        self.assertIsNone(data["pmid"])
        self.assertEqual(data["count"], 1)

    def test_missing_pdb_id_errors(self):
        """Missing pdb_id returns an error envelope, never raises."""
        tool = _sabdab_tool()
        result = tool.run({"operation": "get_structure_summary"})
        self.assertEqual(result["status"], "error")
        self.assertIn("pdb_id", result["error"])

    def test_404_returns_error_not_raise(self):
        """A 404 from SAbDab yields a structured error, not an exception."""
        tool = _sabdab_tool()
        resp = MagicMock()
        resp.status_code = 404
        resp.headers = {}
        resp.text = ""
        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_structure_summary", "pdb_id": "9zzz"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["error"].lower())


# ---------------------------------------------------------------------------
# TheraSAbDab_get_therapeutic_sequences
# ---------------------------------------------------------------------------

_THERA_HTML = """
<table>
<tr><td><a href="/webapps/sabdab-sabpred/therasabdab/therasummary/?INN=abciximab&amp;format=Fab&amp;clintrial=Approved&amp;status=NFD&amp;target=ITGA2B/CD41&amp;yearprop=1993&amp;isotype=G1&amp;heavy1=EVQLQQSGTVLARPGASVKMSCEAS&amp;light1=EIVLTQSPVTLSVTPGDSVSLSCRAS&amp;heavy2=na&amp;light2=na&amp;struc100=6v4p:CD&amp;struc99=None&amp;struc95to98=None&amp;yearrec=1994&amp;companies=Janssen;Eli+Lilly&amp;cond_approved=Unstable+angina&amp;cond_active=na&amp;cond_disc=Stroke&amp;dev_tech=na&amp;notes=na">abciximab</a></td></tr>
<tr><td><a href="/webapps/sabdab-sabpred/therasabdab/therasummary/?INN=adalimumab&amp;format=Whole+mAb&amp;clintrial=Approved&amp;status=Active&amp;target=TNF/TNFA&amp;yearprop=1999&amp;isotype=G1&amp;heavy1=EVQLVESGGGLVQPGRSLRLSCAAS&amp;light1=DIQMTQSPSSLSASVGDRVTITCRAS&amp;heavy2=na&amp;light2=na&amp;struc100=6cr1:HL&amp;struc99=3wd5:HL&amp;struc95to98=None&amp;yearrec=2000&amp;companies=Abbvie&amp;cond_approved=Ankylosing+spondylitis&amp;cond_active=na&amp;cond_disc=na&amp;dev_tech=na&amp;notes=na">adalimumab</a></td></tr>
</table>
"""


def _thera_tool():
    from tooluniverse.therasabdab_tool import TheraSAbDabTool

    # Reset the class-level cache so each test starts clean.
    TheraSAbDabTool._sequences_cache = None
    return TheraSAbDabTool(
        {
            "name": "TheraSAbDab_get_therapeutic_sequences",
            "fields": {"operation": "get_therapeutic_sequences"},
            "timeout": 30,
        }
    )


class TestTheraSAbDabSequences(unittest.TestCase):
    def tearDown(self):
        from tooluniverse.therasabdab_tool import TheraSAbDabTool

        TheraSAbDabTool._sequences_cache = None

    def test_parses_sequences_and_metadata_from_hrefs(self):
        """VH/VL sequences and metadata are parsed from the summary hrefs."""
        tool = _thera_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = _THERA_HTML
        resp.raise_for_status.return_value = None

        with patch("tooluniverse.therasabdab_tool.requests.get", return_value=resp):
            result = tool.run({"name": "abciximab"})

        self.assertEqual(result["status"], "success")
        thera = result["data"]["therapeutic"]
        self.assertEqual(thera["inn_name"], "abciximab")
        self.assertEqual(thera["isotype"], "G1")
        self.assertEqual(thera["target"], "ITGA2B/CD41")
        self.assertEqual(thera["heavy1"], "EVQLQQSGTVLARPGASVKMSCEAS")
        self.assertEqual(thera["light1"], "EIVLTQSPVTLSVTPGDSVSLSCRAS")
        self.assertEqual(thera["struc100"], "6v4p:CD")
        # "na" / "None" normalize to None
        self.assertIsNone(thera["heavy2"])
        self.assertIsNone(thera["struc99"])
        self.assertEqual(thera["companies"], "Janssen;Eli Lilly")
        self.assertEqual(thera["conditions_discontinued"], "Stroke")
        self.assertEqual(result["metadata"]["total_records"], 2)

    def test_missing_name_errors(self):
        """Missing therapeutic name returns an error envelope."""
        tool = _thera_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("name", result["error"].lower())

    def test_unknown_therapeutic_errors(self):
        """An unknown INN returns a not-found error."""
        tool = _thera_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.text = _THERA_HTML
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.therasabdab_tool.requests.get", return_value=resp):
            result = tool.run({"name": "not-a-real-antibody"})
        self.assertEqual(result["status"], "error")
        self.assertIn("no therapeutic", result["error"].lower())


# ---------------------------------------------------------------------------
# IMGT_get_germline_gene_fasta
# ---------------------------------------------------------------------------

_IMGT_PAGE = (
    "<html><body>"
    "<pre>\nThe FASTA header contains 15 fields separated by '|':\n1. accession\n</pre>"
    "<pre>\n"
    ">AB019441|IGHV(II)-1-1*01|Homo sapiens|P|V-REGION|78242..78477|236 nt|1| | | | |236+0=236| | |\n"
    "cagatgcagctactggagtcatgcccagggctggtgaggtcctcacagacctctgggcct\n"
    ">BK063799|IGHV(II)-12-1*01|Homo sapiens|P|V-REGION|752552..752735|184 nt|1| | | | |184+0=184| | |\n"
    "caggagcagctgcaggagtcagccctggacctgaagagcacacacttaccctctgcttca\n"
    "</pre></body></html>"
)


def _imgt_tool():
    from tooluniverse.imgt_tool import IMGTTool

    return IMGTTool({"name": "IMGT_get_germline_gene_fasta", "timeout": 30})


class TestIMGTGermlineFasta(unittest.TestCase):
    def test_parses_fasta_from_second_pre_block(self):
        tool = _imgt_tool()

        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.text = _IMGT_PAGE
        page_resp.url = "https://www.imgt.org/genedb/fastaC.action"
        page_resp.headers = {"Content-Type": "text/html"}
        page_resp.raise_for_status.return_value = None

        # The tool builds a requests.Session(); patch the class so .get returns
        # our terminal (non-redirect) response immediately.
        session = MagicMock()
        session.headers = {}
        session.get.return_value = page_resp

        with patch("tooluniverse.imgt_tool.requests.Session", return_value=session):
            result = tool.run(
                {
                    "operation": "get_germline_fasta",
                    "gene_type": "IGHV",
                    "species": "Homo sapiens",
                }
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["gene_type"], "IGHV")
        self.assertEqual(data["query"], "7.2 IGHV")
        self.assertEqual(data["record_count"], 2)
        self.assertTrue(data["fasta"].startswith(">AB019441|IGHV(II)-1-1*01|"))
        self.assertIn(">BK063799|IGHV(II)-12-1*01|", data["fasta"])
        # The documentation <pre> must NOT leak in as a record.
        self.assertNotIn("15 fields", data["fasta"])

    def test_missing_gene_type_errors(self):
        """Missing gene_type returns an error envelope."""
        tool = _imgt_tool()
        result = tool.run({"operation": "get_germline_fasta"})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene_type", result["error"])

    def test_no_fasta_block_returns_error(self):
        """A page with no FASTA <pre> block returns an error."""
        tool = _imgt_tool()
        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.text = "<html><body>No results found.</body></html>"
        page_resp.url = "https://www.imgt.org/genedb/fastaC.action"
        page_resp.headers = {"Content-Type": "text/html"}
        page_resp.raise_for_status.return_value = None

        session = MagicMock()
        session.headers = {}
        session.get.return_value = page_resp

        with patch("tooluniverse.imgt_tool.requests.Session", return_value=session):
            result = tool.run(
                {"operation": "get_germline_fasta", "gene_type": "NOTAGENE"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("No FASTA records", result["error"])


# ---------------------------------------------------------------------------
# IEDB_predict_antigen_processing
# ---------------------------------------------------------------------------

_IEDB_SUBMIT_OK = {"result_id": "rid-proc", "warnings": []}

# Column set confirmed live for a netmhcpan binding predictor chained with
# the netctlpan processing predictor.
_IEDB_PROCESSING_DONE = {
    "status": "done",
    "data": {
        "errors": [],
        "warnings": [],
        "results": [
            {
                "type": "peptide_table",
                "table_columns": [
                    {"name": n}
                    for n in (
                        "sequence_number",
                        "peptide",
                        "start",
                        "end",
                        "length",
                        "allele",
                        "netmhcpan_ba_ic50",
                        "mhc_prediction",
                        "tap_prediction_score",
                        "cleavage_prediction_score",
                        "combined_prediction_score",
                    )
                ],
                "table_data": [
                    [
                        1,
                        "LYNTVATLY",
                        2,
                        10,
                        9,
                        "HLA-A*02:01",
                        30582.45,
                        0.035,
                        3.153,
                        0.97688,
                        0.33362,
                    ],
                    [
                        1,
                        "SLYNTVATL",
                        1,
                        9,
                        9,
                        "HLA-A*02:01",
                        46.5,
                        0.438,
                        1.394,
                        0.97756,
                        0.6928,
                    ],
                ],
            }
        ],
    },
}


def _iedb_tool():
    from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

    tool = IEDBPredictionTool(
        {
            "name": "IEDB_predict_antigen_processing",
            "fields": {"endpoint_type": "predict_processing"},
        }
    )
    tool.poll_interval = 0
    return tool


def _iedb_resp(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.text = str(payload)
    resp.raise_for_status.return_value = None
    return resp


class TestIEDBAntigenProcessing(unittest.TestCase):
    def test_parses_processing_scores_and_sorts(self):
        """Rows carry the cleavage/TAP/MHC components and sort by the
        combined score, highest first."""
        tool = _iedb_tool()

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_iedb_resp(_IEDB_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_iedb_resp(_IEDB_PROCESSING_DONE),
            ),
        ):
            result = tool.run(
                {
                    "sequence": "SLYNTVATLYCVHQRIDVKQNTLKLATGGKS",
                    "allele": "HLA-A*02:01",
                    "length": 9,
                }
            )

        self.assertEqual(result["status"], "success")
        rows = result["data"]
        self.assertEqual(len(rows), 2)
        # Sorted by combined_prediction_score descending, so the row that
        # arrived second comes first.
        first = rows[0]
        self.assertEqual(first["peptide"], "SLYNTVATL")
        self.assertEqual(first["cleavage_prediction_score"], 0.97756)
        self.assertEqual(first["tap_prediction_score"], 1.394)
        self.assertEqual(first["mhc_prediction"], 0.438)
        self.assertEqual(first["combined_prediction_score"], 0.6928)
        self.assertEqual(first["netmhcpan_ba_ic50"], 46.5)
        self.assertGreater(
            first["combined_prediction_score"],
            rows[1]["combined_prediction_score"],
        )
        self.assertEqual(result["metadata"]["allele"], "HLA-A*02:01")
        self.assertEqual(result["metadata"]["processing_method"], "netctlpan")

    def test_missing_sequence_errors(self):
        """Missing sequence returns an error envelope."""
        tool = _iedb_tool()
        result = tool.run({"allele": "HLA-A*02:01"})
        self.assertEqual(result["status"], "error")
        self.assertIn("sequence", result["error"].lower())

    def test_network_error_returns_error_not_raise(self):
        """A request timeout is caught and returned as an error."""
        import requests as _requests

        tool = _iedb_tool()
        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            side_effect=_requests.exceptions.Timeout(),
        ):
            result = tool.run({"sequence": "SLYNTVATL"})
        self.assertEqual(result["status"], "error")
        self.assertIn("timeout", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
