"""Regression tests for Dfam's real page-size support."""

from unittest.mock import Mock

import pytest

from tooluniverse.dfam_tool import DfamTool

pytestmark = pytest.mark.unit


def _tool():
    return DfamTool(
        {"name": "Dfam_search_families", "fields": {"endpoint": "search_families"}}
    )


def test_limit_above_old_cap_is_forwarded(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "total_count": 30_646,
        "results": [{"accession": f"DF{index}"} for index in range(101)],
    }
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return response

    monkeypatch.setattr("tooluniverse.dfam_tool.requests.get", get)
    result = _tool().run({"limit": 101, "offset": 101})

    assert requested["params"]["limit"] == 101
    assert requested["params"]["start"] == 101
    assert result["metadata"]["returned"] == 101
    assert result["metadata"]["total_count"] == 30_646
    assert result["metadata"]["next_offset"] == 202
    assert result["metadata"]["total_is_exact"] is True


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"limit": 0}, "limit must be"),
        ({"limit": 1001}, "limit must be"),
        ({"limit": True}, "limit must be"),
        ({"offset": -1}, "offset must be"),
        ({"offset": 1.5}, "offset must be"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, message):
    result = _tool().run(arguments)
    assert result["status"] == "error"
    assert message in result["error"]
