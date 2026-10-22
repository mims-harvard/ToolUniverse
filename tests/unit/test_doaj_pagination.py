from unittest.mock import Mock

import pytest

from tooluniverse.doaj_tool import DOAJTool


def _tool():
    return DOAJTool({"name": "DOAJ_search_articles"})


def _response(page=2, total=7, page_size=3, returned=3, next_url="next"):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "next": next_url,
        "last": "last",
        "results": [
            {
                "bibjson": {
                    "title": f"Article {page}-{i}",
                    "author": [{"name": "Author"}],
                    "identifier": [{"type": "doi", "id": f"10.test/{page}.{i}"}],
                    "journal": {"title": "Journal"},
                }
            }
            for i in range(returned)
        ],
    }
    return response


def test_doaj_forwards_page_and_exposes_exact_navigation(monkeypatch):
    get = Mock(return_value=_response())
    monkeypatch.setattr("tooluniverse.doaj_tool.requests.get", get)

    result = _tool().run(
        {"query": "cancer", "max_results": 3, "page": 2, "type": "articles"}
    )

    assert get.call_args.kwargs["params"] == {"pageSize": 3, "page": 2}
    assert len(result["data"]) == 3
    assert result["metadata"] == {
        "query": "cancer",
        "type": "articles",
        "total_results": 7,
        "total_results_is_exact": True,
        "returned": 3,
        "page": 2,
        "page_size": 3,
        "total_pages": 3,
        "has_more": True,
        "next_page": 3,
        "last_page": 3,
    }


def test_doaj_final_page_reports_completion(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.doaj_tool.requests.get",
        Mock(return_value=_response(page=3, returned=1, next_url=None)),
    )

    result = _tool().run({"query": "cancer", "max_results": 3, "page": 3})

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["returned"] == 1


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "cancer", "max_results": 0},
        {"query": "cancer", "max_results": 101},
        {"query": "cancer", "max_results": True},
        {"query": "cancer", "max_results": "10"},
        {"query": "cancer", "page": 0},
        {"query": "cancer", "page": -1},
        {"query": "cancer", "page": True},
        {"query": "cancer", "page": "2"},
    ],
)
def test_doaj_rejects_values_previously_clamped_or_coerced(monkeypatch, arguments):
    get = Mock()
    monkeypatch.setattr("tooluniverse.doaj_tool.requests.get", get)

    result = _tool().run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()
