"""Regression guard: SPL stacked-fraction equations must keep their division.

SPL has no fraction element, so a dosing equation is drawn as a stacked
fraction -- an underlined <content> numerator on its own line, a <br/>, then
the denominator, with the underline acting as the division bar. _cell_text()
renders <br/> as a space, which deleted the division entirely.

Measured on the live DigiFab label (digoxin immune fab, setid
c05ee6a5-c98b-45f4-83fd-40781639d653), whose two dosing equations both use
this encoding. Before the fix DailyMed_parse_dosing returned

    Dose (in vials) = (Serum digoxin ng/mL)(weight in kg) 100

which a bedside reader parses as a multiplication by 100 rather than a
division by it -- a 10,000-fold error in an antidote dose, with nothing in
the response indicating anything had been dropped.

The bar is recognised only on the exact stacked-fraction shape: an underlined
<content> directly following an "=" and directly followed by a <br/>. The
"=" requirement is what keeps an underlined *heading* before a line break --
a common, unrelated use of underline -- from being turned into a division,
which is the false positive this guard's second test pins down.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool

pytestmark = pytest.mark.unit

# Structure copied from the live DigiFab SPL, including the non-breaking-space
# indentation DailyMed uses to centre the denominator under the bar.
_DOSING_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34068-7"/>
      <text>
        <table>
          <tbody>
            <tr>
              <td><content styleCode="bold">Acute ingestion of known amounts</content></td>
              <td>Dose (in vials) =
                 <br/>
                 <content styleCode="underline">Amount of digoxin ingested (in mg)</content>
                 <br/>    0.5 mg/vial</td>
            </tr>
            <tr>
              <td><content styleCode="bold">Chronic toxicity, known concentration</content></td>
              <td>Dose (in vials) =
                 <br/>
                 <content styleCode="underline">(Serum digoxin ng/mL)(weight in kg)</content>
                 <br/>    100
              </td>
            </tr>
          </tbody>
        </table>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""

# An underlined heading on its own line, followed by a <br/> and body text.
# Same element shape as a fraction, no "=" -- must stay a line break.
_UNDERLINED_HEADING_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34068-7"/>
      <text>
        <table>
          <tbody>
            <tr>
              <td>Renal impairment</td>
              <td>
                 <content styleCode="underline">Recommended Dosage</content>
                 <br/>Reduce the dose to 5 mg once daily.</td>
            </tr>
          </tbody>
        </table>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""


# The same fraction as above, encoded in a <paragraph> instead of a <td> --
# the shape DigiFab section 2.1 actually uses.
_PARAGRAPH_FRACTION_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34068-7"/>
      <text>
        <paragraph>Dose = <content styleCode="underline">(Serum digoxin concentration in ng/mL)(weight in kg)</content>
           <br/>100</paragraph>
      </text>
    </section></component>
  </structuredBody></component>
</document>
"""


def _parse_dosing(xml):
    tool = DailyMedSPLParserTool(
        {"name": "DailyMed_parse_dosing", "parameter": {"properties": {}}}
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.text = xml

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"operation": "parse_dosing", "setid": "fake-setid"})

    assert result["status"] == "success"
    return [
        item["data"]
        for item in result["data"]["dosing_info"]
        if item["type"] == "table_row"
    ]


def test_stacked_fraction_keeps_its_division_operator():
    rows = _parse_dosing(_DOSING_XML)

    assert rows[0][1] == (
        "Dose (in vials) = Amount of digoxin ingested (in mg) / 0.5 mg/vial"
    )
    assert rows[1][1] == "Dose (in vials) = (Serum digoxin ng/mL)(weight in kg) / 100"


def test_underlined_heading_before_a_break_is_not_a_division():
    rows = _parse_dosing(_UNDERLINED_HEADING_XML)

    assert rows[0][1] == "Recommended Dosage Reduce the dose to 5 mg once daily."
    assert "/" not in rows[0][1]


def test_paragraph_fractions_are_handled_like_table_ones():
    """The same equation must not render two different ways in one response.

    DigiFab states its dosing equations twice: once in a table and again in
    <paragraph>s in section 2.1. Fixing only the table path left the response
    self-contradicting -- the table row said "/ 100" while the paragraph still
    said " 100" for the same equation on the same drug. <br/> is a property of
    SPL markup, not of tables, so every flow element goes through _flow_text.
    """
    tool = DailyMedSPLParserTool(
        {"name": "DailyMed_parse_dosing", "parameter": {"properties": {}}}
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _PARAGRAPH_FRACTION_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"operation": "parse_dosing", "setid": "fake-setid"})

    texts = [
        item["content"]
        for item in result["data"]["dosing_info"]
        if item["type"] == "dosing_text"
    ]
    assert any("(weight in kg) / 100" in t for t in texts), texts
