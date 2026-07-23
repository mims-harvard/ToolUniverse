"""Unit test: MonarchTool (restful) normalizes underscore CURIEs in the URL path.

Regression: get_phenotype_by_HPO_ID (type Monarch) substituted the id straight
into /entity/{id}, so the underscore CURIE OpenTargets emits ('HP_0000639')
404'd and Monarch returned "Entity not found" wrapped in status:success -- a
silent false-empty breaking the OpenTargets -> Monarch phenotype chain.
"""
from unittest.mock import patch

import pytest

from tooluniverse.restful_tool import MonarchTool, _normalize_curie


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("HP_0000639", "HP:0000639"),
        ("MONDO_0008765", "MONDO:0008765"),
        ("HP:0000639", "HP:0000639"),
        ("Nystagmus", "Nystagmus"),
    ],
)
def test_normalize_curie(raw, expected):
    assert _normalize_curie(raw) == expected


@pytest.mark.unit
def test_url_key_is_normalized_to_colon():
    cfg = {
        "name": "get_phenotype_by_HPO_ID",
        "type": "Monarch",
        "tool_url": "/entity/{url_key}",
        "query_schema": {"url_key": "id", "id": ""},
        "parameter": {"type": "object", "properties": {"id": {"type": "string"}}},
    }
    tool = MonarchTool(cfg)
    captured = {}

    def fake_query(endpoint_url, variables=None):
        captured["url"] = endpoint_url
        return {"id": "HP:0000639", "name": "Nystagmus"}

    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query", side_effect=fake_query
    ):
        tool.run({"id": "HP_0000639"})
    assert captured["url"].endswith("/entity/HP:0000639")
