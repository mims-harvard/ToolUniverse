"""Figshare_search_articles and Dryad_search_datasets ignored the search text.

Both hit a *list* endpoint with a search parameter the endpoint does not read, so
"wolf" and "zzqxjvwk" returned the same newest records (Dryad: 72415 datasets;
Figshare: the same three articles). Text search lives elsewhere:

* Dryad: ``GET /api/v2/search?q=...`` (``/api/v2/datasets`` ignores ``q``)
* Figshare: ``POST /v2/articles/search`` with a JSON body (``GET /v2/articles``
  ignores ``search_for``)
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.figshare_tool import FigshareRESTTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _config(filename, name):
    return next(
        t
        for t in json.loads((DATA / filename).read_text(encoding="utf-8"))
        if t["name"] == name
    )


def _response(body, status=200):
    response = MagicMock(status_code=status, text=json.dumps(body))
    response.json.return_value = body
    response.headers = {"content-type": "application/json"}
    return response


def test_dryad_search_uses_the_search_endpoint_not_the_dataset_list():
    fields = _config("dryad_tools.json", "Dryad_search_datasets")["fields"]
    assert fields["endpoint"] == "https://datadryad.org/api/v2/search"


def test_dryad_get_dataset_still_uses_the_dataset_endpoint():
    fields = _config("dryad_tools.json", "Dryad_get_dataset")["fields"]
    assert fields["endpoint"] == "https://datadryad.org/api/v2/datasets/{dataset_id}"


def test_figshare_search_is_a_post_with_the_query_in_the_json_body():
    config = _config("figshare_tools.json", "Figshare_search_articles")
    assert config["type"] == "FigshareRESTTool"
    tool = FigshareRESTTool(config)
    with patch(
        "tooluniverse.figshare_tool.request_with_retry",
        return_value=_response([{"id": 1, "title": "wolf data"}]),
    ) as request:
        result = tool.run(
            {
                "search_for": "wolf",
                "item_type": 3,
                "page_size": 5,
                "published_since": None,
            }
        )
    args, kwargs = request.call_args
    assert args[1:] == ("POST", "https://api.figshare.com/v2/articles/search")
    assert kwargs["json"] == {"search_for": "wolf", "item_type": 3, "page_size": 5}
    assert "params" not in kwargs  # nothing is sent as ignored query-string params
    assert result["status"] == "success"
    assert result["data"][0]["title"] == "wolf data"


def test_figshare_http_error_is_reported():
    tool = FigshareRESTTool(_config("figshare_tools.json", "Figshare_search_articles"))
    with patch(
        "tooluniverse.figshare_tool.request_with_retry",
        return_value=_response({"message": "bad"}, status=422),
    ):
        result = tool.run({"search_for": "wolf"})
    assert result["status"] == "error" and result["status_code"] == 422


def test_figshare_get_article_is_still_a_plain_get():
    config = _config("figshare_tools.json", "Figshare_get_article")
    tool = FigshareRESTTool(config)
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=_response({"id": 123, "title": "t"}),
    ) as request:
        result = tool.run({"article_id": 123})
    assert request.call_args.args[1] == "GET"
    assert request.call_args.args[2].endswith("/articles/123")
    assert result["status"] == "success"
