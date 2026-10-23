import inspect
import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.openalex_tool import OpenAlexRESTTool
from tooluniverse.tools.openalex_search_authors import openalex_search_authors
from tooluniverse.tools.openalex_search_institutions import openalex_search_institutions
from tooluniverse.tools.openalex_search_sources import openalex_search_sources
from tooluniverse.tools.openalex_search_works import openalex_search_works


NAMES = [
    "openalex_search_works",
    "openalex_search_authors",
    "openalex_search_institutions",
    "openalex_search_sources",
]


def config(name):
    with open("src/tooluniverse/data/openalex_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def response(count=25000, ids=(1, 2), next_cursor="opaque-next"):
    result = Mock(status_code=200, text="", url="https://api.openalex.org/request")
    result.json.return_value = {
        "meta": {"count": count, "next_cursor": next_cursor},
        "results": [{"id": f"https://openalex.org/W{i}"} for i in ids],
    }
    return result


@pytest.mark.parametrize("name", NAMES)
@patch("tooluniverse.openalex_tool.request_with_retry")
def test_openalex_cursor_is_forwarded_without_conflicting_page(request, name):
    request.return_value = response()
    result = OpenAlexRESTTool(config(name)).run(
        {"search": "cancer", "per_page": 2, "page": 1, "cursor": "*"}
    )

    params = request.call_args.kwargs["params"]
    assert params["cursor"] == "*"
    assert params["per-page"] == 2
    assert "page" not in params
    assert result["metadata"]["mode"] == "cursor"
    assert result["metadata"]["total_results"] == 25000
    assert result["metadata"]["next_cursor"] == "opaque-next"


@patch("tooluniverse.openalex_tool.request_with_retry")
def test_openalex_basic_page_discloses_unreachable_tail_and_limit_alias(request):
    request.return_value = response()
    result = OpenAlexRESTTool(config("openalex_search_works")).run(
        {"search": "cancer", "per_page": 10, "limit": 2, "page": 2}
    )

    assert request.call_args.kwargs["params"]["per-page"] == 2
    metadata = result["metadata"]
    assert metadata["mode"] == "basic_page"
    assert metadata["total_results"] == 25000
    assert metadata["accessible_results"] == 10000
    assert metadata["upstream_truncated"] is True
    assert metadata["next_page"] == 3
    assert "cursor='*'" in metadata["warning"]


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"per_page": 0}, "per_page"),
        ({"per_page": 201}, "per_page"),
        ({"page": 0}, "page"),
        ({"page": 51, "per_page": 200}, "page"),
        ({"cursor": ""}, "cursor"),
        ({"cursor": 123}, "cursor"),
    ],
)
@patch("tooluniverse.openalex_tool.request_with_retry")
def test_openalex_rejects_invalid_or_unreachable_paging_before_network(
    request, arguments, parameter
):
    result = OpenAlexRESTTool(config("openalex_search_works")).run(
        {"search": "cancer", **arguments}
    )
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()


def test_generated_openalex_search_wrappers_expose_cursor():
    for wrapper in (
        openalex_search_works,
        openalex_search_authors,
        openalex_search_institutions,
        openalex_search_sources,
    ):
        assert "cursor" in inspect.signature(wrapper).parameters
