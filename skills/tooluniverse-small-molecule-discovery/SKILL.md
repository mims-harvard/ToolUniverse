---
name: tooluniverse-small-molecule-discovery
description: >
  Find, characterize, and source small molecules for chemical biology and drug
  discovery. Covers compound identification (PubChem, ChEMBL), structure search,
  binding affinity data, ADMET/drug-likeness prediction, and commercial availability
  (eMolecules, Enamine). Use when asked to find compounds, assess drug-likeness,
  search by structure, retrieve binding affinities, or source chemicals.
---

# Small Molecule Discovery Skill

Systematic small molecule identification, characterization, and sourcing using PubChem, ChEMBL, BindingDB, ADMET-AI, SwissADME, eMolecules, and Enamine. Covers the full pipeline from compound name to structure, activity, ADMET properties, and commercial procurement.

## Domain Reasoning

Drug-likeness is not a binary property. Lipinski's Rule of 5 was derived from orally administered, passively absorbed drugs and has many well-known exceptions: natural products, macrocycles, PROTACs, and many approved drugs violate one or more rules. The relevant question is not "does this pass Ro5?" but "does this compound's physicochemical profile match the requirements of the target, the intended route of administration, and the therapeutic context?" Focus on the specific requirements, not rigid rules.

## LOOK UP DON'T GUESS

- Compound identity (CID, ChEMBL ID, SMILES): call `PubChem_get_CID_by_compound_name` and `ChEMBL_search_molecules`; do not assume IDs from memory.
- ADMET properties: run `SwissADME_calculate_adme` or `ADMETAI_predict_*` on the actual SMILES; do not estimate logP, TPSA, or bioavailability.
- Binding affinities against a target: query `ChEMBL_search_activities` or `BindingDB_get_ligands_by_uniprot`; never cite IC50 values from memory.
- Commercial availability: check `eMolecules_search` or `Enamine_search_catalog`; do not assume availability.

---

**KEY PRINCIPLES**:
1. **Resolve identity first** - Always get CID and ChEMBL ID before research
2. **SMILES required for property prediction** - Extract canonical SMILES from PubChem early
3. **English names in tools** - Use IUPAC or common English names; avoid abbreviations in tool calls
4. **BindingDB is often unavailable** - Fall back to ChEMBL activities when BindingDB times out
5. **eMolecules/Enamine return URLs** - These tools generate search URLs, not direct data; note this to user

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

- "Find information about compound X"
- "What is the drug-likeness of this SMILES?"
- "Show binding affinities for EGFR inhibitors"
- "Search for compounds similar to imatinib"
- "Is this compound commercially available?"
- "What are the ADMET properties of this molecule?"
- "Find ChEMBL activities for target Y"
- "Predict targets for this small molecule"

---

## Key Tools

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `PubChem_get_CID_by_compound_name` | Name to CID lookup | `compound_name` |
| `PubChem_get_CID_by_SMILES` | SMILES to CID lookup | `smiles` |
| `PubChem_get_compound_properties_by_CID` | MW, formula, SMILES, InChIKey | `cid`, `properties` |
| `PubChem_search_compounds_by_similarity` | Find structurally similar compounds | `smiles`, `threshold` (0-100) |
| `PubChem_search_compounds_by_substructure` | Substructure search | `smiles` |
| `PubChem_get_compound_synonyms_by_CID` | All names/synonyms | `cid` |
| `ChEMBL_search_molecules` | Search ChEMBL by name or ID | `query` |
| `ChEMBL_get_molecule` | Full ChEMBL molecule record | `chembl_id` |
| `ChEMBL_search_similar_molecules` | Similarity search in ChEMBL | `query` (SMILES or ChEMBL ID) |
| `ChEMBL_search_activities` | Binding affinities and assay data | `molecule_chembl_id`, `target_chembl_id`, `pchembl_value__gte` |
| `ChEMBL_get_drug_mechanisms` | MOA for approved drugs | `drug_chembl_id` or `drug_name` |
| `ChEMBL_search_targets` | Find targets by name | `query`, `organism` |
| `ChEMBL_get_target_activities` | All ligands for a target | `target_chembl_id` |
| `SwissADME_calculate_adme` | Physicochemical + ADMET properties | `operation="calculate_adme"`, `smiles` |
| `SwissADME_check_druglikeness` | Lipinski, Veber, Egan rules | `operation="check_druglikeness"`, `smiles` |
| `ADMETAI_predict_physicochemical_properties` | MW, logP, TPSA, HBD/HBA | `smiles` (list) |
| `ADMETAI_predict_bioavailability` | Oral bioavailability prediction | `smiles` (list) |
| `ADMETAI_predict_BBB_penetrance` | Blood-brain barrier permeability | `smiles` (list) |
| `ADMETAI_predict_toxicity` | hERG, DILI, mutagenicity | `smiles` (list) |
| `ADMETAI_predict_CYP_interactions` | CYP450 inhibition/substrate | `smiles` (list) |
| `SwissTargetPrediction_predict` | Predict protein targets for compound | `operation="predict"`, `smiles` |
| `eMolecules_search` | Find commercially available compounds | `query` (name or keyword) |
| `eMolecules_search_smiles` | Structure-based commercial search | `smiles` |
| `eMolecules_get_vendors` | Find vendors for a specific compound | `compound_id` |
| `Enamine_search_catalog` | Search Enamine screening library | `query` |
| `Enamine_search_smiles` | Search Enamine by structure | `smiles` |
| `Enamine_get_libraries` | List Enamine compound libraries | (none required) |

