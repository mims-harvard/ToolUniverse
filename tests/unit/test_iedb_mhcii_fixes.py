"""Regression guard for Fix-R18D-1/R18D-2: IEDB's MHC-II prediction endpoint
had two bugs, both confirmed live --

1. A too-short input sequence gets a plain-text validation error back with
   HTTP 200 (not real TSV data). csv.DictReader silently misparsed the
   error's first line as a single-column header, producing a fabricated
   "successful" result with `percentile_rank: 100.0`. _iedb_error_response
   now detects a non-tabular response (no tab in the first line) before
   parsing and returns a real error instead.
2. Even on a genuine successful response, the real TSV column is named
   "rank" (unlike the sibling MHC-I endpoint, which really does use
   "percentile_rank"), so `r.get("percentile_rank", 100)` always hit the
   default -- every result silently reported rank 100 regardless of the
   real value.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

pytestmark = pytest.mark.unit


def _tool(endpoint_type):
    return IEDBPredictionTool(
        {"name": "IEDB_predict", "fields": {"endpoint_type": endpoint_type}}
    )


def _resp(text):
    r = MagicMock()
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_short_sequence_error_text_is_reported_as_error_not_success():
    tool = _tool("predict_mhcii")
    error_text = (
        "The length of input sequence is less than the input/default length 15.\n"
        "* Please go to the link below for usage info:\n"
        "http://tools.iedb.org/main/html/tools_api.html"
    )

    with patch(
        "tooluniverse.iedb_prediction_tool.requests.post",
        return_value=_resp(error_text),
    ):
        result = tool.run({"sequence": "PKYVKQNTLKLAT", "allele": "HLA-DRB1*01:01"})

    assert result["status"] == "error"
    assert "length of input sequence" in result["error"]


def test_percentile_rank_reads_from_real_rank_column():
    tool = _tool("predict_mhcii")
    tsv = (
        "allele\tseq_num\tstart\tend\tlength\tcore_peptide\tpeptide\tscore\trank\n"
        "HLA-DRB1*01:01\t1\t15\t29\t15\tYAGSYPYDV\tVPDYAGSYPYDVPDY\t0.2922\t6.4\n"
        "HLA-DRB1*01:01\t1\t14\t28\t15\tYAGSYPYDV\tDVPDYAGSYPYDVPD\t0.2454\t7.4\n"
    )

    with patch(
        "tooluniverse.iedb_prediction_tool.requests.post", return_value=_resp(tsv)
    ):
        result = tool.run(
            {
                "sequence": "YPYDVPDYAGYPYDVPDYAGSYPYDVPDYA",
                "allele": "HLA-DRB1*01:01",
            }
        )

    assert result["status"] == "success"
    ranks = [r["percentile_rank"] for r in result["data"]]
    assert ranks == [6.4, 7.4]


def test_mhci_percentile_rank_column_unaffected():
    tool = _tool("predict_mhci")
    tsv = (
        "allele\tseq_num\tstart\tend\tlength\tpeptide\tcore\ticore\tscore\tpercentile_rank\n"
        "HLA-A*02:01\t1\t18\t26\t9\tYAGSYPYDV\tYAGSYPYDV\tYAGSYPYDV\t0.0512\t2.1\n"
    )

    with patch(
        "tooluniverse.iedb_prediction_tool.requests.post", return_value=_resp(tsv)
    ):
        result = tool.run(
            {
                "sequence": "YPYDVPDYAGYPYDVPDYAGSYPYDVPDYA",
                "allele": "HLA-A*02:01",
                "length": 9,
            }
        )

    assert result["status"] == "success"
    assert result["data"][0]["percentile_rank"] == 2.1


def test_empty_response_is_reported_as_error():
    tool = _tool("predict_mhcii")

    with patch(
        "tooluniverse.iedb_prediction_tool.requests.post", return_value=_resp("")
    ):
        result = tool.run({"sequence": "A" * 20, "allele": "HLA-DRB1*01:01"})

    assert result["status"] == "error"
