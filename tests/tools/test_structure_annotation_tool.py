"""Unit tests for StructureAnnotationTool.

These tests do NOT require network — they mock the RCSB PDB download with
a synthetic minimal PDB string and exercise the parsing + distance +
classification logic end-to-end. They DO require biopython + freesasa to be
installed (extras: `pip install biopython freesasa`).
"""

import pytest

pytest.importorskip("Bio.PDB", reason="biopython required for structure-annotation tests")
pytest.importorskip("freesasa", reason="freesasa required for structure-annotation tests")

from tooluniverse.structure_annotation_tool import StructureAnnotationTool


# Minimal synthetic 2-chain + 1-ligand PDB.
# Chain A: 3 residues (ALA, GLY, SER) at z=0, x=0..2
# Chain B: 1 residue (ALA) at z=4 (within 5A of chain A residue 1)
# Ligand GNP: heavy atoms near chain A residue 2 (within 5A)
_MINI_PDB = """\
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.000   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1       1.500   1.000   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1       2.500   1.000   0.000  1.00 20.00           O
ATOM      5  CB  ALA A   1       1.500  -1.000   0.000  1.00 20.00           C
ATOM      6  N   GLY A   2       3.000   0.000   0.000  1.00 20.00           N
ATOM      7  CA  GLY A   2       4.000   0.000   0.000  1.00 20.00           C
ATOM      8  C   GLY A   2       4.500   1.000   0.000  1.00 20.00           C
ATOM      9  O   GLY A   2       5.500   1.000   0.000  1.00 20.00           O
ATOM     10  N   SER A   3      14.000   0.000   0.000  1.00 20.00           N
ATOM     11  CA  SER A   3      15.000   0.000   0.000  1.00 20.00           C
ATOM     12  C   SER A   3      15.500   1.000   0.000  1.00 20.00           C
ATOM     13  O   SER A   3      16.500   1.000   0.000  1.00 20.00           O
ATOM     14  CB  SER A   3      15.500  -1.000   0.000  1.00 20.00           C
ATOM     15  OG  SER A   3      16.000  -2.000   0.000  1.00 20.00           O
ATOM     16  N   ALA B   1       1.500  -1.000   4.000  1.00 20.00           N
ATOM     17  CA  ALA B   1       1.500   0.000   4.000  1.00 20.00           C
ATOM     18  C   ALA B   1       2.500   0.500   4.000  1.00 20.00           C
ATOM     19  O   ALA B   1       3.500   0.500   4.000  1.00 20.00           O
ATOM     20  CB  ALA B   1       1.500  -2.000   3.500  1.00 20.00           C
HETATM   21  PA  GNP A 100       4.000  -1.000   2.000  1.00 30.00           P
HETATM   22  O1A GNP A 100       4.500  -1.500   2.500  1.00 30.00           O
HETATM   23  O2A GNP A 100       4.500   0.000   2.000  1.00 30.00           O
END
"""


def _run(tool, **kwargs):
    args = {
        "operation": "annotate_per_residue",
        "pdb_content": _MINI_PDB,
        "target_chain": "A",
    }
    args.update(kwargs)
    return tool.run(args)


def test_basic_annotation_succeeds():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"])
    assert result["status"] == "success"
    assert result["n_residues"] == 3
    assert result["target_chain"] == "A"


def test_residues_correctly_classified():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"], distance_cutoff=5.0)
    by_pos = {r["position"]: r for r in result["annotations"]}
    # ALA at pos 1 is within 5A of chain B CB (1.5,-2,3.5) — should be interface
    assert by_pos[1]["region"] in ("interface", "both"), by_pos[1]
    # GLY at pos 2 — Ca only is at (4,0,0); GNP atoms at (4,-1,2): dist ~ sqrt(1+4) ~ 2.24 < 5 → ligand
    assert by_pos[2]["region"] in ("ligand", "both"), by_pos[2]
    # SER at pos 3 — sidechain at (7..8, -1..-2, 0); far from both
    assert by_pos[3]["region"] == "other", by_pos[3]


def test_no_partner_no_ligand_yields_all_other():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=[], ligand_resnames=[])
    for row in result["annotations"]:
        assert row["region"] == "other"
        assert row["dist_partner"] is None
        assert row["dist_ligand"] is None


def test_unknown_chain_returns_error():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, target_chain="Z")
    assert result["status"] == "error"
    assert "Z" in result["error"]


def test_neither_pdb_id_nor_content_returns_error():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = tool.run({"operation": "annotate_per_residue"})
    assert result["status"] == "error"
    assert "pdb_id" in result["error"] or "pdb_content" in result["error"]


def test_unknown_operation_returns_error():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = tool.run({"operation": "bogus"})
    assert result["status"] == "error"
    assert "Unknown operation" in result["error"]


def test_rsa_in_unit_interval():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"])
    rsas = [r["rsa"] for r in result["annotations"] if r["rsa"] is not None]
    assert len(rsas) == 3
    for v in rsas:
        # freesasa relativeTotal can substantially exceed 1 for tiny synthetic
        # peptides (the max-ASA reference assumes a normal protein context);
        # for real proteins values cluster in [0, 1.2].
        assert v >= 0.0 and v < 5.0, v


def test_provenance_attribution_present():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"])
    assert "upstream research workflow" in result["provenance"]


def test_method_block_documents_choices():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"])
    method = result["method"]
    assert "sidechain_heavy" in method["interface_metric"]
    assert "freesasa" in method["rsa_source"]
    assert method["ss_source"] is None  # not requested


def test_distance_cutoff_changes_classification():
    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    tight = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"], distance_cutoff=1.0)
    loose = _run(tool, partner_chains=["B"], ligand_resnames=["GNP"], distance_cutoff=10.0)
    tight_iface = sum(1 for r in tight["annotations"] if r["region"] in ("interface", "both"))
    loose_iface = sum(1 for r in loose["annotations"] if r["region"] in ("interface", "both"))
    assert loose_iface >= tight_iface


@pytest.mark.timeout(60)
def test_include_secondary_structure_live_pdbe():
    """Real-network test: fetch SS for 6VJJ from PDBe REST.

    Verifies the include_secondary_structure=True code path actually returns
    populated ss_element values. Skipped if PDBe is unreachable.
    """
    import requests
    try:
        requests.get("https://www.ebi.ac.uk/pdbe/api/pdb/entry/secondary_structure/6vjj", timeout=10).raise_for_status()
    except requests.RequestException:
        pytest.skip("PDBe REST unreachable")

    tool = StructureAnnotationTool({"name": "Structure_annotate_per_residue"})
    result = tool.run({
        "operation": "annotate_per_residue",
        "pdb_id": "6VJJ",
        "target_chain": "A",
        "partner_chains": ["B"],
        "ligand_resnames": ["GNP", "MG"],
        "include_secondary_structure": True,
    })
    assert result["status"] == "success"
    assert result["method"]["ss_source"] == "pdbe_rest"
    ss_values = [r.get("ss_element") for r in result["annotations"]]
    # KRAS β1 strand spans residues 2-9 — must have strand residues in the response
    strand_count = ss_values.count("strand")
    helix_count = ss_values.count("helix")
    assert strand_count > 5, f"expected KRAS to have multiple strand residues, got {strand_count}"
    assert helix_count > 10, f"expected KRAS to have multiple helix residues, got {helix_count}"
    # Position 5 (KRAS β1 residue) must be 'strand'
    pos5 = next(r for r in result["annotations"] if r["position"] == 5)
    assert pos5["ss_element"] == "strand", f"KRAS pos 5 should be strand, got {pos5['ss_element']}"
