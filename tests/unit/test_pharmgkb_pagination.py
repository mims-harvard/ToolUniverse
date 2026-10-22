from unittest.mock import Mock

from tooluniverse.pharmgkb_tool import PharmGKBTool


def _tool(operation, rows):
    tool = PharmGKBTool({"fields": {"operation": operation}})
    tool._request_json = Mock(return_value=(200, {"data": rows}, None))
    return tool


def test_label_listing_offset_pagination():
    rows = [{"id": f"PA{i}", "name": f"label {i}"} for i in range(5)]
    result = _tool("drug_label_annotations", rows).run(
        {"source": "FDA", "limit": 2, "offset": 2}
    )

    assert [row["id"] for row in result["data"]] == ["PA2", "PA3"]
    assert result["metadata"]["total_results"] == 5
    assert result["metadata"]["next_offset"] == 4


def test_variant_annotation_tail_page():
    rows = [{"id": i} for i in range(5)]
    result = _tool("variant_annotations", rows).run(
        {"gene_id": "PA126", "limit": 2, "offset": 4}
    )

    assert [row["id"] for row in result["data"]] == [4]
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
