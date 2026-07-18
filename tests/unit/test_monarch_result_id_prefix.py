"""Regression guard for Fix-R16A-2: Monarch's search endpoint has no
server-side namespace filter (confirmed live: a "prefix" query param is
silently ignored) and its "category" filter matches equivalent terms
across multiple ontologies (HP, MP, UPHENO, ...) -- so
get_HPO_ID_by_phenotype could return a non-HPO term as its top-ranked hit
despite its name promising HPO IDs. `MonarchTool.run()` now supports an
opt-in `result_id_prefix` config key that client-side filters `items` by ID
prefix, over-fetching first so the returned count still matches what the
caller requested. The filter must stay opt-in so it doesn't affect other
Monarch-type tools (e.g. gene/disease search) that don't declare it.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.restful_tool import MonarchTool

pytestmark = pytest.mark.unit

MIXED_NAMESPACE_RESPONSE = {
    "limit": 30,
    "offset": 0,
    "total": 386,
    "items": [
        {"id": "MP:0002064", "name": "seizures"},
        {"id": "HP:0001250", "name": "Seizure"},
        {"id": "UPHENO:7000475", "name": "focal seizures"},
        {"id": "HP:0011145", "name": "Symptomatic seizures"},
        {"id": "HP:0031165", "name": "Multifocal seizures"},
        {"id": "HP:0002173", "name": "Hypoglycemic seizures"},
        {"id": "HP:0002199", "name": "Hypocalcemic seizures"},
        {"id": "HP:0010819", "name": "Atonic seizure"},
        {"id": "HP:0020219", "name": "Motor seizure"},
        {"id": "HP:0031951", "name": "Nocturnal seizures"},
    ],
}


def _hpo_tool():
    return MonarchTool(
        {
            "name": "get_HPO_ID_by_phenotype",
            "tool_url": "/search",
            "parameter": {"properties": {}},
            "query_schema": {
                "query": None,
                "category": ["biolink:PhenotypicFeature"],
                "limit": 20,
                "offset": 0,
            },
            "result_id_prefix": "HP:",
        }
    )


def _generic_tool():
    return MonarchTool(
        {
            "name": "Monarch_search_gene",
            "tool_url": "/search",
            "parameter": {"properties": {}},
            "query_schema": {"query": None, "limit": 20, "offset": 0},
        }
    )


def test_result_id_prefix_filters_out_other_namespaces():
    tool = _hpo_tool()
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query",
        return_value=dict(MIXED_NAMESPACE_RESPONSE),
    ):
        result = tool.run({"query": "seizures", "limit": 10})

    ids = [item["id"] for item in result["data"]["items"]]
    assert all(i.startswith("HP:") for i in ids)
    assert "MP:0002064" not in ids
    assert "UPHENO:7000475" not in ids


def test_result_id_prefix_preserves_requested_count():
    tool = _hpo_tool()
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query",
        return_value=dict(MIXED_NAMESPACE_RESPONSE),
    ):
        result = tool.run({"query": "seizures", "limit": 8})

    assert len(result["data"]["items"]) == 8


def test_overfetch_requests_a_larger_limit_from_the_api():
    tool = _hpo_tool()
    captured = {}

    def fake_query(endpoint_url, variables=None):
        captured["variables"] = variables
        return dict(MIXED_NAMESPACE_RESPONSE)

    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query", side_effect=fake_query
    ):
        tool.run({"query": "seizures", "limit": 10})

    assert captured["variables"]["limit"] == 30


def test_tools_without_result_id_prefix_are_unaffected():
    tool = _generic_tool()
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query",
        return_value=dict(MIXED_NAMESPACE_RESPONSE),
    ):
        result = tool.run({"query": "SCN2A", "limit": 10})

    ids = [item["id"] for item in result["data"]["items"]]
    assert ids == [item["id"] for item in MIXED_NAMESPACE_RESPONSE["items"]]
