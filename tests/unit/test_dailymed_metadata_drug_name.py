"""Regression guard for Fix-R9A-2/R9D-3: DailyMedSPLParserTool's
metadata.drug_name was only ever populated from the caller's own
drug_name argument, so it was always null for the common case of calling
with setid directly (e.g. after a prior search_spls call) -- independently
reported by two personas this round -- even though the SPL itself already
names the product via its manufacturedProduct element. Falls back to that
element, which is already parsed on the XML at no extra network cost.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool

pytestmark = pytest.mark.unit

_SPL_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34068-7"/>
      <text><paragraph>Take as directed.</paragraph></text>
    </section></component>
  </structuredBody></component>
  <component>
    <structuredBody>
      <component><section>
        <subject>
          <manufacturedProduct>
            <manufacturedProduct>
              <name>Warfarin Sodium</name>
            </manufacturedProduct>
          </manufacturedProduct>
        </subject>
      </section></component>
    </structuredBody>
  </component>
</document>
"""


def _tool():
    return DailyMedSPLParserTool(
        {"name": "DailyMed_parse_dosing", "parameter": {"properties": {}}}
    )


def test_drug_name_falls_back_to_spl_manufactured_product_name():
    tool = _tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _SPL_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run({"operation": "parse_dosing", "setid": "fake-setid"})

    assert result["status"] == "success"
    assert result["metadata"]["drug_name"] == "Warfarin Sodium"


def test_explicit_drug_name_argument_takes_precedence():
    tool = _tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.text = _SPL_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=resp):
        result = tool.run(
            {
                "operation": "parse_dosing",
                "setid": "fake-setid",
                "drug_name": "apixaban",
            }
        )

    assert result["metadata"]["drug_name"] == "apixaban"
