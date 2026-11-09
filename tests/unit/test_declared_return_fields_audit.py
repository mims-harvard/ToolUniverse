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


def test_a_oneOf_branch_may_declare_an_open_level_with_additionalProperties():
    """Merging the branches made the recommended form impossible to use.

    This script's own doctrine is that `additionalProperties` with a value
    shape is the honest way to declare a level keyed out of the data. But the
    walker merged the `properties` of every branch into one set, so a success
    branch that declares its open level with additionalProperties and no
    properties, beside this repo's conventional error branch declaring
    `error`, merged to declared={"error"}: non-empty, so the
    additionalProperties was never consulted and every data key was reported
    undeclared.

    InterPro_get_residue_annotations is exactly that shape -- 75 signature
    accessions as keys -- and it could not be declared at all until the
    branches were evaluated independently, which is what oneOf means.
    """
    schema = {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {"accession": {"type": "string"}},
                },
            },
            {"type": "object", "properties": {"error": {"type": "string"}}},
        ]
    }
    value = {"PIRSR000605-51": {"accession": "PIRSR000605-51"}}
    assert undeclared(value, schema) == []


def test_evaluating_branches_independently_still_reports_a_real_gap():
    """The permissive reading must not swallow a finding.

    Each branch is walked alone and the fewest findings win, so the risk is
    that a loose branch hides a gap in the strict one. It does not: a key no
    branch declares is still reported, and so is a gap nested under a
    declared property.
    """
    err = {"type": "object", "properties": {"error": {"type": "string"}}}
    flat = {
        "oneOf": [{"type": "object", "properties": {"a": {}, "b": {}}}, err]
    }
    assert undeclared({"a": 1, "b": 2, "c": 3}, flat) == [".c"]

    nested = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "a": {"type": "object", "properties": {"x": {}}}
                },
            },
            err,
        ]
    }
    assert undeclared({"a": {"x": 1, "y": 2}}, nested) == [".a.y"]

    # additionalProperties: true says the level is open without saying what is
    # in it, so it declares nothing a reader can act on and the level itself
    # is the finding.
    boolean = {"oneOf": [{"type": "object", "additionalProperties": True}, err]}
    assert undeclared({"a": 1}, boolean) == [f".{LEVEL}"]
