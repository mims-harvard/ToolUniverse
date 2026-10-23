from unittest.mock import MagicMock, patch

from tooluniverse.string_ext_tool import STRINGExtTool


def _response(rows):
    response = MagicMock()
    response.json.return_value = rows
    response.raise_for_status.return_value = None
    return response


def test_functional_annotations_page_each_category_independently():
    rows = [
        {"category": "Process", "term": f"GO:{index:07d}"} for index in range(20)
    ] + [{"category": "Pfam", "term": f"PF{index:05d}"} for index in range(4)]
    tool = STRINGExtTool({"fields": {"endpoint": "functional_annotation"}})
    with patch(
        "tooluniverse.string_ext_tool.requests.get", return_value=_response(rows)
    ):
        result = tool._get_functional_annotations(
            {"identifiers": "TP53", "limit": 3, "offset": 3}
        )

    assert [row["term"] for row in result["data"]["annotations"]["Process"]] == [
        "GO:0000003",
        "GO:0000004",
        "GO:0000005",
    ]
    assert [row["term"] for row in result["data"]["annotations"]["Pfam"]] == ["PF00003"]
    assert result["data"]["total_annotations"] == 24
    assert result["metadata"]["category_pagination"]["Process"]["next_offset"] == 6
    assert result["metadata"]["category_pagination"]["Pfam"]["has_more"] is False


def test_category_filter_has_exact_total_and_tail_page():
    rows = [{"category": "HPO", "term": f"HP:{index:07d}"} for index in range(8)] + [
        {"category": "KEGG", "term": "hsa00001"}
    ]
    tool = STRINGExtTool({"fields": {"endpoint": "functional_annotation"}})
    with patch(
        "tooluniverse.string_ext_tool.requests.get", return_value=_response(rows)
    ):
        result = tool._get_functional_annotations(
            {"identifiers": "TP53", "category": "HPO", "limit": 3, "offset": 6}
        )

    assert result["data"]["total_annotations"] == 8
    assert list(result["data"]["annotations"]) == ["HPO"]
    assert len(result["data"]["annotations"]["HPO"]) == 2
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
