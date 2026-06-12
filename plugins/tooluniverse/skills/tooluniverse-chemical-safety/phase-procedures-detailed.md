# Chemical Safety: Detailed Phase Procedures

Referenced from SKILL.md. Contains detailed tool parameters, output templates, decision logic, and fallback strategies.

---

## Phase 0: Compound Disambiguation (ALWAYS FIRST)

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
4. **Extract SMILES**: Get from PubChem properties (`ConnectivitySMILES`, `CanonicalSMILES`, or `IsomericSMILES`)
5. **Store resolved IDs**: Maintain dict with `name`, `smiles`, `cid`, `formula`, `weight`, `inchi`

### Output Table

```markdown
## Compound Identity
| Property | Value |
|----------|-------|
| **Name** | Acetaminophen |
| **PubChem CID** | 1983 |
| **SMILES** | CC(=O)Nc1ccc(O)cc1 |
| **Formula** | C8H9NO2 |
| **Molecular Weight** | 151.16 |
```

---

## Phase 1: Predictive Toxicology (ADMET-AI)

**When**: SMILES is available

### Tools (all take `smiles`: list[str])

| Tool | Predicted Endpoints |
|------|---------------------|
| `ADMETAI_predict_toxicity` | AMES, Carcinogens_Lagunin, ClinTox, DILI, LD50_Zhu, Skin_Reaction, hERG |
| `ADMETAI_predict_stress_response` | Stress response pathways (ARE, ATAD5, HSE, MMP, p53) |
| `ADMETAI_predict_nuclear_receptor_activity` | AhR, AR, ER, PPARg, Aromatase |

### Decision Logic

