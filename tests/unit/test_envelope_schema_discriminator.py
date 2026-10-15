"""Whether a schema describes the envelope or the payload inside it.

A tool answers {"status": ..., "data": ...}. The runner validates the payload,
not the envelope -- except when the schema is describing the envelope itself,
because unwrapping first would leave the declared `data` property absent and,
nothing being `required`, pass whatever the tool returned.

The check looked only at top-level `properties`, so it missed the 138 schemas
that declare `data` inside a oneOf/anyOf/allOf branch. All six
unified_guideline tools reported "Schema Mismatch: At root: [...]" with both
the tool and the schema correct.

Recursing alone is wrong, which took three attempts to establish. A branch can
declare `data` because the payload has a field of that name:

    IDR               {"data": [...], "meta": {...}}
    Art Institute     {"config", "data", "info", "pagination", "preference"}

Measured: recursing on the key alone fixed unified_guideline and broke idr and
artic -- the same pair an earlier attempt at this broke.

`status` separates them. The envelope is the thing that carries a status, so a
branch describes it only when it declares `status` and `data` together.
Measured across the 13 affected categories: unified_guideline schema_error ->
passed, idr and artic unchanged.
"""

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"


def _runner():
    spec = importlib.util.spec_from_file_location(
        "test_new_tools_envelope", ROOT / "scripts" / "test_new_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema(file_name, tool_name):
    tools = json.loads((DATA / file_name).read_text("utf-8"))
    return next(t for t in tools if t["name"] == tool_name)["return_schema"]


def test_a_top_level_envelope_is_recognised():
    describes = _runner().schema_describes_envelope

    assert describes({"properties": {"status": {}, "data": {}}})


def test_an_envelope_inside_a_oneof_branch_is_recognised():
    """The case that made six correct tools report a schema mismatch."""
    describes = _runner().schema_describes_envelope

    assert describes(
        {
            "oneOf": [
                {"properties": {"status": {}, "data": {}, "metadata": {}}},
                {"properties": {"error": {}}},
            ]
        }
    )


@pytest.mark.parametrize("keyword", ["oneOf", "anyOf", "allOf"])
def test_every_combinator_is_searched(keyword):
    describes = _runner().schema_describes_envelope

    assert describes({keyword: [{"properties": {"status": {}, "data": {}}}]})


def test_a_payload_with_its_own_data_field_is_not_an_envelope():
    """IDR's API answers {"data": [...], "meta": {...}} -- no status."""
    describes = _runner().schema_describes_envelope

    assert not describes({"properties": {"data": {}, "meta": {}}})
    assert not describes(
        {"oneOf": [{"properties": {"config": {}, "data": {}, "info": {}}}]}
    )


def test_the_real_schemas_are_classified_the_way_they_were_measured():
    describes = _runner().schema_describes_envelope

    assert describes(
        _schema("unified_guideline_tools.json", "NICE_Clinical_Guidelines_Search")
    )
    assert not describes(_schema("idr_tools.json", "IDR_list_studies"))
    assert not describes(_schema("artic_tools.json", "ArtIC_search_artworks"))


def test_a_schema_with_neither_key_is_not_an_envelope():
    describes = _runner().schema_describes_envelope

    assert not describes({"properties": {"results": {}, "total": {}}})
    assert not describes({"type": "array", "items": {"type": "object"}})


def test_recursion_is_bounded_and_never_raises():
    describes = _runner().schema_describes_envelope

    deep = {"properties": {}}
    for _ in range(40):
        deep = {"oneOf": [deep]}

    assert describes(deep) is False
    assert describes(None) is False
    assert describes([]) is False


def test_the_cli_uses_the_same_rule():
    """Two runners disagreeing about this is how the problem stayed hidden."""
    source = (ROOT / "src" / "tooluniverse" / "cli.py").read_text("utf-8")

    assert "_schema_describes_envelope(return_schema)" in source
    assert '"data" in properties and "status" in properties' in source


def test_mychem_pubchem_accepts_both_shapes():
    """MyChem merges source records: object for one, array for several.

    Measured across 12 queries and 120 hits: pubchem was an object 53 times
    and an array 11 times. chembl (64) and drugbank (50) were objects in every
    one of those hits, so they stay as declared rather than widened on a hunch.
    """
    schema = _schema("biothings_tools.json", "MyChem_query_chemicals")
    hit = schema["properties"]["hits"]["items"]["properties"]

    assert hit["pubchem"]["type"] == ["object", "array"]
    assert hit["chembl"]["type"] == "object"
    assert hit["drugbank"]["type"] == "object"
