"""Regression tests for strict Pathoplexus parameters and pagination metadata."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pathoplexus_tool import PathoplexusCountTool
from tooluniverse.pathoplexus_tool import PathoplexusMutationsTool


def _response(*, data=None, text=None, info=None):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": data or [], "info": info or {}}
    response.text = text
    return response


def _details_tool():
    return PathoplexusCountTool(
        {
            "name": "Pathoplexus_get_sequence_details",
            "fields": {"timeout": 30, "mode": "details"},
        }
    )


def _fasta_tool():
    return PathoplexusCountTool(
        {
            "name": "Pathoplexus_get_sequences_fasta",
            "fields": {"timeout": 30, "mode": "fasta"},
        }
    )


def _mutations_tool():
    return PathoplexusMutationsTool(
        {"name": "Pathoplexus_get_mutations", "fields": {"timeout": 30}}
    )


def test_details_uses_sentinel_row_and_reports_next_page():
    response = _response(
        data=[{"accession": "a"}, {"accession": "b"}, {"accession": "c"}],
        info={"dataVersion": "2026-08-01", "requestId": "request-1"},
    )
    with patch(
        "tooluniverse.pathoplexus_tool.requests.get", return_value=response
    ) as get:
        result = _details_tool().run({"organism": "mpox", "limit": 2, "offset": 4})

    assert [row["accession"] for row in result["data"]] == ["a", "b"]
    assert get.call_args.kwargs["params"]["limit"] == 3
    assert get.call_args.kwargs["params"]["offset"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["api_info"]["requestId"] == "request-1"


def test_mutations_preserves_zero_threshold_and_paginates():
    rows = [
        {"mutation": "OPG001:M1I"},
        {"mutation": "OPG002:A2V"},
        {"mutation": "OPG003:G3D"},
    ]
    with patch(
        "tooluniverse.pathoplexus_tool.requests.get",
        return_value=_response(data=rows),
    ) as get:
        result = _mutations_tool().run(
            {
                "organism": "mpox",
                "min_proportion": 0,
                "limit": 2,
                "offset": 5,
            }
        )

    params = get.call_args.kwargs["params"]
    assert params["minProportion"] == 0
    assert params["limit"] == 3
    assert params["offset"] == 5
    assert len(result["data"]) == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 7


def test_fasta_forwards_offset_and_marks_short_page_complete():
    fasta = ">sequence-1\nACGT\n"
    with patch(
        "tooluniverse.pathoplexus_tool.requests.get",
        return_value=_response(text=fasta),
    ) as get:
        result = _fasta_tool().run({"organism": "mpox", "limit": 2, "offset": 8})

    assert get.call_args.kwargs["params"]["offset"] == 8
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert result["metadata"]["page_completeness"] == "complete"


@pytest.mark.parametrize(
    ("tool", "arguments", "parameter"),
    [
        (_details_tool, {"organism": "mpox", "limit": "2"}, "limit"),
        (_details_tool, {"organism": "mpox", "offset": -1}, "offset"),
        (_fasta_tool, {"organism": "mpox", "aligned": "false"}, "aligned"),
        (
            _fasta_tool,
            {"organism": "mpox", "sequence_type": "protein"},
            "sequence_type",
        ),
        (
            _mutations_tool,
            {"organism": "mpox", "min_proportion": 1.1},
            "min_proportion",
        ),
        (_mutations_tool, {"organism": "mpox", "mutation_type": "aa"}, "mutation_type"),
    ],
)
def test_invalid_parameters_fail_before_network(tool, arguments, parameter):
    with patch("tooluniverse.pathoplexus_tool.requests.get") as get:
        result = tool().run(arguments)

    assert result["status"] == "error"
    assert parameter in result["error"]
    get.assert_not_called()
