import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.openaire_dataset_tool import OpenAIREDatasetTool


def _config():
    with open("src/tooluniverse/data/openaire_dataset_tools.json") as handle:
        return json.load(handle)[0]


def _response(total=1934, page=2, size=3):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "header": {"total": {"$": total}, "page": {"$": page}, "size": {"$": size}},
            "results": {
                "result": [
                    {
                        "metadata": {
                            "oaf:entity": {
                                "oaf:result": {
                                    "title": {"$": f"Dataset {item}"},
                                    "creator": [{"$": "Researcher"}],
                                }
                            }
                        }
                    }
                    for item in range(size)
                ]
            },
        }
    }
    return response


@patch("tooluniverse.openaire_dataset_tool.requests.get")
def test_dataset_search_forwards_page_and_exposes_exact_navigation(mock_get):
    mock_get.return_value = _response()
    result = OpenAIREDatasetTool(_config()).run(
        {"keywords": "genomics cancer", "size": 3, "page": 2}
    )

    assert mock_get.call_args.kwargs["params"]["page"] == 2
    assert result["metadata"] == {
        "source": "OpenAIRE",
        "api": "https://api.openaire.eu/search/datasets",
        "page": 2,
        "size": 3,
        "returned": 3,
        "total_results": 1934,
        "total_results_is_exact": True,
        "has_more": True,
        "next_page": 3,
        "result_set_complete": False,
    }


@pytest.mark.parametrize(
    "arguments,message",
    [
        ({"size": 0}, "size"),
        ({"size": 101}, "size"),
        ({"page": 0}, "page"),
        ({"page": True}, "page"),
    ],
)
def test_invalid_paging_is_rejected_instead_of_clamped(arguments, message):
    result = OpenAIREDatasetTool(_config()).run({"keywords": "x", **arguments})
    assert result["status"] == "error"
    assert message in result["error"]["message"].lower()
