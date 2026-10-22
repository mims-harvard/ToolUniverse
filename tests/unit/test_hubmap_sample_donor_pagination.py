from unittest.mock import patch

import pytest

from tooluniverse.hubmap_sample_tool import HuBMAPSampleTool


def _tool(operation):
    return HuBMAPSampleTool({"name": operation, "fields": {"operation": operation}})


def _payload(entity_type, total=152):
    source = {
        "hubmap_id": "HBM.TEST.001",
        "uuid": "uuid-1",
        "group_name": "TMC",
    }
    if entity_type == "Sample":
        source.update(
            {
                "sample_category": "block",
                "origin_samples": [{"organ": "LK"}],
                "donor": {"hubmap_id": "HBM.DONOR.1"},
            }
        )
    else:
        source["metadata"] = {"organ_donor_data": []}
    return {"hits": {"total": {"value": total}, "hits": [{"_source": source}]}}


@patch.object(HuBMAPSampleTool, "_post")
def test_sample_search_forwards_offset_and_reports_exact_total(mock_post):
    mock_post.return_value = _payload("Sample")
    result = _tool("search_samples").run({"organ": "LK", "limit": 3, "offset": 6})

    assert mock_post.call_args.args[0]["from"] == 6
    assert result["metadata"]["total_results"] == 152
    assert result["metadata"]["next_offset"] == 7
    assert result["metadata"]["has_more"] is True


@patch.object(HuBMAPSampleTool, "_post")
def test_donor_search_forwards_offset_and_reports_exact_total(mock_post):
    mock_post.return_value = _payload("Donor", total=154)
    result = _tool("search_donors").run({"query": "Female", "limit": 3, "offset": 3})

    assert mock_post.call_args.args[0]["from"] == 3
    assert result["metadata"]["total_results"] == 154
    assert result["metadata"]["next_offset"] == 4


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 51}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
def test_invalid_paging_is_rejected_instead_of_clamped(arguments, parameter):
    result = _tool("search_samples").run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
