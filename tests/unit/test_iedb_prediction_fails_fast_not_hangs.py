"""Regression guard for Fix-R29A-1: the IEDB T-cell predictors must not hang.

``IEDB_predict_mhci_binding``, ``IEDB_predict_mhcii_binding`` and
``IEDB_predict_antigen_processing`` all POSTed to the legacy synchronous
endpoint ``https://tools-cluster-interface.iedb.org/tools_api/{mhci,mhcii,
processing}/``. That host still answers a GET with 405, but it never sends
any response body for a POST -- confirmed live::

    curl -X POST --max-time 90 \\
      https://tools-cluster-interface.iedb.org/tools_api/mhci/ \\
      -d "method=netmhcpan_el&sequence_text=GILGFVFTL&allele=HLA-A*02:01&length=9"
    -> curl exit 28, http_code 000, time 90.00

so every call, including each tool's own registered example, stalled for the
full 120 s client timeout and then reported "IEDB prediction timed out".

These three predictions now run on IEDB's next-generation tools API
(``POST /api/v1/pipeline`` then poll ``GET /api/v1/results/{id}``). The
``bcell/`` route on the legacy host does still respond and stays there.

The guards below are all mocked -- no live calls.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.iedb_prediction_tool import (
    IEDB_NEXTGEN_BASE,
    IEDBPredictionTool,
)

pytestmark = pytest.mark.unit

RETIRED_HOST = "tools-cluster-interface.iedb.org"


def _tool(endpoint_type, **overrides):
    tool = IEDBPredictionTool(
        {"name": "iedb_test", "fields": {"endpoint_type": endpoint_type}}
    )
    for key, value in overrides.items():
        setattr(tool, key, value)
    return tool


def _json_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.text = str(payload)
    resp.raise_for_status = MagicMock()
    return resp


_SUBMIT_OK = {"result_id": "rid-123", "warnings": []}

# Shape copied verbatim from a live GET /api/v1/results/{id} for
# {"sequence": "GILGFVFTL", "allele": "HLA-A*02:01", "length": 9}.
_MHCI_DONE = {
    "id": "rid-123",
    "status": "done",
    "data": {
        "errors": [],
        "warnings": [],
        "results": [
            {
                "type": "peptide_table",
                "table_columns": [
                    {"name": "sequence_number"},
                    {"name": "peptide"},
                    {"name": "allele"},
                    {"name": "median_percentile"},
                    {"name": "netmhcpan_el_score"},
                    {"name": "netmhcpan_el_percentile"},
                ],
                "table_data": [
                    [1, "GILGFVFTL", "HLA-A*02:01", 0.09, 0.789948, 0.09],
                    [1, "AAAAAAAAA", "HLA-A*02:01", 42.0, 0.0011, 42.0],
                ],
            }
        ],
    },
}


class TestNoLegacyHost:
    """The retired synchronous endpoint must not be contacted any more."""

    @pytest.mark.parametrize(
        "endpoint_type,arguments",
        [
            (
                "predict_mhci",
                {"sequence": "GILGFVFTL", "allele": "HLA-A*02:01", "length": 9},
            ),
            (
                "predict_mhcii",
                {"sequence": "PKYVKQNTLKLAT", "allele": "HLA-DRB1*01:01"},
            ),
            (
                "predict_processing",
                {"sequence": "SLYNTVATLYCVHQRIDVKQNTLKLATGGKS", "length": 9},
            ),
        ],
    )
    def test_tcell_predictions_use_nextgen_api(self, endpoint_type, arguments):
        tool = _tool(endpoint_type, poll_interval=0)
        post = MagicMock(return_value=_json_response(_SUBMIT_OK))
        get = MagicMock(return_value=_json_response(_MHCI_DONE))

        with (
            patch("tooluniverse.iedb_prediction_tool.requests.post", post),
            patch("tooluniverse.iedb_prediction_tool.requests.get", get),
        ):
            result = tool.run(arguments)

        assert result["status"] == "success"
        called = [c.args[0] for c in post.call_args_list] + [
            c.args[0] for c in get.call_args_list
        ]
        assert called, "expected at least one upstream request"
        assert all(RETIRED_HOST not in url for url in called), called
        assert any(url.startswith(IEDB_NEXTGEN_BASE) for url in called), called


class TestBoundedWait:
    """An unresponsive upstream must fail quickly and say why."""

    def test_submit_timeout_reports_the_request_timeout_not_a_120s_hang(self):
        import requests as _requests

        tool = _tool("predict_mhci")
        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post",
            side_effect=_requests.exceptions.Timeout(),
        ):
            started = time.monotonic()
            result = tool.run({"sequence": "GILGFVFTL"})
            elapsed = time.monotonic() - started

        assert result["status"] == "error"
        assert "120" not in result["error"]
        assert str(tool.request_timeout) in result["error"]
        assert elapsed < 5
        # The per-request budget must stay far below the old 120 s stall.
        assert max(tool.request_timeout) <= 30

    def test_perpetually_pending_job_stops_at_max_wait(self):
        """A job that never finishes is abandoned with an actionable message."""
        tool = _tool("predict_mhci", poll_interval=0, max_wait=0.05)
        pending = {"status": "pending", "data": {"errors": [], "results": []}}

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_json_response(_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(pending),
            ) as get,
        ):
            started = time.monotonic()
            result = tool.run({"sequence": "GILGFVFTL"})
            elapsed = time.monotonic() - started

        assert result["status"] == "error"
        assert "did not finish" in result["error"]
        assert "rid-123" in result["error"]
        assert elapsed < 5
        assert get.call_count >= 1

    def test_stage_failure_reported_even_while_status_stays_pending(self):
        """Live behaviour: a crashed stage populates data.errors but can keep
        reporting status 'pending' forever, so errors must end the poll."""
        tool = _tool("predict_mhci", poll_interval=0, max_wait=60)
        broken = {
            "status": "pending",
            "data": {"errors": ["Command 'tcell_mhci.py' returned non-zero"]},
        }

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_json_response(_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(broken),
            ) as get,
        ):
            result = tool.run({"sequence": "GILGFVFTL"})

        assert result["status"] == "error"
        assert "non-zero" in result["error"]
        assert get.call_count == 1, "must not keep polling a failed stage"


class TestRequestContract:
    """The submitted pipeline body matches the documented next-gen contract."""

    def test_mhci_submits_a_single_binding_stage(self):
        tool = _tool("predict_mhci", poll_interval=0)
        post = MagicMock(return_value=_json_response(_SUBMIT_OK))

        with (
            patch("tooluniverse.iedb_prediction_tool.requests.post", post),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(_MHCI_DONE),
            ),
        ):
            tool.run({"sequence": "GILGFVFTL", "allele": "HLA-A*02:01", "length": 9})

        assert post.call_args.args[0] == f"{IEDB_NEXTGEN_BASE}/pipeline"
        stage = post.call_args.kwargs["json"]["stages"][0]
        assert stage["tool_group"] == "mhci"
        assert stage["input_sequence_text"].endswith("GILGFVFTL")
        assert stage["input_sequence_text"].startswith(">")
        params = stage["input_parameters"]
        assert params["alleles"] == "HLA-A*02:01"
        assert params["peptide_length_range"] == [9, 9]
        assert params["predictors"] == [{"type": "binding", "method": "netmhcpan_el"}]

    def test_mhcii_window_shrinks_to_a_short_sequence(self):
        """The class II window defaults to 15 and cannot exceed the input;
        the tool's own registered example is a 13-mer."""
        tool = _tool("predict_mhcii", poll_interval=0)
        post = MagicMock(return_value=_json_response(_SUBMIT_OK))

        with (
            patch("tooluniverse.iedb_prediction_tool.requests.post", post),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(_MHCI_DONE),
            ),
        ):
            tool.run({"sequence": "PKYVKQNTLKLAT", "allele": "HLA-DRB1*01:01"})

        stage = post.call_args.kwargs["json"]["stages"][0]
        assert stage["tool_group"] == "mhcii"
        assert stage["input_parameters"]["peptide_length_range"] == [13, 13]

    def test_processing_chains_netctlpan_onto_the_binding_predictor(self):
        tool = _tool("predict_processing", poll_interval=0)
        post = MagicMock(return_value=_json_response(_SUBMIT_OK))

        with (
            patch("tooluniverse.iedb_prediction_tool.requests.post", post),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(_MHCI_DONE),
            ),
        ):
            tool.run({"sequence": "SLYNTVATLYCVHQRIDVKQNTLKLATGGKS", "length": 9})

        predictors = post.call_args.kwargs["json"]["stages"][0]["input_parameters"][
            "predictors"
        ]
        assert {"type": "processing", "method": "netctlpan"} in predictors
        assert any(p["type"] == "binding" for p in predictors)

    def test_legacy_mouse_allele_spelling_is_translated(self):
        """Live: the next-gen API rejects 'H-2-Kd' as an invalid allele but
        accepts 'H2-Kd'. The registered example uses the legacy spelling."""
        tool = _tool("predict_mhci", poll_interval=0)
        post = MagicMock(return_value=_json_response(_SUBMIT_OK))

        with (
            patch("tooluniverse.iedb_prediction_tool.requests.post", post),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(_MHCI_DONE),
            ),
        ):
            result = tool.run(
                {"sequence": "TYQRTRALV", "allele": "H-2-Kd", "length": 9}
            )

        stage = post.call_args.kwargs["json"]["stages"][0]
        assert stage["input_parameters"]["alleles"] == "H2-Kd"
        assert result["metadata"]["allele"] == "H2-Kd"


