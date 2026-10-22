import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.unibind_tool import UniBindRESTTool


pytestmark = pytest.mark.unit
_ROOT = Path(__file__).parents[2]


def _config(name):
    configs = json.loads(
        (_ROOT / "src/tooluniverse/data/unibind_tools.json").read_text()
    )
    return next(config for config in configs if config["name"] == name)


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("page", 0),
        ("page", True),
        ("page", "2"),
        ("page_size", 0),
        ("page_size", 1001),
        ("page_size", True),
        ("page_size", "25"),
    ],
)
def test_dataset_search_rejects_silent_integer_coercion_and_clamping(parameter, value):
    tool = UniBindRESTTool(_config("UniBind_search_datasets"))
    with patch.object(tool, "_get_json") as request:
        result = tool.run({parameter: value})

    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()


@pytest.mark.parametrize("filter_name", ["tf_name", "species", "cell_line"])
@pytest.mark.parametrize("value", ["", "  ", True, 10])
def test_dataset_search_rejects_invalid_optional_filters(filter_name, value):
    tool = UniBindRESTTool(_config("UniBind_search_datasets"))
    with patch.object(tool, "_get_json") as request:
        result = tool.run({filter_name: value})

    assert result["status"] == "error"
    assert result["parameter"] == filter_name
    request.assert_not_called()


def test_dataset_search_exposes_both_page_directions_and_completeness():
    tool = UniBindRESTTool(_config("UniBind_search_datasets"))
    payload = {
        "count": 982,
        "next": "https://example.test?page=3",
        "previous": "https://example.test?page=1",
        "results": [{"tf_name": "CTCF", "url": "https://x/datasets/DS2/"}],
    }
    with patch.object(tool, "_get_json", return_value=payload):
        result = tool.run({"tf_name": "CTCF", "page": 2, "page_size": 2})

    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["previous_page"] == 1
    assert result["metadata"]["truncated"] is True
    assert result["metadata"]["result_set_complete"] is False


def test_tf_catalog_exhausts_every_upstream_page_before_local_offset():
    tool = UniBindRESTTool(_config("UniBind_list_tfs"))
    pages = [
        {
            "count": 4,
            "next": "https://example.test?page=2",
            "results": [{"tf_name": "TF1"}, {"tf_name": "TF2"}],
        },
        {
            "count": 4,
            "next": None,
            "results": [{"tf_name": "TF3"}, {"tf_name": "TF4"}],
        },
    ]
    with patch.object(tool, "_get_json", side_effect=pages) as request:
        result = tool.run({"limit": 2, "offset": 2})

    assert request.call_count == 2
    assert request.call_args_list[0].args[1]["page"] == 1
    assert request.call_args_list[1].args[1]["page"] == 2
    assert result["data"] == ["TF3", "TF4"]
    assert result["metadata"]["upstream_records_retrieved"] == 4
    assert result["metadata"]["upstream_pages_fetched"] == 2
    assert result["metadata"]["upstream_complete"] is True


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("limit", 0),
        ("limit", 1001),
        ("limit", True),
        ("limit", "20"),
        ("offset", -1),
        ("offset", True),
        ("offset", "2"),
        ("search", ""),
        ("search", True),
    ],
)
def test_tf_catalog_rejects_invalid_local_controls(parameter, value):
    tool = UniBindRESTTool(_config("UniBind_list_tfs"))
    with patch.object(tool, "_get_json") as request:
        result = tool.run({parameter: value})

    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()


def test_unknown_operation_is_rejected_instead_of_becoming_dataset_search():
    tool = UniBindRESTTool(_config("UniBind_search_datasets"))
    with patch.object(tool, "_get_json") as request:
        result = tool.run({"operation": "typo"})

    assert result["status"] == "error"
    assert result["parameter"] == "operation"
    request.assert_not_called()
