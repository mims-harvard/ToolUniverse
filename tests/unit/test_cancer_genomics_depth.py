"""Cancer-genomics depth tools: parse + error-path coverage (mocked HTTP).

Covers three new tools that close confirmed per-cancer-type capability gaps:

* ``GDC_get_mutation_frequency_by_project`` (GDCMutationFreqByProjectTool) —
  per-project mutated-case-count / total-case-count from the GDC
  ``/analysis/mutated_cases_count_by_project`` endpoint.
* ``cBioPortal_get_copy_number_alterations`` (CBioPortalRESTTool) — discrete
  GISTIC copy-number calls per sample for a gene in a study.
* ``Progenetix_get_cnv_frequencies`` (ProgenetixTool) — genome-wide aggregate
  CNV gain/loss frequency profile per cancer type.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# GDC_get_mutation_frequency_by_project
# ---------------------------------------------------------------------------


def _gdc_tool():
    from tooluniverse.gdc_tool import GDCMutationFreqByProjectTool

    return GDCMutationFreqByProjectTool(
        {"settings": {"base_url": "https://api.gdc.cancer.gov", "timeout": 30}}
    )


_GDC_FAKE = {
    "aggregations": {
        "projects": {
            "buckets": [
                {
                    "key": "CPTAC-3",
                    "doc_count": 510,
                    "case_summary": {
                        "doc_count": 3521,
                        "case_with_ssm": {"doc_count": 510},
                    },
                },
                {
                    "key": "TINY-PROJ",
                    "doc_count": 6,
                    "case_summary": {
                        "doc_count": 10,
                        "case_with_ssm": {"doc_count": 6},
                    },
                },
            ]
        }
    }
}


class TestGDCMutationFreqByProject(unittest.TestCase):
    def test_parses_numerator_and_denominator_per_project(self):
        """Per-project numerator/denominator are preserved and frequency computed."""
        tool = _gdc_tool()
        with patch("tooluniverse.gdc_tool._http_get") as http:
            http.return_value = _GDC_FAKE
            result = tool.run({"gene_symbol": "KRAS"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["gene"], "KRAS")
        self.assertEqual(data["project_count"], 2)
        # Numerator and denominator preserved per project.
        by_id = {p["project_id"]: p for p in data["projects"]}
        self.assertEqual(by_id["CPTAC-3"]["mutated_case_count"], 510)
        self.assertEqual(by_id["CPTAC-3"]["total_case_count"], 3521)
        # frequency = mutated / total.
        self.assertAlmostEqual(by_id["CPTAC-3"]["frequency"], round(510 / 3521, 4))
        # Aggregate totals.
        self.assertEqual(data["total_mutated_cases"], 516)
        self.assertEqual(data["total_cases"], 3531)

    def test_results_sorted_by_frequency_descending(self):
        """Projects are ranked by mutation frequency, highest first."""
        tool = _gdc_tool()
        with patch("tooluniverse.gdc_tool._http_get") as http:
            http.return_value = _GDC_FAKE
            result = tool.run({"gene": "KRAS"})  # exercise the `gene` alias too
        projects = result["data"]["projects"]
        # TINY-PROJ (6/10 = 0.6) ranks above CPTAC-3 (510/3521 ~= 0.145).
        self.assertEqual(projects[0]["project_id"], "TINY-PROJ")

    def test_missing_gene_returns_error(self):
        """A missing gene symbol yields a structured error, not a raise."""
        tool = _gdc_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene_symbol", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """An HTTP failure is caught and returned as a structured error."""
        tool = _gdc_tool()
        with patch("tooluniverse.gdc_tool._http_get") as http:
            http.side_effect = RuntimeError("boom")
            result = tool.run({"gene_symbol": "KRAS"})
        self.assertEqual(result["status"], "error")
        self.assertIn("boom", result["error"])


# ---------------------------------------------------------------------------
# cBioPortal_get_copy_number_alterations
# ---------------------------------------------------------------------------


def _cbio_tool():
    from tooluniverse.cbioportal_tool import CBioPortalRESTTool

    return CBioPortalRESTTool(
        {
            "name": "cBioPortal_get_copy_number_alterations",
            "type": "CBioPortalRESTTool",
            "fields": {
                "endpoint": "https://www.cbioportal.org/api/molecular-profiles/{study_id}_gistic/discrete-copy-number/fetch",
                "method": "POST",
            },
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _make_response(json_payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_payload
    resp.raise_for_status = MagicMock()
    return resp


class TestCBioPortalCNA(unittest.TestCase):
    def test_parses_discrete_cna_and_counts(self):
        """Discrete GISTIC CNA calls are parsed with per-category counts."""
        tool = _cbio_tool()

        profiles = [
            {
                "molecularProfileId": "brca_tcga_pan_can_atlas_2018_gistic",
                "molecularAlterationType": "COPY_NUMBER_ALTERATION",
                "datatype": "DISCRETE",
            }
        ]
        genes = [{"entrezGeneId": 2064, "hugoGeneSymbol": "ERBB2"}]
        cna_data = [
            {"sampleId": "S1", "entrezGeneId": 2064, "alteration": 2},
            {"sampleId": "S2", "entrezGeneId": 2064, "alteration": 2},
            {"sampleId": "S3", "entrezGeneId": 2064, "alteration": -2},
        ]

        def fake_get(url, timeout=None):
            if "molecular-profiles" in url:
                return _make_response(profiles)
            if "genes" in url:
                return _make_response(genes)
            return _make_response([])

        with patch.object(tool.session, "get", side_effect=fake_get), patch.object(
            tool.session, "post", return_value=_make_response(cna_data)
        ) as post:
            result = tool.run(
                {
                    "study_id": "brca_tcga_pan_can_atlas_2018",
                    "gene_list": "ERBB2",
                    "alteration_type": "AMP",
                }
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["entrez_gene_ids"], [2064])
        self.assertEqual(
            result["molecular_profile_id"], "brca_tcga_pan_can_atlas_2018_gistic"
        )
        self.assertEqual(result["alteration_type"], "AMP")
        # Alteration values mapped to readable categories.
        self.assertEqual(result["alteration_counts"]["amplification"], 2)
        self.assertEqual(result["alteration_counts"]["deep_deletion"], 1)
        # The POST URL carries the event-type filter and projection.
        post_url = post.call_args[0][0]
        self.assertIn("discreteCopyNumberEventType=AMP", post_url)
        self.assertIn("projection=SUMMARY", post_url)

    def test_unresolvable_gene_returns_error(self):
        """An unresolvable gene symbol yields a structured error."""
        tool = _cbio_tool()

        profiles = [
            {
                "molecularProfileId": "brca_tcga_pan_can_atlas_2018_gistic",
                "molecularAlterationType": "COPY_NUMBER_ALTERATION",
                "datatype": "DISCRETE",
            }
        ]

        def fake_get(url, timeout=None):
            if "molecular-profiles" in url:
                return _make_response(profiles)
            # gene keyword search returns no hits.
            return _make_response([])

        with patch.object(tool.session, "get", side_effect=fake_get):
            result = tool.run(
                {
                    "study_id": "brca_tcga_pan_can_atlas_2018",
                    "gene_list": "NOTAGENE",
                    "alteration_type": "AMP",
                }
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("Entrez", result["error"])

    def test_missing_study_returns_error(self):
        """A missing study_id yields a structured error."""
        tool = _cbio_tool()
        result = tool.run({"gene_list": "ERBB2"})
        self.assertEqual(result["status"], "error")
        self.assertIn("study_id", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """An HTTP failure is caught and returned as a structured error."""
        tool = _cbio_tool()
        with patch.object(tool.session, "get", side_effect=RuntimeError("network down")):
            result = tool.run(
                {"study_id": "brca_tcga_pan_can_atlas_2018", "gene_list": "ERBB2"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("network down", result["error"])


# ---------------------------------------------------------------------------
# Progenetix_get_cnv_frequencies
# ---------------------------------------------------------------------------


def _progenetix_tool():
    from tooluniverse.progenetix_tool import ProgenetixTool

    return ProgenetixTool(
        {
            "name": "Progenetix_get_cnv_frequencies",
            "type": "ProgenetixTool",
            "fields": {"endpoint": "interval_frequencies"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


_PROGENETIX_FAKE = {
    "response": {
        "results": [
            {
                "datasetId": "progenetix",
                "groupId": "NCIT:C3058",
                "label": "Glioblastoma",
                "sampleCount": 7257,
                "intervalFrequencies": [
                    {
                        "no": 1,
                        "referenceName": "1",
                        "cytobands": "1p36.33",
                        "start": 0,
                        "end": 400000,
                        "size": 400000,
                        "gainFrequency": 4.258,
                        "lossFrequency": 5.278,
                        "gainHlfrequency": 0.721,
                        "lossHlfrequency": 0.498,
                    },
                    {
                        "no": 2,
                        "referenceName": "1",
                        "cytobands": "1p36.32",
                        "gainFrequency": 4.0,
                        "lossFrequency": 5.0,
                    },
                ],
            }
        ]
    }
}


class TestProgenetixCNVFrequencies(unittest.TestCase):
    def test_parses_interval_frequency_profile(self):
        """Interval gain/loss frequency profile is parsed per cancer type."""
        tool = _progenetix_tool()
        with patch("tooluniverse.progenetix_tool.requests") as rq:
            rq.get.return_value = _make_response(_PROGENETIX_FAKE)
            result = tool.run({"filters": "NCIT:C3058"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["label"], "Glioblastoma")
        self.assertEqual(data["sample_count"], 7257)
        self.assertEqual(data["interval_count"], 2)
        first = data["intervals"][0]
        self.assertEqual(first["cytobands"], "1p36.33")
        self.assertEqual(first["gain_frequency"], 4.258)
        self.assertEqual(first["loss_frequency"], 5.278)
        # Request targeted the services intervalFrequencies endpoint with filters=.
        called_url = rq.get.call_args[0][0]
        self.assertIn("intervalFrequencies", called_url)
        sent_params = rq.get.call_args.kwargs.get("params", {})
        self.assertEqual(sent_params.get("filters"), "NCIT:C3058")

    def test_max_intervals_caps_returned_bins(self):
        """max_intervals caps returned bins while preserving the full count."""
        tool = _progenetix_tool()
        with patch("tooluniverse.progenetix_tool.requests") as rq:
            rq.get.return_value = _make_response(_PROGENETIX_FAKE)
            result = tool.run({"filters": "NCIT:C3058", "max_intervals": 1})
        data = result["data"]
        # Full count preserved, but only one bin returned.
        self.assertEqual(data["interval_count"], 2)
        self.assertEqual(data["returned_interval_count"], 1)
        self.assertEqual(len(data["intervals"]), 1)

    def test_missing_filters_returns_error(self):
        """A missing filters code yields a structured error."""
        tool = _progenetix_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("filters", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """An HTTP failure is caught and returned as a structured error."""
        tool = _progenetix_tool()
        with patch("tooluniverse.progenetix_tool.requests") as rq:
            # Real requests exceptions are exposed via the patched module too.
            import requests as real_requests

            rq.exceptions = real_requests.exceptions
            rq.get.side_effect = real_requests.exceptions.ConnectionError("no route")
            result = tool.run({"filters": "NCIT:C3058"})
        self.assertEqual(result["status"], "error")
        self.assertIn("connect", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
