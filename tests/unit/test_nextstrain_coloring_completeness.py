"""Nextstrain dataset summaries must retain every coloring dimension."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.nextstrain_tool import NextstrainTool


pytestmark = pytest.mark.unit


def test_all_colorings_are_returned_not_first_fifteen():
    response = MagicMock()
    response.json.return_value = {
        "meta": {
            "title": "test",
            "colorings": [{"key": f"color_{index}"} for index in range(23)],
        },
        "tree": {"name": "root"},
    }
    tool = NextstrainTool({"fields": {"endpoint_type": "get_dataset"}})

    with patch("tooluniverse.nextstrain_tool.requests.get", return_value=response):
        result = tool.run({"dataset": "flu/seasonal/h3n2/ha/2y"})

    data = result["data"]
    assert data["available_colorings"] == [f"color_{index}" for index in range(23)]
    assert data["available_colorings_count"] == 23
    assert data["available_colorings_complete"] is True
