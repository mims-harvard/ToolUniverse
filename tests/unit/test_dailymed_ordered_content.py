"""Regression guard for Fix-R5B-1: DailyMed dosing/interactions/pharmacology
parsers used to extract all <table> elements first, then all <paragraph>
elements, then all <list><item> elements, in three separate passes -- this
destroyed document order and separated a heading paragraph (e.g.
"Juvenile Idiopathic Arthritis (2.3):") from the table it introduces.
_extract_ordered_content walks a <text> element's direct children in
document order instead, so heading text and its table/list stay adjacent.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool

pytestmark = pytest.mark.unit

_INTERLEAVED_DOSING_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34068-7"/>
      <text>
        <paragraph>Adult Dosing (2.1):</paragraph>
        <table>
          <tbody>
            <tr><td>Adults</td><td>40 mg every other week</td></tr>
          </tbody>
        </table>
        <paragraph>Pediatric Dosing (2.2):</paragraph>
        <list>
          <item>10 kg to less than 15 kg: 10 mg every other week</item>
        </list>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""


def _tool():
    return DailyMedSPLParserTool(
        {"name": "DailyMed_parse_dosing", "parameter": {"properties": {}}}
    )


def test_dosing_preserves_document_order_across_heading_table_and_list():
    tool = _tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _INTERLEAVED_DOSING_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"operation": "parse_dosing", "setid": "fake-setid"})

    assert result["status"] == "success"
    items = result["data"]["dosing_info"]

    # The heading immediately before a table/list must stay immediately
    # before it in the output -- not grouped away into a separate block.
    contents = [item.get("content") or item.get("data") for item in items]
    assert contents[0] == "Adult Dosing (2.1):"
    assert contents[1] == ["Adults", "40 mg every other week"]
    assert contents[2] == "Pediatric Dosing (2.2):"
    assert contents[3] == "10 kg to less than 15 kg: 10 mg every other week"


def test_dosing_no_section_returns_empty_list():
    tool = _tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.text = (
        '<?xml version="1.0"?><document xmlns="urn:hl7-org:v3"></document>'
    )

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"operation": "parse_dosing", "setid": "fake-setid"})

    assert result["status"] == "success"
    assert result["data"]["dosing_info"] == []
