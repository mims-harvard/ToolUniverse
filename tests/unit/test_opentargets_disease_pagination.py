"""Regression guard for Fix-R26D-2: OpenTargets_get_diseases_phenotypes_by_
target_ensembl's associatedDiseases query had no `page` argument, so Open
Targets silently applied its default page size (25 rows) regardless of how
many associations actually existed -- confirmed live for SIRT1
(ENSG00000096717): count: 3432 but only 25 rows returned, with no way to
retrieve the other 3407. OpenTargets' associatedDiseases field does accept
a `page: Pagination` argument (confirmed via GraphQL introspection), matching
the same `page: {index, size}` convention already used by several sibling
OpenTarget tools (e.g. OpenTargets_get_target_interactions_by_ensemblID).
Fixed by exposing that argument through the query_schema and parameter
schema instead of silently truncating with no way to page further.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "opentarget_tools.json"
)


def _load_tool_config():
    configs = json.loads(_CONFIG_PATH.read_text())
    for cfg in configs:
        if cfg["name"] == "OpenTargets_get_diseases_phenotypes_by_target_ensembl":
            return cfg
    raise AssertionError("tool config not found")


def _tool():
    cfg = _load_tool_config()
    return OpentargetTool(cfg), cfg


class TestQuerySchemaExposesPagination:
    def test_query_schema_declares_page_variable(self):
        _, cfg = _tool()
        assert "$page: Pagination" in cfg["query_schema"]
        assert "associatedDiseases(page: $page)" in cfg["query_schema"]

    def test_parameter_schema_has_page_object(self):
        _, cfg = _tool()
        page_param = cfg["parameter"]["properties"]["page"]
        assert set(page_param["properties"].keys()) == {"index", "size"}
        assert "ensemblId" in cfg["parameter"]["required"]
        assert "page" not in cfg["parameter"]["required"]


class TestPageArgumentForwarded:
    def test_page_argument_passed_through_as_graphql_variable(self):
        tool, _ = _tool()
        response = MagicMock()
        response.ok = True
        response.json.return_value = {
            "data": {
                "target": {
                    "id": "ENSG00000096717",
                    "associatedDiseases": {"count": 3432, "rows": []},
                }
            }
        }
        with patch(
            "tooluniverse.graphql_tool.requests.post", return_value=response
        ) as mock_post:
            tool.run(
                {
                    "ensemblId": "ENSG00000096717",
                    "page": {"index": 1, "size": 25},
                }
            )

        sent_variables = mock_post.call_args.kwargs["json"]["variables"]
        assert sent_variables["page"] == {"index": 1, "size": 25}
