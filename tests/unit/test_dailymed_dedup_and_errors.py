"""Regression guard for Fix-R4C-1 (duplicate SPL section dedup) and
Fix-R4C-2 (misleading "missing setid" error when drug_name lookup fails).

SPL XML documents often expose the same section content through multiple
matching <section> elements (e.g. a Highlights summary plus the Full
Prescribing Information), so naive parsers double-count identical
paragraphs -- confirmed live against the apixaban SPL (20 drug-interaction
items / 10 unique, 103 dosing items / 79 unique).
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import DailyMedSPLParserTool, _dedupe_items

pytestmark = pytest.mark.unit

_DUPLICATED_INTERACTIONS_XML = """<?xml version="1.0"?>
<document xmlns="urn:hl7-org:v3">
  <component><structuredBody>
    <component><section>
      <code code="34073-7"/>
      <text><paragraph>Coadministration with strong CYP3A4 inhibitors increases exposure.</paragraph></text>
    </section></component>
    <component><section>
      <code code="34073-7"/>
      <text><paragraph>Coadministration with strong CYP3A4 inhibitors increases exposure.</paragraph></text>
    </section></component>
  </structuredBody></component>
</document>
"""


def _tool():
    return DailyMedSPLParserTool(
        {"name": "DailyMed_parse_drug_interactions", "parameter": {"properties": {}}}
    )


def test_dedupe_items_preserves_order_and_drops_exact_repeats():
    items = [
        {"type": "interaction_text", "content": "a"},
        {"type": "interaction_text", "content": "b"},
        {"type": "interaction_text", "content": "a"},
    ]
    assert _dedupe_items(items) == [
        {"type": "interaction_text", "content": "a"},
        {"type": "interaction_text", "content": "b"},
    ]


def test_dedupe_items_is_noop_when_no_duplication():
    items = [{"type": "x", "content": "1"}, {"type": "x", "content": "2"}]
    assert _dedupe_items(items) == items


def test_parse_drug_interactions_dedupes_duplicated_spl_sections():
    tool = _tool()
    fetch_resp = MagicMock()
    fetch_resp.status_code = 200
    fetch_resp.text = _DUPLICATED_INTERACTIONS_XML

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=fetch_resp):
        result = tool.run(
            {"operation": "parse_drug_interactions", "setid": "fake-setid"}
        )

    assert result["status"] == "success"
    assert result["data"]["count"] == 1
    assert len(result["data"]["interactions"]) == 1


def test_missing_setid_with_drug_name_gives_actionable_not_found_error():
    tool = _tool()
    lookup_resp = MagicMock()
    lookup_resp.status_code = 200
    lookup_resp.json.return_value = {"data": []}  # no SPL matched

    with patch("tooluniverse.dailymed_tool.requests.get", return_value=lookup_resp):
        result = tool.run(
            {"operation": "parse_drug_interactions", "drug_name": "apixiban"}
        )

    assert result["status"] == "error"
    assert "No DailyMed SPL found for drug_name='apixiban'" in result["error"]
    assert "Missing required parameter: setid" not in result["error"]


def test_missing_setid_and_drug_name_gives_original_generic_error():
    tool = _tool()
    result = tool.run({"operation": "parse_drug_interactions"})

    assert result["status"] == "error"
    assert "Missing required parameter: setid" in result["error"]
