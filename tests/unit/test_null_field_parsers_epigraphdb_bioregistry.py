"""Two tools returned rows whose fields were all null or empty.

* EpiGraphDB_get_genetic_correlations read ``trait1``/``trait2``/``cor{rg_se,rg_pval}``
  but /genetic-cor now answers ``trait``/``assoc_trait``/``gc{rg_SE,p}``, so all 9 fields
  of every correlation were null.
* Bioregistry_search_registries used the search endpoint's second column as the name,
  but that column is the matched alias (empty for most hits), so 8 of 10 results for
  "protein" had no name and none had a description.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.bioregistry_tool import BioregistryTool
from tooluniverse.epigraphdb_tool import EpiGraphDBTool

pytestmark = pytest.mark.unit

NEW_SHAPE = {
    "trait": {"id": "ukb-a-382", "trait": "Waist circumference"},
    "assoc_trait": {"id": "ukb-a-287", "trait": "Arm fat mass (left)"},
    "gc": {
        "Z": 278.9,
        "p": 1e-300,
        "rg": 0.9541,
        "rg_SE": 0.0034,
        "h2": 0.203,
        "h2_intercept": 1.055,
    },
}
OLD_SHAPE = {
    "trait1": {"id": "a", "trait": "T1"},
    "trait2": {"id": "b", "trait": "T2"},
    "cor": {"rg": 0.9, "rg_se": 0.01, "rg_pval": 0.02, "h2": 0.3, "h2_intercept": 1.0},
}


def _correlations(raw):
    tool = EpiGraphDBTool({"name": "EpiGraphDB_get_genetic_correlations"})
    with patch.object(tool, "_query_genetic_cor", return_value=[raw]):
        result = tool._get_genetic_cor({"trait": "Waist circumference"})
    return result["data"]["correlations"][0]


def test_current_api_shape_fills_every_field():
    row = _correlations(NEW_SHAPE)
    assert row == {
        "trait1_id": "ukb-a-382",
        "trait1_trait": "Waist circumference",
        "trait2_id": "ukb-a-287",
        "trait2_trait": "Arm fat mass (left)",
        "rg": 0.9541,
        "rg_se": 0.0034,
        "rg_pval": 1e-300,
        "h2": 0.203,
        "h2_intercept": 1.055,
    }


def test_previous_api_shape_still_parses():
    row = _correlations(OLD_SHAPE)
    assert (row["trait1_trait"], row["rg"], row["rg_se"], row["rg_pval"]) == (
        "T1",
        0.9,
        0.01,
        0.02,
    )


def _response(body, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = body
    return response


REGISTRY = {
    "aspgd.protein": {
        "name": "AspGD Protein",
        "description": "Aspergillus protein IDs. " * 20,
    },
    "gramene.protein": {"name": "Gramene protein", "description": "Grass genomes."},
}


def _search(limit=10):
    def fake_get(url, params=None, timeout=None):
        if url.endswith("/search"):
            return _response(
                [
                    ["aspgd.protein", ""],
                    ["gramene.protein", "grprotein"],
                    ["zzz.gone", ""],
                ]
            )
        prefix = url.rsplit("/", 1)[1]
        if prefix in REGISTRY:
            return _response(REGISTRY[prefix])
        return _response({}, status=404)

    tool = BioregistryTool(
        {
            "name": "Bioregistry_search_registries",
            "fields": {"operation": "search_registries"},
        }
    )
    with patch("tooluniverse.bioregistry_tool.requests.get", side_effect=fake_get):
        return tool.run(
            {"operation": "search_registries", "query": "protein", "limit": limit}
        )


def test_names_and_descriptions_come_from_the_registry_records():
    rows = _search()["data"]["results"]
    assert [r["prefix"] for r in rows] == [
        "aspgd.protein",
        "gramene.protein",
        "zzz.gone",
    ]
    assert rows[0]["name"] == "AspGD Protein"
    assert 0 < len(rows[0]["description"]) <= 200
    assert rows[1]["name"] == "Gramene protein"


def test_matched_alias_is_kept_only_when_present():
    rows = _search()["data"]["results"]
    assert rows[1]["matched_alias"] == "grprotein"
    assert "matched_alias" not in rows[0]


def test_unknown_prefix_degrades_to_blank_fields_not_an_error():
    result = _search()
    assert result["status"] == "success"
    assert result["data"]["results"][2]["name"] == ""


def test_limit_caps_the_number_of_registry_lookups():
    rows = _search(limit=1)["data"]["results"]
    assert [r["prefix"] for r in rows] == ["aspgd.protein"]
