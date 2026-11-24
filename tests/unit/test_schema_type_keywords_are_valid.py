"""Every `type` in a tool's parameter or return schema must be valid JSON Schema.

A `type` list has to hold unique names from the seven JSON Schema types.
GenomeNexus_annotate_mutation declared `["object", "null", "boolean", "array",
"object", "null"]` and MouseMine_search declared that and `["integer", "null",
"boolean", "array", "object", "null"]`, so `jsonschema` rejected the schema
itself and never checked the result: scripts/test_new_tools.py reported every
example of both tools as "Schema Invalid", and the weekly sweep listed
genome_nexus and mousemine as failing.

A full meta-schema check over every schema finds the same two, but takes over a
minute, so this checks the keyword that broke.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}

# Keywords whose value is one subschema, a list of them, or a map of them.
ONE = ("items", "additionalProperties", "not", "if", "then", "else", "contains")
MANY = ("oneOf", "anyOf", "allOf", "prefixItems")
MAP = ("properties", "patternProperties", "$defs", "definitions")


def _type_errors(schema, path):
    if not isinstance(schema, dict):
        return []
    errors = []
    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        if (
            not names
            or not all(isinstance(n, str) and n in TYPES for n in names)
            or len(set(names)) != len(names)
        ):
            errors.append(f"{path}/type = {declared!r}")
    for key in ONE:
        sub = schema.get(key)
        if isinstance(sub, list):
            for i, item in enumerate(sub):
                errors += _type_errors(item, f"{path}/{key}/{i}")
        else:
            errors += _type_errors(sub, f"{path}/{key}")
    for key in MANY:
        for i, item in enumerate(schema.get(key) or []):
            errors += _type_errors(item, f"{path}/{key}/{i}")
    for key in MAP:
        for name, item in (schema.get(key) or {}).items():
            errors += _type_errors(item, f"{path}/{key}/{name}")
    return errors


def _tool_configs():
    for path in sorted(DATA.glob("*.json")):
        configs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(configs, list):
            continue
        for config in configs:
            if isinstance(config, dict) and "name" in config:
                yield path.name, config


def test_every_schema_type_is_a_list_of_unique_json_types():
    failures = []
    for file_name, config in _tool_configs():
        for key in ("parameter", "return_schema"):
            for error in _type_errors(config.get(key), key):
                failures.append(f"{file_name} {config['name']}: {error}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": ["object", "null", "object"]},
        {"type": "obj"},
        {"type": []},
        {"properties": {"x": {"items": {"type": ["string", "string"]}}}},
        {"oneOf": [{"additionalProperties": {"type": "float"}}]},
    ],
)
def test_the_check_catches_a_bad_type(schema):
    assert _type_errors(schema, "s")


def test_a_property_named_type_is_not_read_as_the_keyword():
    schema = {"type": "object", "properties": {"type": {"type": "string"}}}
    assert _type_errors(schema, "s") == []
