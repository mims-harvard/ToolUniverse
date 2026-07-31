"""Regression guard for two Fix-R23B bugs in IEDBPredictionTool.

Fix-R23B-1 (percentile_rank): the mhcii/ endpoint's real TSV column is
"rank", not "percentile_rank" (confirmed live) -- _predict_mhcii read the
wrong key, so every result silently defaulted to percentile_rank=100.0
regardless of true binding strength, hiding real strong binders from any
caller filtering on the documented convention.

Fix-R23B-2 (invalid-allele silent success): IEDB's tools_api endpoints
return HTTP 200 with a plain-text error message (not a TSV table) for
invalid input like an unrecognized HLA allele name -- confirmed live for
mhci/. Naively parsing that as TSV produced bogus single-column "rows"
keyed on the error prose itself, with status:"success" and fabricated
score/percentile_rank of 0.0/100.0. Fixed by detecting non-tabular
responses before parsing and returning a clear error instead.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

pytestmark = pytest.mark.unit

_MHCII_TSV = (
    "allele\tseq_num\tstart\tend\tlength\tcore_peptide\tpeptide\tscore\trank\n"
    "HLA-DRB1*01:01\t1\t194\t208\t15\tFELLHAPAT\tVLSFELLHAPATVCG\t0.8447\t0.67\n"
    "HLA-DRB1*01:01\t1\t192\t206\t15\tFELLHAPAT\tVVVLSFELLHAPATV\t0.8119\t0.86\n"
)

_MHCI_INVALID_ALLELE_TEXT = (
    "Invalid allele name HLA-A*99:99 found.\n\n"
    "* Please go to the link below for more usage info:\n"
    "http://tools.iedb.org/main/html/tools_api.html"
)

_MHCI_VALID_TSV = (
    "allele\tseq_num\tstart\tend\tlength\tpeptide\tcore\ticore\tscore\tpercentile_rank\n"
    "HLA-A*02:01\t1\t1\t9\t9\tKIADYNYKL\tKIADYNYKL\tKIADYNYKL\t0.865\t0.05\n"
)


def _tool(endpoint_type):
    return IEDBPredictionTool(
        {"name": "iedb_test", "fields": {"endpoint_type": endpoint_type}}
    )


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


class TestMhciiPercentileRank:
    def test_reads_rank_column_not_hardcoded_100(self):
        tool = _tool("predict_mhcii")
        resp = _resp(_MHCII_TSV)

        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post", return_value=resp
        ):
            result = tool.run({"sequence": "X" * 20, "allele": "HLA-DRB1*01:01"})

        assert result["status"] == "success"
        ranks = [r["percentile_rank"] for r in result["data"]]
        assert ranks == [0.67, 0.86]
        assert all(r != 100.0 for r in ranks)


class TestInvalidAlleleErrorDetection:
    def test_mhci_plain_text_error_returns_status_error(self):
        tool = _tool("predict_mhci")
        resp = _resp(_MHCI_INVALID_ALLELE_TEXT)

        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post", return_value=resp
        ):
            result = tool.run({"sequence": "KIADYNYKLPDDFTGC", "allele": "HLA-A*99:99"})

        assert result["status"] == "error"
        assert "Invalid allele name HLA-A*99:99" in result["error"]
        assert "data" not in result

    def test_mhci_valid_tsv_still_succeeds(self):
        tool = _tool("predict_mhci")
        resp = _resp(_MHCI_VALID_TSV)

        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post", return_value=resp
        ):
            result = tool.run({"sequence": "KIADYNYKLPDDFTGC", "allele": "HLA-A*02:01"})

        assert result["status"] == "success"
        assert result["data"][0]["peptide"] == "KIADYNYKL"
        assert result["data"][0]["percentile_rank"] == 0.05
