"""The KEGG module DEFINITION string must say how to read its operators.

arXiv 2609.26836 records the same agent-side mistake twice over KEGG module
definitions. The wrapper hands the string across unchanged -- correctly --
under a field description that read "Boolean K-number reaction-step
expression" and a tool description calling modules "central to metabolic
reconstruction and completeness analysis". It asked for an analysis and did
not state the rules.

The rules are punctuation. In

    (K00844,K12407,K00845,K25026,K00886,K08074,K00918) (K01810,...) ...

a space separates sequential steps (AND), a comma separates alternatives
within a step (OR), `+` joins a required subunit of a complex, `-` marks an
optional component, and a module is complete when every space-separated step
has at least one alternative present. M00001's first block is seven
alternative hexokinases, not seven required genes. Counting K numbers, or
reading the commas as AND, overstates what a genome needs by severalfold.

The two upstream endpoints that would do the reconstruction instead --
BlastKOALA and /mapper/reconstruct -- are web-UI only and answer 404 on
rest.kegg.jp (measured 2026-11-12), so the evaluation really is the caller's
and the rules really do have to travel with the string.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "kegg_ext_tools.json"
)


@pytest.fixture(scope="module")
def module_tool():
    for tool in json.loads(CONFIG.read_text()):
        if tool.get("name") == "KEGG_get_module":
            return tool
    raise AssertionError("KEGG_get_module is not in kegg_ext_tools.json")


def test_every_operator_is_explained(module_tool):
    definition = module_tool["return_schema"]["oneOf"][0]["properties"]["definition"]
    text = definition["description"]
    assert "SPACE" in text and "AND" in text
    assert "COMMA" in text and "OR" in text
    assert "PLUS" in text
    assert "MINUS" in text and "OPTIONAL" in text.upper()
    # The completeness rule is the point of the whole string.
    assert "complete" in text.lower()
    assert "at least one" in text


def test_the_worked_example_is_the_one_that_misleads(module_tool):
    text = module_tool["return_schema"]["oneOf"][0]["properties"]["definition"][
        "description"
    ]
    assert "K00844" in text, "the rule needs the string it applies to"
    assert "not seven required genes" in text


def test_the_tool_description_does_not_ask_for_an_analysis_without_the_rules(
    module_tool,
):
    text = module_tool["description"]
    assert "completeness analysis" in text
    assert "does not compute completeness" in text
    # And it names where the rules are.
    assert "`definition`" in text
