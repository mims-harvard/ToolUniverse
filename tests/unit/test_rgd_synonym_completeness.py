"""Regression test for complete RGD/Alliance gene synonyms."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.rgd_tool import RGDTool

pytestmark = pytest.mark.unit


def test_search_keeps_all_gene_synonyms_and_reports_count():
    synonyms = [f"Tp53-alias-{index}" for index in range(9)]
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "total": 1,
        "results": [
            {
                "category": "gene_search_result",
                "curie": "RGD:3889",
                "symbol": "Tp53",
                "name": "tumor protein p53",
                "species": "Rattus norvegicus",
                "synonyms": synonyms,
            }
        ],
    }
    tool = RGDTool({"fields": {"endpoint_type": "search_genes"}})
    with patch.object(tool.session, "get", return_value=response):
        result = tool.run({"query": "Tp53", "species": "rat"})

    gene = result["data"][0]
    assert gene["synonyms"] == synonyms
    assert gene["synonym_count"] == 9
