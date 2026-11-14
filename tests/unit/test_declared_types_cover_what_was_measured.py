"""A declared return type must include every type the field was measured to hold.

The field-axis work (#867, #871, #872) widened ~60 wrappers so they stop
dropping fields their upstream answers with. Each newly surfaced field also
got a `type` in its tool's `return_schema` -- and those types were inferred
from the field's name and purpose, not measured. The full live sweep on
2026-11-14 found 65 of them contradicted by the data: `gwas`'s `or_value`
declared `number` while the API sends `'1.33'`, `genebe`'s `strand` declared
`integer` while 140 observations were all booleans, `umls`'s `partialSearch`
declared `boolean` while the value is the request URL.

Nothing validates `return_schema` at runtime -- `execute_function.py` discards
it and `base_tool.py`'s jsonschema call checks *arguments* -- so none of this
could error a caller. It misleads instead: `tu test` reports the mismatch, and
an agent that reads the schema and trusts the type gets it wrong. That is the
same defect the field-axis work set out to remove, one layer up.

The fixture is a RECORDING, not a measurement: it is what the tools returned
on the date it names. Re-measure before trusting it as current. As a guard it
is still exact, because the invariant only ever gets stronger with more data --
a type seen once must be declared forever.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
FIXTURE = REPO / "tests" / "fixtures" / "measured_return_types.json"

_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
ROWS = _fixture["rows"]


def _satisfies(observed, declared):
    """JSON Schema type containment, which is not plain set membership.

    `{"type": "number"}` accepts an integer -- integer is a subset of number --
    so an observed `integer` against a declared `number` is NOT a mismatch.
    Measuring without this rule reported 11 false positives on 2026-11-14
    (`USGS.mag`, `GeneBe.acmg_score`, `FlyMine.relevance` and others, all
    declared `number` and holding whole numbers).
    """
    if observed in declared:
        return True
    return observed == "integer" and "number" in declared


def _declared_types(schema, field):
    """Every `type` declared for a property named `field`, at any depth."""
    found = []
    if isinstance(schema, dict):
        props = schema.get("properties")
        if isinstance(props, dict):
            for key, value in props.items():
                if key == field and isinstance(value, dict) and "type" in value:
                    declared = value["type"]
                    found.append(
                        set(declared) if isinstance(declared, list) else {declared}
                    )
                found += _declared_types(value, field)
        for key in ("items", "additionalProperties"):
            if isinstance(schema.get(key), dict):
                found += _declared_types(schema[key], field)
        for key in ("oneOf", "anyOf", "allOf"):
            if isinstance(schema.get(key), list):
                for branch in schema[key]:
                    found += _declared_types(branch, field)
    return found


def _tool_config(config_name, tool_name):
    tools = json.loads((DATA / config_name).read_text(encoding="utf-8"))
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name") == tool_name:
            return tool
    return None


def test_the_fixture_is_not_empty():
    """A guard that can only pass is not a guard."""
    assert len(ROWS) >= 60, f"fixture has shrunk to {len(ROWS)} rows"
    assert all(r["measured_types"] for r in ROWS), "a row records no measured type"


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['tool']}.{r['field']}" for r in ROWS])
def test_declared_type_covers_every_measured_type(row):
    tool = _tool_config(row["config"], row["tool"])
    assert tool is not None, (
        f"{row['tool']} is no longer in {row['config']} -- if it was renamed or "
        "removed, update the fixture; the measurement must not be left pointing "
        "at nothing"
    )
    schema = tool.get("return_schema")
    assert schema, f"{row['tool']} has no return_schema"

    declared = _declared_types(schema, row["field"])
    assert declared, (
        f"{row['tool']}.{row['field']} is no longer declared in return_schema. "
        "This test exists because the field WAS declared, with the wrong type; "
        "dropping the declaration is not the fix."
    )

    measured = set(row["measured_types"])
    covering = [
        one for one in declared if not {t for t in measured if not _satisfies(t, one)}
    ]
    assert covering, (
        f"{row['tool']}.{row['field']} declares "
        f"{[sorted(one) for one in declared]} and none of those covers the "
        f"measured {sorted(measured)} "
        f"({row['observations']}, measured {_fixture['measured_on']}). "
        "A type that was observed once has to stay in the declaration."
    )

    # Every declaration had to cover the measurement until AMPSphere showed why
    # that is too strong: `_declared_types` finds a name anywhere in the schema,
    # and a union's branches can reuse one for different things. The AMP record
    # declares `isoelectric_point` as a number; the filter-options branch of the
    # same tool declares it as a {min,max} range object. Requiring both to cover
    # the record's measurement would force the range to be declared a number.
    #
    # So a non-covering sibling declaration is allowed -- but only when the row
    # says why, in `name_reused_for_another_shape`. Without that, a second
    # declaration that contradicts the measurement still fails, which is what
    # keeps this from quietly becoming "some declaration somewhere is right".
    if len(covering) < len(declared):
        assert row.get("name_reused_for_another_shape"), (
            f"{row['tool']}.{row['field']} is declared "
            f"{len(declared)} times and only {len(covering)} of those cover the "
            f"measured {sorted(measured)}: "
            f"{[sorted(one) for one in declared]}. If the name means two "
            "different things in two branches, say so in the row's "
            "`name_reused_for_another_shape`; otherwise the extra declaration "
            "is wrong."
        )
