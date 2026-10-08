---
name: tooluniverse-chemical-compound-retrieval
description: Retrieve chemical compound data from PubChem and ChEMBL with disambiguation, cross-referencing, and stereochemistry handling. Use for resolving compound names to SMILES/InChI/CID/ChEMBL IDs (including OPSIN deterministic IUPAC-name-to-structure parsing), fetching molecular properties, distinguishing isomers/stereo forms, and cross-validating identity across databases. Always use English compound names; flags ambiguous queries (e.g., Vitamin D has multiple forms).
disable-model-invocation: true
---

# Chemical Compound Information Retrieval

Retrieve comprehensive chemical compound data with proper disambiguation and cross-database validation.

**LOOK UP DON'T GUESS**: Never assume a CID, ChEMBL ID, or molecular property value. Always retrieve from PubChem/ChEMBL.

**English-first**: Always use English compound names in tool calls. Respond in user's language.

## Domain Reasoning: Disambiguation

"Aspirin" = one compound. "Vitamin D" = multiple forms (D2/D3/active metabolite). For generic class names (steroids, vitamins, acids), present candidates and confirm before proceeding.

---

## Workflow

```
Phase 0: Clarify (only if highly ambiguous -- skip for unambiguous names or specific IDs)
Phase 1: Disambiguate → resolve PubChem CID + ChEMBL ID
Phase 2: Retrieve data (silent)
Phase 3: Report compound profile
```

### Phase 1: Disambiguation

```python
# By name
result = tu.tools.PubChem_get_CID_by_compound_name(compound_name=name)
# By SYSTEMATIC (IUPAC) name -> structure, deterministic parser (no DB lookup)
opsin = tu.tools.OPSIN_name_to_structure(name="2-acetoxybenzoic acid")
# Returns {parsed, smiles, inchi, inchikey}; use the SMILES/InChIKey to anchor a
# PubChem_get_CID_by_SMILES lookup. Trade/trivial names give parsed=false -> fall
# back to PubChem_get_CID_by_compound_name for those.
# By SMILES
result = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)
# Cross-reference
chembl_result = tu.tools.ChEMBL_search_molecules(query=name, limit=5)
```

Verify: CID + ChEMBL ID + canonical SMILES + stereochemistry + salt forms.

### Phase 2: Data Retrieval

**PubChem**: `PubChem_get_compound_properties_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_compound_2D_image_by_CID`

**ChEMBL**: `ChEMBL_get_compound_record_activities`, `ChEMBL_get_molecule_targets`, `ChEMBL_get_assay_activities`

**Optional**: `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`

### Phase 3: Report

Compound Profile with: Identity (CID, ChEMBL ID, IUPAC, SMILES), Chemical Properties (MW, LogP, HBD, HBA, PSA, Lipinski), Bioactivity (targets, IC50/Ki), Drug Info (if approved), Data Sources.

---

## Fallback Chains

| Primary | Fallback |
|---------|----------|
| PubChem name lookup (systematic name) | `OPSIN_name_to_structure` → SMILES/InChIKey → PubChem_get_CID_by_SMILES |
| PubChem name lookup | ChEMBL search → SMILES → PubChem_get_CID_by_SMILES |
| ChEMBL bioactivity | PubChem bioassay summary |
| Drug label | Note "unavailable" |

---

## Evidence Grading

| Grade | Criteria |
|-------|----------|
| **Confirmed** | CID + ChEMBL cross-match, InChI/SMILES agree |
| **Probable** | CID found, partial ChEMBL match |
| **Uncertain** | Single database only, or multiple CIDs |
| **Unverified** | No cross-reference, single-source |

**Bioactivity**: ChEMBL > PubChem BioAssay for curated data. IC50/Ki < 100nM = potent, 100nM-1uM = moderate, >10uM = weak. Lipinski violations reduce oral bioavailability but don't disqualify.

---

## SMILES Verification

Always verify novel SMILES: `python3 src/tooluniverse/tools/smiles_verifier.py --smiles "SMILES_STRING"`. Invalid SMILES produce wrong results or cryptic errors.

---

## Identifier Resolution and Cross-Database Referencing

Beyond PubChem/ChEMBL, two more tools resolve identifiers when a name doesn't
hit in PubChem or you need cross-references across other chemical databases:

