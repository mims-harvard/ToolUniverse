"""Regression for complete Xenbase search synonyms."""

from unittest.mock import Mock

import pytest

from tooluniverse.xenbase_tool import XenbaseTool

pytestmark = pytest.mark.unit


def test_search_keeps_all_upstream_synonyms(monkeypatch):
    synonyms = [
        "wagr",
        "an2",
        "mgda",
        "pax-6",
        "xpax6",
        "pax6-b",
        "paired box 6",
        "pax6",
        "XLPAX6",
        "pax6-a",
    ]
    response = Mock()
    response.json.return_value = {
        "total": 1,
        "results": [
            {
                "category": "gene_search_result",
                "curie": "Xenbase:XB-GENE-484088",
                "symbol": "pax6",
                "name": "paired box 6",
                "species": "Xenopus tropicalis",
                "taxonId": "NCBITaxon:8364",
                "synonyms": synonyms,
            }
        ],
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.xenbase_tool.requests.get", lambda *args, **kwargs: response
    )

    tool = XenbaseTool(
        {
            "name": "Xenbase_search_genes",
            "fields": {"endpoint_type": "search_genes"},
            "parameter": {"properties": {}},
        }
    )
    result = tool.run({"query": "pax6", "species": "tropicalis", "limit": 1})

    assert len(synonyms) > 5
    assert result["data"][0]["synonyms"] == synonyms
    assert result["data"][0]["synonyms_count"] == len(synonyms)
