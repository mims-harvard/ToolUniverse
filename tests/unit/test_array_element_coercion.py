"""Regression guard: `_coerce_value_to_type` must coerce array elements too.

The array branch of `ToolUniverse._coerce_value_to_type` sat below the
`if not isinstance(value, str): return value` guard, so a list was returned
before the per-item recursion could run. The branch was unreachable: array
elements stayed strings while the identical scalar was coerced, and a caller
that rendered numbers as JSON strings had list arguments rejected by schema
validation. `_coerce_arguments_to_schema` passes top-level list values
straight in, so this was reached from the ordinary `tu.run` path.

Live example at the time: `DoseResponse_calculate_ic50` rejected
`{"concentrations": ["0.001", ...], "responses": ["2", ...]}` with
"is not of type 'number'" and fitted the identical call written with floats.

The branch has to accept a union `type` as well. `["array", "null"]` is this
project's spelling for an optional parameter, and a tool can declare one
parameter each way: `EnzymeKinetics_calculate` takes `substrate_concs` as
`"array"` and `velocities` as `["array", "null"]`, both with number items.
Matching only the bare string would coerce one and refuse the other inside a
single call.
"""

import logging

import pytest

from tooluniverse import ToolUniverse

pytestmark = pytest.mark.unit


def _engine():
    """A bare engine: these methods need no loaded catalogue."""
    return ToolUniverse.__new__(ToolUniverse)


@pytest.mark.parametrize(
    "value,schema,expected",
    [
        (
            ["10", "20"],
            {"type": "array", "items": {"type": "integer"}},
            [10, 20],
        ),
        (
            ["0.1", "1"],
            {"type": "array", "items": {"type": "number"}},
            [0.1, 1.0],
        ),
        (
            ["true", "false"],
            {"type": "array", "items": {"type": "boolean"}},
            [True, False],
        ),
        (
            ["10", "20"],
            {"type": "array", "items": {"type": ["integer", "null"]}},
            [10, 20],
        ),
        (
            [["1", "2"]],
            {
                "type": "array",
                "items": {"type": "array", "items": {"type": "integer"}},
            },
            [[1, 2]],
        ),
        # An optional array is spelled as a union. It must coerce like a bare
        # one: EnzymeKinetics_calculate.velocities is declared this way.
        (
            ["10", "18"],
            {"type": ["array", "null"], "items": {"type": "number"}},
            [10.0, 18.0],
        ),
        # A union array of arrays, as SPrediXcan_associate.covariance declares.
        (
            [["1", "2"]],
            {
                "type": ["array", "null"],
                "items": {"type": "array", "items": {"type": "number"}},
            },
            [[1.0, 2.0]],
        ),
    ],
)
def test_array_elements_are_coerced(value, schema, expected):
    got = _engine()._coerce_value_to_type(value, schema)
    assert got == expected
    assert [type(x) for x in got] == [type(x) for x in expected]


def test_scalar_and_array_agree():
    """The asymmetry itself: the same string must coerce either way."""
    engine = _engine()
    scalar = engine._coerce_value_to_type("10", {"type": "integer"})
    array = engine._coerce_value_to_type(
        ["10"], {"type": "array", "items": {"type": "integer"}}
    )
    assert scalar == 10
    assert array == [scalar]


@pytest.mark.parametrize(
    "value,schema",
    [
        # items says string, so digits stay strings
        (["10", "20"], {"type": "array", "items": {"type": "string"}}),
        # uncoercible elements are left alone, not dropped or errored
        (["abc"], {"type": "array", "items": {"type": "integer"}}),
        # a float is not an integer
        (["1.5"], {"type": "array", "items": {"type": "integer"}}),
        # no items schema to recurse with
        (["10"], {"type": "array"}),
        # tuple-form items is a list of schemas, which the recursion cannot
        # consume; leave the value alone rather than raise
        (["10"], {"type": "array", "items": [{"type": "integer"}]}),
        # a union array whose items accept a string keeps them as strings
        (["10"], {"type": ["array", "string"], "items": {"type": "string"}}),
        (["10"], {"type": ["array", "null"], "items": {"type": ["integer", "string"]}}),
        # no "array" member, so this is not an array schema at all
        (["10"], {"type": ["integer", "null"], "items": {"type": "integer"}}),
    ],
)
def test_values_that_must_stay_strings(value, schema):
    got = _engine()._coerce_value_to_type(value, schema)
    assert got == value
    assert all(isinstance(x, str) for x in got)


def test_non_array_behaviour_is_unchanged():
    """The string-only guard still governs everything that is not a list."""
    engine = _engine()
    assert engine._coerce_value_to_type(7, {"type": "integer"}) == 7
    assert engine._coerce_value_to_type(None, {"type": "integer"}) is None
    # a string against an array schema has no elements to coerce
    assert (
        engine._coerce_value_to_type(
            "abc", {"type": "array", "items": {"type": "integer"}}
        )
        == "abc"
    )


def test_list_arguments_reach_the_coercion():
    """`_coerce_arguments_to_schema` is the path a tool call actually takes."""
    engine = _engine()
    engine.logger = logging.getLogger("test_array_element_coercion")
    engine.all_tool_dict = {
        "fit_curve": {
            "name": "fit_curve",
            "parameter": {
                "type": "object",
                "properties": {
                    "concentrations": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "label": {"type": "string"},
                },
            },
        }
    }

    coerced = engine._coerce_arguments_to_schema(
        "fit_curve", {"concentrations": ["0.001", "0.01"], "label": "run1"}
    )

    assert coerced["concentrations"] == [0.001, 0.01]
    assert all(isinstance(x, float) for x in coerced["concentrations"])
    assert coerced["label"] == "run1"


def test_both_array_spellings_agree_in_one_call():
    """A required array and an optional one must not disagree.

    Shape copied from `EnzymeKinetics_calculate`, which declares
    `substrate_concs` as `"array"` and `velocities` as `["array", "null"]`,
    both with number items. Matching only the bare spelling coerced the first
    and left the second a list of strings, so one call carried two numeric
    arrays and validation rejected only one of them.
    """
    engine = _engine()
    engine.logger = logging.getLogger("test_array_element_coercion")
    engine.all_tool_dict = {
        "kinetics": {
            "name": "kinetics",
            "parameter": {
                "type": "object",
                "properties": {
                    "substrate_concs": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                    "velocities": {
                        "type": ["array", "null"],
                        "items": {"type": "number"},
                    },
                },
            },
        }
    }

    coerced = engine._coerce_arguments_to_schema(
        "kinetics",
        {"substrate_concs": ["0.1", "0.2"], "velocities": ["10", "18"]},
    )

    assert coerced["substrate_concs"] == [0.1, 0.2]
    assert coerced["velocities"] == [10.0, 18.0]
    assert all(isinstance(x, float) for x in coerced["velocities"])
