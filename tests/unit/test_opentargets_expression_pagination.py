"""OpenTargets_get_target_expression_by_ensemblID must paginate, and must say so.

Regression: the tool's GraphQL query called ``baselineExpression { ... }`` with
no ``page`` argument, so the OpenTargets default page size of 25 applied
silently. For NLRP7 (ENSG00000167634) the response advertised
``count: 1409`` and delivered 25 rows -- the remaining 1384 were unreachable
because the tool exposed no pagination parameter at all. Those 25 rows held
exactly one GTEx tissue and omitted testis (median 7.53), the gene's
highest-expressing GTEx tissue, so the truncated answer was well-formed,
confident and biologically wrong.

The fix wires ``page: {index: $index, size: $size}`` into the query (default
size 250, API maximum 3000) and annotates the response with
``returned`` / ``truncated`` / ``page`` so a caller can tell "250 of 1409"
from "1409 of 1409" without counting array elements.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import tooluniverse
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

TOOL_NAME = "OpenTargets_get_target_expression_by_ensemblID"
_CONFIG = Path(tooluniverse.__file__).parent / "data" / "opentarget_tools.json"


def _tool_config():
    for entry in json.loads(_CONFIG.read_text()):
        if isinstance(entry, dict) and entry.get("name") == TOOL_NAME:
            return entry
    raise AssertionError(f"{TOOL_NAME} not found in {_CONFIG}")


def _mock_post(payload):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


def _expression_payload(count, n_rows):
    return {
        "data": {
            "target": {
                "id": "ENSG00000167634",
                "approvedSymbol": "NLRP7",
                "baselineExpression": {
                    "count": count,
                    "rows": [
                        {
                            "datasourceId": "gtex",
                            "median": 1.0,
                            "tissueBiosample": {"biosampleName": f"tissue{i}"},
                        }
                        for i in range(n_rows)
                    ],
                },
            }
        }
    }


def test_query_paginates_baseline_expression():
    """The shipped GraphQL string must pass a page argument, not rely on the
    API's silent default of 25."""
    query = _tool_config()["query_schema"]
    assert "baselineExpression(page:" in query.replace(" (", "(")
    assert "$index" in query and "$size" in query
    # A bare `baselineExpression {` (no page argument) is the defect.
    assert "baselineExpression {" not in query


def test_size_and_index_parameters_are_exposed():
    props = _tool_config()["parameter"]["properties"]
    assert props["size"]["type"] == "integer"
    # Default must be materially better than the API's silent 25.
    assert props["size"]["default"] == 250
    # 3000 is the API's hard ceiling (probed live: 5000 -> pagination error).
    assert props["size"]["maximum"] == 3000
    assert props["index"]["type"] == "integer"
    assert props["index"]["default"] == 0


def test_return_schema_advertises_partialness_fields():
    target_props = _tool_config()["return_schema"]["oneOf"][0]["properties"]["target"][
        "properties"
    ]
    expr_props = target_props["baselineExpression"]["properties"]
    assert expr_props["returned"]["type"] == "integer"
    assert expr_props["truncated"]["type"] == "boolean"
    assert "page" in expr_props


def test_description_documents_pagination():
    description = _tool_config()["description"]
    assert "truncated" in description
    assert "3000" in description


def test_partial_response_is_flagged():
    tool = OpentargetTool(_tool_config())
    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(_expression_payload(1409, 250))
        result = tool.run({"ensemblId": "ENSG00000167634"})

    # The default page size must reach the API, not the API's own default of 25.
    sent = post.call_args.kwargs["json"]["variables"]
    assert sent["size"] == 250
    assert sent["index"] == 0

    expr = result["data"]["target"]["baselineExpression"]
    assert expr["count"] == 1409
    assert expr["returned"] == 250
    assert expr["truncated"] is True
    assert expr["page"] == {"index": 0, "size": 250}
    note = result["metadata"]["note"]
    assert "250 of 1409" in note


def test_complete_response_is_not_flagged_as_truncated():
    """A target whose rows all fit in one page must not claim truncation."""
    tool = OpentargetTool(_tool_config())
    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(_expression_payload(42, 42))
        result = tool.run({"ensemblId": "ENSG00000167634"})

    expr = result["data"]["target"]["baselineExpression"]
    assert expr["returned"] == 42
    assert expr["truncated"] is False
    assert "note" not in result.get("metadata", {})


def test_later_page_accounts_for_skipped_rows():
    """returned=700 at index=1 means 1400 rows seen, so 1409 is still partial,
    while index=1 of a 500-row page covering the tail is complete."""
    tool = OpentargetTool(_tool_config())
    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(_expression_payload(1409, 700))
        partial = tool.run({"ensemblId": "ENSG00000167634", "size": 700, "index": 1})
    assert partial["data"]["target"]["baselineExpression"]["truncated"] is True

    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(_expression_payload(900, 400))
        done = tool.run({"ensemblId": "ENSG00000167634", "size": 500, "index": 1})
    assert done["data"]["target"]["baselineExpression"]["truncated"] is False


def test_oversized_page_is_clamped_to_api_maximum():
    """The API rejects size > 3000 outright; clamp instead of forwarding it."""
    tool = OpentargetTool(_tool_config())
    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(_expression_payload(1409, 1409))
        tool.run({"ensemblId": "ENSG00000167634", "size": 99999})
    assert post.call_args.kwargs["json"]["variables"]["size"] == 3000
