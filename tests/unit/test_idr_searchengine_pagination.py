from unittest.mock import MagicMock

from tooluniverse.idr_searchengine_tool import IDRSearchEngineTool


def _image(image_id):
    return {"id": image_id, "name": f"image-{image_id}", "key_values": []}


def _page(ids, total, bookmark):
    return {
        "results": {
            "results": [_image(image_id) for image_id in ids],
            "size": total,
            "bookmark": [bookmark] if bookmark is not None else None,
        }
    }


def test_image_search_reports_global_total_and_crosses_server_page():
    tool = IDRSearchEngineTool({"name": "IDR_search_images"})
    tool._get = MagicMock(
        side_effect=[
            (_page([0, 1, 2, 3], 7, 3), None),
            (_page([4, 5, 6], 7, 6), None),
        ]
    )

    result = tool.run(
        {"key": "Gene Symbol", "value": "TP53", "offset": 3, "max_results": 3}
    )

    data = result["data"]
    assert [row["image_id"] for row in data["images"]] == [3, 4, 5]
    assert data["image_count"] == 3
    assert data["total_image_count"] == 7
    assert data["has_more"] is True
    assert data["next_offset"] == 6
    assert data["result_set_complete"] is False
    assert tool._get.call_args_list[1].args[1]["bookmark"] == 3


def test_image_search_tail_page_terminates():
    tool = IDRSearchEngineTool({"name": "IDR_search_images"})
    tool._get = MagicMock(
        side_effect=[
            (_page([0, 1, 2, 3], 7, 3), None),
            (_page([4, 5, 6], 7, 6), None),
        ]
    )

    result = tool.run(
        {"key": "Gene Symbol", "value": "TP53", "offset": 6, "max_results": 3}
    )

    data = result["data"]
    assert [row["image_id"] for row in data["images"]] == [6]
    assert data["total_image_count"] == 7
    assert data["has_more"] is False
    assert data["next_offset"] is None


def test_distinct_values_expose_total_and_adjacent_page():
    tool = IDRSearchEngineTool({"name": "IDR_list_values_for_key"})
    tool._get = MagicMock(
        return_value=(
            {
                "data": [
                    {"Value": f"phenotype-{index}", "Number of images": index}
                    for index in range(5)
                ]
            },
            None,
        )
    )

    result = tool.run({"key": "Phenotype", "offset": 2, "max_results": 2})

    data = result["data"]
    assert [row["value"] for row in data["values"]] == [
        "phenotype-2",
        "phenotype-3",
    ]
    assert data["value_count"] == 2
    assert data["total_value_count"] == 5
    assert data["next_offset"] == 4
    assert data["result_set_complete"] is False


def test_pagination_rejects_invalid_values():
    image_tool = IDRSearchEngineTool({"name": "IDR_search_images"})
    values_tool = IDRSearchEngineTool({"name": "IDR_list_values_for_key"})

    assert image_tool.run({"value": "TP53", "offset": -1})["status"] == "error"
    assert values_tool.run({"key": "Phenotype", "max_results": 0})["status"] == "error"
