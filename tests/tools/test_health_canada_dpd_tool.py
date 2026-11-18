"""Live smoke test for the Health Canada DPD tools (needs network)."""

import pytest

from tooluniverse import ToolUniverse

pytestmark = [pytest.mark.integration, pytest.mark.network]


@pytest.fixture(scope="module")
def tu():
    universe = ToolUniverse()
    universe.load_tools(
        include_tools=[
            "HealthCanadaDPD_search_products",
            "HealthCanadaDPD_search_by_ingredient",
            "HealthCanadaDPD_get_product",
        ]
    )
    return universe


def test_gleevec_round_trip(tu):
    found = tu.run(
        {
            "name": "HealthCanadaDPD_search_products",
            "arguments": {"brand_name": "gleevec", "marketed_only": True},
        }
    )
    assert found["status"] == "success"
    assert any(row["din"] == "02253275" for row in found["data"])

    product = tu.run(
        {"name": "HealthCanadaDPD_get_product", "arguments": {"din": "02253275"}}
    )
    assert product["data"]["atc"][0]["code"] == "L01EA01"
    assert product["data"]["routes"] == ["Oral"]

    by_ingredient = tu.run(
        {
            "name": "HealthCanadaDPD_search_by_ingredient",
            "arguments": {"ingredient": "imatinib", "limit": 2},
        }
    )
    assert by_ingredient["metadata"]["total_products"] >= 2
    assert "IMATINIB" in by_ingredient["data"][0]["matched_ingredients"][0][
        "ingredient"
    ]
