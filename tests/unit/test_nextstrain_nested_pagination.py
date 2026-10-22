"""Regression tests for Nextstrain's nested dataset pagination."""

from unittest.mock import MagicMock, patch

from tooluniverse.nextstrain_tool import NextstrainTool


def test_dataset_groups_are_recoverably_paged_and_totals_remain_global():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "datasets": [{"request": f"avian-flu/dataset-{i}"} for i in range(7)]
        + [{"request": f"zika/dataset-{i}"} for i in range(2)]
    }
    tool = NextstrainTool(
        {
            "name": "Nextstrain_list_datasets",
            "fields": {"endpoint_type": "list_datasets"},
        }
    )

    with patch("tooluniverse.nextstrain_tool.requests.get", return_value=response):
        result = tool.run(
            {"pathogen": "avian-flu", "dataset_limit": 3, "dataset_offset": 3}
        )

    group = result["data"][0]
    assert group["dataset_count"] == 7
    assert group["datasets_returned"] == 3
    assert group["datasets"] == [
        "avian-flu/dataset-3",
        "avian-flu/dataset-4",
        "avian-flu/dataset-5",
    ]
    assert group["has_more"] is True
    assert group["next_dataset_offset"] == 6
    assert result["metadata"]["total_datasets"] == 7
    assert result["metadata"]["returned_datasets"] == 3
    assert result["metadata"]["groups_with_more"] == 1
