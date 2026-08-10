"""Regression guard for two Fix-R23B defects in IEDBPredictionTool.

Fix-R23B-1 (percentile_rank): every result silently reported
percentile_rank=100.0 regardless of true binding strength, hiding real
strong binders from any caller filtering on the documented convention.

Fix-R23B-2 (invalid-allele silent success): an unrecognized HLA allele name
produced a bogus `status: "success"` payload with fabricated scores instead
of an error.

Both concerns still apply after Fix-R29A-1 moved the MHC-I and MHC-II
predictions off the retired synchronous ``tools-cluster-interface.iedb.org``
endpoint (which accepts a POST and then never answers) onto IEDB's
next-generation async pipeline API, so the guards are expressed against that
contract: a peptide table of ``table_columns``/``table_data``, and a
validation rejection that returns HTTP 200 carrying ``errors`` and no
``result_id`` (both shapes confirmed live).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.iedb_prediction_tool import IEDBPredictionTool

pytestmark = pytest.mark.unit


def _tool(endpoint_type):
    tool = IEDBPredictionTool(
        {"name": "iedb_test", "fields": {"endpoint_type": endpoint_type}}
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


def _done(columns, rows):
    return {
        "status": "done",
        "data": {
            "errors": [],
            "warnings": [],
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

_MHCII_DONE = _done(
    [
        "allele",
        "start",
        "end",
        "length",
        "netmhciipan_el_core",
        "peptide",
        "netmhciipan_el_score",
        "median_percentile",
        "netmhciipan_el_percentile",
    ],
    [
        [
            "HLA-DRB1*01:01",
            194,
            208,
            15,
            "FELLHAPAT",
            "VLSFELLHAPATVCG",
            0.8447,
            0.67,
            0.67,
        ],
        [
            "HLA-DRB1*01:01",
            192,
            206,
            15,
            "FELLHAPAT",
            "VVVLSFELLHAPATV",
            0.8119,
            0.86,
            0.86,
        ],
    ],
)

_MHCI_DONE = _done(
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
    [["HLA-A*02:01", 1, 9, 9, "KIADYNYKL", 0.865, 0.05, 0.05]],
)

# Live shape for an unknown allele: HTTP 200, `errors`, no `result_id`.
_INVALID_ALLELE_REJECTION = {
    "errors": ["The following are not valid alleles: HLA-A*99:99"],
    "warnings": [],
}


class TestMhciiPercentileRank:
    def test_reads_real_percentile_not_hardcoded_100(self):
        tool = _tool("predict_mhcii")

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_resp(_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_resp(_MHCII_DONE),
            ),
        ):
            result = tool.run({"sequence": "X" * 20, "allele": "HLA-DRB1*01:01"})

        assert result["status"] == "success"
        ranks = [r["percentile_rank"] for r in result["data"]]
        assert ranks == [0.67, 0.86]
        assert all(r != 100.0 for r in ranks)


class TestInvalidAlleleErrorDetection:
    def test_mhci_invalid_allele_returns_status_error(self):
        tool = _tool("predict_mhci")

        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            return_value=_resp(_INVALID_ALLELE_REJECTION),
        ):
            result = tool.run({"sequence": "KIADYNYKLPDDFTGC", "allele": "HLA-A*99:99"})

        assert result["status"] == "error"
        assert "HLA-A*99:99" in result["error"]
        assert "data" not in result

    def test_mhci_valid_response_still_succeeds(self):
        tool = _tool("predict_mhci")

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_resp(_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_resp(_MHCI_DONE),
            ),
        ):
            result = tool.run({"sequence": "KIADYNYKLPDDFTGC", "allele": "HLA-A*02:01"})

        assert result["status"] == "success"
        assert result["data"][0]["peptide"] == "KIADYNYKL"
        assert result["data"][0]["percentile_rank"] == 0.05
