"""Regression guard for Fix-R21B-2: VDJDBTool's `species` filter was typed
as a free-text string in the schema but is actually an exact-match filter
against a closed set of 3 CamelCase values (HomoSapiens/MusMusculus/
MacacaMulatta). A plausible plain-language alias like "human" silently
matched zero records instead of the real 20,139 HomoSapiens records for
the same epitope (confirmed live for GILGFVFTL). Fixed by normalizing
common aliases to the canonical VDJdb value before building the filter,
in both _search_cdr3 and _get_antigen_specificity.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.vdjdb_tool import VDJDBTool, _normalize_species

pytestmark = pytest.mark.unit


def _tool():
    return VDJDBTool({"name": "vdjdb_test"})


def _resp(json_body):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


def _empty_search_body():
    return {"rows": [], "recordsFound": 0, "page": 0, "pageSize": 25, "pageCount": 0}


@pytest.mark.parametrize(
    "alias,canonical",
    [
        ("human", "HomoSapiens"),
        ("HUMAN", "HomoSapiens"),
        ("mouse", "MusMusculus"),
        ("macaque", "MacacaMulatta"),
        ("monkey", "MacacaMulatta"),
    ],
)
def test_normalize_species_aliases(alias, canonical):
    assert _normalize_species(alias) == canonical


def test_normalize_species_canonical_value_passthrough():
    assert _normalize_species("HomoSapiens") == "HomoSapiens"


def test_normalize_species_none_passthrough():
    assert _normalize_species(None) is None


def test_get_antigen_specificity_normalizes_species_filter():
    tool = _tool()
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["body"] = json
        return _resp(_empty_search_body())

    with patch.object(tool.session, "post", side_effect=fake_post):
        tool.run(
            {
                "operation": "get_antigen_specificity",
                "epitope": "GILGFVFTL",
                "species": "human",
            }
        )

    species_filters = [
        f for f in captured["body"]["filters"] if f["column"] == "species"
    ]
    assert species_filters == [
        {"column": "species", "value": "HomoSapiens", "filterType": "exact", "negative": False}
    ]


def test_search_cdr3_normalizes_species_filter():
    tool = _tool()
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["body"] = json
        return _resp(_empty_search_body())

    with patch.object(tool.session, "post", side_effect=fake_post):
        tool.run(
            {
                "operation": "search_cdr3",
                "cdr3": "CASSIRSSYEQYF",
                "species": "mouse",
            }
        )

    species_filters = [
        f for f in captured["body"]["filters"] if f["column"] == "species"
    ]
    assert species_filters == [
        {"column": "species", "value": "MusMusculus", "filterType": "exact", "negative": False}
    ]


def test_no_species_filter_when_omitted():
    tool = _tool()
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["body"] = json
        return _resp(_empty_search_body())

    with patch.object(tool.session, "post", side_effect=fake_post):
        tool.run({"operation": "search_cdr3", "cdr3": "CASSIRSSYEQYF"})

    assert not any(f["column"] == "species" for f in captured["body"]["filters"])
