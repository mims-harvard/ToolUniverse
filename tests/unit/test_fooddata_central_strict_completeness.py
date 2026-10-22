from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.fooddata_central_tool import FoodDataCentralTool


pytestmark = pytest.mark.unit


def _tool(operation):
    return FoodDataCentralTool({"fields": {"operation": operation}})


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"query": 123}, "non-empty string"),
        ({"query": "banana", "page_size": True}, "page_size"),
        ({"query": "banana", "page_size": 201}, "page_size"),
        ({"query": "banana", "page_number": 0}, "page_number"),
        ({"query": "banana", "data_type": "Experimental"}, "data_type"),
    ],
)
def test_invalid_search_controls_are_rejected_before_network(arguments, error):
    with patch.object(FoodDataCentralTool, "_make_get_request") as get:
        result = _tool("search").run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_server_page_mismatch_is_explicit():
    payload = {"foods": [], "totalHits": 10, "currentPage": 1, "totalPages": 5}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("search").run(
            {"query": "banana", "page_size": 2, "page_number": 2}
        )
    assert result["status"] == "error"
    assert result["requested_page"] == 2
    assert result["returned_page"] == 1


def test_empty_page_before_total_is_marked_stalled():
    payload = {"foods": [], "totalHits": 10, "currentPage": 2, "totalPages": 5}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("search").run(
            {"query": "banana", "page_size": 2, "page_number": 2}
        )
    metadata = result["metadata"]
    assert metadata["hasMore"] is True
    assert metadata["nextPage"] is None
    assert metadata["requestedPageComplete"] is False
    assert metadata["paginationStalled"] is True


def test_nonempty_short_page_is_not_silently_treated_as_complete():
    food = {"fdcId": 1, "description": "Banana", "foodNutrients": []}
    payload = {"foods": [food], "totalHits": 10, "currentPage": 2, "totalPages": 5}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("search").run(
            {"query": "banana", "page_size": 2, "page_number": 2}
        )
    metadata = result["metadata"]
    assert metadata["returned"] == 1
    assert metadata["expectedReturned"] == 2
    assert metadata["returnedCountMatchesMetadata"] is False
    assert metadata["requestedPageComplete"] is False
    assert metadata["nextPage"] is None


def test_inconsistent_total_pages_is_an_error():
    payload = {"foods": [], "totalHits": 10, "currentPage": 1, "totalPages": 4}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("search").run({"query": "banana", "page_size": 2})
    assert result["status"] == "error"
    assert result["expected_total_pages"] == 5


@pytest.mark.parametrize(
    "foods",
    [[None], [{"fdcId": 1}], [{"fdcId": 1, "foodNutrients": [None]}]],
)
def test_malformed_nested_search_records_are_errors(foods):
    payload = {"foods": foods, "totalHits": 1, "currentPage": 1, "totalPages": 1}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("search").run({"query": "banana"})
    assert result["status"] == "error"
    assert "malformed" in result["error"]


@pytest.mark.parametrize("fdc_id", [True, "2344723", 0, -1])
def test_invalid_fdc_id_is_rejected_before_network(fdc_id):
    with patch.object(FoodDataCentralTool, "_make_get_request") as get:
        result = _tool("detail").run({"fdc_id": fdc_id})
    assert result["status"] == "error"
    assert "positive integer" in result["error"]
    get.assert_not_called()


def test_detail_id_mismatch_is_explicit():
    payload = {"fdcId": 1, "foodNutrients": []}
    with patch.object(
        FoodDataCentralTool, "_make_get_request", return_value=_response(payload)
    ):
        result = _tool("detail").run({"fdc_id": 2344723})
    assert result["status"] == "error"
    assert result["requested_fdc_id"] == 2344723
    assert result["returned_fdc_id"] == 1
