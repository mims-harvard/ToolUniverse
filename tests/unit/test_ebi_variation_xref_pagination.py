"""Regression tests for reachable EBI variation cross-references."""

from unittest.mock import Mock

import pytest

from tooluniverse.ebi_proteins_ext_tool import EBIProteinsExtTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "endpoint,identifier",
    [
        ("variation_dbsnp", {"dbsnp_id": "rs1042522"}),
        ("variation_hgvs", {"hgvs": "NC_000017.11:g.7676154G>A"}),
    ],
)
def test_reverse_variation_pages_feature_xrefs(endpoint, identifier, monkeypatch):
    response = Mock()
    response.json.return_value = [
        {
            "accession": "P04637",
            "features": [
                {
                    "type": "VARIANT",
                    "xrefs": [
                        {"name": "ClinVar", "id": f"xref-{index}"}
                        for index in range(12)
                    ],
                }
            ],
        }
    ]
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.ebi_proteins_ext_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    tool = EBIProteinsExtTool(
        {
            "name": f"EBIProteins_{endpoint}",
            "fields": {"endpoint": endpoint},
            "parameter": {"properties": {}},
        }
    )

    feature = tool.run({**identifier, "xref_offset": 5, "xref_limit": 3})["data"][
        "entries"
    ][0]["features"][0]

    assert [xref["id"] for xref in feature["xrefs"]] == [
        "xref-5",
        "xref-6",
        "xref-7",
    ]
    assert feature["xrefs_total"] == 12
    assert feature["xrefs_returned"] == 3
    assert feature["xrefs_truncated"] is True
    assert feature["next_xref_offset"] == 8
