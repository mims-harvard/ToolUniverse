import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/ncbi_gene_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NCBIGene_search"
    )


def test_ncbi_gene_search_forwards_retstart_and_retmax():
    config = _config()
    tool = BaseRESTTool(config)
    response = Mock(status_code=200, headers={})
    response.json.return_value = {
        "esearchresult": {
            "count": "25",
            "retmax": "3",
            "retstart": "3",
            "idlist": ["4", "5", "6"],
        }
    }

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=response
    ) as request:
        result = tool.run({"term": "cancer[Title]", "retmax": 3, "retstart": 3})

    assert request.call_args.kwargs["params"]["retmax"] == 3
    assert request.call_args.kwargs["params"]["retstart"] == 3
    assert result["data"]["esearchresult"]["count"] == "25"
    assert result["data"]["esearchresult"]["idlist"] == ["4", "5", "6"]


def test_ncbi_gene_search_defaults_are_real_first_page_controls():
    config = _config()
    params = BaseRESTTool(config)._build_params({"term": "TP53[Symbol]"})

    assert params["retmax"] == 10
    assert params["retstart"] == 0
