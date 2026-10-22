"""Regression tests for nested EBI Proteins variation pagination."""

from unittest.mock import MagicMock

import pytest

from tooluniverse.proteins_api_tool import ProteinsAPIRESTTool


pytestmark = pytest.mark.unit


def _tool():
    return ProteinsAPIRESTTool(
        {
            "name": "proteins_api_get_variants",
            "fields": {"endpoint": "https://www.ebi.ac.uk/proteins/api/variation"},
        }
    )


def _response(accession="P04637", count=12):
    response = MagicMock()
    response.status_code = 200
    response.url = "https://www.ebi.ac.uk/proteins/api/variation?accession=P04637"
    response.json.return_value = [
        {
            "accession": accession,
            "features": [{"id": index} for index in range(count)],
        }
    ]
    return response


def test_single_accession_pages_nested_features_not_parent_records():
    tool = _tool()
    tool.session.get = MagicMock(return_value=_response())

    result = tool.run({"accession": "P04637", "size": 5, "offset": 5})

    entry = result["data"][0]
    assert [feature["id"] for feature in entry["features"]] == [5, 6, 7, 8, 9]
    assert entry["total_features"] == 12
    assert entry["features_returned"] == 5
    assert entry["feature_offset"] == 5
    assert entry["has_more_features"] is True
    assert entry["next_feature_offset"] == 10
    # EBI's parent-record size/offset must not be sent upstream.
    params = tool.session.get.call_args.kwargs["params"]
    assert "size" not in params
    assert "offset" not in params


def test_tail_page_terminates_and_reports_completeness():
    tool = _tool()
    tool.session.get = MagicMock(return_value=_response())

    result = tool.run({"accession": "P04637", "size": 5, "offset": 10})

    entry = result["data"][0]
    assert [feature["id"] for feature in entry["features"]] == [10, 11]
    assert entry["has_more_features"] is False
    assert entry["next_feature_offset"] is None
    assert entry["result_set_complete"] is False


def test_batch_accessions_receive_same_per_protein_page():
    tool = _tool()

    def response_for(_url, params, timeout):
        return _response(params["accession"], count=8)

    tool.session.get = MagicMock(side_effect=response_for)
    result = tool.run(
        {"accession": ["P04637", "P05067"], "size": 3, "offset": 3}
    )

    assert result["count"] == 2
    for parent in result["data"]:
        entry = parent["data"][0]
        assert [feature["id"] for feature in entry["features"]] == [3, 4, 5]
        assert entry["total_features"] == 8
        assert entry["next_feature_offset"] == 6


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"size": 0}, "size"),
        ({"size": True}, "size"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
def test_invalid_nested_pagination_is_rejected_before_request(arguments, message):
    tool = _tool()
    tool.session.get = MagicMock()

    result = tool.run({"accession": "P04637", **arguments})

    assert result["status"] == "error"
    assert message in result["error"]
    tool.session.get.assert_not_called()
