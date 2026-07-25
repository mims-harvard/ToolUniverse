"""Regression guards for values, counts and sentinels that misreported reality.

* RDKit_matched_molecular_pair labelled ExactMolWt (monoisotopic mass) as "MW"
  and formatted deltas in Da, so imatinib read 493.26 against the 493.6 every
  other tool in the suite reports.
* RDKit_pharmacophore_features counted amide, anilide and every neutral
  aromatic nitrogen as PosIonizable (imatinib: 7, RDKit's own reference: 2),
  and reported filtered-out features as a hard 0 rather than "not computed".
* PubChem_get_CID_by_SMILES passed through PubChem's CID-0 not-found sentinel
  as a success.
* DGIdb interaction tools reported metadata.total as the GENE count.
* Five IEDB tools declared an `offset` that always failed, because PostgREST
  rejects offset without order.
* intact_get_interactions truncated to 25 of 87 with the working `size`
  parameter undeclared.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dgidb_tool import DGIdbTool
from tooluniverse.pubchem_tool import PubChemRESTTool

pytestmark = pytest.mark.unit

DATA_DIR = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _config(filename, tool_name):
    for tool in json.loads((DATA_DIR / filename).read_text()):
        if tool.get("name") == tool_name:
            return tool
    raise AssertionError(f"{tool_name} not found in {filename}")


# --------------------------------------------------------------------------
# RDKit descriptors and pharmacophore features
# --------------------------------------------------------------------------

rdkit = pytest.importorskip("rdkit", reason="rdkit not installed")

IMATINIB = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1"


def _cheminfo(endpoint):
    from tooluniverse.rdkit_cheminfo_tool import RDKitCheminfoTool

    return RDKitCheminfoTool({"name": "rdkit", "fields": {"endpoint": endpoint}})


def test_mw_is_average_molecular_weight_not_monoisotopic():
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(IMATINIB)
    descriptors = _cheminfo("matched_molecular_pair")._get_descriptors(mol)

    assert descriptors["MW"] == round(Descriptors.MolWt(mol), 2) == 493.62
    assert descriptors["MW"] != round(Descriptors.ExactMolWt(mol), 2)


def test_exact_mass_is_reported_separately():
    from rdkit import Chem

    mol = Chem.MolFromSmiles(IMATINIB)
    descriptors = _cheminfo("matched_molecular_pair")._get_descriptors(mol)
    assert descriptors["exact_mass"] == pytest.approx(493.259, abs=0.01)


def test_halogen_mw_matches_average_mass():
    """The monoisotopic/average gap is widest for heavy halogens."""
    from rdkit import Chem

    descriptors = _cheminfo("matched_molecular_pair")._get_descriptors(
        Chem.MolFromSmiles("CC(=O)Nc1ccc(Br)cc1")
    )
    assert descriptors["MW"] == pytest.approx(214.06, abs=0.01)


@pytest.mark.parametrize(
    "name,smiles,expected",
    [
        ("acetamide", "CC(N)=O", 0),
        ("acetanilide", "CC(=O)Nc1ccccc1", 0),
        ("pyridine", "c1ccncc1", 0),
        ("aniline", "Nc1ccccc1", 0),
        ("sulfanilamide", "Nc1ccc(S(N)(=O)=O)cc1", 0),
        ("triethylamine", "CCN(CC)CC", 1),
        ("benzylamine", "NCc1ccccc1", 1),
        ("piperazine", "C1CNCCN1", 2),
        ("imatinib", IMATINIB, 2),
    ],
)
def test_posionizable_matches_rdkit_reference_definitions(name, smiles, expected):
    """Counts must agree with RDKit's own BaseFeatures.fdef."""
    from rdkit import Chem
    from tooluniverse.rdkit_cheminfo_tool import _PHARM_SMARTS

    mol = Chem.MolFromSmiles(smiles)
    matched = set()
    for smarts in _PHARM_SMARTS["PosIonizable"]:
        pattern = Chem.MolFromSmarts(smarts)
        assert pattern is not None, f"PosIonizable SMARTS failed to parse: {smarts}"
        for hit in mol.GetSubstructMatches(pattern):
            matched.update(hit)
    assert len(matched) == expected, name


