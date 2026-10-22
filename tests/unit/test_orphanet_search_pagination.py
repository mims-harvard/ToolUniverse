from unittest.mock import Mock, patch

import pytest

from tooluniverse.orphanet_tool import OrphanetTool


@pytest.mark.parametrize(
    ("operation", "arguments"),
    [
        ("search_diseases", {"query": "syndrome"}),
        ("search_by_name", {"name": "syndrome", "exact": False}),
    ],
)
def test_orphanet_search_pages_are_recoverable(operation, arguments):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {"ORPHAcode": str(i), "Preferred term": f"Syndrome {i}"}
        for i in range(7)
    ]
    tool = OrphanetTool({"name": "test", "fields": {"operation": operation}})

    with patch("tooluniverse.orphanet_tool.requests.get", return_value=response):
        first = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 0})["data"]
        second = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 3})["data"]
        tail = tool.run({"operation": operation, **arguments, "limit": 3, "offset": 6})["data"]

    assert [r["ORPHAcode"] for r in first["results"]] == ["0", "1", "2"]
    assert [r["ORPHAcode"] for r in second["results"]] == ["3", "4", "5"]
    assert [r["ORPHAcode"] for r in tail["results"]] == ["6"]
    assert first["has_more"] is True
    assert first["next_offset"] == 3
    assert tail["has_more"] is False
    assert tail["next_offset"] is None
