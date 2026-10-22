"""Regressions for reachable PROSITE/InterPro cursor pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.prosite_tool import PROSITETool

pytestmark = pytest.mark.unit


def _tool():
    return PROSITETool(
        {
            "name": "PROSITE_search",
            "fields": {"endpoint": "search"},
            "parameter": {"properties": {}},
        }
    )


def test_search_sends_cursor_and_returns_next_cursor(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "count": 45,
        "next": (
            "https://www.ebi.ac.uk/interpro/api/entry/prosite?"
            "cursor=cD1QUzAwMTEx&page_size=5&search=kinase"
        ),
        "results": [
            {
                "metadata": {
                    "accession": "PS00107",
                    "name": {"name": "Kinase signature", "short": "KINASE"},
                    "type": "conserved_site",
                    "source_database": "prosite",
                    "integrated": "IPR000001",
                }
            }
        ],
    }
    response.raise_for_status.return_value = None
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return response

    monkeypatch.setattr("tooluniverse.prosite_tool.requests.get", get)

    result = _tool().run({"query": "kinase", "limit": 5, "cursor": "cD1QUzAwMTA2"})

    assert requested["params"] == {
        "search": "kinase",
        "page_size": 5,
        "cursor": "cD1QUzAwMTA2",
    }
    assert result["data"][0]["accession"] == "PS00107"
    assert result["metadata"] == {
        "source": "PROSITE via InterPro API (EBI)",
        "query": "kinase",
        "total_results": 45,
        "returned": 1,
        "page_size": 5,
        "cursor": "cD1QUzAwMTA2",
        "has_more": True,
        "next_cursor": "cD1QUzAwMTEx",
    }


def test_search_final_page_reports_no_next_cursor(monkeypatch):
    response = Mock()
    response.json.return_value = {"count": 3, "next": None, "results": []}
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.prosite_tool.requests.get", lambda *args, **kwargs: response
    )

    result = _tool().run({"query": "insulin", "limit": 5})

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None
    assert result["metadata"]["cursor"] is None


def test_search_forwards_page_sizes_above_old_silent_cap(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "count": 264,
        "next": (
            "https://www.ebi.ac.uk/interpro/api/entry/prosite?"
            "cursor=cD1QUzAwOTk5&page_size=101&search=protein"
        ),
        "results": [],
    }
    response.raise_for_status.return_value = None
    get = Mock(return_value=response)
    monkeypatch.setattr("tooluniverse.prosite_tool.requests.get", get)

    result = _tool().run({"query": "protein", "limit": 101})

    assert result["status"] == "success"
    assert get.call_args.kwargs["params"]["page_size"] == 101
    assert result["metadata"]["page_size"] == 101
    assert result["metadata"]["total_results"] == 264
    assert result["metadata"]["next_cursor"] == "cD1QUzAwOTk5"


@pytest.mark.parametrize("limit", [0, -1, 1001, True, 1.5, "51"])
def test_search_rejects_invalid_limits_without_calling_api(monkeypatch, limit):
    get = Mock()
    monkeypatch.setattr("tooluniverse.prosite_tool.requests.get", get)

    result = _tool().run({"query": "protein", "limit": limit})

    assert result["status"] == "error"
    assert "between 1 and 1000" in result["error"]
    get.assert_not_called()
