"""Regression tests for Open Genes real page size and navigation metadata."""

from unittest.mock import Mock

import pytest

from tooluniverse.open_genes_tool import OpenGenesSearchTool

pytestmark = pytest.mark.unit


def _tool():
    return OpenGenesSearchTool({"name": "OpenGenes_search_genes", "fields": {}})


def test_limit_above_old_cap_is_forwarded(monkeypatch):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "items": [{"symbol": str(index)} for index in range(101)],
        "options": {
            "total": 2405,
            "pagination": {"page": 2, "pageSize": 101, "pagesTotal": 24},
        },
    }
    requested = {}

    def get(url, params, headers, timeout):
        requested.update(params)
        return response

    monkeypatch.setattr("tooluniverse.open_genes_tool.requests.get", get)
    result = _tool().run({"limit": 101, "page": 2})
    assert requested == {"pageSize": 101, "page": 2}
    assert result["metadata"]["total_aging_genes"] == 2405
    assert result["metadata"]["total_pages"] == 24
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"limit": 0}, "limit must be"),
        ({"limit": 1001}, "limit must be"),
        ({"limit": True}, "limit must be"),
        ({"page": 0}, "page must be"),
        ({"page": 1.5}, "page must be"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, message):
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]
