from unittest.mock import MagicMock, patch

from tooluniverse.fooddata_central_tool import FoodDataCentralTool


def test_search_preserves_all_nutrients_and_page_continuation():
    nutrients = [
        {"nutrientName": f"Nutrient {i}", "value": i, "unitName": "g"}
        for i in range(41)
    ]
    response = MagicMock()
    response.json.return_value = {
        "foods": [
            {
                "fdcId": 1105073 + index,
                "description": "Bananas, overripe, raw",
                "foodNutrients": nutrients,
            }
            for index in range(5)
        ],
        "totalHits": 164,
        "currentPage": 1,
        "totalPages": 33,
    }
    tool = FoodDataCentralTool(
        {"name": "FoodDataCentral_search_foods", "fields": {"operation": "search"}}
    )

    with patch.object(tool, "_make_get_request", return_value=response):
        result = tool.run({"query": "banana raw", "page_size": 5})

    food = result["data"][0]
    assert food["nutrientCount"] == 41
    assert len(food["nutrients"]) == 41
    assert len(food["topNutrients"]) == 10
    assert result["metadata"]["returned"] == 5
    assert result["metadata"]["returnedCountMatchesMetadata"] is True
    assert result["metadata"]["hasMore"] is True
    assert result["metadata"]["nextPage"] == 2