---

## Workflow

### Phase 1: Compound Identification

```
# Step 1: Name -> CID (PubChem canonical identity)
PubChem_get_CID_by_compound_name(compound_name="imatinib")
# -> CID: 5291

# Step 2: Get SMILES and properties (needed for all downstream tools)
PubChem_get_compound_properties_by_CID(
    cid="5291",
    properties="MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey,IUPACName"
)
# -> canonical SMILES, InChIKey (global identifier)

# Step 3: Get ChEMBL ID (for activity data)
ChEMBL_search_molecules(query="imatinib")
# -> ChEMBL ID (e.g., "CHEMBL941")

# Step 4: Get all synonyms (brand names, INN, etc.)
PubChem_get_compound_synonyms_by_CID(cid="5291")
```

**ID resolution priority**:
1. Start with PubChem CID (most universal)
2. Get ChEMBL ID (for bioactivity data)
3. Use canonical SMILES for structure-based searches and ADMET

### Phase 2: Structure-Based Search

**Similarity search** (find analogs):
```
PubChem_search_compounds_by_similarity(
    smiles="CANONICAL_SMILES",
    threshold=85   # Tanimoto threshold 0-100; 85 = highly similar
)
# Returns: list of CIDs of similar compounds

ChEMBL_search_similar_molecules(query="CHEMBL941")  # Or SMILES
# Returns: ChEMBL entries sorted by similarity
```

**Substructure search** (find compounds containing a scaffold):
```
PubChem_search_compounds_by_substructure(smiles="SCAFFOLD_SMILES")
# Returns: CIDs of compounds containing the scaffold
```

### Phase 3: Bioactivity and Binding Affinity

**Get all activities for a compound** (across all targets):
```
ChEMBL_search_activities(
    molecule_chembl_id="CHEMBL941",
    pchembl_value__gte=6,   # pIC50/Ki >= 6 = IC50/Ki <= 1 µM
    limit=50
)
# Returns: assay_type, target_name, pchembl_value, units
```

**Get all ligands for a target**:
```
# First find target ChEMBL ID
ChEMBL_search_targets(query="EGFR", organism="Homo sapiens")
# -> target_chembl_id, e.g., "CHEMBL203"

ChEMBL_get_target_activities(
    target_chembl_id="CHEMBL203"
)
# Returns: all compounds with binding data against this target
```

**BindingDB** (when available — often times out):
```
BindingDB_get_ligands_by_uniprot(uniprot_id="P00533")  # EGFR
# Returns: Ki, IC50, Kd data with literature references
# Note: BindingDB REST API is frequently unavailable; fall back to ChEMBL
```

**pChEMBL Value interpretation**:
| pChEMBL | IC50 / Ki | Affinity |
|---------|-----------|---------|
| >= 9 | <= 1 nM | Very potent |
| >= 7 | <= 100 nM | Potent |
| >= 6 | <= 1 µM | Moderate |
| >= 5 | <= 10 µM | Weak |
| < 5 | > 10 µM | Inactive |

### Phase 4: Drug-likeness and ADMET

