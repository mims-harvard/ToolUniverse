import json
from pathlib import Path
from unittest.mock import Mock, patch

import jsonschema
import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


pytestmark = pytest.mark.unit
_NAMES = ("DBLP_search_authors", "DBLP_search_venues")


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/dblp_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response():
    response = Mock(status_code=200, headers={}, reason="OK")
    response.json.return_value = {
        "result": {
            "hits": {
                "@total": "50",
                "@computed": "10",
                "@sent": "2",
                "@first": "2",
                "hit": [{"info": {"value": "a"}}, {"info": {"value": "b"}}],
            }
        }
    }
    return response


@pytest.mark.parametrize("name", _NAMES)
def test_dblp_search_forwards_f_and_exposes_computed_window(name):
    tool = BaseRESTTool(_config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=_response()
    ) as request:
        result = tool.run({"query": "machine", "limit": 2, "offset": 2})

    params = request.call_args.kwargs["params"]
    assert params["q"] == "machine"
    assert params["h"] == 2
    assert params["f"] == 2
    assert result["metadata"] == {
        "total_matches": 50,
        "accessible_results": 10,
        "upstream_truncated": True,
        "returned": 2,
        "offset": 2,
        "requested_offset": 2,
        "limit": 2,
        "has_more": True,
        "next_offset": 4,
        "truncated": True,
        "warning": (
            "DBLP matched more records than its search engine computed for this query. "
            "Pagination can traverse only accessible_results; refine the query to reach "
            "records outside that ranked window."
        ),
    }


@pytest.mark.parametrize("name", _NAMES)
def test_dblp_search_defaults_are_explicit_first_page_controls(name):
    params = BaseRESTTool(_config(name))._build_params({"query": "ICML"})

    assert params["h"] == 10
    assert params["f"] == 0


@pytest.mark.parametrize("name", _NAMES)
def test_dblp_search_data_satisfies_declared_return_schema(name):
    result = BaseRESTTool(_config(name))._process_response(
        _response(), "https://dblp.org/search/api"
    )

    # ToolUniverse CLI validates return_schema against result["data"], not
    # against the surrounding BaseRESTTool status/url/metadata envelope.
    jsonschema.validate(result["data"], _config(name)["return_schema"])


@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("limit", [0, 1001, True, "10"])
def test_dblp_search_rejects_invalid_limits_before_network(name, limit):
    tool = BaseRESTTool(_config(name))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        result = tool.run({"query": "machine", "limit": limit})

    assert result["status"] == "error"
    assert result["parameter"] == "limit"
    request.assert_not_called()


@pytest.mark.parametrize("name", _NAMES)
@pytest.mark.parametrize("offset", [-1, True, "2"])
def test_dblp_search_rejects_invalid_offsets_before_network(name, offset):
    tool = BaseRESTTool(_config(name))
    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        result = tool.run({"query": "machine", "offset": offset})

    assert result["status"] == "error"
    assert result["parameter"] == "offset"
    request.assert_not_called()
