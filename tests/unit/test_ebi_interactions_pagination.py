"""Regression tests for reachable EBI Proteins interaction pages."""

from unittest.mock import Mock

import pytest

from tooluniverse.ebi_proteins_interactions_tool import EBIProteinsInteractionsTool

pytestmark = pytest.mark.unit


def _payload():
    return [
        {
            "accession": "P04637",
            "name": "P53_HUMAN",
            "interactions": [
                {
                    "accession1": "P04637",
                    "accession2": f"P{index:05d}",
                    "gene": f"GENE{index}",
                    "experiments": 100 - index,
                }
                for index in range(12)
            ],
            "diseases": [{"diseaseId": "Li-Fraumeni syndrome"}],
            "subcellularLocations": [
                {"locations": [{"location": {"value": "Nucleus"}}]}
            ],
        },
        {
            "accession": "NEIGHBOUR",
            "interactions": [
                {"accession1": "NEIGHBOUR", "accession2": "WRONG", "experiments": 999}
            ],
        },
    ]


def _tool(endpoint, monkeypatch):
    response = Mock()
    response.json.return_value = _payload()
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.ebi_proteins_interactions_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    return EBIProteinsInteractionsTool(
        {
            "name": f"EBIProteins_{endpoint}",
            "fields": {"endpoint": endpoint},
            "parameter": {"properties": {}},
        }
    )


@pytest.mark.parametrize("endpoint,result_key", [("interactions", "interactions"), ("interaction_details", "top_interactions")])
def test_interaction_endpoints_page_sorted_query_partners(
    endpoint, result_key, monkeypatch
):
    result = _tool(endpoint, monkeypatch).run(
        {"accession": "P04637", "offset": 5, "limit": 3}
    )["data"]

    assert [item["partner_accession"] for item in result[result_key]] == [
        "P00005",
        "P00006",
        "P00007",
    ]
    assert result["total_interactions"] == 12
    assert result["offset"] == 5
    assert result["interactions_returned"] == 3
    assert result["interactions_truncated"] is True
    assert result["next_offset"] == 8