**SwissADME** (comprehensive, requires SMILES string — not list):
```
SwissADME_calculate_adme(
    operation="calculate_adme",
    smiles="CANONICAL_SMILES"
)
# Returns: physicochemical, lipophilicity, water solubility, pharmacokinetics,
#          drug-likeness scores (Lipinski, Veber, Egan, Muegge), PAINS alerts

SwissADME_check_druglikeness(
    operation="check_druglikeness",
    smiles="CANONICAL_SMILES"
)
# Returns: Lipinski/Veber/Egan pass/fail + lead-likeness
```

**ADMET-AI** (ML-based, requires SMILES as list — install tooluniverse[ml]):
```
ADMETAI_predict_physicochemical_properties(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_bioavailability(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_BBB_penetrance(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_toxicity(smiles=["CANONICAL_SMILES"])
ADMETAI_predict_CYP_interactions(smiles=["CANONICAL_SMILES"])
```

**Note**: ADMET-AI requires `pip install tooluniverse[ml]`. If unavailable, use SwissADME as fallback.

**Key drug-likeness rules**:
- **Lipinski Ro5**: MW <= 500, logP <= 5, HBD <= 5, HBA <= 10 (oral drugs)
- **Veber**: TPSA <= 140 Å², rotatable bonds <= 10 (oral bioavailability)
- **Lead-like**: MW <= 350, logP <= 3, HBD <= 3, HBA <= 6 (fragment/lead)

### Phase 5: Target Prediction

When you have a novel compound and want to predict targets:
```
SwissTargetPrediction_predict(
    operation="predict",
    smiles="CANONICAL_SMILES"
)
# Returns: predicted protein targets with probability scores
# Note: SwissTargetPrediction uses structure-similarity to known drug-target pairs
# May time out for complex molecules
```

### Phase 6: Commercial Availability

**eMolecules** (aggregates 200+ suppliers — returns search URL, not direct data):
```
eMolecules_search(query="compound_name")
# -> Returns search_url to visit on eMolecules.com

eMolecules_search_smiles(smiles="CANONICAL_SMILES")
# -> Returns URL for exact/similar structure search
```

**Enamine** (37B+ make-on-demand compounds — returns URL when API unavailable):
```
Enamine_search_catalog(query="compound_name")
# -> If API available: returns catalog entries with catalog_id, price
# -> If API unavailable: returns search_url for manual search

Enamine_search_smiles(smiles="CANONICAL_SMILES")
# -> Exact or similarity structure search

Enamine_get_libraries()
# -> Lists available Enamine screening collections
```

**Note**: eMolecules and Enamine APIs frequently return search URLs rather than live data. Present these to the user as "search here" links.

---

## Tool Parameter Reference

| Tool | Required Params | Notes |
|------|----------------|-------|
| `PubChem_get_CID_by_compound_name` | `compound_name` | Returns list of CIDs; take first or most relevant |
| `PubChem_get_CID_by_SMILES` | `smiles` | Use canonical SMILES |
| `PubChem_get_compound_properties_by_CID` | `cid`, `properties` | `cid` as string; `properties` comma-separated |
| `PubChem_search_compounds_by_similarity` | `smiles` | `threshold` (int 0-100, default 90) |
| `PubChem_search_compounds_by_substructure` | `smiles` | Returns CIDs matching scaffold |
| `ChEMBL_search_molecules` | `query` | Name, ChEMBL ID, or InChIKey |
| `ChEMBL_get_molecule` | `chembl_id` | Full format: "CHEMBL941" not "941" |
| `ChEMBL_search_similar_molecules` | `query` | SMILES or ChEMBL ID |
| `ChEMBL_search_activities` | `molecule_chembl_id` OR `target_chembl_id` | Use `pchembl_value__gte=6` to filter potent |
| `ChEMBL_get_drug_mechanisms` | `drug_chembl_id` or `drug_name` | For approved drugs only |
| `ChEMBL_search_targets` | `query` | Add `organism="Homo sapiens"` to filter human |
| `ChEMBL_get_target_activities` | `target_chembl_id` | Returns all ligands for target |
| `SwissADME_calculate_adme` | `operation="calculate_adme"`, `smiles` | SMILES as string (not list) |
| `SwissADME_check_druglikeness` | `operation="check_druglikeness"`, `smiles` | SMILES as string |
| `ADMETAI_predict_*` | `smiles` | Must be a **list**: `["SMILES"]` not `"SMILES"` |
| `SwissTargetPrediction_predict` | `operation="predict"`, `smiles` | May time out |
| `eMolecules_search` | `query` | Returns search URL (no live data) |
| `eMolecules_search_smiles` | `smiles` | Canonical SMILES |
| `eMolecules_get_vendors` | `compound_id` | eMolecules internal ID |
| `Enamine_search_catalog` | `query` | Returns URL when API unavailable |
| `Enamine_search_smiles` | `smiles` | `search_type`: "exact", "similarity", "substructure" |
| `Enamine_get_compound` | `enamine_id` | Enamine-specific catalog ID |
| `BindingDB_get_ligands_by_uniprot` | `uniprot_id` | Frequently unavailable — use ChEMBL as fallback |
| `BindingDB_get_targets_by_compound` | `smiles` | SMILES-based target lookup |

