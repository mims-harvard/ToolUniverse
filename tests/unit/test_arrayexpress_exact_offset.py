"""ArrayExpress offsets must not be rounded down to BioStudies page boundaries."""

from unittest.mock import MagicMock

import pytest

from tooluniverse.arrayexpress_tool import ArrayExpressRESTTool

pytestmark = pytest.mark.unit


def _tool():
    return ArrayExpressRESTTool(
        {"name": "arrayexpress_search_experiments", "fields": {}}
    )


def _response(start, stop, *, total=250, page=1, exact=True):
    response = MagicMock()
    response.headers = {"content-type": "application/json"}
    response.url = f"https://example.test/search?page={page}"
    response.json.return_value = {
        "hits": [{"accession": f"E-TEST-{index}"} for index in range(start, stop)],
        "totalHits": total,
        "isTotalHitsExact": exact,
        "page": page,
        "pageSize": 100,
    }
    return response


def test_non_aligned_offset_is_sliced_exactly():
    tool = _tool()
    tool.session.get = MagicMock(return_value=_response(0, 100))

    result = tool.run({"keywords": "cancer", "limit": 10, "offset": 5})

    assert [row["accession"] for row in result["data"]["experiments"]] == [
        f"E-TEST-{index}" for index in range(5, 15)
    ]
    assert result["data"]["next_offset"] == 15
    assert tool.session.get.call_args.kwargs["params"]["pageSize"] == 100
    assert tool.session.get.call_args.kwargs["params"]["page"] == 1


def test_offset_window_crossing_upstream_page_fetches_next_page():
    tool = _tool()
    tool.session.get = MagicMock(
        side_effect=[_response(0, 100), _response(100, 200, page=2)]
    )

    result = tool.run({"keywords": "cancer", "limit": 10, "offset": 95})

    assert [row["accession"] for row in result["data"]["experiments"]] == [
        f"E-TEST-{index}" for index in range(95, 105)
    ]
    assert [
        call.kwargs["params"]["page"] for call in tool.session.get.call_args_list
    ] == [1, 2]


def test_deep_cross_page_offset_uses_absolute_upstream_window():
    tool = _tool()
    tool.session.get = MagicMock(
        side_effect=[_response(100, 200, page=2), _response(200, 250, page=3)]
    )

    result = tool.run({"keywords": "cancer", "limit": 10, "offset": 195})

    assert [row["accession"] for row in result["data"]["experiments"]] == [
        f"E-TEST-{index}" for index in range(195, 205)
    ]
    assert [
        call.kwargs["params"]["page"] for call in tool.session.get.call_args_list
    ] == [2, 3]


def test_non_exact_total_is_preserved_as_lower_bound():
    tool = _tool()
    tool.session.get = MagicMock(
        return_value=_response(0, 100, total=1279, exact=False)
    )

    result = tool.run({"keywords": "cancer", "limit": 3, "offset": 0})

    assert result["data"]["totalHits"] == 1279
    assert result["data"]["totalHitsExact"] is False
    assert result["data"]["totalHitsRelation"] == "lower_bound"
    assert "lower bound" in result["data"]["totalHitsWarning"]
    assert result["data"]["has_more"] is True


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
def test_invalid_page_arguments_fail_before_network(arguments, error):
    tool = _tool()
    tool.session.get = MagicMock()

    result = tool.run(arguments)

    assert result["status"] == "error"
    assert error in result["error"]
    tool.session.get.assert_not_called()
