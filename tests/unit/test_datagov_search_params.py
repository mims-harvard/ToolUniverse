"""DataGov_search_datasets sent parameters the catalog ignores.

catalog.data.gov/search reads the text from ``q``, the page size from ``per_page`` and
the agency from ``org_slug``. The tool sent ``_q``, ``rows`` and ``organization``, all
ignored, so every call listed the same 20 datasets (a nonsense query matched as many
as "climate", "rows=3" returned 20 and a made-up organization filtered nothing).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.datagov_tool import DataGovTool

pytestmark = pytest.mark.unit


def _search(arguments, results=None):
    response = MagicMock()
    response.json.return_value = {"results": results or []}
    tool = DataGovTool({"name": "DataGov_search_datasets"})
    with patch("tooluniverse.datagov_tool.requests.get", return_value=response) as get:
        result = tool.run(arguments)
    return result, get.call_args.kwargs["params"]


def test_query_page_size_and_organization_use_the_parameters_the_endpoint_reads():
    _, params = _search({"query": "wolf", "rows": 3, "organization": "noaa"})
    assert params["q"] == "wolf"
    assert params["per_page"] == 3
    assert params["org_slug"] == "noaa"
    assert not {"_q", "rows", "organization"} & set(params)


def test_legacy_gov_suffix_is_dropped_from_the_organization_slug():
    _, params = _search({"query": "air", "organization": "EPA-gov"})
    assert params["org_slug"] == "epa"


def test_no_organization_sends_no_org_slug():
    _, params = _search({"query": "air"})
    assert "org_slug" not in params


def test_unknown_organization_with_no_results_explains_the_slug_format():
    result, _ = _search({"query": "air", "organization": "zzznope"})
    assert result["status"] == "success" and result["data"]["datasets"] == []
    assert "slug 'zzznope'" in result["metadata"]["note"]
    assert "'epa'" in result["metadata"]["note"]


def test_results_are_normalised():
    pkg = {
        "title": "Wolf survey",
        "slug": "wolf-survey",
        "description": "d",
        "organization": {"slug": "doi", "name": "Department of the Interior"},
        "keyword": ["wolf"],
    }
    result, _ = _search({"query": "wolf"}, [pkg])
    (dataset,) = result["data"]["datasets"]
    assert dataset["title"] == "Wolf survey" and dataset["organization"] == "doi"
    assert dataset["url"] == "https://catalog.data.gov/dataset/wolf-survey"
