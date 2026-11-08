"""The three vacuous schema shapes must fail, not pass.

`scripts/audit_declared_return_fields.py` measures the second half of the
field axis: a field the wrapper returns that the `return_schema` does not
declare. Its whole value depends on not being fooled by a schema that
declares nothing, and all three shapes that fool a naive walk are in this
catalogue -- they are why `Harmonizome_search`, `Alliance_get_gene_orthologs`'s
paralogs and the FlyBase/ZFIN ortholog rows went several rounds with real
fields undeclared.

These run the walker alone, over literals. No network, no tool loading.
"""

import importlib.util
import pathlib

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "audit_declared_return_fields.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("declared_return_fields", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = _module()
undeclared = AUDIT.undeclared
LEVEL = AUDIT.UNDECLARED_LEVEL


def test_a_declared_field_is_not_reported():
    schema = {
        "oneOf": [
            {"type": "object", "properties": {"symbol": {"type": "string"}}},
            {"type": "object", "properties": {"error": {"type": "string"}}},
        ]
    }
    assert undeclared({"symbol": "TP53"}, schema) == []


def test_an_undeclared_field_is_reported_by_path():
    schema = {"type": "object", "properties": {"symbol": {"type": "string"}}}
    assert undeclared({"symbol": "TP53", "synonyms": ["P53"]}, schema) == [".synonyms"]


def test_a_null_or_empty_value_is_not_a_finding():
    """A key whose value is absent everywhere cannot be checked from one call,
    and reporting it would recreate the false-positive class the sibling audit
    had to split out."""
    schema = {"type": "object", "properties": {"symbol": {"type": "string"}}}
    assert undeclared({"symbol": "TP53", "description": None}, schema) == []
    assert undeclared({"symbol": "TP53", "synonyms": []}, schema) == []


def test_an_array_schema_descends_into_its_items():
    schema = {
        "oneOf": [
            {"type": "array", "items": {"type": "object", "properties": {
                "pdb_id": {"type": "string"}}}},
            {"type": "object", "properties": {"error": {"type": "string"}}},
        ]
    }
    rows = [{"pdb_id": "1uaz", "species": "Halobacterium sp."}]
    assert undeclared(rows, schema) == ["[].species"]


def test_an_array_with_empty_items_is_not_a_pass():
    """Harmonizome_search's shape: `{"type": "array", "items": {}}`, which
    declared neither of the two fields a round had just added to its rows."""
    schema = {"type": "array", "items": {}}
    found = undeclared([{"symbol": "TP53", "synonyms": ["P53"]}], schema)
    assert found == [f"[].{LEVEL}"], found


def test_an_array_with_no_items_at_all_is_not_a_pass():
    schema = {"type": "array"}
    assert undeclared([{"symbol": "TP53"}], schema) == [f"[]{LEVEL}"]


def test_a_bare_object_as_items_is_not_a_pass():
    """Alliance_get_gene_orthologs' `paralogs`, whose rows carry ten fields."""
    schema = {
        "type": "object",
        "properties": {"paralogs": {"type": "array", "items": {"type": "object"}}},
    }
    found = undeclared({"paralogs": [{"paralog_symbol": "Pax7", "rank": 1}]}, schema)
    assert found == [f".paralogs[].{LEVEL}"], found


def test_additional_properties_is_the_honest_open_level():
    """A map keyed by a value out of the data declares its values, not its keys:
    `synonym_type_counts` cannot list TRADE_NAME and ATC in advance."""
    schema = {
        "type": "object",
        "properties": {
            "synonym_type_counts": {
                "type": "object",
                "additionalProperties": {"type": "integer"},
            }
        },
    }
    value = {"synonym_type_counts": {"TRADE_NAME": 64, "ATC": 1}}
    assert undeclared(value, schema) == []


def test_an_open_object_without_additional_properties_is_reported():
    schema = {"type": "object", "properties": {"counts": {"type": "object"}}}
    assert undeclared({"counts": {"TRADE_NAME": 64}}, schema) == [f".counts.{LEVEL}"]


def test_the_error_branch_declares_fields_at_the_same_level():
    """A success schema plus an error schema is this repo's idiom, and a field
    named only in the error branch is still declared."""
    schema = {
        "oneOf": [
            {"type": "object", "properties": {"rows": {"type": "array"}}},
            {"type": "object", "properties": {"error": {"type": "string"}}},
        ]
    }
    assert undeclared({"error": "not found"}, schema) == []


def test_a_shard_is_a_slice_of_the_sorted_names():
    names = ["d", "a", "c", "b"]
    assert AUDIT.select_shard(names, "0/2") == ["a", "c"]
    assert AUDIT.select_shard(names, "1/2") == ["b", "d"]
    assert AUDIT.select_shard(names, None) == names
    with pytest.raises(SystemExit):
        AUDIT.select_shard(names, "2/2")


def test_the_catalogue_is_the_catalogue():
    """A smoke check that the loader sees the configs, so a rename of the data
    directory cannot leave the script silently auditing nothing."""
    cfgs = AUDIT.catalogue()
    assert len(cfgs) > 2000
    assert "GOAPI_get_gene_functions" in cfgs
