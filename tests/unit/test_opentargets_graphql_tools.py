"""OpenTargets_query_graphql / OpenTargets_get_graphql_schema (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _post(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    sent = []

    def fake(session, method, url, json=None, **kwargs):
        sent.append(json)
        return response

    return fake, sent


def _query(arguments, payload, status=200):
    from tooluniverse.opentargets_graphql_tool import OpenTargetsGraphQLQueryTool

    tool = OpenTargetsGraphQLQueryTool({"name": "OpenTargets_query_graphql"})
    fake, sent = _post(payload, status)
    with patch("tooluniverse.opentargets_graphql_tool.request_with_retry", fake):
        return tool.run(arguments), sent


def _schema(arguments, payload):
    from tooluniverse.opentargets_graphql_tool import OpenTargetsGraphQLSchemaTool

    tool = OpenTargetsGraphQLSchemaTool({"name": "OpenTargets_get_graphql_schema"})
    fake, sent = _post(payload)
    with patch("tooluniverse.opentargets_graphql_tool.request_with_retry", fake):
        return tool.run(arguments), sent


def test_query_returns_data_and_forwards_variables():
    payload = {"data": {"disease": {"id": "MONDO_0004975"}}}
    result, sent = _query(
        {
            "query": "query($id: String!){disease(efoId:$id){id}}",
            "variables": '{"id": "MONDO_0004975"}',
        },
        payload,
    )
    assert result == {"status": "success", "data": payload["data"]}
    assert sent[0]["variables"] == {"id": "MONDO_0004975"}


def test_graphql_error_without_data_is_an_error_with_the_server_message():
    result, _ = _query(
        {"query": "{ nope }"},
        {"errors": [{"message": "Cannot query field 'nope' on type 'Query'"}]},
        status=400,
    )
    assert result["status"] == "error"
    assert "Cannot query field 'nope'" in result["error"]


def test_partial_data_with_errors_keeps_data_and_reports_errors():
    result, _ = _query(
        {"query": '{ target(ensemblId:"X"){id} }'},
        {"data": {"target": None}, "errors": [{"message": "not found"}]},
    )
    assert result["status"] == "success"
    assert result["metadata"]["graphql_errors"] == [{"message": "not found"}]


def test_mutations_and_bad_variables_are_refused_without_a_request():
    result, sent = _query({"query": "mutation { x }"}, {})
    assert result["status"] == "error" and sent == []
    result, sent = _query({"query": "{ a }", "variables": "{not json"}, {})
    assert result["status"] == "error" and sent == []


def _ref(name, kind="SCALAR"):
    return {"kind": kind, "name": name, "ofType": None}


def test_schema_renders_graphql_type_notation():
    non_null_list = {
        "kind": "NON_NULL",
        "name": None,
        "ofType": {
            "kind": "LIST",
            "name": None,
            "ofType": {
                "kind": "NON_NULL",
                "name": None,
                "ofType": _ref("Target", "OBJECT"),
            },
        },
    }
    payload = {
        "data": {
            "__type": {
                "name": "Disease",
                "kind": "OBJECT",
                "description": "d",
                "fields": [
                    {
                        "name": "targets",
                        "description": None,
                        "args": [
                            {"name": "page", "type": _ref("Pagination", "INPUT_OBJECT")}
                        ],
                        "type": non_null_list,
                    }
                ],
                "inputFields": None,
                "enumValues": None,
            }
        }
    }
    result, sent = _schema({"type_name": "Disease"}, payload)
    field = result["data"]["fields"][0]
    assert field["type"] == "[Target!]!"
    assert field["arguments"] == {"page": "Pagination"}
    assert sent[0]["variables"] == {"name": "Disease"}


def test_unknown_type_name_is_an_error():
    result, _ = _schema({"type_name": "Nope"}, {"data": {"__type": None}})
    assert result["status"] == "error"
    assert "case-sensitive" in result["error"]


def test_root_schema_lists_queries_and_type_names():
    payload = {
        "data": {
            "__schema": {
                "queryType": {
                    "fields": [
                        {
                            "name": "target",
                            "description": "d",
                            "args": [
                                {
                                    "name": "ensemblId",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": _ref("String"),
                                    },
                                }
                            ],
                            "type": _ref("Target", "OBJECT"),
                        }
                    ]
                },
                "types": [
                    {"name": "Target", "kind": "OBJECT"},
                    {"name": "__Type", "kind": "OBJECT"},
                    {"name": "String", "kind": "SCALAR"},
                ],
            }
        }
    }
    result, _ = _schema({}, payload)
    assert result["data"]["queries"][0]["arguments"] == {"ensemblId": "String!"}
    assert result["data"]["type_names"] == ["Target"]
