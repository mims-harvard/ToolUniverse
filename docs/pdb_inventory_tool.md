# PDB coordinate inventory

`PDB_inspect_structure` checks the actual contents of a legacy PDB before a downstream calculation. Supply exactly one of `pdb_path`, `pdb_content`, or `pdb_id`. File and inline inputs stay local; an explicit four-character PDB ID downloads the public RCSB file. Inputs are capped at 4 MiB and downloads at 30 seconds. Mutable path inputs are not cached.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["pdb_inventory"])
result = tu.tools.PDB_inspect_structure(
    pdb_path="prepared_complex.pdb",
    expected_chain_lengths={"A": 75, "B": 621},
    glycan_residue_names=["0MA", "3MA", "0YB", "4YB", "VMA", "VMB"],
    protein_residue_aliases={"NLN": "ASN"},
)
```

The optional GLYCAM labels/alias above are **caller declarations**, not universal PDB chemical-component assignments. Use names appropriate to the force field that wrote your input. The tool includes a small common PDB glycan-name set, counts matching coordinates in **both ATOM and HETATM**, and reports recognized names explicitly. No match means no coordinates with these names; it does not prove biological absence of glycans or complete glycoform coverage.

The response reports chains, residue identifiers including insertion codes, coordinate-derived protein sequences, alternate locations, TER records, nonprotein residues, glycan coordinate counts, element inference, warnings, and input SHA256. Unknown residues with N/CA/C atom names appear as heuristic `X` residues rather than disappearing. Standard amino acids cannot be remapped to different amino acids. Multiple residue identities at one position are flagged.

Exactly coincident heavy-coordinate records are counted with at most 50 groups and eight example identities per group. This can reveal zero-position side-chain placeholders before hydrogen placement. Coincident alternate-location records remain visible too; this is not a general distance-based clash calculation or proof of a physical collision. The tool never removes or reconstructs atoms.

`max_residue_details` defaults to 100 (range 0–1000). It limits the total protein-residue detail rows across chains and each other residue-detail list; counts and coordinate sequences remain complete. `residue_details_truncated` makes clipping explicit. Coincident-coordinate examples use their separate fixed bound.

`expected_chain_lengths_match` compares the **protein-chain mapping exactly** and can expose a missing/renamed/merged chain. The tool does not split a 696-residue chain into a binder and receptor automatically. A mismatch is a reported finding, not a failed tool invocation.

`model_index` selects one model by file order, default 1. Model serial and total model count remain visible; coordinates are never pooled across models. Malformed MODEL/ENDMDL framing, nonfinite coordinates, ambiguous input sources, and out-of-range selections fail explicitly. Alternate locations are counted as coordinate records and remain unresolved; counts are not deduplicated atom populations.

This inventory does not validate chemistry, covalent links, missing residues, collisions, affinity, or pH selectivity. `structure_chemistry_verified`, `binding_verified`, and `pH_selectivity_verified` remain false. B factors are not interpreted as confidence. Coordinate sequences are not SEQRES or full biological sequences.

The fixed-column parser follows the [wwPDB coordinate format](https://www.wwpdb.org/documentation/file-format-content/format33/sect9.html); mmCIF and hybrid-36 residue numbering are unsupported. Public 1UBQ provides an offline fixture and live retrieval example.

SEQRES declarations are checked separately from coordinates. `seqres_chains` reports declared lengths, parsed residue counts, serial/declaration consistency, and whether the selected model's coordinate protein sequence is an ordered subsequence of the declared protein sequence. A consistent subsequence can expose unobserved declared residues, but does not uniquely assign their positions. Unknown names need explicit caller aliases; malformed, contradictory or incompatible metadata remains a reported warning without suppressing the coordinate inventory.

`coordinate_only_protein_chains` identifies protein coordinate chains without SEQRES. Coordinate-only folding loaders may infer a shorter sequence when unresolved residues are absent. `expected_chain_lengths_match` retains its coordinate-count meaning; `expected_chain_lengths_match_seqres` independently compares declared protein-chain lengths, or returns null for unusable metadata. Matching lengths does not prove correct biological sequence identity. Verify the actual downstream parser's sequence and binding-site indices after any input repair. This tool does not write SEQRES, fill coordinates, or reconstruct missing loops.
