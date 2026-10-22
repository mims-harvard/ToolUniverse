from unittest.mock import patch

import pytest

from tooluniverse.eol_tool import EOLTool


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "endpoint,arguments,error",
    [
        ("pages", {"page_id": "327955"}, "page_id"),
        ("pages", {"page_id": 1, "images_per_page": 76}, "images_per_page"),
        ("pages", {"page_id": 1, "common_name_offset": -1}, "common_name_offset"),
        ("pages", {"page_id": 1, "details": "false"}, "details must be a boolean"),
        ("hierarchy_entries", {"hierarchy_entry_id": True}, "hierarchy_entry_id"),
        (
            "hierarchy_entries",
            {"hierarchy_entry_id": 1, "child_limit": 0},
            "child_limit",
        ),
        ("collections", {"collection_id": 1, "page": 0}, "page"),
        ("collections", {"collection_id": 1, "per_page": 501}, "per_page"),
        ("collections", {"collection_id": 1, "filter": "bogus"}, "filter"),
    ],
)
def test_invalid_controls_are_rejected_before_network(endpoint, arguments, error):
    tool = EOLTool({"fields": {"endpoint": endpoint}})
    with patch("tooluniverse.eol_tool._eol_http_get") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()
