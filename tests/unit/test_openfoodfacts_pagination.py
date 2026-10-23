import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/openfoodfacts_tools.json"
)


def config(name):
    return next(c for c in json.loads(CONFIG_PATH.read_text()) if c["name"] == name)


def response(payload):
    result = Mock(status_code=200, text="")
    result.json.return_value = payload
    return result


@pytest.mark.parametrize(
    "name,arguments,total",
    [
        (
            "OpenFoodFacts_search_products",
            {"search_terms": "nutella", "page_size": 3, "page": 1},
            1022,
        ),
        (
            "OpenFoodFacts_filter_products_by_tags",
            {"categories_tags_en": "Sodas", "page_size": 3, "page": 1},
            20370,
        ),
    ],
)
def test_openfoodfacts_distinguishes_current_page_count_from_total_pages(
    name, arguments, total
):
    payload = {
        "count": total,
        "page": "1",
        "page_count": 3,
        "page_size": 3,
        "skip": 0,
        "products": [{"code": "1"}, {"code": "2"}, {"code": "3"}],
    }
    tool = BaseRESTTool(config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=response(payload),
    ):
        result = tool.run(arguments)

    metadata = result["metadata"]
    assert metadata["returned"] == 3
    assert metadata["upstream_page_count"] == 3
    assert metadata["upstream_page_count_semantics"] == "records_on_current_page"
    assert metadata["total_results"] == total
    assert metadata["total_pages"] == (total + 2) // 3
    assert metadata["next_page"] == 2


@pytest.mark.parametrize(
    "name,base",
    [
        ("OpenFoodFacts_search_products", {"search_terms": "x"}),
        ("OpenFoodFacts_filter_products_by_tags", {"categories_tags_en": "Sodas"}),
    ],
)
def test_openfoodfacts_rejects_pagination_coercions(name, base):
    tool = BaseRESTTool(config(name))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        assert tool.run({**base, "page": 0})["parameter"] == "page"
        assert tool.run({**base, "page": True})["parameter"] == "page"
        assert tool.run({**base, "page_size": 0})["parameter"] == "page_size"
        assert tool.run({**base, "page_size": 101})["parameter"] == "page_size"
    request.assert_not_called()


def test_free_text_search_preserves_barcode_for_product_followup():
    search = config("OpenFoodFacts_search_products")
    assert "code" in search["fields"]["params"]["fields"].split(",")
    product_properties = search["return_schema"]["oneOf"][0]["properties"]["products"][
        "items"
    ]["properties"]
    assert product_properties["code"]["type"] == "string"
