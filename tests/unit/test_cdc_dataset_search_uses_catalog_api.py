"""cdc_data_search_datasets listed every CDC dataset whatever the search text.

It called ``data.cdc.gov/api/views.json?$q=...&$limit=...``. That endpoint ignores
``$q``, ``q``, ``$limit`` and ``$offset``: "mortality" and "zzqxjvwk" both returned the
same 1,478 views in the same order. Search now goes to Socrata's Discovery API.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.cdc_tool import CDCRESTTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _config(name):
    tools = json.loads((DATA / "cdc_tools.json").read_text(encoding="utf-8"))
    return next(t for t in tools if t["name"] == name)


HIT = {
    "resource": {
        "id": "v6ab-adf5",
        "name": "NCHS - Childhood Mortality Rates",
        "description": "d",
        "updatedAt": "2024-01-01T00:00:00.000Z",
        "download_count": 7,
        "columns_name": ["Year", "Rate"],
    },
    "classification": {
        "domain_category": "National Center for Health Statistics",
        "domain_tags": ["mortality"],
    },
    "permalink": "https://data.cdc.gov/d/v6ab-adf5",
}


def _search(arguments, body=None):
    response = MagicMock()
    response.json.return_value = body or {"resultSetSize": 1, "results": [HIT]}
    tool = CDCRESTTool(_config("cdc_data_search_datasets"))
    with patch("tooluniverse.cdc_tool.requests.get", return_value=response) as get:
        return tool.run(arguments), get


def test_search_text_limit_offset_and_category_go_to_the_discovery_api():
    _, get = _search(
        {"search_query": "mortality", "limit": 5, "offset": 10, "category": "NNDSS"}
    )
    (url,), kwargs = get.call_args
    assert url == "https://api.us.socrata.com/api/catalog/v1"
    params = kwargs["params"]
    assert (
        params["q"] == "mortality" and params["limit"] == 5 and params["offset"] == 10
    )
    assert params["categories"] == "NNDSS"
    assert params["domains"] == params["search_context"] == "data.cdc.gov"
    assert params["only"] == "datasets"
    assert "views.json" not in url


def test_results_are_flat_dataset_records_with_the_total():
    result, _ = _search({"search_query": "mortality"})
    assert result["status"] == "success"
    (dataset,) = result["data"]
    assert dataset["id"] == "v6ab-adf5"
    assert dataset["category"] == "National Center for Health Statistics"
    assert dataset["link"] == "https://data.cdc.gov/d/v6ab-adf5"
    assert result["metadata"]["total_matches"] == 1


def test_no_matches_is_an_empty_success():
    result, _ = _search(
        {"search_query": "zzqxjvwk"}, {"resultSetSize": 0, "results": []}
    )
    assert result["status"] == "success" and result["data"] == []


def test_request_failure_is_reported():
    tool = CDCRESTTool(_config("cdc_data_search_datasets"))
    with patch(
        "tooluniverse.cdc_tool.requests.get",
        side_effect=requests.exceptions.ConnectionError("down"),
    ):
        result = tool.run({"search_query": "x"})
    assert result["status"] == "error" and "down" in result["error"]


def test_dataset_rows_endpoint_still_uses_soda_parameters():
    config = _config("cdc_data_get_dataset")
    tool = CDCRESTTool(config)
    url = tool._build_url({"dataset_id": "abcd-1234", "limit": 3})
    query = parse_qs(urlparse(url).query)
    assert urlparse(url).path == "/api/views/abcd-1234/rows.json"
    assert query["$limit"] == ["3"]
