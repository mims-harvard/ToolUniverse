"""Unit test: OpenTargets associated-targets pagination + size-default honoring.

Regression: OpenTargets_get_associated_targets_by_disease_efoId hard-capped at
25 rows (the API default) and silently ignored size/page -- for LQTS
(MONDO_0019171) count=2490 but only 25 targets were reachable. Separately,
GraphQLTool.run injected a hardcoded default size of 5 whenever a tool declared
a `size` param without a value, silently overriding a tool's own larger schema
default (e.g. OpenTargets_get_evidence_by_datasource documents 50 but got 5).
"""
import glob
import json
from unittest.mock import patch

import pytest

from tooluniverse.graphql_tool import GraphQLTool


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


@pytest.mark.unit
def test_associated_targets_query_paginates_and_declares_size():
    cfg = _load("OpenTargets_get_associated_targets_by_disease_efoId")
    query = cfg["query_schema"]
    assert "associatedTargets(page: {index: $index, size: $size})" in query
    assert "$size: Int = 50" in query
    props = cfg["parameter"]["properties"]
    assert props["size"]["default"] == 50
    assert "index" in props


@pytest.mark.unit
def test_graphqltool_honors_declared_size_default_not_hardcoded_5():
    cfg = {
        "name": "x",
        "query_schema": "query q($size: Int) { thing(size: $size) }",
        "parameter": {"type": "object", "properties": {"size": {"type": "integer", "default": 50}}},
    }
    tool = GraphQLTool(cfg, "https://example.test/graphql")
    captured = {}

    def fake_exec(endpoint_url, query, variables=None):
        captured["variables"] = variables
        return {"data": {"thing": 1}}

    with patch("tooluniverse.graphql_tool.execute_query", side_effect=fake_exec):
        tool.run({})
    assert captured["variables"]["size"] == 50  # not the hardcoded 5


@pytest.mark.unit
def test_graphqltool_falls_back_to_5_when_no_size_default():
    cfg = {
        "name": "x",
        "query_schema": "query q($size: Int) { thing(size: $size) }",
        "parameter": {"type": "object", "properties": {"size": {"type": "integer"}}},
    }
    tool = GraphQLTool(cfg, "https://example.test/graphql")
    captured = {}

    def fake_exec(endpoint_url, query, variables=None):
        captured["variables"] = variables
        return {"data": {"thing": 1}}

    with patch("tooluniverse.graphql_tool.execute_query", side_effect=fake_exec):
        tool.run({})
    assert captured["variables"]["size"] == 5  # unchanged fallback
