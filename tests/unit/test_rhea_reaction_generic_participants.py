"""Regression guard for Fix-R20E-1: RheaReactionTool's htmlequation parser
silently dropped generic/polymer participants (e.g. protein-linked residues
like "L-tyrosyl-[protein]") from reactants/products.

Confirmed live for RHEA:10596 (protein-tyrosine kinase reaction): Rhea's
htmlequation identifies these participants with a `data-molid="rhea-comp:..."`
attribute instead of `data-molid="chebi:..."`, since they aren't discrete
ChEBI compounds -- they're Rhea "generic compounds". The old regex only
matched the `chebi:` namespace, so both protein-residue participants
(visible in the plain-text `equation` string) were completely absent from
the parsed reactants/products arrays, even though the upstream API returned
them. Fixed by matching both namespaces and marking generic participants
with `is_generic: true` + a `rhea_comp_id` field (with `chebi_id: null`,
since they have no real ChEBI id) instead of silently dropping them.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.rhea_reaction_tool import RheaReactionTool

pytestmark = pytest.mark.unit

# Real htmlequation for RHEA:10596, captured live from the Rhea REST API.
_KINASE_HTMLEQUATION = (
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="rhea-comp:10136"><small>L</small>-tyrosyl-[protein]</a>'
    '<span class="location"> </span></span> + '
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="chebi:30616">ATP</a><span class="location"> </span></span>'
    " = "
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="rhea-comp:20101"><i>O</i>-phospho-<small>L</small>-tyrosyl-[protein]</a>'
    '<span class="location"> </span></span> + '
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="chebi:456216">ADP</a><span class="location"> </span></span> + '
    '<span class="participant"><span class="stoichiometry"> </span>'
    '<a data-molid="chebi:15378">H<small><sup>+</sup></small></a>'
    '<span class="location"> </span></span>'
)


def _tool(endpoint):
    return RheaReactionTool({"name": "rhea_test", "fields": {"endpoint": endpoint}})


def _json_resp(payload):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


def _tsv_resp(text):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    return r


def _mock_get_for(rhea_id, htmlequation, equation):
    """Build a requests.get side_effect handling both the JSON and TSV
    sub-requests _get_reaction makes (dispatched by `format` param)."""

    def fake_get(url, params=None, **kwargs):
        if params.get("format") == "json":
            return _json_resp(
                {
                    "results": [
                        {
                            "id": rhea_id,
                            "equation": equation,
                            "htmlequation": htmlequation,
                            "status": "approved",
                            "balanced": True,
                            "transport": False,
                            "comment": "",
                        }
                    ]
                }
            )
        # TSV request (full get_reaction only).
        headers = (
            "Reaction identifier\tEquation\tEC number\tUniProt\tPubMed\t"
            "Cross-reference (KEGG)\tCross-reference (MetaCyc)"
        )
        row = f"RHEA:{rhea_id}\t{equation}\tEC:2.7.10.1\t\t15504335\tKEGG:R02584\tMetaCyc:2.7.10.1-RXN"
        return _tsv_resp(headers + "\n" + row)

    return fake_get


def test_get_reaction_participants_includes_generic_protein_residues():
    tool = _tool("get_participants")
    equation = "L-tyrosyl-[protein] + ATP = O-phospho-L-tyrosyl-[protein] + ADP + H(+)"
    fake_get = _mock_get_for("10596", _KINASE_HTMLEQUATION, equation)

    with patch("tooluniverse.rhea_reaction_tool.requests.get", side_effect=fake_get):
        result = tool.run({"rhea_id": "RHEA:10596"})

    assert result["status"] == "success"
    data = result["data"]
    reactant_names = [p["name"] for p in data["reactants"]]
    product_names = [p["name"] for p in data["products"]]
    assert "L-tyrosyl-[protein]" in reactant_names
    assert "O-phospho-L-tyrosyl-[protein]" in product_names
    assert data["n_reactants"] == 2
    assert data["n_products"] == 3


def test_generic_participant_marked_and_carries_rhea_comp_id_not_chebi():
    tool = _tool("get_participants")
    equation = "L-tyrosyl-[protein] + ATP = O-phospho-L-tyrosyl-[protein] + ADP + H(+)"
    fake_get = _mock_get_for("10596", _KINASE_HTMLEQUATION, equation)

    with patch("tooluniverse.rhea_reaction_tool.requests.get", side_effect=fake_get):
        result = tool.run({"rhea_id": "RHEA:10596"})

    generic = next(
        p for p in result["data"]["reactants"] if p["name"] == "L-tyrosyl-[protein]"
    )
    assert generic["is_generic"] is True
    assert generic["chebi_id"] is None
    assert generic["rhea_comp_id"] == "RHEA-COMP:10136"


def test_ordinary_chebi_participants_unaffected():
    tool = _tool("get_participants")
    equation = "L-tyrosyl-[protein] + ATP = O-phospho-L-tyrosyl-[protein] + ADP + H(+)"
    fake_get = _mock_get_for("10596", _KINASE_HTMLEQUATION, equation)

    with patch("tooluniverse.rhea_reaction_tool.requests.get", side_effect=fake_get):
        result = tool.run({"rhea_id": "RHEA:10596"})

    atp = next(p for p in result["data"]["reactants"] if p["name"] == "ATP")
    assert atp["is_generic"] is False
    assert atp["chebi_id"] == "CHEBI:30616"
    assert "rhea_comp_id" not in atp


def test_get_reaction_full_record_also_includes_generic_participants():
    tool = _tool("get_reaction")
    equation = "L-tyrosyl-[protein] + ATP = O-phospho-L-tyrosyl-[protein] + ADP + H(+)"
    fake_get = _mock_get_for("10596", _KINASE_HTMLEQUATION, equation)

    with patch("tooluniverse.rhea_reaction_tool.requests.get", side_effect=fake_get):
        result = tool.run({"rhea_id": "RHEA:10596"})

    assert result["status"] == "success"
    data = result["data"]
    assert len(data["reactants"]) == 2
    assert len(data["products"]) == 3
    assert data["ec_numbers"] == ["EC:2.7.10.1"]


def test_reaction_with_no_generic_participants_has_no_regression():
    """Small-molecule-only reaction (all chebi: namespace) parses identically
    to before the fix -- no is_generic=True entries, no rhea_comp_id keys."""
    tool = _tool("get_participants")
    htmlequation = (
        '<span class="participant"><a data-molid="chebi:17234">D-glucose</a></span>'
        " = "
        '<span class="participant"><a data-molid="chebi:4167">D-glucose 6-phosphate</a></span>'
    )
    equation = "D-glucose = D-glucose 6-phosphate"
    fake_get = _mock_get_for("00001", htmlequation, equation)

    with patch("tooluniverse.rhea_reaction_tool.requests.get", side_effect=fake_get):
        result = tool.run({"rhea_id": "1"})

    assert result["status"] == "success"
    data = result["data"]
    assert len(data["reactants"]) == 1
    assert len(data["products"]) == 1
    for p in data["reactants"] + data["products"]:
        assert p["is_generic"] is False
        assert p["chebi_id"] is not None
        assert "rhea_comp_id" not in p
