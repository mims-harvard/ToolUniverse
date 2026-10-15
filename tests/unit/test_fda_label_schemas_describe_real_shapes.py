"""openFDA label sections are arrays of strings, not nulls.

16 tools in fda_drug_labeling_tools.json declared their own result field as
`{"type": "null"}` -- the shape a schema generator records when it samples one
label that happens to lack that section. Every call that did return the section
then failed validation, which is how repairing 27 placeholder test_examples
immediately surfaced 10 schema mismatches that the broken examples had been
hiding: the examples never reached validation.

Both shapes are real. The mismatches were reported at `results->4->field` with
rows 0-3 passing, so some matched labels carry the section and some do not.
`["array", "null"]` is what openFDA actually returns, confirmed field by field
against live records before the schemas were rewritten.

This guard is scoped to this one file on purpose. 221 nodes across 78 tools
carry `{"type": "null"}` repo-wide, so asserting it everywhere would fail; the
rest are tracked separately rather than papered over here.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src" / "tooluniverse" / "data" / "fda_drug_labeling_tools.json"
)


def _result_item_properties(tool):
    schema = tool.get("return_schema") or {}
    results = (schema.get("properties") or {}).get("results") or {}
    return (results.get("items") or {}).get("properties") or {}


def test_no_fda_label_result_field_is_typed_null():
    tools = json.loads(CONFIG.read_text(encoding="utf-8"))
    offenders = [
        f"{tool['name']}.{field}"
        for tool in tools
        for field, spec in _result_item_properties(tool).items()
        if isinstance(spec, dict) and spec.get("type") == "null"
    ]

    assert not offenders, (
        "These result fields are declared `{\"type\": \"null\"}`, so any call "
        "that actually returns the label section fails its own schema:\n  "
        + "\n  ".join(offenders)
    )


def test_no_fda_label_example_uses_a_placeholder_value():
    """`E11.9` is an ICD-10 code and the pangram is a typing test.

    Neither belongs in a label-text search. They were templated across this
    file and made 12 tools unable to match anything.
    """
    tools = json.loads(CONFIG.read_text(encoding="utf-8"))
    junk = ("E11.9", "quick brown fox", "lorem ipsum")
    offenders = [
        f"{tool['name']} example {index + 1}: {key}={value!r}"
        for tool in tools
        for index, example in enumerate(tool.get("test_examples") or [])
        if isinstance(example, dict)
        for key, value in example.items()
        if isinstance(value, str) and any(j.lower() in value.lower() for j in junk)
    ]

    assert not offenders, "Placeholder values in test_examples:\n  " + "\n  ".join(
        offenders
    )
