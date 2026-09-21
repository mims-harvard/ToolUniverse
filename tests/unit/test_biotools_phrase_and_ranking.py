"""bio.tools: multi-word EDAM terms are phrase-matched; text search is relevance-ranked.

Unquoted, `operation=Variant calling` matched 4,165 tools (any word) instead of the
1,015 tools with that EDAM operation, and un-sorted text queries returned unrelated
packages first (q=blast did not put BLAST first). Verified live against bio.tools.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.biotools_tool import BioToolsRESTTool

pytestmark = pytest.mark.unit

_DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
_TOOLS = {
    t["name"]: t
    for t in json.loads((_DATA / "biotools_registry_tools.json").read_text())
}


def _tool(name="BioTools_search_by_operation"):
    return BioToolsRESTTool(_TOOLS[name])


def test_multi_word_operation_is_sent_as_an_exact_phrase():
    params = _tool()._build_params({"operation": "Variant calling", "size": 5})
    assert params["operation"] == '"Variant calling"'


def test_multi_word_topic_is_sent_as_an_exact_phrase():
    tool = _tool("BioTools_search_by_topic")
    assert tool._build_params({"topic": "Functional genomics"})["topic"] == (
        '"Functional genomics"'
    )


def test_single_word_and_already_quoted_values_are_left_alone():
    tool = _tool("BioTools_search_by_topic")
    assert tool._build_params({"topic": "Genomics"})["topic"] == "Genomics"
    assert tool._build_params({"topic": '"Functional genomics"'})["topic"] == (
        '"Functional genomics"'
    )


def test_other_parameters_are_not_quoted():
    params = _tool()._build_params({"operation": "Variant calling", "page": 2})
    assert params["page"] == 2


def test_phrase_matching_applies_to_the_operation_and_topic_tools_only():
    assert _TOOLS["BioTools_search_by_operation"]["type"] == "BioToolsRESTTool"
    assert _TOOLS["BioTools_search_by_topic"]["type"] == "BioToolsRESTTool"
    assert _TOOLS["BioTools_get_tool"]["type"] == "BaseRESTTool"


@pytest.mark.parametrize("name", ["BioTools_search", "BioTools_search_by_type"])
def test_text_search_tools_default_to_relevance_ordering(name):
    assert _TOOLS[name]["fields"]["params"]["sort"] == "score"
