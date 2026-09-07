"""Orphanet_get_genes must not resolve a parent code to a numerically
adjacent disease.

Orphanet curates gene associations on subtype codes, so Orphanet_get_genes
falls back to searching the Orphadata orphacode list for entries whose
preferred term contains the parent's name. That test was a bare substring
check, and Orphanet's terms are numbered: "Mucopolysaccharidosis type 1"
(ORPHA:579, MPS I) is a substring of "Mucopolysaccharidosis type 10"
(ORPHA:662216, MPS X). MPS I therefore reported ARSK -- the MPS X gene, on a
different chromosome -- instead of IDUA, as a plain success.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool, _name_contains_disease

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "candidate",
    [
        "Mucopolysaccharidosis type 10",
        "Mucopolysaccharidosis type 11",
        "Familial hyperaldosteronism type II",
        "Pseudoachondroplasia",
        "Ganglioneuroblastoma",
    ],
)
def test_rejects_names_that_only_extend_the_same_token(candidate):
    parent = {
        "Mucopolysaccharidosis type 10": "Mucopolysaccharidosis type 1",
        "Mucopolysaccharidosis type 11": "Mucopolysaccharidosis type 1",
        "Familial hyperaldosteronism type II": "Familial hyperaldosteronism type I",
        "Pseudoachondroplasia": "Achondroplasia",
        "Ganglioneuroblastoma": "Neuroblastoma",
    }[candidate]
    assert not _name_contains_disease(candidate, parent)


@pytest.mark.parametrize(
    "candidate,parent",
    [
        ("Mucopolysaccharidosis type 4A", "Mucopolysaccharidosis type 4"),
        ("Mucopolysaccharidosis type 2, severe form", "Mucopolysaccharidosis type 2"),
        ("Marfan syndrome type 1", "Marfan syndrome"),
        ("Neonatal Marfan syndrome", "Marfan syndrome"),
        (
            "Autosomal dominant Charcot-Marie-Tooth disease type 2N",
            "Charcot-Marie-Tooth disease",
        ),
        ("Classical Ehlers-Danlos syndrome", "Ehlers-Danlos syndrome"),
    ],
)
def test_accepts_real_subtype_names(candidate, parent):
    assert _name_contains_disease(candidate, parent)


def _json_response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


@patch("tooluniverse.orphanet_tool.requests.get")
def test_mps_one_does_not_borrow_the_mps_ten_gene(mock_get):
    tool = OrphanetTool({"name": "Orphanet_get_genes", "fields": {}})
    name_resp = _json_response(
        {"ORPHAcode": 579, "Preferred term": "Mucopolysaccharidosis type 1"}
    )
    direct_resp = _json_response({}, status_code=404)
    list_resp = _json_response(
        {
            "data": {
                "results": [
                    {
                        "ORPHAcode": 662216,
                        "Preferred term": "Mucopolysaccharidosis type 10",
                    }
                ]
            }
        }
    )
    mock_get.side_effect = [name_resp, direct_resp, list_resp]

    result = tool._get_genes({"orpha_code": "579"})

    assert result["status"] == "success"
    assert result["data"]["genes"] == []
    assert "subtype_sources" not in result["data"]