def test_filtered_out_features_report_null_not_zero():
    result = _cheminfo("pharmacophore_features").run(
        {"smiles": IMATINIB, "include_features": ["HBD"]}
    )
    interpretation = result["data"]["interpretation"]
    assert interpretation["HBD_count"] == 2
    assert interpretation["HBA_count"] is None
    assert interpretation["aromatic_atom_count"] is None
    assert interpretation["hydrophobic_atom_count"] is None
    assert "include_features" in interpretation["note"]


def test_unfiltered_request_still_reports_every_count():
    result = _cheminfo("pharmacophore_features").run({"smiles": IMATINIB})
    interpretation = result["data"]["interpretation"]
    assert interpretation["HBA_count"] == 6
    assert interpretation["aromatic_atom_count"] == 24
    assert interpretation["hydrophobic_atom_count"] == 28
    assert result["data"]["feature_counts"]["PosIonizable"] == 2


# --------------------------------------------------------------------------
# PubChem CID-0 sentinel
# --------------------------------------------------------------------------


def test_cid_zero_sentinel_becomes_an_error():
    result = PubChemRESTTool._cid_not_found({"IdentifierList": {"CID": [0]}})
    assert result is not None
    assert result["status"] == "error"
    assert "No CID found" in result["error"]


def test_real_cid_is_not_treated_as_not_found():
    assert PubChemRESTTool._cid_not_found({"IdentifierList": {"CID": [2244]}}) is None


def test_mixed_cid_list_is_not_treated_as_not_found():
    assert PubChemRESTTool._cid_not_found({"IdentifierList": {"CID": [0, 2244]}}) is None


def test_non_cid_payloads_pass_through():
    assert PubChemRESTTool._cid_not_found({"PropertyTable": {}}) is None
    assert PubChemRESTTool._cid_not_found([1, 2, 3]) is None


# --------------------------------------------------------------------------
# DGIdb counts
# --------------------------------------------------------------------------


def test_dgidb_reports_interaction_total_alongside_gene_count():
    payload = {
        "data": {
            "genes": {
                "nodes": [
                    {"name": "PDCD1", "interactions": [{}] * 68},
                    {"name": "CD274", "interactions": [{}] * 36},
                    {"name": "CTLA4", "interactions": [{}] * 36},
                ]
            }
        }
    }
    result = DGIdbTool._envelope(payload, "genes")
    assert result["metadata"]["genes_returned"] == 3
    assert result["metadata"]["interactions_total"] == 140


def test_dgidb_errors_still_propagate():
    result = DGIdbTool._envelope({"errors": [{"message": "boom"}]}, "genes")
    assert result["status"] == "error"


# --------------------------------------------------------------------------
# Config-level declarations
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_name",
    [
        "iedb_search_antigens",
        "iedb_search_mhc",
        "iedb_search_bcell",
        "iedb_search_references",
        "iedb_get_epitope_antigens",
        "iedb_get_epitope_mhc",
        "iedb_get_epitope_references",
    ],
)
def test_iedb_tools_declare_a_default_order_so_offset_works(tool_name):
    """PostgREST rejects offset without order; every offset-bearing tool needs one."""
    config = _config("iedb_tools.json", tool_name)
    order = (config.get("fields") or {}).get("default_params", {}).get("order")
    assert order, f"{tool_name} declares offset but has no default order"
    assert order.endswith((".asc", ".desc"))


@pytest.mark.parametrize(
    "tool_name", ["intact_get_interactions", "intact_get_interactor"]
)
def test_intact_declares_the_size_parameter_it_already_honours(tool_name):
    config = _config("intact_tools.json", tool_name)
    assert "size" in config["parameter"]["properties"]


def test_intact_format_enum_does_not_advertise_xml_it_cannot_produce():
    config = _config("intact_tools.json", "intact_get_interactions")
    assert config["parameter"]["properties"]["format"]["enum"] == ["json"]


def test_hla_ligand_atlas_documents_all_three_binder_flags():
    """s/ = strong, w/ = weak, n/ = NON-binder -- the docs had n/ as 'strong'."""
    description = _config(
        "hlaligandatlas_tools.json", "HLALigandAtlas_get_benign_peptides"
    )["description"]
    assert "'s/' = strong binder" in description
    assert "'n/' = NON-binder" in description
    assert "strong 'n/'" not in description
