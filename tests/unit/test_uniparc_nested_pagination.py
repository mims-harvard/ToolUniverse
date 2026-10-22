"""Regressions for reachable UniParc organism/gene-name lists."""

from unittest.mock import Mock

import pytest

from tooluniverse.uniparc_tool import UniParcTool

pytestmark = pytest.mark.unit


def test_search_pages_nested_organisms_and_gene_names(monkeypatch):
    organisms = [
        {"scientificName": f"Species {index}", "taxonId": index} for index in range(12)
    ]
    gene_names = [f"GENE{index}" for index in range(11)]
    response = Mock(headers={})
    response.json.return_value = {
        "results": [
            {
                "uniParcId": "UPI000000003C",
                "organisms": organisms,
                "geneNames": gene_names,
            }
        ]
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.uniparc_tool.requests.get", lambda *args, **kwargs: response
    )
    tool = UniParcTool(
        {
            "name": "UniParc_search",
            "fields": {"endpoint": "search"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run(
        {
            "query": "accession:P62805",
            "size": 1,
            "organism_offset": 5,
            "organism_limit": 3,
            "gene_name_offset": 4,
            "gene_name_limit": 2,
        }
    )

    entry = result["data"][0]
    assert [x["name"] for x in entry["organisms"]] == [
        "Species 5",
        "Species 6",
        "Species 7",
    ]
    assert entry["organisms_total"] == 12
    assert entry["organisms_returned"] == 3
    assert entry["organisms_truncated"] is True
    assert entry["next_organism_offset"] == 8
    assert entry["gene_names"] == ["GENE4", "GENE5"]
    assert entry["gene_names_total"] == 11
    assert entry["gene_names_returned"] == 2
    assert entry["gene_names_truncated"] is True
    assert entry["next_gene_name_offset"] == 6
