"""The HPO differential was intersected over disease names.

`get_joint_associated_diseases_by_HPO_ID_list` asks Monarch for each
phenotype's diseases and returns the ones every phenotype shares. It read
`subject_label` from each association and intersected the labels, while
`subject` -- the MONDO curie -- sat unread on every one of the 5,331
associations of HP:0001250 alone.

Intersecting labels is wrong in two directions:

* Two MONDO diseases that happen to share a label merge into one, so a
  disease can enter the differential on another disease's evidence.
* One disease whose label differs between two legs ("Niemann-Pick type C"
  against "Niemann-Pick disease type C") fails to match itself and drops out
  of a differential it belongs in -- the same disease an earlier round's
  pagination fix was written to stop losing.

The intersection is now keyed by the curie where Monarch sends one and by
the label where it does not, so a response without `subject` behaves exactly
as before. The output stays a list of names: its shape is declared in the
return schema and documented in two skills, and widening it is a contract
change rather than a dropped field, recorded as deferred in
`test_wrappers_carry_the_fields_the_api_answered.py`.
"""

import json
import pathlib
from unittest.mock import patch

import pytest

from tooluniverse.restful_tool import MonarchDiseasesForMultiplePhenoTool

pytestmark = pytest.mark.unit

DATA = pathlib.Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
TOOL = "get_joint_associated_diseases_by_HPO_ID_list"


def _tool():
    configs = json.loads((DATA / "monarch_tools.json").read_text())
    config = next(c for c in configs if c["name"] == TOOL)
    return MonarchDiseasesForMultiplePhenoTool(config)


def _page(items, total=None):
    return {"items": items, "total": total if total is not None else len(items)}


def _association(curie, label):
    return {"subject": curie, "subject_label": label}


def test_one_disease_whose_label_differs_between_legs_still_matches():
    legs = [
        _page(
            [
                _association("MONDO:0018982", "Niemann-Pick type C"),
                _association("MONDO:0010096", "narcolepsy 1"),
            ]
        ),
        _page([_association("MONDO:0018982", "Niemann-Pick disease type C")]),
    ]
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query", side_effect=legs
    ):
        result = _tool().run({"HPO_ID_list": ["HP:0001250", "HP:0002524"], "limit": 50})
    # The first leg's label is the one reported, in the first leg's order.
    assert result == ["Niemann-Pick type C"]


def test_two_diseases_sharing_a_label_do_not_vouch_for_each_other():
    """Neither disease has both phenotypes, and the label said one did.

    MONDO:2 carries the first phenotype and MONDO:1 the second, and the two
    share a label. Intersecting labels found "shared name" in both legs and
    reported a disease that has neither phenotype pair; intersecting curies
    finds no disease in both legs, which is the truth.
    """
    legs = [
        _page(
            [
                _association("MONDO:2", "shared name"),
                _association("MONDO:3", "only here"),
            ]
        ),
        _page([_association("MONDO:1", "shared name")]),
    ]
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query", side_effect=legs
    ):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 50})
    assert result == []


def test_a_response_without_a_curie_falls_back_to_the_label():
    """Monarch has always sent `subject`, but a fixture or a future response
    without it must behave as the label intersection did rather than fail."""
    legs = [
        _page([{"subject_label": "disease a"}, {"subject_label": "disease b"}]),
        _page([{"subject_label": "disease a"}]),
    ]
    with patch(
        "tooluniverse.restful_tool.execute_RESTful_query", side_effect=legs
    ):
        result = _tool().run({"HPO_ID_list": ["HP:1", "HP:2"], "limit": 50})
    assert result == ["disease a"]


def test_the_label_lookup_spans_every_leg():
    """The label map is built across all legs, not rebuilt per leg: a
    per-leg map happens to work because an intersected key is in the last
    leg too, and correct by accident is not correct."""
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "restful_tool.py"
    ).read_text()
    before_loop = source.index("label_by_key = {}")
    loop = source.index('for HPOID in arguments["HPO_ID_list"]:')
    assert before_loop < loop, "label_by_key is rebuilt for each phenotype"
