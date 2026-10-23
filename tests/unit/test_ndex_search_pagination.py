"""Regression tests for NDEx search windows and short-page semantics."""

from unittest.mock import Mock

import pytest

from tooluniverse.ndex_tool import NDExTool

pytestmark = pytest.mark.unit


def _tool():
    return NDExTool({"name": "NDEx_search_networks", "fields": {"endpoint": "search"}})


def test_size_above_old_cap_is_forwarded_and_page_is_navigable(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "numFound": 500,
        "networks": [{"externalId": str(index)} for index in range(101)],
    }
    requested = {}

    def post(url, params, json, timeout):
        requested.update(
            {"url": url, "params": params, "json": json, "timeout": timeout}
        )
        return response

    monkeypatch.setattr("tooluniverse.ndex_tool.requests.post", post)
    result = _tool().run({"query": "cancer", "size": 101, "start": 1})
    assert requested["params"] == {"start": 1, "size": 101}
    assert result["metadata"]["returned"] == 101
    assert result["metadata"]["page_index"] == 1
    assert result["metadata"]["next_start"] == 2
    assert result["metadata"]["short_page"] is False


def test_short_page_does_not_falsely_end_search(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "numFound": 17_075,
        "networks": [{"externalId": str(index)} for index in range(89)],
    }
    monkeypatch.setattr(
        "tooluniverse.ndex_tool.requests.post", lambda *args, **kwargs: response
    )
    metadata = _tool().run({"query": "*", "size": 101})["metadata"]
    assert metadata["returned"] == 89
    assert metadata["short_page"] is True
    assert metadata["has_more"] is True
    assert metadata["next_start"] == 1
    assert "fewer visible networks" in metadata["warning"]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"query": "x", "size": 0}, "size must be"),
        ({"query": "x", "size": 1001}, "size must be"),
        ({"query": "x", "size": True}, "size must be"),
        ({"query": "x", "start": -1}, "start must be"),
        ({"query": "x", "start": 1.5}, "start must be"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, message):
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]
