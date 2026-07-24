"""
Unit tests for the central "not found" guard in GraphQLTool.

A GraphQL response whose every top-level field is null/empty is stripped to
``{"data": {}}`` by ``remove_none_and_empty_values()``. The base
``GraphQLTool.run`` now reports that as an explicit error instead of a
misleading empty success, so *every* GraphQL-backed tool inherits the
behaviour rather than each one re-implementing it. A genuine empty result set
(e.g. a 0-hit search) keeps its container key and must still succeed.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

MINIMAL_CFG = {
    "name": "dummy_graphql",
    "description": "test-only graphql tool",
    "parameter": {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
    "query_schema": "query($id: String!) { thing(id: $id) { id } }",
    "return_schema": {"type": "object"},
}


def _base_tool():
    from tooluniverse.graphql_tool import GraphQLTool

    return GraphQLTool(MINIMAL_CFG, "https://example.org/graphql")


class TestGraphQLEmptyGuard:
    def test_null_entity_returns_error_with_generic_message(self):
        tool = _base_tool()
        with patch(
            "tooluniverse.graphql_tool.execute_query", return_value={"data": {}}
        ):
            result = tool.run({"id": "does-not-exist"})
        assert result["status"] == "error"
        # The generic message names the arguments so the caller sees what failed.
        assert "does-not-exist" in result["error"]

    def test_zero_hit_search_still_succeeds(self):
        # {"search": {"hits": []}} -> stripped to {"search": {}}: a non-empty
        # container, so it is a legitimate empty *result set*, not "not found".
        tool = _base_tool()
        with patch(
            "tooluniverse.graphql_tool.execute_query",
            return_value={"data": {"search": {}}},
        ):
            result = tool.run({"id": "anything"})
        assert result["status"] == "success"
        assert result["data"] == {"search": {}}

    def test_real_data_succeeds(self):
        tool = _base_tool()
        with patch(
            "tooluniverse.graphql_tool.execute_query",
            return_value={"data": {"thing": {"id": "1"}}},
        ):
            result = tool.run({"id": "1"})
        assert result["status"] == "success"
        assert result["data"]["thing"]["id"] == "1"

    def test_subclass_can_override_message(self):
        from tooluniverse.graphql_tool import GraphQLTool

        class Custom(GraphQLTool):
            def _empty_result_error(self, arguments):
                return "custom-not-found-message"

        tool = Custom(MINIMAL_CFG, "https://example.org/graphql")
        with patch(
            "tooluniverse.graphql_tool.execute_query", return_value={"data": {}}
        ):
            result = tool.run({"id": "x"})
        assert result["status"] == "error"
        assert result["error"] == "custom-not-found-message"


def _load_auditor():
    path = Path(__file__).resolve().parents[2] / "scripts" / "audit_empty_success.py"
    spec = importlib.util.spec_from_file_location("audit_empty_success", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAuditorEmptyDetection:
    def test_is_effectively_empty(self):
        audit = _load_auditor()
        is_empty = audit.is_effectively_empty
        # empty shapes
        assert is_empty(None)
        assert is_empty({})
        assert is_empty([])
        assert is_empty("")
        assert is_empty({"disease": None})
        assert is_empty({"search": {"hits": []}})
        assert is_empty([{}, {"a": []}])
        # content present
        assert not is_empty({"thing": {"id": "1"}})
        assert not is_empty([{"id": 1}])
        assert not is_empty(0)  # a real scalar, even falsy, is content
        assert not is_empty("x")
