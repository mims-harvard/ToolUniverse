from unittest.mock import Mock

import pytest

from tooluniverse.openaire_tool import OpenAIRETool


def _tool(kind="publications"):
    return OpenAIRETool(
        {
            "name": f"OpenAIRE_search_{kind}",
            "parameter": {
                "properties": {
                    "type": {
                        "default": kind,
                    }
                }
            },
        }
    )


def _response(page, size, total, returned):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "header": {
                "page": {"$": page},
                "size": {"$": size},
                "total": {"$": total},
            },
            "results": {
                "result": [{"metadata": {}} for _ in range(returned)],
            },
        }
    }
    return response


def test_openaire_forwards_large_page_and_discloses_result_window(monkeypatch):
    get = Mock(return_value=_response(page=2, size=101, total=4_875_410, returned=101))
    monkeypatch.setattr("tooluniverse.openaire_tool.requests.get", get)

    result = _tool().run(
        {
            "query": "cancer",
            "max_results": 101,
            "page": 2,
            "type": "publications",
        }
    )
    data = result["data"]

    assert get.call_args.kwargs["params"] == {
        "format": "json",
        "size": 101,
        "page": 2,
        "keywords": "cancer",
    }
    assert data["returned"] == 101
    assert data["total_results"] == 4_875_410
    assert data["total_results_is_exact"] is True
    assert data["accessible_results"] == 10_000
    assert data["upstream_truncated"] is True
    assert data["has_more"] is True
    assert data["next_page"] == 3
    assert "first 10,000" in data["warning"]


def test_openaire_stops_at_end_of_accessible_window(monkeypatch):
    get = Mock(return_value=_response(page=10, size=1000, total=20_000, returned=1000))
    monkeypatch.setattr("tooluniverse.openaire_tool.requests.get", get)

    data = _tool().run({"query": "cancer", "max_results": 1000, "page": 10})["data"]

    assert data["has_more"] is False
    assert data["next_page"] is None
    assert data["upstream_truncated"] is True


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": "x", "max_results": 0}, "between 1 and 1000"),
        ({"query": "x", "max_results": 1001}, "between 1 and 1000"),
        ({"query": "x", "max_results": True}, "between 1 and 1000"),
        ({"query": "x", "max_results": "100"}, "between 1 and 1000"),
        ({"query": "x", "page": 0}, "positive integer"),
        ({"query": "x", "page": True}, "positive integer"),
        ({"query": "x", "max_results": 1000, "page": 11}, "<= 10000"),
    ],
)
def test_openaire_rejects_invalid_or_unreachable_pages(monkeypatch, arguments, error):
    get = Mock()
    monkeypatch.setattr("tooluniverse.openaire_tool.requests.get", get)

    data = _tool().run(arguments)["data"]

    assert data["status"] == "error"
    assert error in data["error"]
    get.assert_not_called()
