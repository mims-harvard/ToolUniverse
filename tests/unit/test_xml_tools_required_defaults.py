"""Regression guard for Fix-R10C-2: 19 XMLTool-family tools (drugbank_*,
mesh_*) declared `default` values for case_sensitive/exact_match/limit but
ALSO listed those same params in `required`, making the declared defaults
completely unusable -- every caller had to always pass all 4 params
explicitly, defeating the point of having defaults at all (confirmed live:
{"query": "clopidogrel"} alone errored with
"'case_sensitive' is a required property" before the fix). Removed the
defaulted params from `required`, keeping only the genuinely-required
search field.
"""

import json

import jsonschema
import pytest

pytestmark = pytest.mark.unit


def _load_tools():
    with open("src/tooluniverse/data/xml_tools.json") as f:
        return json.load(f)


AFFECTED_TOOLS = [
    "drugbank_get_drug_interactions_by_drug_name_or_id",
    "drugbank_get_drug_basic_info_by_drug_name_or_id",
    "mesh_get_subjects_by_subject_name",
]


@pytest.mark.parametrize("tool_name", AFFECTED_TOOLS)
def test_query_alone_satisfies_schema(tool_name):
    tools = _load_tools()
    schema = next(t for t in tools if t["name"] == tool_name)["parameter"]
    jsonschema.validate({"query": "clopidogrel"}, schema)


@pytest.mark.parametrize("tool_name", AFFECTED_TOOLS)
def test_only_query_remains_required(tool_name):
    tools = _load_tools()
    schema = next(t for t in tools if t["name"] == tool_name)["parameter"]
    assert schema["required"] == ["query"]


def test_no_xml_tool_has_a_defaulted_required_param():
    """No tool in the file should still have this anti-pattern anywhere."""
    tools = _load_tools()
    for t in tools:
        param = t.get("parameter", {})
        props = param.get("properties", {})
        required = set(param.get("required", []))
        offenders = [
            k for k in required if k in props and "default" in props[k]
        ]
        assert not offenders, f"{t['name']} still requires defaulted param(s) {offenders}"
