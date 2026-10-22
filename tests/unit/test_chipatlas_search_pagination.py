from unittest.mock import Mock, patch

import pytest

from tooluniverse.chipatlas_tool import ChIPAtlasTool


def _tool():
    return ChIPAtlasTool(
        {
            "name": "ChIPAtlas_search_datasets",
            "fields": {"operation": "search_datasets"},
            "parameter": {
                "properties": {"operation": {"default": "search_datasets"}}
            },
        }
    )


def _metadata_response():
    text = "\n".join(
        [
            "hg38\tTFs and others\tCTCF\t7\tSRX1,SRX2,SRX3,SRX4,SRX5,SRX6,SRX7",
            "hg38\tTFs and others\tCTCFL\t4\tSRX8,SRX9,SRX10,SRX11",
            "mm10\tTFs and others\tCTCF\t1\tSRX12",
        ]
    )
    response = Mock(status_code=200, text=text)
    response.raise_for_status.return_value = None
    return response


def test_search_paginates_rows_and_nested_experiment_ids_without_truncation():
    with patch(
        "tooluniverse.chipatlas_tool.requests.get", return_value=_metadata_response()
    ):
        first = _tool().run(
            {
                "antigen": "CTCF",
                "limit": 1,
                "offset": 0,
                "experiment_id_limit": 3,
                "experiment_id_offset": 0,
            }
        )["data"]
        second_ids = _tool().run(
            {
                "antigen": "CTCF",
                "limit": 1,
                "offset": 0,
                "experiment_id_limit": 3,
                "experiment_id_offset": 3,
            }
        )["data"]
        second_row = _tool().run(
            {
                "antigen": "CTCF",
                "limit": 1,
                "offset": 1,
                "experiment_id_limit": 3,
            }
        )["data"]

    assert first["num_results"] == 2
    assert first["returned"] == 1
    assert first["has_more"] is True
    assert first["next_offset"] == 1
    assert first["results"][0]["num_experiments"] == 7
    assert first["results"][0]["experiment_ids"] == ["SRX1", "SRX2", "SRX3"]
    assert first["results"][0]["experiment_ids_have_more"] is True
    assert first["results"][0]["next_experiment_id_offset"] == 3
    assert second_ids["results"][0]["experiment_ids"] == ["SRX4", "SRX5", "SRX6"]
    assert second_row["results"][0]["name"] == "CTCFL"
    assert second_row["has_more"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"antigen": "CTCF", "cell_type": "K-562"},
        {"antigen": "CTCF", "limit": 0},
        {"antigen": "CTCF", "offset": -1},
        {"antigen": "CTCF", "experiment_id_limit": "10"},
        {"antigen": "CTCF", "experiment_id_offset": True},
    ],
)
def test_search_rejects_ignored_or_invalid_parameters(arguments):
    with patch(
        "tooluniverse.chipatlas_tool.requests.get",
        side_effect=AssertionError("invalid input must not hit the network"),
    ):
        result = _tool().run(arguments)

    assert result["status"] == "error"
