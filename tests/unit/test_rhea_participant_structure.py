"""Regression coverage for scientific structure in Rhea participants."""

import json
from pathlib import Path

import pytest

from tooluniverse.rhea_reaction_tool import RheaReactionTool


pytestmark = pytest.mark.unit

DATA_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "rhea_reaction_tools.json"
)

# Shape captured from the live RHEA:18353 sodium/potassium ATPase response.
_TRANSPORT_EQUATION = (
    '<span class="participant"><span class="stoichiometry">2 </span>'
    '<a data-molid="chebi:29103">K<small><sup>+</sup></small></a>'
    '<span class="location"> (out)</span></span> + '
    '<span class="participant"><span class="stoichiometry">3 </span>'
    '<a data-molid="chebi:29101">Na<small><sup>+</sup></small></a>'
    '<span class="location"> (in)</span></span> + '
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="chebi:30616">ATP</a>'
    '<span class="location"> </span></span> = '
    '<span class="participant"><span class="stoichiometry">2 </span>'
    '<a data-molid="chebi:29103">K<small><sup>+</sup></small></a>'
    '<span class="location"> (in)</span></span> + '
    '<span class="participant"><span class="stoichiometry">3 </span>'
    '<a data-molid="chebi:29101">Na<small><sup>+</sup></small></a>'
    '<span class="location"> (out)</span></span>'
)

# Representative live Rhea markup for symbolic polymer stoichiometry and
# entity-encoded chemical names (RHEA:10256).
_POLYMER_EQUATION = (
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="rhea-comp:12983">'
    '[(1&#8594;4)-6-phospho-&#945;-<small>D</small>-glucosyl]'
    '<small><sub>(<i>n</i>)</sub></small></a>'
    '<span class="location"> </span></span> + '
    '<span class="participant"><span class="stoichiometry">n </span>'
    '<a data-molid="chebi:30616">ATP</a>'
    '<span class="location"> </span></span> = '
    '<span class="participant"><span class="stoichiometry">2n </span>'
    '<a data-molid="chebi:15378">H<small><sup>+</sup></small></a>'
    '<span class="location"> </span></span>'
)


@pytest.fixture
def tool():
    return RheaReactionTool(
        {"name": "rhea_participant_test", "fields": {"endpoint": "get_participants"}}
    )


def test_transport_participants_preserve_coefficients_and_compartments(tool):
    parsed = tool._parse_participants(_TRANSPORT_EQUATION)

    assert parsed["reactants"] == [
        {
            "chebi_id": "CHEBI:29103",
            "name": "K+",
            "is_generic": False,
            "stoichiometry": "2",
            "location": "out",
        },
        {
            "chebi_id": "CHEBI:29101",
            "name": "Na+",
            "is_generic": False,
            "stoichiometry": "3",
            "location": "in",
        },
        {
            "chebi_id": "CHEBI:30616",
            "name": "ATP",
            "is_generic": False,
            "stoichiometry": "1",
            "location": None,
        },
    ]
    assert parsed["products"][0]["location"] == "in"
    assert parsed["products"][1]["location"] == "out"
    assert [item["stoichiometry"] for item in parsed["products"]] == ["2", "3"]


def test_symbolic_stoichiometry_and_html_entities_are_preserved(tool):
    parsed = tool._parse_participants(_POLYMER_EQUATION)

    polymer, atp = parsed["reactants"]
    assert polymer["name"] == "[(1\u21924)-6-phospho-\u03b1-D-glucosyl](n)"
    assert polymer["rhea_comp_id"] == "RHEA-COMP:12983"
    assert polymer["stoichiometry"] == "1"
    assert atp["stoichiometry"] == "n"
    assert parsed["products"][0]["stoichiometry"] == "2n"


def test_empty_or_unsplittable_equations_remain_safe(tool):
    assert tool._parse_participants("") == {"reactants": [], "products": []}

    one_side = _TRANSPORT_EQUATION.split(" = ", maxsplit=1)[0]
    parsed = tool._parse_participants(one_side)
    assert len(parsed["reactants"]) == 3
    assert parsed["products"] == []


def test_every_participant_schema_declares_structured_fields():
    configs = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    for config in configs:
        success_schema = config["return_schema"]["oneOf"][0]
        for side in ("reactants", "products"):
            properties = success_schema["properties"][side]["items"]["properties"]
            assert properties["stoichiometry"]["type"] == "string"
            assert properties["location"]["type"] == ["string", "null"]


def test_live_complex_examples_are_registered_for_both_endpoints():
    configs = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    for config in configs:
        ids = {example["rhea_id"].removeprefix("RHEA:") for example in config["test_examples"]}
        assert {"18353", "10256"}.issubset(ids)
