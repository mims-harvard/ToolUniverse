---
name: tooluniverse-chemical-compound-retrieval
description: Retrieves chemical compound information from PubChem and ChEMBL with disambiguation, cross-referencing, and quality assessment. Creates comprehensive compound profiles with identifiers, properties, bioactivity, and drug information. Use when users need chemical data, drug information, or mention PubChem CID, ChEMBL ID, SMILES, InChI, or compound names.
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
# By SMILES
result = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)
# Cross-reference
chembl_result = tu.tools.ChEMBL_search_compounds(query=name, limit=5)
```

Verify: CID + ChEMBL ID + canonical SMILES + stereochemistry + salt forms.

### Phase 2: Data Retrieval

**PubChem**: `PubChem_get_compound_properties_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_compound_2D_image_by_CID`

**ChEMBL**: `ChEMBL_get_bioactivity_by_chemblid`, `ChEMBL_get_target_by_chemblid`, `ChEMBL_get_assays_by_chemblid`

**Optional**: `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`

### Phase 3: Report

Compound Profile with: Identity (CID, ChEMBL ID, IUPAC, SMILES), Chemical Properties (MW, LogP, HBD, HBA, PSA, Lipinski), Bioactivity (targets, IC50/Ki), Drug Info (if approved), Data Sources.

---

## Fallback Chains

| Primary | Fallback |
|---------|----------|
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

## Tool Reference

**PubChem**: `PubChem_get_CID_by_compound_name`, `PubChem_get_CID_by_SMILES`, `PubChem_get_compound_properties_by_CID`, `PubChem_get_compound_2D_image_by_CID`, `PubChemBioAssay_get_assay_summary`, `PubChemTox_get_acute_effects`, `PubChem_get_associated_patents_by_CID`, `PubChem_search_compounds_by_similarity`, `PubChem_search_compounds_by_substructure`

**ChEMBL**: `ChEMBL_search_drugs`, `ChEMBL_get_molecule`, `ChEMBL_get_activity`, `ChEMBL_get_target`, `ChEMBL_search_targets`, `ChEMBL_search_assays`