---

## Common Patterns

### Pattern 1: Full Compound Profile
```
Input: Compound name (e.g., "imatinib")
Flow:
  1. PubChem_get_CID_by_compound_name -> CID + SMILES
  2. ChEMBL_search_molecules -> ChEMBL ID
  3. PubChem_get_compound_properties_by_CID -> physicochemical props
  4. SwissADME_calculate_adme / ADMETAI_predict_* -> ADMET profile
  5. ChEMBL_search_activities(molecule_chembl_id) -> binding data
  6. ChEMBL_get_drug_mechanisms -> MOA (if approved drug)
Output: Complete compound profile with identity, ADMET, and activity data
```

### Pattern 2: Analog Discovery
```
Input: Reference compound SMILES
Flow:
  1. PubChem_search_compounds_by_similarity(smiles, threshold=85) -> similar CIDs
  2. ChEMBL_search_similar_molecules(query=smiles) -> ChEMBL analogs
  3. For each hit: PubChem_get_compound_properties_by_CID -> properties
  4. SwissADME_check_druglikeness -> filter by drug-likeness
Output: Ranked list of analogs with activity data and drug-likeness scores
```

### Pattern 3: Target-Based Compound Search
```
Input: Target name (e.g., "EGFR")
Flow:
  1. ChEMBL_search_targets(query="EGFR", organism="Homo sapiens") -> target_chembl_id
  2. ChEMBL_get_target_activities(target_chembl_id) -> all ligands with Ki/IC50
  3. Filter by pchembl_value >= 7 (potent compounds)
  4. For top hits: SwissADME_check_druglikeness -> assess drug-likeness
  5. eMolecules_search(query=compound_name) -> check commercial availability
Output: Prioritized list of potent, drug-like, commercially available compounds
```

### Pattern 4: ADMET Risk Assessment
```
Input: Novel compound SMILES
Flow:
  1. SwissADME_calculate_adme(operation="calculate_adme", smiles) -> full ADMET
  2. ADMETAI_predict_toxicity(smiles=[smiles]) -> hERG, DILI, mutagenicity
  3. ADMETAI_predict_CYP_interactions(smiles=[smiles]) -> drug-drug interaction risk
  4. ADMETAI_predict_BBB_penetrance(smiles=[smiles]) -> CNS penetration
Output: ADMET risk profile with flagged liabilities
```

---

## Fallback Chains

| Primary | Fallback | When |
|---------|----------|------|
| `BindingDB_get_ligands_by_uniprot` | `ChEMBL_get_target_activities` | BindingDB API unavailable |
| `ADMETAI_predict_*` | `SwissADME_calculate_adme` | ml dependencies not installed |
| `Enamine_search_catalog` | Returns URL only | API returns HTTP 500 (common) |
| `SwissTargetPrediction_predict` | `ChEMBL_search_similar_molecules` + known targets | Prediction times out |
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_molecules(query=name)` | Name not in PubChem |

---

## Limitations

- **BindingDB**: REST API frequently times out; ChEMBL is the reliable alternative for binding data
- **Enamine API**: Returns HTTP 500 often; tool provides search URL as fallback
- **eMolecules**: No public API; tool generates search URLs only
- **ADMET-AI**: Requires `pip install tooluniverse[ml]`; not always available in base install
- **SwissTargetPrediction**: Web scraping-based; may time out for complex molecules
- **SMILES format**: ADMET-AI requires a **list** `["SMILES"]`; SwissADME requires a **string** `"SMILES"`
- **ChEMBL IDs**: Always use full format `"CHEMBL941"`, never just `"941"`
