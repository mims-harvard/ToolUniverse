"""Regression guard for two round-6 DailyMed fixes:

Fix-R6A-2/R6D-3/R6E-3: DailyMed's own API literally serializes absent
pagination links as the JSON string "null" rather than a real null.
SearchSPLTool now normalizes these to None before returning.

Fix-R6E-2: SPL table cells use <br/> as an in-cell line break (e.g.
"TRIKAFTA" / "N=202" / "n (%)" on three visual lines), but the old
itertext()-with-no-separator join collapsed these into a single run like
"TRIKAFTAN=202n (%)". _cell_text() now inserts a space at each <br/>.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool, SearchSPLTool

pytestmark = pytest.mark.unit

_TABLE_WITH_BR_HEADER_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34084-4"/>
      <text>
        <table>
          <thead>
            <tr>
              <th>Adverse Reactions</th>
              <th>TRIKAFTA<br/>N=202<br/>n (%)</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Headache</td><td>35 (17)</td></tr>
          </tbody>
        </table>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""


def test_search_spls_normalizes_literal_null_strings_to_none():
    tool = SearchSPLTool({"name": "DailyMed_search_spls"})
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [{"setid": "abc"}],
        "metadata": {
            "total_elements": 1,
            "next_page_url": "null",
            "previous_page": "null",
        },
    }

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"drug_name": "tolvaptan"})

    assert result["status"] == "success"
    assert result["metadata"]["next_page_url"] is None
    assert result["metadata"]["previous_page"] is None
    assert result["metadata"]["total_elements"] == 1


def test_table_header_with_br_joins_with_spaces_not_concatenated():
    tool = DailyMedSPLParserTool(
        {"name": "DailyMed_parse_adverse_reactions", "parameter": {"properties": {}}}
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _TABLE_WITH_BR_HEADER_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run(
            {"operation": "parse_adverse_reactions", "setid": "fake-setid"}
        )

    assert result["status"] == "success"
    row = result["data"]["adverse_reactions"][0]
    assert row["data"] == {
        "Adverse Reactions": "Headache",
        "TRIKAFTA N=202 n (%)": "35 (17)",
    }
