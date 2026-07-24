"""Depth tests for the gwas-population cluster (mocked HTTP, no live calls).

Covers the two tools added for confirmed coverage gaps, both of which reuse an
existing registered tool class:

  - PGSCatalog_get_performance_metrics  (PGSCatalogTool, operation
    'get_performance_metrics') -> published PGS validation metrics
    (OR/HR/AUROC/C-index/R2 with 95% CIs) + evaluation cohort ancestry/size.
  - EnsemblLD_get_ld_region  (EnsemblLDTool, endpoint_type 'ld_region') ->
    region-wide pairwise r2/D' LD matrix for a 1000 Genomes population.

Each tool gets a parse test and an error-path test.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _resp(status_code, body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# PGSCatalog_get_performance_metrics
# ---------------------------------------------------------------------------

# Shape mirrors a real /rest/performance/search?pgs_id=PGS000001 record.
_PERF = {
    "id": "PPM000001",
    "associated_pgs_id": "PGS000001",
    "phenotyping_reported": "Breast cancer",
    "covariates": "age, genetic PCs",
    "performance_comments": None,
    "publication": {
        "firstauthor": "Mavaddat N",
        "journal": "Am J Hum Genet",
        "date_publication": "2018-12-13",
        "PMID": 30554720,
        "doi": "10.1016/j.ajhg.2018.11.002",
    },
    "sampleset": {
        "id": "PSS000001",
        "samples": [
            {
                "sample_number": 67054,
                "sample_cases": 33673,
                "sample_controls": 33381,
                "ancestry_broad": "European",
                "ancestry_free": None,
                "ancestry_country": "UK, USA",
                "phenotyping_free": "All breast cancer",
                "cohorts": [
                    {"name_short": "ABCFS", "name_full": "Australian BCFS"},
                    {"name_short": "MCCS", "name_full": "Melbourne CCS"},
                ],
            }
        ],
    },
    "performance_metrics": {
        "effect_sizes": [
            {
                "name_short": "OR",
                "name_long": "Odds Ratio",
                "estimate": 1.55,
                "ci_lower": 1.52,
                "ci_upper": 1.58,
            }
        ],
        "class_acc": [
            {
                "name_short": "C-index",
                "name_long": "Concordance Statistic",
                "estimate": 0.622,
                "ci_lower": 0.619,
                "ci_upper": 0.627,
            }
        ],
        "othermetrics": [],
    },
}


def _pgs_tool():
    from tooluniverse.pgs_catalog_tool import PGSCatalogTool

    return PGSCatalogTool(
        {
            "name": "PGSCatalog_get_performance_metrics",
            "type": "PGSCatalogTool",
            "fields": {"operation": "get_performance_metrics"},
        }
    )


class TestPGSPerformanceMetrics(unittest.TestCase):
    def test_parses_metrics_and_eval_cohort(self):
        """Flattens OR/C-index with CIs and the evaluation cohort ancestry/size."""
        tool = _pgs_tool()
        body = {"count": 19, "results": [_PERF]}
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(200, body)
            result = tool.run({"pgs_id": "pgs000001"})  # lowercase -> normalized

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total"], 19)
        self.assertEqual(result["metadata"]["pgs_id"], "PGS000001")
        # endpoint + param wiring
        self.assertTrue(get.call_args.args[0].endswith("/performance/search"))
        self.assertEqual(get.call_args.kwargs["params"]["pgs_id"], "PGS000001")

        rec = result["data"][0]
        self.assertEqual(rec["ppm_id"], "PPM000001")
        self.assertEqual(rec["pgs_id"], "PGS000001")
        # Odds Ratio with 95% CI flattened out of effect_sizes
        es = rec["effect_sizes"][0]
        self.assertEqual(es["name_short"], "OR")
        self.assertEqual(es["estimate"], 1.55)
        self.assertEqual(es["ci_lower"], 1.52)
        self.assertEqual(es["ci_upper"], 1.58)
        # C-index out of class_acc
        ca = rec["classification_accuracy"][0]
        self.assertEqual(ca["name_short"], "C-index")
        self.assertEqual(ca["estimate"], 0.622)
        # evaluation cohort ancestry + sample size
        samp = rec["evaluation_samples"][0]
        self.assertEqual(samp["ancestry_broad"], "European")
        self.assertEqual(samp["sample_number"], 67054)
        self.assertEqual(samp["cohorts"], ["ABCFS", "MCCS"])
        self.assertEqual(rec["evaluation_sampleset_id"], "PSS000001")
        self.assertEqual(rec["publication"]["year"], "2018")

    def test_missing_pgs_id_rejected(self):
        """Missing pgs_id returns a clean error, not an exception."""
        result = _pgs_tool().run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("pgs_id", result["error"])

    def test_http_error_is_clean_error(self):
        """Upstream HTTP 500 is surfaced as a status=error result."""
        tool = _pgs_tool()
        with patch("tooluniverse.pgs_catalog_tool.requests.get") as get:
            get.return_value = _resp(500, {})
            result = tool.run({"pgs_id": "PGS000001"})
        self.assertEqual(result["status"], "error")
        self.assertIn("500", result["error"])


# ---------------------------------------------------------------------------
# EnsemblLD_get_ld_region
# ---------------------------------------------------------------------------

# Shape mirrors /ld/human/region/6:25837556..25840000/1000GENOMES:phase_3:CEU
_REGION_LD = [
    {
        "population_name": "1000GENOMES:phase_3:CEU",
        "variation1": "rs1165182",
        "variation2": "rs62394275",
        "r2": "0.122494",
        "d_prime": "0.999978",
    },
    {
        "population_name": "1000GENOMES:phase_3:CEU",
        "variation1": "rs62394274",
        "variation2": "rs62394275",
        "r2": "1.000000",
        "d_prime": "1.000000",
    },
]


def _ld_region_tool():
    from tooluniverse.ensembl_ld_tool import EnsemblLDTool

    return EnsemblLDTool(
        {
            "name": "EnsemblLD_get_ld_region",
            "type": "EnsemblLDTool",
            "fields": {"endpoint_type": "ld_region"},
        }
    )


class TestEnsemblLDRegion(unittest.TestCase):
    def test_parses_region_pairs_sorted_by_r2(self):
        """Parses region LD pairs and sorts them strongest-r2 first."""
        tool = _ld_region_tool()
        with patch("tooluniverse.ensembl_ld_tool.requests.get") as get:
            get.return_value = _resp(200, _REGION_LD)
            result = tool.run(
                {
                    "region": "6:25837556..25840000",
                    "population": "1000GENOMES:phase_3:CEU",
                }
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["region"], "6:25837556..25840000")
        self.assertEqual(data["ld_count"], 2)
        # strongest pair first (numeric sort, strings coerced to float)
        top = data["ld_pairs"][0]
        self.assertEqual(top["variant1"], "rs62394274")
        self.assertEqual(top["variant2"], "rs62394275")
        self.assertEqual(top["r2"], 1.0)
        self.assertEqual(top["d_prime"], 1.0)
        # URL built with region path segment
        self.assertIn(
            "/ld/human/region/6:25837556..25840000/1000GENOMES:phase_3:CEU",
            get.call_args.args[0],
        )
        self.assertEqual(result["metadata"]["endpoint"], "ld/region")

    def test_missing_region_rejected(self):
        """Missing region parameter returns a clean error."""
        result = _ld_region_tool().run({"population": "1000GENOMES:phase_3:CEU"})
        self.assertEqual(result["status"], "error")
        self.assertIn("region", result["error"])

    def test_missing_population_rejected(self):
        """Missing population parameter returns a clean error."""
        result = _ld_region_tool().run({"region": "6:25837556..25840000"})
        self.assertEqual(result["status"], "error")
        self.assertIn("population", result["error"])

    def test_http_400_window_too_large(self):
        """HTTP 400 (window > 1 Mb / bad format) returns a helpful error."""
        tool = _ld_region_tool()
        with patch("tooluniverse.ensembl_ld_tool.requests.get") as get:
            get.return_value = _resp(400, {})
            result = tool.run(
                {
                    "region": "6:1..2000000",
                    "population": "1000GENOMES:phase_3:CEU",
                }
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("1 Mb", result["error"])

    def test_timeout_never_raises(self):
        """A request timeout is caught and returned as status=error."""
        import requests

        tool = _ld_region_tool()
        with patch("tooluniverse.ensembl_ld_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout()
            result = tool.run(
                {
                    "region": "6:25837556..25840000",
                    "population": "1000GENOMES:phase_3:CEU",
                }
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"])


if __name__ == "__main__":
    unittest.main()
