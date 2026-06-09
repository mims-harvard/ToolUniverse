"""Microbiology / pathogen depth tools: parse + error-path coverage (mocked HTTP).

Covers five new tools that close confirmed record-level capability gaps in the
microbiology-pathogen cluster. Each new tool reuses an existing registered tool
class (no new @register_tool class, no registration changes):

* ``Pathoplexus_get_sequence_details`` (PathoplexusCountTool, mode="details") —
  per-sequence metadata rows from LAPIS /details.
* ``Pathoplexus_get_sequences_fasta`` (PathoplexusCountTool, mode="fasta") —
  unaligned/aligned nucleotide or amino-acid FASTA from LAPIS.
* ``MGnify_get_samples`` (MGnifyExpandedTool, sample/list) — sample-level
  geographic / host / environment metadata table.
* ``MGnify_list_analysis_downloads`` (MGnifyExpandedTool, analysis/downloads) —
  downloadable result-file listing for an analysis.
* ``ENAPortal_search_runs_fastq`` (ENAPortalTool, search_runs) — read_run search
  returning direct FASTQ download URLs.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Pathoplexus_get_sequence_details  (PathoplexusCountTool, mode="details")
# ---------------------------------------------------------------------------


def _patho_details_tool():
    from tooluniverse.pathoplexus_tool import PathoplexusCountTool

    return PathoplexusCountTool(
        {
            "name": "Pathoplexus_get_sequence_details",
            "fields": {"timeout": 30, "mode": "details"},
        }
    )


_PATHO_DETAILS_FAKE = {
    "data": [
        {
            "accession": "PP_00005PG",
            "geoLocCountry": None,
            "sampleCollectionDate": None,
            "lineage": "1A",
        },
        {
            "accession": "PP_00009XQ",
            "geoLocCountry": "USA",
            "sampleCollectionDate": "2021-08-01",
            "lineage": "2",
        },
    ],
    "info": {"lapisVersion": "0.8.0"},
}


class TestPathoplexusSequenceDetails(unittest.TestCase):
    def test_parses_per_sequence_rows(self):
        """Per-sequence /details rows are parsed and the fields list forwarded."""
        tool = _patho_details_tool()
        resp = MagicMock()
        resp.json.return_value = _PATHO_DETAILS_FAKE
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.pathoplexus_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run(
                {
                    "organism": "west-nile",
                    "fields": "accession,geoLocCountry,sampleCollectionDate,lineage",
                    "limit": 2,
                }
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["accession"], "PP_00005PG")
        self.assertEqual(result["data"][1]["lineage"], "2")
        self.assertEqual(result["metadata"]["returned"], 2)
        # /details endpoint hit with the requested fields as a list
        _, kwargs = get.call_args
        self.assertIn("/west-nile/sample/details", get.call_args[0][0])
        self.assertEqual(
            kwargs["params"]["fields"],
            ["accession", "geoLocCountry", "sampleCollectionDate", "lineage"],
        )
        self.assertEqual(kwargs["params"]["limit"], 2)

    def test_missing_organism_returns_error(self):
        """A missing organism yields an error envelope, never an exception."""
        tool = _patho_details_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("organism", result["error"])

    def test_http_error_returns_error_envelope(self):
        """An HTTP error from the API is converted to an error envelope."""
        import requests as _rq

        tool = _patho_details_tool()
        err_resp = MagicMock()
        err_resp.status_code = 400
        http_err = _rq.exceptions.HTTPError(response=err_resp)
        with patch("tooluniverse.pathoplexus_tool.requests.get", side_effect=http_err):
            result = tool.run({"organism": "west-nile"})
        self.assertEqual(result["status"], "error")
        self.assertIn("400", result["error"])


# ---------------------------------------------------------------------------
# Pathoplexus_get_sequences_fasta  (PathoplexusCountTool, mode="fasta")
# ---------------------------------------------------------------------------


def _patho_fasta_tool():
    from tooluniverse.pathoplexus_tool import PathoplexusCountTool

    return PathoplexusCountTool(
        {
            "name": "Pathoplexus_get_sequences_fasta",
            "fields": {"timeout": 30, "mode": "fasta"},
        }
    )


_FASTA_TEXT = ">PP_00005PG.1\nATGAGGTCCATAGCTCTCACG\n"


class TestPathoplexusSequencesFasta(unittest.TestCase):
    def test_parses_fasta_payload(self):
        """Unaligned nucleotide FASTA is returned with a record count."""
        tool = _patho_fasta_tool()
        resp = MagicMock()
        resp.text = _FASTA_TEXT
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.pathoplexus_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run({"organism": "west-nile", "limit": 1})
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["data"]["fasta"].startswith(">PP_00005PG.1"))
        self.assertEqual(result["data"]["num_records"], 1)
        self.assertEqual(result["metadata"]["endpoint"], "unalignedNucleotideSequences")
        # FASTA dataFormat requested, default unaligned nucleotide endpoint hit
        url = get.call_args[0][0]
        _, kwargs = get.call_args
        self.assertIn("/west-nile/sample/unalignedNucleotideSequences", url)
        self.assertEqual(kwargs["params"]["dataFormat"], "FASTA")
        self.assertEqual(kwargs["headers"]["Accept"], "text/x-fasta")

    def test_amino_acid_aligned_endpoint_selected(self):
        """sequence_type=aminoAcid + aligned selects the aligned-AA endpoint."""
        tool = _patho_fasta_tool()
        resp = MagicMock()
        resp.text = ">PP_x\nMKT\n"
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.pathoplexus_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run(
                {"organism": "mpox", "sequence_type": "aminoAcid", "aligned": True}
            )
        self.assertEqual(result["status"], "success")
        self.assertIn("/mpox/sample/alignedAminoAcidSequences", get.call_args[0][0])

    def test_empty_fasta_returns_error(self):
        """An empty FASTA body yields an error envelope."""
        tool = _patho_fasta_tool()
        resp = MagicMock()
        resp.text = ""
        resp.raise_for_status.return_value = None
        with patch("tooluniverse.pathoplexus_tool.requests.get", return_value=resp):
            result = tool.run({"organism": "west-nile"})
        self.assertEqual(result["status"], "error")
        self.assertIn("no FASTA", result["error"])

    def test_missing_organism_returns_error(self):
        """A missing organism yields an error envelope, never an exception."""
        tool = _patho_fasta_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("organism", result["error"])


# ---------------------------------------------------------------------------
# MGnify_get_samples  (MGnifyExpandedTool, sample/list)
# ---------------------------------------------------------------------------


def _mgnify_samples_tool():
    from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool

    return MGnifyExpandedTool(
        {
            "name": "MGnify_get_samples",
            "fields": {"endpoint_type": "sample", "query_mode": "list"},
        }
    )


_MGNIFY_SAMPLES_FAKE = {
    "data": [
        {
            "id": "SRS10016989",
            "attributes": {
                "biosample": "SAMN21216536",
                "sample-name": "GutSample",
                "latitude": 51.5,
                "longitude": -0.12,
                "geo-loc-name": "United Kingdom",
                "collection-date": "2020-01-15",
                "host-tax-id": 9606,
                "species": "Homo sapiens",
                "environment-biome": "human gut",
                "environment-feature": "gut",
                "environment-material": "feces",
                "last-update": "2026-04-24T07:54:59",
            },
        }
    ],
    "meta": {"pagination": {"count": 435812, "page": 1, "pages": 217906}},
}

_MGNIFY_SINGLE_SAMPLE_FAKE = {
    "data": {
        "id": "SRS10016989",
        "attributes": {
            "biosample": "SAMN21216536",
            "geo-loc-name": "United Kingdom",
            "host-tax-id": 9606,
        },
    }
}


class TestMGnifySamples(unittest.TestCase):
    def test_parses_sample_list_with_provenance(self):
        """Sample rows expose lat/lon/geo/host/environment provenance."""
        tool = _mgnify_samples_tool()
        resp = MagicMock()
        resp.json.return_value = _MGNIFY_SAMPLES_FAKE
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.mgnify_expanded_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run({"page_size": 2})
        self.assertEqual(result["status"], "success")
        row = result["data"][0]
        self.assertEqual(row["sample_accession"], "SRS10016989")
        self.assertEqual(row["biosample"], "SAMN21216536")
        self.assertEqual(row["latitude"], 51.5)
        self.assertEqual(row["geo_loc_name"], "United Kingdom")
        self.assertEqual(row["environment_material"], "feces")
        self.assertEqual(result["metadata"]["total_results"], 435812)
        self.assertIn("/samples", get.call_args[0][0])

    def test_single_sample_detail_path(self):
        """A sample_accession routes to the single-sample detail endpoint."""
        tool = _mgnify_samples_tool()
        resp = MagicMock()
        resp.json.return_value = _MGNIFY_SINGLE_SAMPLE_FAKE
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.mgnify_expanded_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run({"sample_accession": "SRS10016989"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["sample_accession"], "SRS10016989")
        self.assertEqual(result["metadata"]["endpoint"], "samples/detail")
        self.assertIn("/samples/SRS10016989", get.call_args[0][0])

    def test_http_error_returns_error_envelope(self):
        """An HTTP error from the API is converted to an error envelope."""
        import requests as _rq

        tool = _mgnify_samples_tool()
        err_resp = MagicMock()
        err_resp.status_code = 404
        http_err = _rq.exceptions.HTTPError(response=err_resp)
        with patch(
            "tooluniverse.mgnify_expanded_tool.requests.get", side_effect=http_err
        ):
            result = tool.run({"sample_accession": "BOGUS"})
        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])


# ---------------------------------------------------------------------------
# MGnify_list_analysis_downloads  (MGnifyExpandedTool, analysis/downloads)
# ---------------------------------------------------------------------------


def _mgnify_downloads_tool():
    from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool

    return MGnifyExpandedTool(
        {
            "name": "MGnify_list_analysis_downloads",
            "fields": {"endpoint_type": "analysis", "query_mode": "downloads"},
        }
    )


_MGNIFY_DOWNLOADS_FAKE = {
    "data": [
        {
            "id": "ERZ2272727_FASTA_predicted_cds.faa.gz",
            "attributes": {
                "alias": "ERZ2272727_FASTA_predicted_cds.faa.gz",
                "description": {
                    "label": "Predicted CDS (aa)",
                    "description": "Predicted coding sequences",
                },
                "file-format": {"name": "FASTA", "compression": True},
                "group-type": "Sequence data",
            },
            "links": {
                "self": "https://www.ebi.ac.uk/metagenomics/api/v1/analyses/MGYA00585482/file/ERZ2272727_FASTA_predicted_cds.faa.gz?format=json"
            },
        },
        {
            "id": "ERZ2272727_FASTA_emapper.annotations.tsv.gz",
            "attributes": {
                "alias": "ERZ2272727_FASTA_emapper.annotations.tsv.gz",
                "description": {"label": "eggNOG annotation", "description": "eggNOG"},
                "file-format": {"name": "TSV", "compression": True},
                "group-type": "Functional analysis",
            },
            "links": {"self": "https://example/eggnog"},
        },
    ],
    "meta": {"pagination": {"count": 25}},
}


class TestMGnifyAnalysisDownloads(unittest.TestCase):
    def test_parses_download_entries(self):
        """Analysis download entries expose label, format and download URL."""
        tool = _mgnify_downloads_tool()
        resp = MagicMock()
        resp.json.return_value = _MGNIFY_DOWNLOADS_FAKE
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.mgnify_expanded_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run({"analysis_id": "MGYA00585482"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        first = result["data"][0]
        self.assertEqual(first["file_id"], "ERZ2272727_FASTA_predicted_cds.faa.gz")
        self.assertEqual(first["label"], "Predicted CDS (aa)")
        self.assertEqual(first["file_format"], "FASTA")
        self.assertTrue(first["compression"])
        self.assertTrue(
            first["download_url"].endswith("predicted_cds.faa.gz?format=json")
        )
        self.assertEqual(result["metadata"]["total_results"], 25)
        self.assertIn("/analyses/MGYA00585482/downloads", get.call_args[0][0])

    def test_missing_analysis_id_returns_error(self):
        """A missing analysis_id yields an error envelope."""
        tool = _mgnify_downloads_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("analysis_id", result["error"])

    def test_timeout_returns_error_envelope(self):
        """A request timeout is converted to an error envelope."""
        import requests as _rq

        tool = _mgnify_downloads_tool()
        with patch(
            "tooluniverse.mgnify_expanded_tool.requests.get",
            side_effect=_rq.exceptions.Timeout(),
        ):
            result = tool.run({"analysis_id": "MGYA00585482"})
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"])


# ---------------------------------------------------------------------------
# ENAPortal_search_runs_fastq  (ENAPortalTool, search_runs)
# ---------------------------------------------------------------------------


def _ena_runs_tool():
    from tooluniverse.ena_portal_tool import ENAPortalTool

    return ENAPortalTool(
        {
            "name": "ENAPortal_search_runs_fastq",
            "fields": {"endpoint_type": "search_runs"},
        }
    )


_ENA_RUNS_FAKE = [
    {
        "run_accession": "DRR015575",
        "fastq_ftp": "ftp.sra.ebi.ac.uk/vol1/fastq/DRR015/DRR015575/DRR015575_1.fastq.gz;ftp.sra.ebi.ac.uk/vol1/fastq/DRR015/DRR015575/DRR015575_2.fastq.gz",
        "submitted_ftp": "",
        "sra_ftp": "",
        "library_strategy": "WGS",
        "instrument_platform": "ILLUMINA",
    },
    {
        "run_accession": "DRR015576",
        "fastq_ftp": "ftp.sra.ebi.ac.uk/vol1/fastq/DRR015/DRR015576/DRR015576_1.fastq.gz",
        "submitted_ftp": "",
        "sra_ftp": "",
        "library_strategy": "WGS",
        "instrument_platform": "ILLUMINA",
    },
]


class TestENAPortalSearchRuns(unittest.TestCase):
    def test_parses_runs_with_fastq_urls(self):
        """read_run search returns runs with FASTQ FTP URLs."""
        tool = _ena_runs_tool()
        resp = MagicMock()
        resp.json.return_value = _ENA_RUNS_FAKE
        resp.raise_for_status.return_value = None
        with patch(
            "tooluniverse.ena_portal_tool.requests.get", return_value=resp
        ) as get:
            result = tool.run({"query": "tax_eq(1280)", "limit": 3})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["run_accession"], "DRR015575")
        self.assertIn("_1.fastq.gz", result["data"][0]["fastq_ftp"])
        self.assertEqual(result["metadata"]["endpoint"], "search/read_run")
        # read_run result domain requested, query passed through unchanged
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["result"], "read_run")
        self.assertEqual(kwargs["params"]["query"], "tax_eq(1280)")

    def test_missing_query_returns_error(self):
        """A missing query yields an error envelope."""
        tool = _ena_runs_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("query", result["error"])

    def test_http_error_returns_error_envelope(self):
        """An HTTP error from the API is converted to an error envelope."""
        import requests as _rq

        tool = _ena_runs_tool()
        err_resp = MagicMock()
        err_resp.status_code = 400
        http_err = _rq.exceptions.HTTPError(response=err_resp)
        with patch("tooluniverse.ena_portal_tool.requests.get", side_effect=http_err):
            result = tool.run({"query": "tax_eq(1280)"})
        self.assertEqual(result["status"], "error")
        self.assertIn("400", result["error"])


if __name__ == "__main__":
    unittest.main()
