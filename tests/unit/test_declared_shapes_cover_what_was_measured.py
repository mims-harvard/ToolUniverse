"""A declared return shape must match the shape the tool was measured to return.

`#881` fixed the field axis of this defect: a field's declared `type` against
the value it holds. This file guards the axis above it -- the shape of the
whole payload when one tool answers in more than one.

`AMPSphere_search_amps` is the case that named the class. It has two
operations behind one name: a filter search, which returns a LIST of AMP
records, and `list_options=true`, which returns an options OBJECT. Its
`return_schema` declared a single `oneOf` branch for both, typed `object`,
holding the AMP record's own properties, under a description that read "List
of AMP records (search), or the filter-options object (list_options)." So the
declaration described one record while the tool returned a page of them. Every
search call failed validation and the options call passed vacuously -- an
object with no `required` accepts any object, including one whose keys
(`quality`, `habitat`, `pep_length`) the branch never mentions.

The invariant this file checks is not just "validates". It is that EXACTLY ONE
`oneOf` branch matches. Both halves of the defect show up there: a payload no
branch accepts is a declaration contradicted by its data, and a payload two
branches accept means the union is not discriminated at all -- `oneOf` is
exclusive, so it rejects what both halves would have taken. The AMPSphere
schema needed a `not: {"required": ["error"]}` on its success branches for
exactly that reason, and an earlier revision of it had a branch with no `type`
at all, which matched everything and so made every error payload ambiguous.

`PharmGKB_get_drug_label_annotations` is the second case, and it fails for a
subtler reason: it DID declare both shapes, an object alternative and an array
alternative nested under one branch. That branch also carried
`not: {"required": ["error"]}` to keep the error payload out of it -- and
`required` is vacuously satisfied by anything that is not an object, so
negating it rejects every array. The guard meant to exclude one object
excluded every list. Flattening the nesting puts each `not` on the object
branch it belongs to.

A static scan for the signature found seven more schemas typed `object` under
a description promising a list. All seven are correct: the tool really does
return a paginated object whose `list`/`results` field holds the records, and
the description is shorthand. They are listed here because the grep that found
them is the wrong instrument -- the shapes had to be measured to tell the two
cases apart. BioTools_search, EVA_list_studies,
IdentifiersOrg_list_namespaces, KEGG_list_brite_hierarchies and the three
NeuroVault listers all pass `tu test` as declared.

The fixture is a RECORDING, not a measurement: it holds what the tools
returned on the date it names, and a live API can answer in a shape no single
reading saw. Re-measure before trusting it as current. As a guard it is still
exact -- a shape seen once must stay declared.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
FIXTURE = REPO / "tests" / "fixtures" / "measured_return_shapes.json"

_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
ROWS = _fixture["rows"]


def _tool_config(config_file, tool_name):
    """The raw declaration, read from the config file the fixture names.

    Deliberately the file and not `ToolUniverse().all_tool_dict`: the file is
    what a contributor edits, and loading the registry to check a declaration
    would make a unit test depend on tool loading.
    """
    path = DATA / config_file
    if not path.is_file():
        return None
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if isinstance(entry, dict) and entry.get("name") == tool_name:
            return entry
    return None


def _ids(rows):
    return [f"{r['tool']}.{r['operation']}.{i}" for i, r in enumerate(rows)]


def test_the_fixture_is_not_empty():
    """A guard that can only pass is not a guard."""
    assert len(ROWS) >= 13, f"fixture has shrunk to {len(ROWS)} rows"
    assert all("payload" in r for r in ROWS), "a row records no payload"


def test_the_fixture_records_more_than_one_root_shape():
    """The defect IS a shape confusion, so one shape per tool cannot catch it.

    A fixture holding only objects would have passed against the declaration
    this file exists to reject, which typed every answer `object`.
    """
    by_tool = {}
    for row in ROWS:
        by_tool.setdefault(row["tool"], set()).add(row["root_type"])
    for tool, shapes in by_tool.items():
        assert len(shapes) >= 2, (
            f"{tool} is recorded in only one root shape ({shapes}); this guard "
            "cannot detect a shape confusion from a single shape"
        )


@pytest.mark.parametrize("row", ROWS, ids=_ids(ROWS))
def test_declared_schema_accepts_the_measured_payload(row):
    tool = _tool_config(row["config"], row["tool"])
    assert tool is not None, f"{row['tool']} is not declared in {row['config']}"
    schema = tool.get("return_schema")
    assert schema, (
        f"{row['tool']} declares no return_schema; dropping the declaration is "
        "not the fix"
    )
    payload = row["payload"]
    assert (
        type(payload).__name__ == {"array": "list", "object": "dict"}[row["root_type"]]
    ), f"fixture row disagrees with its own root_type: {row['root_type']}"
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        pytest.fail(
            f"{row['tool']} ({row['operation']}, arguments={row['arguments']}) "
            f"returned a payload its own return_schema rejects: {exc.message} "
            f"(at {list(exc.absolute_path)}). Measured {_fixture['measured_on']}."
        )


@pytest.mark.parametrize("row", ROWS, ids=_ids(ROWS))
def test_exactly_one_branch_matches_the_measured_payload(row):
    """`oneOf` is exclusive: two matching branches reject the payload outright.

    This is the half a plain `validate` cannot see coming. A branch that
    declares no `type` matches every payload, so it turns each of its siblings
    into a second match -- the schema still passes the shapes no sibling
    accepts and fails precisely the ones a sibling was written for.
    """
    tool = _tool_config(row["config"], row["tool"])
    schema = (tool or {}).get("return_schema") or {}
    branches = schema.get("oneOf")
    if not branches:
        pytest.skip(f"{row['tool']} does not declare a oneOf")
    matched = [
        index
        for index, branch in enumerate(branches)
        if jsonschema.Draft7Validator(branch).is_valid(row["payload"])
    ]
    assert len(matched) == 1, (
        f"{row['tool']} ({row['operation']}): {len(matched)} of "
        f"{len(branches)} oneOf branches match the payload measured on "
        f"{_fixture['measured_on']} (matched {matched}); exactly one must"
    )
