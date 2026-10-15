"""A Monarch search with no hits must keep the shape of one with hits.

The shared null/empty cleaner removed ``items: []``, so a zero-hit search
returned ``{limit, offset, total}`` and ``data["items"]`` raised KeyError only
when nothing matched. get_HPO_ID_by_phenotype also echoed the over-fetched
page size (3x the request) as ``limit``.
"""

from unittest.mock import patch

import pytest

from tooluniverse.restful_tool import MonarchTool

pytestmark = pytest.mark.unit


def _tool(prefix=None):
    config = {
        "name": "get_HPO_ID_by_phenotype" if prefix else "Monarch_search_gene",
        "tool_url": "/search",
        "parameter": {"properties": {}},
        "query_schema": {"query": None, "limit": 20, "offset": 0},
    }
    if prefix:
        config["result_id_prefix"] = prefix
    return MonarchTool(config)


@pytest.mark.parametrize("prefix", [None, "HP:"])
def test_zero_hit_search_still_has_an_items_list(prefix):
    sent = {}

    def fake(endpoint_url, variables):
        sent.update(variables)
        return {"limit": variables["limit"], "offset": 0, "total": 0, "items": []}

    with patch("tooluniverse.restful_tool.execute_RESTful_query", side_effect=fake):
        result = _tool(prefix).run({"query": "zzqxjvplmk", "limit": 5})

    assert result["status"] == "success"
    assert result["data"]["items"] == []
    assert result["data"]["total"] == 0
    assert result["data"]["limit"] == 5
    if prefix:
        assert sent["limit"] == 15  # the over-fetch still happens upstream


def test_hit_page_reports_the_callers_limit_not_the_over_fetch():
    page = {
        "limit": 6,
        "offset": 0,
        "total": 3,
        "items": [
            {"id": "MP:1", "name": "a"},
            {"id": "HP:1", "name": "b"},
            {"id": "HP:2", "name": "c"},
        ],
    }
    with patch("tooluniverse.restful_tool.execute_RESTful_query", return_value=page):
        result = _tool("HP:").run({"query": "x", "limit": 2})

    assert result["data"]["limit"] == 2
    assert [i["id"] for i in result["data"]["items"]] == ["HP:1", "HP:2"]


def test_other_empty_lists_are_still_removed():
    page = {"limit": 5, "offset": 0, "total": 1, "items": [{"id": "G:1", "xref": []}]}
    with patch("tooluniverse.restful_tool.execute_RESTful_query", return_value=page):
        result = _tool().run({"query": "x", "limit": 5})

    assert result["data"]["items"] == [{"id": "G:1"}]
