"""Regression guard for Fix-R7A-1: DailyMed_parse_adverse_reactions had no
handling for <hl7:list>/<hl7:item> elements at all -- it only extracted
<table> content, or (if no table) <paragraph> text. Confirmed live that
warfarin's adverse-reactions section encodes its actual reaction list as
<list><item> blocks alongside intro <paragraph> sentences, so every real
reaction item (hemorrhage, tissue necrosis, calciphylaxis, ...) was
silently dropped, leaving only the two generic intro sentences.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool

pytestmark = pytest.mark.unit

_ADVERSE_REACTIONS_WITH_LIST_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34084-4"/>
      <text>
        <paragraph>The following serious adverse reactions are discussed elsewhere:</paragraph>
        <list>
          <item>Hemorrhage</item>
          <item>Tissue Necrosis</item>
          <item>Calciphylaxis</item>
        </list>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""


def test_adverse_reactions_includes_list_items_not_just_intro_paragraph():
    tool = DailyMedSPLParserTool(
        {"name": "DailyMed_parse_adverse_reactions", "parameter": {"properties": {}}}
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _ADVERSE_REACTIONS_WITH_LIST_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run(
            {"operation": "parse_adverse_reactions", "setid": "fake-setid"}
        )

    assert result["status"] == "success"
    contents = [item["content"] for item in result["data"]["adverse_reactions"]]
    assert "Hemorrhage" in contents
    assert "Tissue Necrosis" in contents
    assert "Calciphylaxis" in contents
    assert result["data"]["count"] == 4
