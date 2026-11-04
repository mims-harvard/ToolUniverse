"""A sample is as wide as the queries behind it, not the rows it returned.

The previous round put a threshold on how many calls a measurement spanned.
`ChEMBL_search_drugs` satisfied it with three pages of one query -- 150 rows at
`max_phase=4` -- and `availability_type` is an integer in every one of those
rows. At `max_phase` 3, 2 and 1 it is null in every row, so the declaration was
wrong for three quarters of the population and no amount of paging through the
fourth could have shown it.

Re-measured over four distinct values of the filter:

    availability_type   {"type": "integer"}  ->  {"type": ["integer", "null"]}

Three other faults in the same family, all of them schemas written from one
response and all measured here before being changed:

  ChEMBL_search_activities   standard_units declared "string"; null in 5 of 216
                            rows across five targets -- and in 0 of 150 rows
                            for three of those five, so a sample from one
                            target shows none of them however many pages it
                            covers. The sibling field standard_value already
                            carried "null"; this one had been missed.

  Reactome_get_entity_compartment  declared a single object. Measured over nine
                            stable IDs: 3 single objects, 2 lists of 2-3, and 4
                            empty lists. The tool's own test_example is one of
                            the three.

  ChEMBL_search_similar_molecules  declared `{"type": "array"}` with no oneOf,
                            so the {status, error} envelope it returns when the
                            optional epam.indigo dependency is absent could not
                            validate -- an object is not an array. Schemas with
                            no oneOf at all were outside the earlier scan.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _tool(stem, name):
    for entry in json.loads((DATA / f"{stem}.json").read_text()):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _items(stem, name, path):
    node = _tool(stem, name)["return_schema"]
    for seg in path.split("->"):
        if seg == "*":
            node = node["items"]
        else:
            node = (node.get("properties") or {})[seg]
    return node


# field, declared type, and the filter value that showed the null
NULLABLE_ONLY_UNDER_ANOTHER_FILTER = [
    (
        "chembl_tools",
        "ChEMBL_search_drugs",
        "data->drugs",
        "availability_type",
        ["integer", "null"],
        "max_phase 3/2/1",
    ),
    (
        "chembl_tools",
        "ChEMBL_search_activities",
        "data->activities",
        "standard_units",
        ["string", "null"],
        "targets CHEMBL2159 and CHEMBL2074",
    ),
]


@pytest.mark.parametrize(
    "stem,tool,path,field,expected,evidence",
    NULLABLE_ONLY_UNDER_ANOTHER_FILTER,
    ids=[f"{t}:{f}" for _, t, _, f, _, _ in NULLABLE_ONLY_UNDER_ANOTHER_FILTER],
)
def test_a_field_null_under_another_filter_says_so(
    stem, tool, path, field, expected, evidence
):
    node = _items(stem, tool, path)
    spec = (node.get("items", {}).get("properties") or {}).get(field)
    assert spec is not None, f"{field} is no longer declared on {tool}"
    declared = spec["type"]
    declared = [declared] if isinstance(declared, str) else declared
    assert sorted(declared) == sorted(expected), (
        f"{tool}.{field} must admit null: observed null under {evidence}"
    )


SINGLE = {
    "id": "70101",
    "name": "cytosol",
    "type": "Compartment",
    "raw": "70101\tcytosol",
}


@pytest.mark.parametrize(
    "label,instance",
    [
        ("one compartment", SINGLE),
        ("several", [SINGLE, SINGLE]),
        ("none", []),
        ("an error", {"status": "error", "error": "boom"}),
    ],
)
def test_the_compartment_tool_describes_every_shape_it_returns(label, instance):
    schema = _tool("reactome_tools", "Reactome_get_entity_compartment")["return_schema"]
    branches = schema["oneOf"]
    hits = [
        i
        for i, b in enumerate(branches)
        if not list(Draft7Validator(b).iter_errors(instance))
    ]
    assert len(hits) == 1, f"{label} matched branches {hits}"
    assert not list(Draft7Validator(schema).iter_errors(instance)), label


def test_the_similarity_tool_can_validate_its_own_missing_dependency():
    schema = _tool("chembl_tools", "ChEMBL_search_similar_molecules")["return_schema"]
    envelope = {
        "status": "error",
        "error": "epam.indigo is required for structure similarity search.",
    }
    assert not list(Draft7Validator(schema).iter_errors(envelope))
    success = [
        {
            "chembl_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "smiles": "CC(=O)O",
            "similar_molecules": [],
        }
    ]
    assert not list(Draft7Validator(schema).iter_errors(success))
    hits = [
        i
        for i, b in enumerate(schema["oneOf"])
        if not list(Draft7Validator(b).iter_errors(envelope))
    ]
    assert hits == [1], hits
