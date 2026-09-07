"""Regression guard for the IEDB MHC-II prediction defects.

Fix-R18D-1/R18D-2 and Fix-R34A-1 were all found against the legacy
synchronous ``tools_api`` endpoint:

1. An input the endpoint could not handle came back as prose with HTTP 200,
   which was misparsed as TSV into a fabricated "successful" result.
2. The real rank column was named differently from the one being read, so
   every result silently reported rank 100.
3. The class II sliding window defaults to 15 residues and errors on any
   shorter sequence, including this tool's own 13-mer registered example, so
   the window has to shrink to fit.

Fix-R29A-1 then moved MHC-II off that endpoint entirely -- it accepts a POST
and never answers, so every call stalled for the full client timeout. These
guards are therefore expressed against IEDB's next-generation async pipeline
API, where the equivalents are: an upstream failure surfaces in
``data.errors`` (and must not be reported as success), the percentile comes
from the peptide table's real columns, and the window is the submitted
``peptide_length_range``.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

pytestmark = pytest.mark.unit


def _tool(endpoint_type):
    tool = IEDBPredictionTool(
        {"name": "IEDB_predict", "fields": {"endpoint_type": endpoint_type}}
    )
    tool.poll_interval = 0
    return tool


def _resp(payload, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    r.text = str(payload)
    r.raise_for_status = MagicMock()
    return r


def _done(columns, rows, warnings=None):
    return {
        "status": "done",
        "data": {
            "errors": [],
            "warnings": warnings or [],
            "results": [
                {
                    "type": "peptide_table",
                    "table_columns": [{"name": c} for c in columns],
                    "table_data": rows,
                }
            ],
        },
    }


_SUBMIT_OK = {"result_id": "rid-1", "warnings": []}

_MHCII_COLUMNS = [
    "allele",
    "start",
    "end",
    "length",
    "netmhciipan_el_core",
    "peptide",
    "netmhciipan_el_score",
    "median_percentile",
    "netmhciipan_el_percentile",
]


def _submit_and_get(submit_payload, result_payload):
    return patch(
        "tooluniverse.iedb_prediction_tool.requests.post",
        return_value=_resp(submit_payload),
    ), patch(
        "tooluniverse.iedb_prediction_tool.requests.get",
        return_value=_resp(result_payload),
    )


def test_upstream_stage_failure_is_reported_as_error_not_success():
    """A stage that dies upstream must never surface as a prediction."""
    tool = _tool("predict_mhcii")
    failed = {
        "status": "error",
        "data": {
            "errors": [
                (
                    "The following errors occurred during processing. "
                    "stage reference number db5761a5"
                )
            ]
        },
    }
    post, get = _submit_and_get(_SUBMIT_OK, failed)
    with post, get:
        result = tool.run({"sequence": "PKYVKQNTLKLAT", "allele": "HLA-DRB1*01:01"})

    assert result["status"] == "error"
    assert "errors occurred during processing" in result["error"]


def test_percentile_rank_reads_the_real_percentile_column():
    tool = _tool("predict_mhcii")
    payload = _done(
        _MHCII_COLUMNS,
        [
            [
                "HLA-DRB1*01:01",
                15,
                29,
                15,
                "YAGSYPYDV",
                "VPDYAGSYPYDVPDY",
                0.2922,
                6.4,
                6.4,
            ],
            [
                "HLA-DRB1*01:01",
                14,
                28,
                15,
                "YAGSYPYDV",
                "DVPDYAGSYPYDVPD",
                0.2454,
                7.4,
                7.4,
            ],
        ],
    )
    post, get = _submit_and_get(_SUBMIT_OK, payload)
    with post, get:
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
    payload = _done(
        [
            "allele",
            "start",
            "end",
            "length",
            "peptide",
            "netmhcpan_el_score",
            "median_percentile",
            "netmhcpan_el_percentile",
        ],
        [["HLA-A*02:01", 18, 26, 9, "YAGSYPYDV", 0.0512, 2.1, 2.1]],
    )
    post, get = _submit_and_get(_SUBMIT_OK, payload)
    with post, get:
        result = tool.run(
            {
                "sequence": "YPYDVPDYAGYPYDVPDYAGSYPYDVPDYA",
                "allele": "HLA-A*02:01",
                "length": 9,
            }
        )

    assert result["status"] == "success"
    assert result["data"][0]["percentile_rank"] == 2.1


def test_empty_peptide_table_is_not_a_fabricated_hit():
    tool = _tool("predict_mhcii")
    post, get = _submit_and_get(_SUBMIT_OK, _done(_MHCII_COLUMNS, []))
    with post, get:
        result = tool.run({"sequence": "A" * 20, "allele": "HLA-DRB1*01:01"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["n_peptides"] == 0


# Fix-R34A-1: the class II sliding window defaults to 15 residues and cannot
# exceed the input sequence, so a shorter sequence -- such as this tool's own
# registered 13-residue example "PKYVKQNTLKLAT" -- needs the window shrunk to
# its own length. On the next-gen API the window is the submitted
# peptide_length_range.
def _submitted_length_range(mock_post):
    stage = mock_post.call_args.kwargs["json"]["stages"][0]
    return stage["input_parameters"]["peptide_length_range"]


def test_short_sequence_auto_shrinks_the_window():
    tool = _tool("predict_mhcii")
    with (
        patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            return_value=_resp(_SUBMIT_OK),
        ) as mock_post,
        patch(
            "tooluniverse.iedb_prediction_tool.requests.get",
            return_value=_resp(_done(_MHCII_COLUMNS, [])),
        ),
    ):
        result = tool.run({"sequence": "PKYVKQNTLKLAT", "allele": "HLA-DRB1*01:01"})

    assert result["status"] == "success"
    assert _submitted_length_range(mock_post) == [13, 13]


def test_long_sequence_uses_the_default_window_of_15():
    tool = _tool("predict_mhcii")
    with (
        patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            return_value=_resp(_SUBMIT_OK),
        ) as mock_post,
        patch(
            "tooluniverse.iedb_prediction_tool.requests.get",
            return_value=_resp(_done(_MHCII_COLUMNS, [])),
        ),
    ):
        tool.run({"sequence": "A" * 20, "allele": "HLA-DRB1*01:01"})

    assert _submitted_length_range(mock_post) == [15, 15]


def test_explicit_length_argument_takes_precedence():
    tool = _tool("predict_mhcii")
    with (
        patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            return_value=_resp(_SUBMIT_OK),
        ) as mock_post,
        patch(
            "tooluniverse.iedb_prediction_tool.requests.get",
            return_value=_resp(_done(_MHCII_COLUMNS, [])),
        ),
    ):
        tool.run({"sequence": "A" * 20, "allele": "HLA-DRB1*01:01", "length": 11})

    assert _submitted_length_range(mock_post) == [11, 11]
