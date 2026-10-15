"""Blank Single Cell Portal searches must fail locally without an HTTP call."""

from unittest.mock import patch

import pytest

from tooluniverse.single_cell_portal_tool import SingleCellPortalTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("query", [None, "", "   ", "\t"])
def test_blank_query_is_a_local_validation_error(query):
    tool = SingleCellPortalTool(
        {"name": "scp_search_studies", "fields": {"operation": "search_studies"}}
    )
    arguments = {"query": query} if query is not None else {}
    with patch("tooluniverse.single_cell_portal_tool.requests.get") as get:
        result = tool.run(arguments)

    get.assert_not_called()
    assert result["status"] == "error"
    assert "query is required" in result["error"]
