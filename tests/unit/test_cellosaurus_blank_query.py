"""Blank Cellosaurus search queries must fail locally without an HTTP call."""

from unittest.mock import patch

import pytest

from tooluniverse.cellosaurus_tool import CellosaurusSearchTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("query", [None, "", "   ", "\t"])
def test_blank_query_is_a_local_validation_error(query):
    tool = CellosaurusSearchTool({"name": "cellosaurus_search_cell_lines"})
    with patch("tooluniverse.cellosaurus_tool.requests.get") as get:
        result = tool.run({"q": query, "size": 2} if query is not None else {"size": 2})

    get.assert_not_called()
    assert result["status"] == "error"
    assert "`q` parameter is required." in result["error"]
