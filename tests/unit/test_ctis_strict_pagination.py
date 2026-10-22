import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ctis_tool import CTISSearchTrialsTool


pytestmark = pytest.mark.unit


def _config(name="CTIS_search_trials"):
    with open("src/tooluniverse/data/ctis_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _payload(page, ids, *, total=5, pages=3, next_page=True, prev_page=False):
    return {
        "showWarning": False,
        "pagination": {
            "totalRecords": total,
            "currentPage": page,
            "totalPages": pages,
            "nextPage": next_page,
            "prevPage": prev_page,
        },
        "data": [{"ctNumber": ct_number, "ctTitle": ct_number} for ct_number in ids],
    }


def test_adjacent_pages_are_recoverable_and_disjoint():
    tool = CTISSearchTrialsTool(_config())
    with patch(
        "tooluniverse.ctis_tool.requests.post",
        side_effect=[
            _response(_payload(1, ["A", "B"])),
            _response(_payload(2, ["C", "D"], prev_page=True)),
        ],
    ) as post:
        first = tool.run({"query": "breast cancer", "limit": 2, "page": 1})
        second = tool.run({"query": "breast cancer", "limit": 2, "page": 2})

    assert {item["ct_number"] for item in first["data"]}.isdisjoint(
        item["ct_number"] for item in second["data"]
    )
    assert first["metadata"]["total_records"] == 5
    assert first["metadata"]["has_more"] is True
    assert first["metadata"]["next_page"] == 2
    assert second["metadata"]["previous_page"] == 1
    assert post.call_args_list[1].kwargs["json"]["pagination"] == {
        "page": 2,
        "size": 2,
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "cancer", "limit": 0},
        {"query": "cancer", "limit": 101},
        {"query": "cancer", "limit": "10"},
        {"query": "cancer", "limit": True},
        {"query": "cancer", "page": 0},
        {"query": "cancer", "page": "2"},
        {"query": "cancer", "page": False},
    ],
)
def test_invalid_pagination_is_rejected_without_network_call(arguments):
    tool = CTISSearchTrialsTool(_config())
    with patch("tooluniverse.ctis_tool.requests.post") as post:
        result = tool.run(arguments)
    assert result["status"] == "error"
    post.assert_not_called()


def test_upstream_page_mismatch_is_not_silently_accepted():
    tool = CTISSearchTrialsTool(_config())
    with patch(
        "tooluniverse.ctis_tool.requests.post",
        return_value=_response(_payload(1, ["A", "B"])),
    ):
        result = tool.run({"query": "cancer", "limit": 2, "page": 2})
    assert result["status"] == "error"
    assert "ignored requested page 2" in result["error"]


def test_last_page_marks_result_exhausted():
    tool = CTISSearchTrialsTool(_config())
    with patch(
        "tooluniverse.ctis_tool.requests.post",
        return_value=_response(
            _payload(3, ["E"], next_page=False, prev_page=True)
        ),
    ):
        result = tool.run({"query": "cancer", "limit": 2, "page": 3})
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["previous_page"] == 2


def test_malformed_success_payload_is_an_error():
    tool = CTISSearchTrialsTool(_config())
    with patch(
        "tooluniverse.ctis_tool.requests.post", return_value=_response({"data": []})
    ):
        result = tool.run({"query": "cancer"})
    assert result["status"] == "error"
    assert "pagination" in result["error"]


def test_search_preserves_products_endpoints_and_dates():
    tool = CTISSearchTrialsTool(_config())
    payload = _payload(1, [])
    payload["data"] = [
        {
            "ctNumber": "2022-503001-38-01",
            "ctTitle": "Full title",
            "shortTitle": "Protocol short title",
            "product": "RIBOCICLIB",
            "primaryEndPoint": "Primary endpoint",
            "endPoint": "Secondary endpoints",
            "ageRangeSecondary": ["7", "8"],
            "decisionDate": "DE: 11/06/2025",
            "decisionDateOverall": "11/06/2025",
            "lastPublicationUpdate": "25/07/2026",
        }
    ]
    with patch(
        "tooluniverse.ctis_tool.requests.post", return_value=_response(payload)
    ):
        result = tool.run({"query": "breast cancer"})
    record = result["data"][0]
    assert record["short_title"] == "Protocol short title"
    assert record["products"] == "RIBOCICLIB"
    assert record["primary_endpoint"] == "Primary endpoint"
    assert record["endpoints"] == "Secondary endpoints"
    assert record["age_range_secondary"] == ["7", "8"]
    assert record["decision_date_overall"] == "11/06/2025"
    assert record["last_publication_update"] == "25/07/2026"
