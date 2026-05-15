# Phase Details: Chemical Safety Assessment

## Phase 0: Compound Disambiguation (ALWAYS FIRST)

**CRITICAL**: Resolve compound identity before any analysis.

### Input Types Handled

| Input Format | Resolution Strategy |
|-------------|---------------------|
| Drug name (e.g., "Aspirin") | PubChem_get_CID_by_compound_name -> get SMILES from properties |
| SMILES string | Use directly for ADMET-AI; resolve to CID for other tools |
| PubChem CID | PubChem_get_compound_properties_by_CID -> get SMILES + name |
| ChEMBL ID | ChEMBL_get_molecule -> get SMILES + properties |

### Resolution Steps

1. **Input detection**: Determine if input is name, SMILES, CID, or ChEMBL ID
   - SMILES: contains typical SMILES characters (=, #, [, ], (, ), c, n, o and no spaces in middle)
   - CID: numeric only
   - ChEMBL: starts with "CHEMBL"
   - Otherwise: treat as compound name
2. **Name to CID**: `PubChem_get_CID_by_compound_name(name=<compound_name>)`
3. **CID to properties**: `PubChem_get_compound_properties_by_CID(cid=<cid>)`
4. **Extract SMILES**: Get SMILES from PubChem properties (field: `ConnectivitySMILES`, `CanonicalSMILES`, or `IsomericSMILES`)
5. **Store resolved IDs**: Maintain dict with `name`, `smiles`, `cid`, `formula`, `weight`, `inchi`

---

## Phase 1: Predictive Toxicology (ADMET-AI)

**When**: SMILES is available

| Tool | Predicted Endpoints | Parameter |
|------|---------------------|-----------|
| `ADMETAI_predict_toxicity` | AMES, Carcinogens_Lagunin, ClinTox, DILI, LD50_Zhu, Skin_Reaction, hERG | `smiles`: list[str] |
| `ADMETAI_predict_stress_response` | Stress response pathway activation (ARE, ATAD5, HSE, MMP, p53) | `smiles`: list[str] |
| `ADMETAI_predict_nuclear_receptor_activity` | AhR, AR, ER, PPARg, Aromatase nuclear receptor activity | `smiles`: list[str] |

### Workflow
1. Call all 3 tools with `smiles=[resolved_smiles]`
2. Classification endpoints: Active (1) = toxic signal, Inactive (0) = no signal
3. Regression endpoints (LD50): Report numerical value with context
4. All predictions graded [T3]

### Decision Logic
- **hERG = Active**: Flag prominently (cardiac safety risk)
- **AMES = Active**: Flag prominently (mutagenicity concern)
- **DILI = Active**: Flag prominently (liver toxicity concern)
- **Multiple SMILES**: Can batch up to ~10 SMILES in single call
- **Failed prediction**: Note "prediction unavailable" (don't fail entire report)

---

## Phase 2: ADMET Properties

**When**: SMILES is available

| Tool | Properties Predicted | Parameter |
|------|---------------------|-----------|
| `ADMETAI_predict_BBB_penetrance` | Blood-brain barrier crossing probability | `smiles`: list[str] |
| `ADMETAI_predict_bioavailability` | Oral bioavailability (F20%, F30%) | `smiles`: list[str] |
| `ADMETAI_predict_clearance_distribution` | Clearance, VDss, half-life, PPB | `smiles`: list[str] |
| `ADMETAI_predict_CYP_interactions` | CYP1A2, 2C9, 2C19, 2D6, 3A4 inhibition/substrate | `smiles`: list[str] |
| `ADMETAI_predict_physicochemical_properties` | LogP, LogD, LogS, MW, pKa | `smiles`: list[str] |
| `ADMETAI_predict_solubility_lipophilicity_hydration` | Aqueous solubility, lipophilicity, hydration free energy | `smiles`: list[str] |

### Workflow
1. Call all 6 ADMET tools in parallel
2. Compile into Absorption / Distribution / Metabolism / Excretion sections
3. Assess Lipinski Rule of 5 compliance
4. Flag drug-drug interaction risks from CYP inhibition profiles

### Decision Logic
- **BBB penetrant + toxicity**: Flag as neurotoxicity risk
- **Low bioavailability**: Note absorption concerns
- **CYP3A4 inhibitor**: Flag high DDI risk
- **Lipinski violations**: Report drug-likeness assessment

---

## Phase 3: Toxicogenomics (CTD)

**When**: Compound name is resolved

| Tool | Function | Parameter |
|------|----------|-----------|
| `CTD_get_chemical_gene_interactions` | Genes affected by chemical | `input_terms`: str |
| `CTD_get_chemical_diseases` | Diseases linked to chemical exposure | `input_terms`: str |

### Workflow
1. Call both CTD tools with `input_terms=compound_name`
2. Parse gene interactions: extract gene symbols, interaction types
3. Parse disease associations: extract disease names, evidence types (marker/mechanism/therapeutic)
4. Grade curated as [T2], inferred as [T3]

### Decision Logic
- **Direct vs inferred**: CTD separates curated direct evidence from inferred associations
- **Therapeutic vs toxic**: Disease associations can be therapeutic or adverse
- **Prioritize marker/mechanism**: Stronger causal evidence than simple associations

---

## Phase 4: Regulatory Safety (FDA Labels)

**When**: Compound has an approved drug name

| Tool | Information Retrieved | Parameter |
|------|---------------------|-----------|
| `FDA_get_boxed_warning_info_by_drug_name` | Black box warnings (most serious) | `drug_name`: str |
| `FDA_get_contraindications_by_drug_name` | Absolute contraindications | `drug_name`: str |
| `FDA_get_adverse_reactions_by_drug_name` | Known adverse reactions | `drug_name`: str |
| `FDA_get_warnings_by_drug_name` | Warnings and precautions | `drug_name`: str |
| `FDA_get_nonclinical_toxicology_info_by_drug_name` | Animal toxicology data | `drug_name`: str |
| `FDA_get_carcinogenic_mutagenic_fertility_by_drug_name` | Carcinogenicity/mutagenicity/fertility | `drug_name`: str |

### Workflow
1. Call all 6 FDA tools in parallel
2. Prioritize: Boxed Warnings > Contraindications > Warnings > Adverse Reactions
3. All FDA label data is [T1] evidence
4. **Boxed warning present**: Flag as CRITICAL in executive summary
5. **No FDA data**: Note "Not an FDA-approved drug" and continue

---

## Phase 5: Drug Safety Profile (DrugBank)

**When**: Compound is a known drug

| Tool | Information | Parameters |
|------|------------|------------|
| `drugbank_get_safety_by_drug_name_or_drugbank_id` | Toxicity, contraindications | `query`: str, `case_sensitive`: bool, `exact_match`: bool, `limit`: int |

### Workflow
1. Call with `query=drug_name, case_sensitive=False, exact_match=False, limit=5`
2. Parse toxicity information, overdose data, contraindications
3. Cross-reference with FDA data; if conflict, defer to FDA [T1]

---

## Phase 6: Chemical-Protein Interactions (STITCH)

**When**: Compound can be identified by name or SMILES

| Tool | Function | Parameters |
|------|----------|------------|
| `STITCH_resolve_identifier` | Resolve to STITCH ID | `identifier`: str, `species`: int (9606=human) |
| `STITCH_get_chemical_protein_interactions` | Get interactions | `identifiers`: list[str], `species`: int, `required_score`: int |
| `STITCH_get_interaction_partners` | Get interaction network | `identifiers`: list[str], `species`: int, `limit`: int |

### Workflow
1. Resolve compound: `STITCH_resolve_identifier(identifier=compound_name, species=9606)`
2. Get interactions with `required_score=700`
3. Flag safety-relevant targets: hERG (cardiac), CYP enzymes (metabolism), nuclear receptors (endocrine)

### Confidence Levels
- **>900**: Well-established interaction [T2]
- **700-900**: Probable interaction [T3]
- **400-700**: Possible interaction, needs validation [T4]

---

## Phase 7: Structural Alerts (ChEMBL)

**When**: ChEMBL molecule ID is available

| Tool | Function | Parameters |
|------|----------|------------|
| `ChEMBL_search_compound_structural_alerts` | Find structural alert matches | `molecule_chembl_id`: str, `limit`: int |

### Workflow
1. Call with `molecule_chembl_id=chembl_id, limit=20`
2. Parse alert types: PAINS, Brenk, Glaxo
3. **No ChEMBL ID**: Skip gracefully; note "structural alert analysis not available"