- **Multiple SMILES**: Can batch up to ~10 SMILES in single call
- **Failed prediction**: Note "prediction unavailable" (don't fail entire report)
- **Confidence**: All AI predictions are [T3], not definitive
- **Critical flags**: hERG Active = cardiac risk, AMES Active = mutagenicity, DILI Active = liver toxicity

### Output Table

```markdown
### Toxicity Predictions [T3]
| Endpoint | Prediction | Interpretation | Concern Level |
|----------|-----------|---------------|---------------|
| AMES Mutagenicity | Inactive | No mutagenic signal | Low |
| DILI | Active | Drug-induced liver injury risk | HIGH |
| hERG Inhibition | Active | Cardiac arrhythmia risk | HIGH |
*All predictions from ADMET-AI. Evidence tier: [T3]*
```

---

## Phase 2: ADMET Properties

**When**: SMILES is available

### Tools (all take `smiles`: list[str])

| Tool | Properties |
|------|-----------|
| `ADMETAI_predict_BBB_penetrance` | Blood-brain barrier crossing |
| `ADMETAI_predict_bioavailability` | Oral bioavailability (F20%, F30%) |
| `ADMETAI_predict_clearance_distribution` | Clearance, VDss, half-life, PPB |
| `ADMETAI_predict_CYP_interactions` | CYP1A2, 2C9, 2C19, 2D6, 3A4 inhibition/substrate |
| `ADMETAI_predict_physicochemical_properties` | LogP, LogD, LogS, MW, pKa |
| `ADMETAI_predict_solubility_lipophilicity_hydration` | Aqueous solubility, lipophilicity, hydration free energy |

### Decision Logic

- **BBB penetrant + toxicity**: Flag as neurotoxicity risk
- **Low bioavailability**: F20% = Low -> absorption concerns
- **CYP inhibitor**: CYP3A4 inhibitor = Yes -> high DDI risk
- **Lipinski violations**: Count and report drug-likeness assessment

### Output Format

```markdown
### ADMET Profile [T3]
#### Absorption
| Property | Value | Interpretation |
|----------|-------|----------------|
| BBB Penetrance | Yes | Crosses blood-brain barrier |
| Bioavailability (F20%) | 85% | Good oral absorption |

#### Metabolism
| CYP Enzyme | Substrate | Inhibitor |
|------------|-----------|-----------|
| CYP3A4 | Yes | Yes (DDI risk) |
```

---

## Phase 3: Toxicogenomics (CTD)

**When**: Compound name is resolved

### Tools

| Tool | Parameter | Notes |
|------|-----------|-------|
| `CTD_get_chemical_gene_interactions` | `input_terms`: str | Chemical name, MeSH name, CAS RN, or MeSH ID |
| `CTD_get_chemical_diseases` | `input_terms`: str | Same |

### Decision Logic

- **Direct evidence vs inferred**: CTD separates curated (grade [T2]) from inferred ([T3])
- **Therapeutic vs toxic**: Disease associations can be therapeutic or adverse
- **Prioritize marker/mechanism**: Stronger causal evidence than simple associations

---

## Phase 4: Regulatory Safety (FDA Labels)

**When**: Compound has an approved drug name

### Tools (all take `drug_name`: str)

| Tool | Information |
|------|------------|
| `FDA_get_boxed_warning_info_by_drug_name` | Black box warnings (most serious) |
| `FDA_get_contraindications_by_drug_name` | Absolute contraindications |
| `FDA_get_adverse_reactions_by_drug_name` | Known adverse reactions |
| `FDA_get_warnings_by_drug_name` | Warnings and precautions |
| `FDA_get_nonclinical_toxicology_info_by_drug_name` | Animal toxicology data |
| `FDA_get_carcinogenic_mutagenic_fertility_by_drug_name` | Carcinogenicity/mutagenicity/fertility |

### Decision Logic

- **Boxed warning present**: Flag as CRITICAL in executive summary
- **No FDA data**: Note "Not an FDA-approved drug" and continue
- **All FDA findings**: Grade as [T1]; nonclinical toxicology as [T2]

---

## Phase 5: Drug Safety Profile (DrugBank)

**When**: Compound is a known drug

### Tool

`drugbank_get_safety_by_drug_name_or_drugbank_id(query=drug_name, case_sensitive=False, exact_match=False, limit=5)`

All 4 parameters required. Cross-reference with FDA data; defer to FDA [T1] on conflicts.

---

## Phase 6: Chemical-Protein Interactions (STITCH)

### Tools

| Tool | Parameters |
|------|-----------|
| `STITCH_resolve_identifier` | `identifier`: str, `species`: int (9606=human) |
| `STITCH_get_chemical_protein_interactions` | `identifiers`: list[str], `species`: int, `required_score`: int |
| `STITCH_get_interaction_partners` | `identifiers`: list[str], `species`: int, `limit`: int |

### Confidence Scoring

- **>900**: Well-established [T2]
- **700-900**: Probable [T3]
- **400-700**: Possible, needs validation [T4]
- Flag safety-relevant targets: hERG (cardiac), CYP enzymes (metabolism), nuclear receptors (endocrine)

---

## Phase 7: Structural Alerts (ChEMBL)

**When**: ChEMBL molecule ID is available

### Tool

`ChEMBL_search_compound_structural_alerts(molecule_chembl_id=chembl_id, limit=20)`

Alert types: PAINS (pan-assay interference), Brenk (medicinal chemistry), Glaxo (GSK). No ChEMBL ID -> skip gracefully.

---

## Fallback Strategies

### Compound Resolution
- **Primary**: PubChem by name -> CID -> properties -> SMILES
- **Fallback 1**: ChEMBL search by name -> molecule -> SMILES
- **Fallback 2**: If SMILES provided directly, skip name resolution

### Toxicity Prediction
- **Primary**: All 9 ADMET-AI endpoints
- **Fallback**: If fails, note "prediction failed" and continue with database evidence

### Regulatory Data
- **Primary**: FDA labels by drug name
- **Fallback**: Try alternative names (brand vs generic)

### CTD Data
- **Primary**: Search by common chemical name
- **Fallback**: Try MeSH name

---

## Tool Parameter Quick Reference

| Tool | Parameter Name | Type | Notes |
|------|---------------|------|-------|
| All ADMETAI tools | `smiles` | `list[str]` | Always a list, even for single compound |
| All CTD tools | `input_terms` | `str` | Chemical name, MeSH name, CAS RN, or MeSH ID |
| All FDA tools | `drug_name` | `str` | Brand or generic drug name |
| drugbank_get_safety_* | `query`, `case_sensitive`, `exact_match`, `limit` | str, bool, bool, int | All 4 required |
| STITCH_resolve_identifier | `identifier`, `species` | str, int | species=9606 for human |
| STITCH_get_chemical_protein_interactions | `identifiers`, `species`, `required_score` | list[str], int, int | required_score=400 default |
| PubChem_get_CID_by_compound_name | `name` | `str` | Compound name (not SMILES) |
| PubChem_get_compound_properties_by_CID | `cid` | `int` | Numeric CID |
| ChEMBL_search_compound_structural_alerts | `molecule_chembl_id` | `str` | e.g., "CHEMBL112" |

### Response Format Notes

- **ADMET-AI**: `{status: "success", data: {...}}`
- **CTD**: List of interaction/association objects
- **FDA**: `{status, data}` with label text
- **DrugBank**: `{data: [...]}` with drug records
- **STITCH**: List of interaction objects with scores
- **PubChem CID lookup**: `{IdentifierList: {CID: [...]}}`
- **PubChem properties**: Dict with `CID`, `MolecularWeight`, `ConnectivitySMILES`, `IUPACName`
