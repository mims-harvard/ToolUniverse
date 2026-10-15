"""CellMarker must not silently drop records past an unreachable cap."""

import json
from pathlib import Path

import pandas as pd
import pytest

from tooluniverse.cellmarker_tool import DEFAULT_RECORD_LIMIT, _page, _records

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2] / "src/tooluniverse/data/cellmarker_tools.json"
)


def _frame(rows):
    columns = [
        "species",
        "tissue_class",
        "tissue_type",
        "cell_type",
        "cell_name",
        "cell_marker",
        "source",
        "supports",
    ]
    return pd.DataFrame(
        [
            {c: (1 if c == "supports" else f"{c}{i}") for c in columns}
            for i in range(rows)
        ]
    )


def test_default_cap_is_unchanged():
    assert _page({}) == (DEFAULT_RECORD_LIMIT, 0)
    assert len(_records(_frame(384))) == DEFAULT_RECORD_LIMIT


def test_limit_reaches_records_past_the_cap():
    """total_records said 384 while only 200 were retrievable."""
    limit, offset = _page({"limit": 500})
    assert len(_records(_frame(384), limit, offset)) == 384


def test_offset_pages_through_the_remainder():
    limit, offset = _page({"limit": 50, "offset": 380})
    assert len(_records(_frame(384), limit, offset)) == 4


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"limit": 0}, (DEFAULT_RECORD_LIMIT, 0)),
        ({"limit": -5}, (DEFAULT_RECORD_LIMIT, 0)),
        ({"offset": -5}, (DEFAULT_RECORD_LIMIT, 0)),
        ({"limit": "abc"}, (DEFAULT_RECORD_LIMIT, 0)),
        ({"limit": None}, (DEFAULT_RECORD_LIMIT, 0)),
    ],
)
def test_bad_paging_values_degrade_safely(arguments, expected):
    assert _page(arguments) == expected


def test_operation_is_not_a_one_value_choice_in_the_schema():
    """A single-option enum is noise an agent has to reason about."""
    for tool in json.loads(CONFIG.read_text()):
        props = tool["parameter"]["properties"]
        assert "operation" not in props, tool["name"]
        assert tool["fields"]["operation"]
