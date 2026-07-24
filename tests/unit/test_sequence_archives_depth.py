"""Sequence-archives depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed sequence-archive capability gaps,
all reusing existing tool classes (no new @register_tool class):

* ``geo_list_supplementary_files`` (GEORESTTool, mode=supplementary_files) —
  per-file manifest (name, size, type, modified, download_url) for a GEO
  Series via suppl/filelist.txt, or a Sample via the suppl/ directory listing.
* ``NCBI_SRA_locate_run_files`` (NCBISRATool, op=locate_run_files) — verified
  cloud (S3/GCP) location + authoritative size + md5 for an SRA run via the
  SRA Data Locator (SDL) v2 service.
* ``BioSamples_get_relationships`` (BioSamplesTool, endpoint=get_relationships)
  — the sample-to-sample provenance graph (derived from / has member / ...).
* ``BioSamples_get_facets`` (BioSamplesTool, endpoint=get_facets) — faceted
  attribute discovery (organism / status / SRA accession / external reference)
  with counts.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _json_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def _text_response(text, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# geo_list_supplementary_files  (GEORESTTool, mode=supplementary_files)
# ---------------------------------------------------------------------------


def _geo_tool():
    from tooluniverse.geo_tool import GEORESTTool

    return GEORESTTool(
        {
            "fields": {"mode": "supplementary_files"},
            "parameter": {"required": ["accession"]},
        }
    )


_GEO_FILELIST = (
    "#Archive/File\tName\tTime\tSize\tType\n"
    "Archive\tGSE42657_RAW.tar\t12/11/2015 05:01:23\t71680\tTAR\n"
    "File\tGPL8179_humanMI_V2_R0_XS0000124-MAP.txt.gz\t02/11/2009 09:03:04\t65167\tTXT\n"
)

_GSM_DIR_HTML = (
    "<html><body>"
    '<a href="/geo/samples/GSM1045nnn/GSM1045442/">Parent</a>'
    '<a href="GSM1045442_SLd2_W88_EA1024_01.CEL.gz">file</a>'
    '<a href="https://www.hhs.gov/vulnerability-disclosure-policy/index.html">policy</a>'
    "</body></html>"
)


class TestGeoSupplementaryFiles(unittest.TestCase):
    def test_bucket_derivation(self):
        """Bucket directory derivation matches the GEO FTP convention."""
        from tooluniverse.geo_tool import GEORESTTool

        self.assertEqual(GEORESTTool._geo_bucket("GSE42657"), "GSE42nnn")
        self.assertEqual(GEORESTTool._geo_bucket("GSE1000"), "GSE1nnn")
        self.assertEqual(GEORESTTool._geo_bucket("GSE100"), "GSEnnn")
        self.assertEqual(GEORESTTool._geo_bucket("GSE1"), "GSEnnn")
        self.assertEqual(GEORESTTool._geo_bucket("GSM1045442"), "GSM1045nnn")

    def test_series_parse(self):
        """A Series filelist.txt parses into structured per-file records."""
        with patch("tooluniverse.geo_tool.requests.get") as mget:
            mget.return_value = _text_response(_GEO_FILELIST)
            result = _geo_tool().run({"accession": "GSE42657"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["accession"], "GSE42657")
        self.assertEqual(data["file_count"], 2)
        f0 = data["files"][0]
        self.assertEqual(f0["name"], "GSE42657_RAW.tar")
        self.assertEqual(f0["size"], 71680)  # parsed to int
        self.assertEqual(f0["type"], "TAR")
        self.assertTrue(f0["download_url"].endswith("/GSE42657_RAW.tar"))
        # Bucket appears in URL.
        self.assertIn("GSE42nnn", f0["download_url"])

    def test_sample_dir_parse(self):
        """A Sample suppl/ HTML listing yields downloadable files only."""
        with patch("tooluniverse.geo_tool.requests.get") as mget:
            mget.return_value = _text_response(_GSM_DIR_HTML)
            result = _geo_tool().run({"accession": "GSM1045442"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["file_count"], 1)
        # External policy + parent links must be filtered out.
        self.assertEqual(
            data["files"][0]["name"], "GSM1045442_SLd2_W88_EA1024_01.CEL.gz"
        )

    def test_missing_accession(self):
        """Missing accession returns a structured error, not an exception."""
        result = _geo_tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("accession", result["error"])

    def test_bad_prefix(self):
        """A non-GSE/GSM accession is rejected with an error."""
        result = _geo_tool().run({"accession": "GPL570"})
        self.assertEqual(result["status"], "error")

    def test_http_404_error_path(self):
        """A 404 from the FTP tree returns a structured error."""
        with patch("tooluniverse.geo_tool.requests.get") as mget:
            mget.return_value = _text_response("Not Found", status_code=404)
            result = _geo_tool().run({"accession": "GSE99999999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])


# ---------------------------------------------------------------------------
# NCBI_SRA_locate_run_files  (NCBISRATool, op=locate_run_files)
# ---------------------------------------------------------------------------


def _sra_tool():
    from tooluniverse.ncbi_sra_tool import NCBISRATool

    return NCBISRATool({"fields": {}, "parameter": {}})


_SDL_OK = {
    "version": "2",
    "result": [
        {
            "bundle": "SRR390728",
            "status": 200,
            "msg": "ok",
            "files": [
                {
                    "object": "srapub|SRR390728",
                    "accession": "SRR390728",
                    "type": "sra",
                    "name": "SRR390728",
                    "size": 195174182,
                    "md5": "29a6a1a0dd0702f45225f2eb93c958b5",
                    "modificationDate": "2024-03-23T07:56:36Z",
                    "locations": [
                        {
                            "service": "s3",
                            "region": "us-east-1",
                            "link": "https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR390728/SRR390728",
                        }
                    ],
                }
            ],
        }
    ],
}

_SDL_NOT_FOUND = {
    "version": "2",
    "result": [
        {"bundle": "SRR999999999", "status": 404, "msg": "Cannot resolve accession"}
    ],
}


class TestSraLocateRunFiles(unittest.TestCase):
    def test_parse_ok(self):
        """SDL response parses into size/md5/location records."""
        with patch("tooluniverse.ncbi_sra_tool.requests.get") as mget:
            mget.return_value = _json_response(_SDL_OK)
            result = _sra_tool().run(
                {"operation": "locate_run_files", "accessions": "SRR390728"}
            )

        self.assertEqual(result["status"], "success")
        rec = result["data"][0]
        self.assertEqual(rec["accession"], "SRR390728")
        f = rec["files"][0]
        self.assertEqual(f["size"], 195174182)
        self.assertEqual(f["md5"], "29a6a1a0dd0702f45225f2eb93c958b5")
        loc = f["locations"][0]
        self.assertEqual(loc["service"], "s3")
        self.assertEqual(loc["region"], "us-east-1")
        self.assertTrue(loc["link"].startswith("https://"))

    def test_sdl_404_becomes_per_run_error(self):
        """An SDL 404 surfaces as a per-run error inside a successful call."""
        with patch("tooluniverse.ncbi_sra_tool.requests.get") as mget:
            mget.return_value = _json_response(_SDL_NOT_FOUND)
            result = _sra_tool().run(
                {"operation": "locate_run_files", "accessions": "SRR999999999"}
            )
        # Top-level call still succeeds; the per-run record carries the error.
        self.assertEqual(result["status"], "success")
        self.assertIn("error", result["data"][0])
        self.assertEqual(result["data"][0]["status_code"], 404)

    def test_invalid_accession_prefix(self):
        """A non-run accession is flagged per-run, not raised."""
        result = _sra_tool().run(
            {"operation": "locate_run_files", "accessions": "GSE12345"}
        )
        self.assertEqual(result["status"], "success")
        self.assertIn("error", result["data"][0])

    def test_missing_accessions(self):
        """Missing accessions returns a structured error."""
        result = _sra_tool().run({"operation": "locate_run_files"})
        self.assertEqual(result["status"], "error")
        self.assertIn("accessions", result["error"])

    def test_request_exception_per_run(self):
        """A network failure is captured per-run, not raised."""
        import requests as _requests

        with patch("tooluniverse.ncbi_sra_tool.requests.get") as mget:
            mget.side_effect = _requests.exceptions.ConnectionError("boom")
            result = _sra_tool().run(
                {"operation": "locate_run_files", "accessions": "SRR390728"}
            )
        self.assertEqual(result["status"], "success")
        self.assertIn("error", result["data"][0])


# ---------------------------------------------------------------------------
# BioSamples_get_relationships  (BioSamplesTool, endpoint=get_relationships)
# ---------------------------------------------------------------------------


def _biosamples_tool(endpoint_type):
    from tooluniverse.biosamples_tool import BioSamplesTool

    return BioSamplesTool({"fields": {"endpoint_type": endpoint_type}})


_BS_SAMPLE = {
    "accession": "SAMEA4451312",
    "name": "SIGi001-A-10 M001 vial 0008",
    "relationships": [
        {
            "source": "SAMEA4451312",
            "type": "derived from",
            "target": "SAMEA4451117",
        },
        {
            "source": "SAMEG315830",
            "type": "has member",
            "target": "SAMEA4451312",
        },
    ],
}


class TestBioSamplesRelationships(unittest.TestCase):
    def test_parse(self):
        """The relationships/facets array parses into structured records."""
        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.return_value = _json_response(_BS_SAMPLE)
            result = _biosamples_tool("get_relationships").run(
                {"accession": "SAMEA4451312"}
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["relationship_count"], 2)
        rels = {(r["type"], r["direction"]) for r in data["relationships"]}
        self.assertIn(("derived from", "outgoing"), rels)
        self.assertIn(("has member", "incoming"), rels)
        # outgoing edge points at the parent tissue
        outgoing = [r for r in data["relationships"] if r["direction"] == "outgoing"][0]
        self.assertEqual(outgoing["related_accession"], "SAMEA4451117")

    def test_no_relationships_field(self):
        """A sample lacking relationships yields an empty list."""
        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.return_value = _json_response({"accession": "SAMEA0", "name": "x"})
            result = _biosamples_tool("get_relationships").run({"accession": "SAMEA0"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["relationship_count"], 0)

    def test_missing_accession(self):
        """Missing accession returns a structured error, not an exception."""
        result = _biosamples_tool("get_relationships").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("accession", result["error"])

    def test_http_error_path(self):
        """A network failure returns a structured error."""
        import requests as _requests

        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.side_effect = _requests.exceptions.ConnectionError("down")
            result = _biosamples_tool("get_relationships").run(
                {"accession": "SAMEA4451312"}
            )
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# BioSamples_get_facets  (BioSamplesTool, endpoint=get_facets)
# ---------------------------------------------------------------------------


_BS_FACETS = {
    "_embedded": {
        "facets": [
            {
                "type": "attribute",
                "label": "organism",
                "count": 59585,
                "content": [
                    {"label": "Homo sapiens", "count": 24480},
                    {"label": "Mus musculus", "count": 1032},
                ],
            },
            {
                "type": "attribute",
                "label": "SRA accession",
                "count": 54248,
                "content": [],
            },
        ],
        "externalReferenceDataFacets": [
            {
                "type": "external reference data",
                "label": "ENA",
                "count": 53344,
                "content": [{"label": "SAMD00065372", "count": 1}],
            }
        ],
    }
}


class TestBioSamplesFacets(unittest.TestCase):
    def test_parse(self):
        """The relationships/facets array parses into structured records."""
        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.return_value = _json_response(_BS_FACETS)
            result = _biosamples_tool("get_facets").run(
                {"text": "cancer", "max_values": 5}
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(len(data["facets"]), 2)
        organism = data["facets"][0]
        self.assertEqual(organism["attribute"], "organism")
        self.assertEqual(organism["count"], 59585)
        self.assertEqual(organism["top_values"][0]["label"], "Homo sapiens")
        # external reference facet surfaced
        self.assertEqual(data["external_reference_data_facets"][0]["attribute"], "ENA")
        self.assertEqual(result["metadata"]["facet_count"], 2)

    def test_max_values_truncation(self):
        """max_values caps the number of top values per facet."""
        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.return_value = _json_response(_BS_FACETS)
            result = _biosamples_tool("get_facets").run(
                {"text": "cancer", "max_values": 1}
            )
        organism = result["data"]["facets"][0]
        self.assertEqual(len(organism["top_values"]), 1)

    def test_missing_text(self):
        """Missing text query returns a structured error."""
        result = _biosamples_tool("get_facets").run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("text", result["error"])

    def test_http_error_path(self):
        """A network failure returns a structured error."""
        import requests as _requests

        with patch("tooluniverse.biosamples_tool.requests.get") as mget:
            mget.side_effect = _requests.exceptions.Timeout("slow")
            result = _biosamples_tool("get_facets").run({"text": "cancer"})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
