"""Discovery tools must answer for the documented name of a shortened tool.

96 of the shipped tools have a registered name longer than
``MAX_TOOL_NAME_LENGTH``. The MCP layer keys them by a shortened form
("OpenTargets_get_asso_drug_by_dise_efoI") while the docs, the website and the
Python SDK all use the long one. ``execute_tool`` already resolved both
spellings; ``get_tool_info`` answered "not found" for the long one and
``grep_tools`` could not find it at all, so a user pasting a documented name
got a contradiction from two of the three discovery tools.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.tool_discovery_tools import GetToolInfoTool, GrepToolsTool

pytestmark = pytest.mark.unit

LONG = "OpenTargets_get_associated_drugs_by_disease_efoId"
SHORT = "OpenTargets_get_asso_drug_by_dise_efoI"


class _ShortenedUniverse:
    """A catalogue keyed the way the MCP layer keys it."""

    def __init__(self):
        self.all_tool_dict = {
            SHORT: {
                "name": SHORT,
                "original_name": LONG,
                "description": "Known drugs and clinical candidates for a disease.",
                "type": "OpenTarget",
                "category": "opentargets",
            },
            "UniProt_get_function": {
                "name": "UniProt_get_function",
                "description": "Protein function annotation.",
                "type": "UniProtRESTTool",
                "category": "uniprot",
            },
        }
        self._excluded_api_key_tools = {}

    def _resolve_tool_name(self, name):
        if name in self.all_tool_dict:
            return name
        for key, tool in self.all_tool_dict.items():
            if tool.get("original_name") == name:
                return key
        return name

    def tool_specification(self, name, return_prompt=False):
        return self.all_tool_dict.get(name)

    def get_tool_specification_by_names(self, names):
        return [self.all_tool_dict[n] for n in names if n in self.all_tool_dict]


def _info():
    return GetToolInfoTool({"name": "get_tool_info"}, tooluniverse=_ShortenedUniverse())


def _grep():
    return GrepToolsTool({"name": "grep_tools"}, tooluniverse=_ShortenedUniverse())


@pytest.mark.parametrize("name", [LONG, SHORT])
def test_get_tool_info_answers_for_either_spelling(name):
    out = _info().run({"tool_names": [name], "detail_level": "description"})

    assert out["total_found"] == 1
    assert "error" not in out["tools"][0]


def test_get_tool_info_full_detail_accepts_the_documented_name():
    out = _info().run({"tool_names": LONG})

    assert out.get("original_name") == LONG or out.get("name") in (LONG, SHORT)
    assert "error" not in out


def test_an_unknown_name_is_still_not_found():
    """The fallback must not turn a typo into a silent wrong answer."""
    out = _info().run({"tool_names": ["NoSuchTool_xyz"], "detail_level": "description"})

    assert out["total_found"] == 0
    assert out["tools"][0]["error"] == "not found"


def test_grep_finds_a_shortened_tool_by_its_documented_name():
    hits = _grep().run({"pattern": "associated_drugs_by_disease", "limit": 5})

    assert [t["name"] for t in hits["tools"]] == [SHORT]


def test_grep_still_finds_it_by_the_shortened_name():
    hits = _grep().run({"pattern": "asso_drug_by_dise", "limit": 5})

    assert [t["name"] for t in hits["tools"]] == [SHORT]


def test_grep_does_not_widen_matches_for_tools_without_a_long_name():
    hits = _grep().run({"pattern": "UniProt", "limit": 5})

    assert [t["name"] for t in hits["tools"]] == ["UniProt_get_function"]
