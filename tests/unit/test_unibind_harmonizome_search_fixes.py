from unittest.mock import MagicMock, patch

from tooluniverse.harmonizome_tool import HarmonizomeTool
from tooluniverse.unibind_tool import UniBindRESTTool


def test_unibind_tf_catalog_offset_recovers_tail():
    tool = UniBindRESTTool({"fields": {"operation": "list_tfs"}})
    response = MagicMock()
    response.json.return_value = {
        "count": 5,
        "results": [{"tf_name": f"TF{index}"} for index in range(5)],
    }
    response.raise_for_status.return_value = None
    with patch.object(tool.session, "get", return_value=response):
        result = tool.run({"limit": 2, "offset": 4})

    assert result["data"] == ["TF4"]
    assert result["metadata"]["total_matches"] == 5
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_unibind_tf_filter_is_applied_before_offset():
    tool = UniBindRESTTool({"fields": {"operation": "list_tfs"}})
    response = MagicMock()
    response.json.return_value = {
        "count": 5,
        "results": [
            {"tf_name": "SMAD1"},
            {"tf_name": "OTHER"},
            {"tf_name": "SMAD2"},
            {"tf_name": "SMAD3"},
        ],
    }
    response.raise_for_status.return_value = None
    with patch.object(tool.session, "get", return_value=response):
        result = tool.run({"search": "smad", "limit": 1, "offset": 1})

    assert result["data"] == ["SMAD2"]
    assert result["metadata"]["total_matches"] == 3
    assert result["metadata"]["next_offset"] == 2


def test_harmonizome_search_genes_delegates_to_symbol_safe_path():
    tool = HarmonizomeTool({"fields": {"endpoint": "search_genes"}})
    safe_result = {
        "status": "success",
        "data": [{"symbol": "TP53"}],
        "metadata": {"has_more": False},
    }
    with patch.object(tool, "_search", return_value=safe_result) as search:
        result = tool.run({"query": "TP53", "limit": 2, "offset": 1})

    search.assert_called_once_with(
        {"query": "TP53", "limit": 2, "offset": 1, "entity_type": "gene"}
    )
    assert result["data"] == [{"symbol": "TP53"}]
    assert result["metadata"]["total_results_known"] is False
    assert "ignores text-search" in result["metadata"]["note"]