class TestResponseParsing:
    def test_peptide_table_becomes_rows_sorted_by_percentile_rank(self):
        tool = _tool("predict_mhci", poll_interval=0)

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_json_response(_SUBMIT_OK),
            ),
            patch(
                "tooluniverse.iedb_prediction_tool.requests.get",
                return_value=_json_response(_MHCI_DONE),
            ),
        ):
            result = tool.run({"sequence": "GILGFVFTLAAAAAAAAA", "length": 9})

        rows = result["data"]
        assert [r["peptide"] for r in rows] == ["GILGFVFTL", "AAAAAAAAA"]
        assert rows[0]["percentile_rank"] == 0.09
        assert rows[0]["score"] == 0.789948
        assert result["metadata"]["n_peptides"] == 2
        assert result["metadata"]["result_id"] == "rid-123"

    def test_invalid_allele_rejection_is_surfaced(self):
        """A validation failure comes back HTTP 200 with `errors` and no
        `result_id` -- confirmed live for an unknown allele name."""
        tool = _tool("predict_mhci", poll_interval=0)
        rejection = {"errors": ["The following are not valid alleles: HLA-NOPE*99:99"]}

        with (
            patch(
                "tooluniverse.iedb_prediction_tool.requests.post",
                return_value=_json_response(rejection),
            ),
            patch("tooluniverse.iedb_prediction_tool.requests.get") as get,
        ):
            result = tool.run({"sequence": "GILGFVFTL", "allele": "HLA-NOPE*99:99"})

        assert result["status"] == "error"
        assert "not valid alleles" in result["error"]
        get.assert_not_called()

    def test_unknown_method_is_rejected_before_any_request(self):
        """An unsupported method name draws an opaque HTML 500 upstream, so
        it is caught locally with the list of accepted methods instead."""
        tool = _tool("predict_mhci")

        with patch("tooluniverse.iedb_prediction_tool.requests.post") as post:
            result = tool.run({"sequence": "GILGFVFTL", "method": "not_a_method"})

        assert result["status"] == "error"
        assert "not_a_method" in result["error"]
        assert "netmhcpan_el" in result["error"]
        post.assert_not_called()


class TestBcellStillUsesWorkingLegacyRoute:
    def test_bcell_keeps_the_legacy_tools_api(self):
        """bcell/ on the legacy host does still answer (verified live), so it
        is deliberately left unmigrated."""
        tool = _tool("predict_bcell")
        resp = MagicMock()
        resp.text = "Position\tResidue\tScore\tAssignment\n1\tS\t0.5\tE\n"
        resp.raise_for_status = MagicMock()

        with patch(
            "tooluniverse.iedb_prediction_tool.requests.post", return_value=resp
        ) as post:
            result = tool.run({"sequence": "SLYNTVATL"})

        assert result["status"] == "success"
        assert RETIRED_HOST in post.call_args.args[0]
