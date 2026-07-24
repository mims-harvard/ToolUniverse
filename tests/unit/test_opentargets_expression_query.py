"""OpenTargets_get_target_expression_by_ensemblID must not request fields
removed from the schema.

Regression (Fix-R23A-1): OpenTargets removed the `Target.expressions` field
entirely (confirmed live via GraphQL introspection: querying it now errors
"Cannot query field 'expressions' on type 'Target'"). The replacement is
`baselineExpression { count rows { datasourceId tissueBiosample { ... }
median min max unit } }`, a differently-shaped biosample/datasource model
rather than the old tissue/rna/protein triple. The query must use the
current field names.
"""

import json
import os

import pytest

pytestmark = pytest.mark.unit

_CONFIG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "opentarget_tools.json",
)


def _tool(name):
    with open(_CONFIG) as fh:
        for t in json.load(fh):
            if isinstance(t, dict) and t.get("name") == name:
                return t
    raise AssertionError(f"{name} not found in opentarget_tools.json")


def test_expression_query_uses_current_fields():
    tool = _tool("OpenTargets_get_target_expression_by_ensemblID")
    query = tool.get("query_schema", "")
    assert "expressions" not in query
    assert "baselineExpression" in query
    assert "tissueBiosample" in query


def test_expression_return_schema_matches_query_shape():
    tool = _tool("OpenTargets_get_target_expression_by_ensemblID")
    # Fix #288: return_schema.oneOf[0] is the promoted data sub-schema itself
    # now, not a {status, data} envelope wrapping it -- "target" is a direct
    # property, not nested under an extra "data" key.
    target_props = tool["return_schema"]["oneOf"][0]["properties"]["target"][
        "properties"
    ]
    assert "baselineExpression" in target_props
    assert "expressions" not in target_props
    row_props = target_props["baselineExpression"]["properties"]["rows"]["items"][
        "properties"
    ]
    assert "datasourceId" in row_props
    assert "tissueBiosample" in row_props


def test_expression_has_real_example():
    tool = _tool("OpenTargets_get_target_expression_by_ensemblID")
    examples = tool.get("test_examples", [])
    assert examples and examples[0].get("ensemblId")
