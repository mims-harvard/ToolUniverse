"""Regression test for complete UniProt reference-proteome descriptions."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.uniprot_ref_tool import UniProtRefTool

pytestmark = pytest.mark.unit


def test_get_proteome_keeps_full_description_and_exact_length():
    description = "C. elegans reference proteome description. " * 70
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "id": "UP000001940",
        "description": description,
        "taxonomy": {
            "scientificName": "Caenorhabditis elegans",
            "taxonId": 6239,
        },
        "components": [],
    }
    tool = UniProtRefTool({"fields": {"endpoint": "get_proteome"}})
    with patch("tooluniverse.uniprot_ref_tool.requests.get", return_value=response):
        result = tool.run({"proteome_id": "UP000001940"})

    data = result["data"]
    assert len(description) > 500
    assert data["description"] == description
    assert data["description_length"] == len(description)
