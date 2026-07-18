"""Regression guard for Fix-R4E-4: USDA_plants_search_by_name common_name HTML leak.

When USDA's PlantSearch API has no true common name for a result, the tool
fell back to the raw autocomplete `Text` field, which USDA wraps in <i>
tags around the scientific name (e.g. "<i>Holcus sorghum</i> L.") -- the
same markup `scientific_name` already strips via `_strip_html`, but the
common_name fallback didn't.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.usda_plants_tool import USDAPlantsProfileTool

pytestmark = pytest.mark.unit


def _tool():
    return USDAPlantsProfileTool(
        {"name": "USDA_plants_search_by_name", "fields": {"action": "search"}}
    )


def test_common_name_fallback_strips_html():
    tool = _tool()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [
        {
            "Text": "<i>Holcus sorghum</i> L.",
            "Plant": {
                "Symbol": "HOSO",
                "ScientificName": "Holcus sorghum L.",
                "CommonName": "",
                "Rank": "Species",
                "Id": 25717,
            },
        }
    ]
    with patch("tooluniverse.usda_plants_tool.requests.get", return_value=resp):
        result = tool.run({"searchText": "sorghum"})

    entry = result["data"][0]
    assert entry["common_name"] == "Holcus sorghum L."
    assert "<i>" not in entry["common_name"]


def test_real_common_name_unaffected():
    tool = _tool()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [
        {
            "Text": "sorghum",
            "Plant": {
                "Symbol": "SORGH2",
                "ScientificName": "Sorghum Moench",
                "CommonName": "sorghum",
                "Rank": "Genus",
                "Id": 25704,
            },
        }
    ]
    with patch("tooluniverse.usda_plants_tool.requests.get", return_value=resp):
        result = tool.run({"searchText": "sorghum"})

    assert result["data"][0]["common_name"] == "sorghum"
