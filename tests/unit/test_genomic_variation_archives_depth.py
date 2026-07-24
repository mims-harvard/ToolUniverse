"""Genomic-variation-archives depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed capability gaps in the
genomic-variation-archives cluster (NCBI Variation Services + EVA accessioning):

* ``NCBIVariation_alfa_frequencies_by_rsid`` (NCBIVariationTool / alfa_frequencies)
  — ALFA per-ancestry allele frequencies for a dbSNP rsID, with SAMN biosample
  ids resolved to ancestry names. Distinct from dbSNP's single aggregate
  global MAF per study.
* ``NCBIVariation_spdi_to_rsids`` (NCBIVariationTool / spdi_to_rsids) — reverse
  SPDI -> co-located dbSNP rsID(s) lookup.
* ``NCBIVariation_vcf_to_spdi`` (NCBIVariationTool / vcf_to_spdi) — raw VCF
  (chrom, pos, ref, alt) -> normalized contextual SPDI.
* ``EVA_get_clustered_variant_by_rs`` (BaseRESTTool) — EVA accessioning service
  resolving a clustered-variant RS accession to its canonical
  assembly/contig/position record.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _ncbi_tool(endpoint_type):
    from tooluniverse.ncbi_variation_tool import NCBIVariationTool

    return NCBIVariationTool(
        {
            "name": f"NCBIVariation_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
        }
    )


def _mock_resp(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# NCBIVariation_alfa_frequencies_by_rsid
# ---------------------------------------------------------------------------

_ALFA_FREQ_FAKE = {
    "build_id": "20260205170148",
    "results": {
        "1@44908683": {
            "ref": "T",
            "counts": {
                "PRJNA507278": {
                    "allele_counts": {
                        "SAMN10492695": {"C": 8521, "T": 264725},
                        "SAMN10492703": {"C": 1971, "T": 35487},
                    }
                }
            },
        }
    },
}

_ALFA_META_FAKE = [
    {
        "id": "dbGaP_PopFreq.1",
        "populations": [
            {
                "name": "Total",
                "biosample_id": "SAMN10492705",
                "subs": [
                    {"name": "European", "biosample_id": "SAMN10492695"},
                    {
                        "name": "African",
                        "biosample_id": "SAMN10492703",
                        "subs": [
                            {
                                "name": "African American",
                                "biosample_id": "SAMN10492698",
                            }
                        ],
                    },
                ],
            }
        ],
    }
]


class TestAlfaFrequencies(unittest.TestCase):
    def test_parses_per_ancestry_counts_and_frequencies(self):
        """SAMN ids resolve to ancestry names; frequencies sum from counts."""
        tool = _ncbi_tool("alfa_frequencies")

        def fake_get(url, *args, **kwargs):
            if url.endswith("/metadata/frequency"):
                return _mock_resp(json_data=_ALFA_META_FAKE)
            return _mock_resp(json_data=_ALFA_FREQ_FAKE)

        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get", side_effect=fake_get
        ):
            result = tool.run({"rsid": "rs429358"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["refsnp_id"], "429358")
        self.assertEqual(data["build_id"], "20260205170148")
        pops = data["positions"][0]["studies"][0]["populations"]
        by_name = {p["population"]: p for p in pops}
        # SAMN biosample ids resolved to ancestry labels via metadata
        self.assertIn("European", by_name)
        self.assertIn("African", by_name)
        eur = by_name["European"]
        self.assertEqual(eur["total_alleles"], 8521 + 264725)
        # Frequency computed from counts / total
        self.assertAlmostEqual(
            eur["allele_frequencies"]["C"], 8521 / (8521 + 264725)
        )

    def test_falls_back_to_bundled_pop_map_when_metadata_fails(self):
        """If metadata is unreachable, bundled SAMN->ancestry map is used."""
        tool = _ncbi_tool("alfa_frequencies")

        def fake_get(url, *args, **kwargs):
            if url.endswith("/metadata/frequency"):
                raise Exception("metadata down")
            return _mock_resp(json_data=_ALFA_FREQ_FAKE)

        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get", side_effect=fake_get
        ):
            result = tool.run({"rsid": "429358"})

        self.assertEqual(result["status"], "success")
        pops = result["data"]["positions"][0]["studies"][0]["populations"]
        names = {p["population"] for p in pops}
        self.assertIn("European", names)
        self.assertIn("African", names)

    def test_missing_rsid_is_error(self):
        tool = _ncbi_tool("alfa_frequencies")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("rsid", result["error"])

    def test_invalid_rsid_is_error(self):
        tool = _ncbi_tool("alfa_frequencies")
        result = tool.run({"rsid": "notanrsid"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid rsID", result["error"])

    def test_empty_results_is_error(self):
        """No ALFA aggregation for the variant -> clear error, never a raise."""
        tool = _ncbi_tool("alfa_frequencies")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(json_data={"build_id": "x", "results": {}}),
        ):
            result = tool.run({"rsid": "rs1"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No ALFA frequency data", result["error"])

    def test_http_error_returns_error(self):
        tool = _ncbi_tool("alfa_frequencies")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(status_code=404, text="not found"),
        ):
            result = tool.run({"rsid": "rs429358"})
        self.assertEqual(result["status"], "error")
        self.assertIn("404", result["error"])


# ---------------------------------------------------------------------------
# NCBIVariation_spdi_to_rsids
# ---------------------------------------------------------------------------


class TestSpdiToRsids(unittest.TestCase):
    def test_parses_rsids(self):
        """SPDI -> co-located rsID list is parsed with a count."""
        tool = _ncbi_tool("spdi_to_rsids")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(json_data={"data": {"rsids": [429358]}}),
        ):
            result = tool.run({"spdi": "NC_000019.10:44908683:T:C"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["rsids"], [429358])
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["spdi"], "NC_000019.10:44908683:T:C")

    def test_missing_spdi_is_error(self):
        """Missing spdi argument returns a clean error, never a raise."""
        tool = _ncbi_tool("spdi_to_rsids")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("spdi", result["error"])

    def test_http_error_returns_error(self):
        """Non-200 response is surfaced as a status=error envelope."""
        tool = _ncbi_tool("spdi_to_rsids")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(status_code=400, text="bad spdi"),
        ):
            result = tool.run({"spdi": "garbage"})
        self.assertEqual(result["status"], "error")
        self.assertIn("400", result["error"])


# ---------------------------------------------------------------------------
# NCBIVariation_vcf_to_spdi
# ---------------------------------------------------------------------------

_VCF_SPDI_FAKE = {
    "data": {
        "spdis": [
            {
                "seq_id": "NC_000007.14",
                "position": 140753335,
                "deleted_sequence": "A",
                "inserted_sequence": "T",
            }
        ]
    }
}


class TestVcfToSpdi(unittest.TestCase):
    def test_parses_contextual_spdi(self):
        """VCF four-field response parses into a normalized contextual SPDI."""
        tool = _ncbi_tool("vcf_to_spdi")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(json_data=_VCF_SPDI_FAKE),
        ):
            result = tool.run(
                {
                    "chrom": "NC_000007.14",
                    "pos": "140753336",
                    "ref": "A",
                    "alt": "T",
                }
            )
        self.assertEqual(result["status"], "success")
        spdi = result["data"]["spdis"][0]
        self.assertEqual(spdi["seq_id"], "NC_000007.14")
        self.assertEqual(spdi["position"], 140753335)
        self.assertEqual(result["data"]["count"], 1)

    def test_url_uses_vcf_four_fields(self):
        """The four VCF fields are placed into the contextuals path."""
        tool = _ncbi_tool("vcf_to_spdi")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(json_data=_VCF_SPDI_FAKE),
        ) as get:
            tool.run(
                {
                    "chrom": "NC_000007.14",
                    "pos": "140753336",
                    "ref": "A",
                    "alt": "T",
                }
            )
        called_url = get.call_args[0][0]
        self.assertIn(
            "/vcf/NC_000007.14/140753336/A/T/contextuals", called_url
        )

    def test_missing_fields_is_error(self):
        """Omitted ref/alt are reported as missing required parameters."""
        tool = _ncbi_tool("vcf_to_spdi")
        result = tool.run({"chrom": "NC_000007.14", "pos": "1"})
        self.assertEqual(result["status"], "error")
        self.assertIn("ref", result["error"])
        self.assertIn("alt", result["error"])

    def test_http_error_returns_error(self):
        """Non-200 response is surfaced as a status=error envelope."""
        tool = _ncbi_tool("vcf_to_spdi")
        with patch(
            "tooluniverse.ncbi_variation_tool.requests.get",
            return_value=_mock_resp(status_code=500, text="server error"),
        ):
            result = tool.run(
                {"chrom": "NC_x", "pos": "1", "ref": "A", "alt": "T"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("500", result["error"])


# ---------------------------------------------------------------------------
# EVA_get_clustered_variant_by_rs (BaseRESTTool)
# ---------------------------------------------------------------------------

_EVA_CLUSTERED_FAKE = [
    {
        "accession": 429358,
        "version": 1,
        "data": {
            "assemblyAccession": "GCA_000001405.27",
            "taxonomyAccession": 9606,
            "contig": "CM000681.2",
            "start": 44908684,
            "type": "SNV",
        },
    }
]


def _eva_tool():
    from tooluniverse.base_rest_tool import BaseRESTTool

    config = {
        "name": "EVA_get_clustered_variant_by_rs",
        "fields": {
            "endpoint": "https://www.ebi.ac.uk/eva/webservices/identifiers/v1/clustered-variants/{accession}"
        },
        "parameter": {
            "type": "object",
            "properties": {"accession": {"type": "string"}},
            "required": ["accession"],
        },
    }
    return BaseRESTTool(config)


class TestEvaClusteredVariant(unittest.TestCase):
    def test_parses_accessioning_record(self):
        """EVA accessioning record resolves assembly/contig/position fields."""
        tool = _eva_tool()
        resp = _mock_resp(json_data=_EVA_CLUSTERED_FAKE)
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ):
            result = tool.run({"accession": "429358"})
        self.assertEqual(result["status"], "success")
        rec = result["data"][0]
        self.assertEqual(rec["accession"], 429358)
        self.assertEqual(rec["data"]["assemblyAccession"], "GCA_000001405.27")
        self.assertEqual(rec["data"]["contig"], "CM000681.2")
        self.assertEqual(rec["data"]["start"], 44908684)
        self.assertEqual(result["count"], 1)

    def test_accession_substituted_into_path(self):
        """The RS accession is substituted into the clustered-variants path."""
        tool = _eva_tool()
        resp = _mock_resp(json_data=_EVA_CLUSTERED_FAKE)
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ) as req:
            tool.run({"accession": "429358"})
        called_url = req.call_args[0][2]
        self.assertTrue(called_url.endswith("/clustered-variants/429358"))

    def test_http_error_returns_error(self):
        """A 404 from the accessioning service yields a status=error envelope."""
        tool = _eva_tool()
        resp = _mock_resp(status_code=404, text="not found")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ):
            result = tool.run({"accession": "0"})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