- **`NCICACTUS_resolve`** (NCI CACTUS resolver) — converts between chemical
  names (IUPAC or common), SMILES, InChI, InChIKey, CAS number, and molecular
  formula. Verified live: `NCICACTUS_resolve(identifier="ibuprofen", representation="smiles")`
  → `CC(C)Cc1ccc(cc1)C(C)C(O)=O`; also resolves a CAS number (`"50-78-2"`) straight
  to an IUPAC name (`"2-acetyloxybenzoic acid"`, i.e. aspirin) or an InChIKey to
  a formula. Useful as a second name-resolution path alongside `OPSIN_name_to_structure`
  and `PubChem_get_CID_by_compound_name` — CACTUS handles CAS numbers and trivial
  names OPSIN can't parse.
- **`UniChem_search_compound`** / **`UniChem_connectivity_search`** — given an
  InChIKey (or a source-database compound ID), returns cross-references across
  UniChem's 25+ registered source databases (ChEMBL, DrugBank, PubChem, Wikipedia,
  ChEBI, etc. — verified live via `UniChem_list_sources`). `connectivity_search`
  additionally finds compounds sharing the same connectivity layer (same skeleton,
  different stereochemistry/salt/isotope) — use this when you want "the same
  molecule under any name/form" rather than an exact match. Verified live on
  aspirin's InChIKey (`BSYNRYMUTXBXSQ-UHFFFAOYSA-N`): both returned real
  cross-database records including a Wikipedia link.

**Chained identifier workflow (real values):** `NCICACTUS_resolve(identifier="aspirin", representation="smiles")`
→ `CC(=O)Oc1ccccc1C(O)=O` → resolve the same identifier with `representation="stdinchikey"`
→ real result `"InChIKey=BSYNRYMUTXBXSQ-UHFFFAOYSA-N"` (**note the `InChIKey=` prefix** —
verified live; strip it before passing the bare key to another tool) → feed the
bare `BSYNRYMUTXBXSQ-UHFFFAOYSA-N` into `UniChem_search_compound` for cross-database
IDs → `PubChem_get_CID_by_SMILES` to re-anchor in PubChem if needed.

## Cheminformatics Calculations and Structure Visualization

For calculations and rendering beyond property lookup:

- **`RDKit_pharmacophore_features`** — extracts pharmacophore feature centers
  (HBD, HBA, aromatic, hydrophobic, etc.) from a SMILES via SMARTS matching.
  Verified live on aspirin (`CC(=O)Oc1ccccc1C(=O)O`): 1 HBD with atom index,
  method documented as `"SMARTS-based pharmacophore features"`.
- **`RDKit_matched_molecular_pair`** — given two SMILES, finds the single-cut
  MMP transformation between them (Hussain-Rea algorithm) plus their Tanimoto
  similarity — useful for "what single substitution turns compound A into
  compound B" (SAR analysis).
- **`visualize_molecule_2d`** — renders a 2D structure (from SMILES, InChI, or
  a molecule name) to PNG/SVG/interactive HTML. Verified live: returns an
  embedded HTML visualization on success.
- **`visualize_molecule_3d`** — renders a 3D structure via RDKit + py3Dmol.
  **Requires `py3Dmol` installed** — verified live that without it, the tool
  returns a clean `{"status": "error", ...: "py3Dmol is not installed. Please
  install it with: pip install py3Dmol"}` rather than crashing; check for this
  before assuming a visualization request has failed for another reason.

---

## Tool Reference

**PubChem**: `PubChem_get_CID_by_compound_name`, `PubChem_get_CID_by_SMILES`, `PubChem_get_compound_properties_by_CID`, `PubChem_get_compound_2D_image_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`, `PubChem_search_compounds_by_substructure`

**ChEMBL**: `ChEMBL_search_drugs`, `ChEMBL_get_molecule`, `ChEMBL_get_activity`, `ChEMBL_get_target`, `ChEMBL_search_targets`, `ChEMBL_search_assays`

**Name parsing**: `OPSIN_name_to_structure` (param `name`) — deterministic IUPAC/systematic-name → SMILES/InChI/InChIKey parser; the go-to for resolving a systematic name to structure without a DB round-trip. Trade/trivial names return `parsed=false` (use PubChem name lookup for those).

**Identifier resolution & cross-referencing**: `NCICACTUS_resolve`, `UniChem_search_compound`, `UniChem_connectivity_search`, `UniChem_list_sources`

**Cheminformatics & visualization**: `RDKit_pharmacophore_features`, `RDKit_matched_molecular_pair`, `visualize_molecule_2d`, `visualize_molecule_3d`
