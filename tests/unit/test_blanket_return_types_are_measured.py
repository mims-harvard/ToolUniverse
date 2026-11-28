"""A return type that admits almost any JSON must be a measurement, not a template.

#904 fixed two `return_schema` type lists that named a type twice, which made
jsonschema refuse the schema outright -- so neither had ever validated anything.
Looking for the rest of that class turned up a larger one no uniqueness check can
see: 864 positions whose `type` list admitted at least five of the seven JSON
types, 862 of them six. A declaration that accepts string, number, integer,
boolean, object, array and null is "any JSON", and nothing can fail it.

Those did not come from 864 judgements. They arrived with the field-axis work --
#872 introduced 812, #881 another 52 -- and 507 of the 864 carried no description
at all, while 115 shared one sentence word for word: "One entry. This upstream
returns such a list as scalars in some replies and as full records in others, so
an element can be either." The same sentence, and the same six types, on every
list-valued field regardless of what each one holds. #881 removed this defect one
layer up, where types had been declared from a field's NAME rather than its data;
this is the same thing declared from a TEMPLATE rather than its data.

So the sweep of 2026-11-27 typed all 864 against live data: each of the 78 tools
holding one was run on its own test_examples and every value the position
describes was counted. Where the evidence supported it the declaration was
narrowed. Where it did not, the position was left alone and the reason recorded --
including the one position that 180 observations showed really does hold all six.

What the corpus was missing was not narrower types. It was any way to tell a
measured declaration from a placeholder. `tests/fixtures/measured_blanket_types.json`
is that record, and this test holds the corpus to it.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
FIXTURE = REPO / "tests" / "fixtures" / "measured_blanket_types.json"

_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
NARROWED = _fixture["narrowed"]
LEFT_WIDE = _fixture["left_wide"]

# Five of the seven leaves two things a value cannot be; six leaves one. Both are
# wide enough to carry almost no information, so both have to be accounted for.
BLANKET = 5
SCHEMA_KEYS = (
    "return_schema",
    "parameter",
    "parameters",
    "input_schema",
    "output_schema",
)


def _configs():
    for path in sorted(DATA.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(doc, list):
            continue
        for config in doc:
            if isinstance(config, dict) and "name" in config:
                yield path.name, config


def _blanket_positions(config):
    """Every position whose `type` list admits BLANKET or more of the seven.

    Paths are segment LISTS, not slash-joined strings: GBIF declares properties
    whose names are URLs ('http://unknown.org/status'), and a slash-joined path
    cannot be navigated back to them. The first encoding of this sweep used one
    and skipped those five positions without saying so.
    """
    found = {}

    def walk(node, path):
        if isinstance(node, dict):
            kinds = node.get("type")
            if isinstance(kinds, list):
                kinds = sorted({k for k in kinds if isinstance(k, str)})
                if len(kinds) >= BLANKET:
                    found[tuple(path)] = kinds
            for key, value in node.items():
                walk(value, path + [key])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + [index])

    for key in SCHEMA_KEYS:
        if key in config:
            walk(config[key], [key])
    return found


def _declared_at(config, path):
    node = config
    for segment in path:
        if isinstance(node, dict):
            if segment not in node:
                return None
            node = node[segment]
        elif isinstance(node, list):
            if not isinstance(segment, int) or segment >= len(node):
                return None
            node = node[segment]
        else:
            return None
    kinds = node.get("type") if isinstance(node, dict) else None
    return sorted(set(kinds)) if isinstance(kinds, list) else None


_BY_NAME = {(f, c["name"]): c for f, c in _configs()}


def test_the_record_describes_a_real_sweep():
    """A guard whose record narrows nothing, or rests on nothing, is not a guard."""
    assert len(NARROWED) >= 100, f"the record has shrunk to {len(NARROWED)} rows"
    assert LEFT_WIDE, "nothing is recorded as left wide, so nothing records why"
    for row in NARROWED:
        before, after = row["declared_before"], row["declared_after"]
        assert len(before) >= BLANKET, f"{row['tool']} {row['path']} was no blanket"
        assert len(after) < len(before), f"{row['tool']} {row['path']} narrowed nothing"
        assert row["total_observations"] >= 10, (
            f"{row['tool']} {row['path']} was narrowed on "
            f"{row['total_observations']} observation(s)"
        )
        # `number` accepts an integer, so containment is not set membership.
        for kind in row["measured_types"]:
            assert kind in after or (kind == "integer" and "number" in after), (
                f"{row['tool']} {row['path']} dropped the measured {kind}"
            )
    for row in LEFT_WIDE:
        assert row["why_not_narrowed"], f"{row['tool']} {row['path']} records no reason"


@pytest.mark.parametrize(
    "row",
    NARROWED,
    ids=[f"{r['tool']}:{'/'.join(str(s) for s in r['path'][-2:])}" for r in NARROWED],
)
def test_a_narrowed_type_stays_exactly_what_was_measured(row):
    config = _BY_NAME.get((row["config"], row["tool"]))
    assert config is not None, (
        f"{row['tool']} is no longer in {row['config']} -- if it was renamed or "
        "removed, update the record; a measurement must not point at nothing"
    )
    declared = _declared_at(config, row["path"])
    assert declared is not None, (
        f"{row['tool']} no longer declares a type list at {row['path']}. The "
        "position WAS declared, as a blanket; dropping the declaration is not "
        "the fix."
    )
    assert declared == row["declared_after"], (
        f"{row['tool']} {row['path']} declares {declared}. "
        f"{row['total_observations']} observations on {_fixture['measured_on']} "
        f"were {row['observations']}, and the recorded declaration is "
        f"{row['declared_after']}: widening it back to a blanket undoes the "
        "measurement, narrowing it further contradicts it. If the upstream has "
        "changed, re-measure and update the record."
    )


@pytest.mark.parametrize(
    "row",
    LEFT_WIDE,
    ids=[f"{r['tool']}:{'/'.join(str(s) for s in r['path'][-2:])}" for r in LEFT_WIDE],
)
def test_a_position_left_wide_still_covers_what_was_seen_there(row):
    """Narrowing one of these later is welcome. Contradicting the sweep is not."""
    config = _BY_NAME.get((row["config"], row["tool"]))
    if config is None:
        pytest.skip(f"{row['tool']} is no longer in {row['config']}")
    declared = _declared_at(config, row["path"])
    if declared is None:
        pytest.skip(f"{row['tool']} no longer declares a type list at {row['path']}")
    missing = sorted(
        kind
        for kind in row["observations"]
        if kind not in declared and not (kind == "integer" and "number" in declared)
    )
    assert not missing, (
        f"{row['tool']} {row['path']} declares {declared} but was measured to "
        f"hold {missing} on {_fixture['measured_on']} ({row['observations']}). "
        "A type seen once has to stay declared."
    )


def test_no_blanket_type_list_exists_that_was_never_measured():
    """The gate that stops the class growing back.

    #904's fix made a duplicate type impossible to ship. Nothing made "any JSON"
    impossible, and 864 accumulated over two rounds without anyone having to say
    why. A new one now has to be typed against real data and recorded first.
    """
    recorded = {
        (row["config"], row["tool"], tuple(row["path"])) for row in NARROWED + LEFT_WIDE
    }
    unrecorded = []
    for file, config in _configs():
        for path, kinds in _blanket_positions(config).items():
            if (file, config["name"], path) not in recorded:
                unrecorded.append(f"{file} {config['name']} {list(path)} {kinds}")
    assert unrecorded == [], (
        f"{len(unrecorded)} position(s) declare five or more of the seven JSON "
        "types with nothing recording what they were measured to hold. Type the "
        "position against live data, narrow it if the evidence supports that, and "
        f"add a row to {FIXTURE.relative_to(REPO)}:\n  "
        + "\n  ".join(sorted(unrecorded)[:30])
    )
