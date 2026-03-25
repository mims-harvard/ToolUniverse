# Drug Research Examples

Detailed workflow examples demonstrating the drug research skill.

---

## Example 1: Approved Drug Profile (Metformin)

### User Query
"Tell me about metformin"

### Step 1: Create Report File

Create `metformin_drug_report.md` with all section headers and `[Researching...]` placeholders.

### Step 2: Compound Disambiguation

```python
# Resolve identifiers
cid_result = tu.tools.PubChem_get_CID_by_compound_name(compound_name="metformin")
# → CID: 4091

chembl_result = tu.tools.ChEMBL_search_compounds(query="metformin", limit=1)
# → CHEMBL1431

dailymed_result = tu.tools.DailyMed_search_spls(drug_name="metformin")
# → Set ID: multiple entries (branded/generic)

pharmgkb_result = tu.tools.PharmGKB_search_drugs(query="metformin")
# → PA450657
```

**Update Section 1** with:
```markdown
## 1. Compound Identity

### 1.1 Database Identifiers
| Identifier | Value | Link |
|------------|-------|------|
| **PubChem CID** | 4091 | [Link](https://pubchem.ncbi.nlm.nih.gov/compound/4091) |
| **ChEMBL ID** | CHEMBL1431 | [Link](https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1431/) |
| **RxNorm CUI** | 6809 | RxNorm |
| **PharmGKB ID** | PA450657 | [Link](https://www.pharmgkb.org/chemical/PA450657) |
| **DailyMed** | Multiple | FDA approved |

*Source: `PubChem_get_CID_by_compound_name`, `ChEMBL_search_drugs`, `PharmGKB_search_drugs`*
```

### Step 3: Chemical Properties

```python
# PubChem properties
props = tu.tools.PubChem_get_compound_properties_by_CID(cid=4091)
# → MW: 129.16, Formula: C4H11N5, XLogP: -2.6

# ADMET-AI predictions
smiles = "CN(C)C(=N)NC(=N)N"
physchem = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=[smiles])
# → logP, TPSA, HBD, HBA, Lipinski, QED

solubility = tu.tools.ADMETAI_predict_solubility_lipophilicity_hydration(smiles=[smiles])
# → Solubility prediction
```

**Update Section 2** with detailed tables and interpretations.

### Step 4: Mechanism & Targets

```python
# ChEMBL bioactivity
bioactivity = tu.tools.ChEMBL_get_bioactivity_by_chemblid(chembl_id="CHEMBL1431")
# → Activity data

targets = tu.tools.ChEMBL_get_target_by_chemblid(chembl_id="CHEMBL1431")
# → Target list with UniProt

# DGIdb drug-gene interactions
dgidb = tu.tools.DGIdb_get_drug_info(drugs=["metformin"])
# → Gene interactions
```

**Update Section 3** with target table, mechanism description, bioactivity summary.

### Step 5: ADMET Properties

```python
# Run all ADMET predictions
absorption = tu.tools.ADMETAI_predict_bioavailability(smiles=[smiles])
bbb = tu.tools.ADMETAI_predict_BBB_penetrance(smiles=[smiles])
cyp = tu.tools.ADMETAI_predict_CYP_interactions(smiles=[smiles])
clearance = tu.tools.ADMETAI_predict_clearance_distribution(smiles=[smiles])
toxicity = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
```

**Update Section 4** with ADMET tables:

```markdown
### 4.1 Absorption
| Endpoint | Prediction | Interpretation |
|----------|------------|----------------|
| **Oral Bioavailability** | 0.68 | Moderate-Good |
| **HIA** | 0.92 | High absorption |
| **Caco-2** | -5.1 log cm/s | Moderate permeability |
| **P-gp Substrate** | 0.15 | Not a P-gp substrate |

*Source: ADMET-AI via `ADMETAI_predict_bioavailability`*

### 4.3 Metabolism
| CYP Enzyme | Inhibitor | Substrate |
|------------|-----------|-----------|
| CYP1A2 | 0.08 (No) | N/A |
| CYP2C9 | 0.05 (No) | 0.12 (No) |
| CYP2C19 | 0.07 (No) | N/A |
| CYP2D6 | 0.04 (No) | 0.08 (No) |
| CYP3A4 | 0.06 (No) | 0.15 (No) |

**Summary**: Metformin is not significantly metabolized by CYP enzymes. Eliminated unchanged renally.

*Source: ADMET-AI via `ADMETAI_predict_CYP_interactions`*
```

### Step 6: Clinical Trials

```python
# Search trials
trials = tu.tools.search_clinical_trials(intervention="metformin", pageSize=100)
# → Total: 500+ trials

# Get trial details for top results
nct_ids = [t['NCT ID'] for t in trials['studies'][:10]]
details = tu.tools.get_clinical_trial_conditions_and_interventions(nct_ids=nct_ids)

# Extract outcomes from completed Phase 3
outcomes = tu.tools.extract_clinical_trial_outcomes(
    nct_ids=["NCT00123456", "NCT00234567"],
    outcome_measure="primary"
)
```

**Update Section 5** with trial landscape table, approved indications, key efficacy data.

### Step 7: Safety Profile

```python
# FAERS data
faers_reactions = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="METFORMIN"
)
# → Top adverse reactions

faers_serious = tu.tools.FAERS_count_seriousness_by_drug_event(
    medicinalproduct="METFORMIN"
)
# → Serious vs non-serious

faers_outcomes = tu.tools.FAERS_count_outcomes_by_drug_event(
    medicinalproduct="METFORMIN"
)
# → Outcome distribution

faers_deaths = tu.tools.FAERS_count_death_related_by_drug(
    medicinalproduct="METFORMIN"
)
# → Fatal outcomes
```

**Update Section 6** with:

```markdown
### 6.2 Post-Marketing Safety (FAERS)

**Total Reports**: 45,234 (as of 2026-02-04)

#### Top Adverse Reactions
| Reaction (MedDRA PT) | Count | % of Reports | Expected? |
|----------------------|-------|--------------|-----------|
| Diarrhoea | 8,234 | 18.2% | Yes (known GI effect) |
| Nausea | 6,892 | 15.2% | Yes (known GI effect) |
| Lactic acidosis | 3,456 | 7.6% | Yes (boxed warning) |
| Vomiting | 2,987 | 6.6% | Yes (known GI effect) |
| Hypoglycaemia | 2,543 | 5.6% | Yes (class effect) |

*Source: FDA FAERS via `FAERS_count_reactions_by_drug_event`*

#### Severity Distribution
| Classification | Count | Percentage |
|----------------|-------|------------|
| Serious | 18,456 | 40.8% |
| Non-serious | 26,778 | 59.2% |

*Source: `FAERS_count_seriousness_by_drug_event`*

### 6.3 Black Box Warnings

**Lactic Acidosis Warning**: Metformin can cause lactic acidosis, a rare but serious 
metabolic complication. Risk increases with renal impairment, hepatic impairment, 
age ≥65, radiologic studies with contrast, surgery, excessive alcohol intake, and 
hypoxic states.

*Source: FDA Label via `PubChem_get_drug_label_info_by_CID`*
```

### Step 8: Pharmacogenomics

```python
# PharmGKB data
pgkb_drug = tu.tools.PharmGKB_search_drugs(query="metformin")
pgkb_details = tu.tools.PharmGKB_get_drug_details(drug_id="PA450657")

# Clinical annotations for related genes
annotations = tu.tools.PharmGKB_get_clinical_annotations(gene_id="PA35858")  # SLC22A1

# Dosing guidelines
guidelines = tu.tools.PharmGKB_get_dosing_guidelines(gene="SLC22A1")
```

**Update Section 7** with pharmacogene table, clinical annotations, guideline status.

### Step 9: Literature

```python
# PubMed search
lit_total = tu.tools.PubMed_search_articles(
    query='"metformin"',
    limit=1
)
# → Total count

lit_recent = tu.tools.PubMed_search_articles(
    query='"metformin" AND ("2024"[Date - Publication] OR "2025"[Date - Publication])',
    limit=20
)
# → Recent papers

lit_drug = tu.tools.PubMed_search_articles(
    query='"metformin" AND (drug OR therapy OR treatment)',
    limit=20
)
# → Drug-focused papers
```

**Update Section 9** with publication metrics and research trends.

### Step 10: Synthesize Conclusions

**Update Section 10** with scorecard:

```markdown
### 10.1 Drug Profile Scorecard

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| **Efficacy Evidence** | 5/5 | Decades of clinical use, multiple Phase 3 trials, proven HbA1c reduction |
| **Safety Profile** | 4/5 | Generally well-tolerated; lactic acidosis is rare but serious (boxed warning) |
| **PK/ADMET** | 4/5 | Good oral bioavailability; renal elimination (caution in CKD) |
| **Target Validation** | 4/5 | AMPK activation well-established; some mechanism debate remains |
| **Competitive Position** | 3/5 | First-line for T2DM but many alternatives (SGLT2i, GLP-1) |
| **Overall** | **4.0/5** | **Strong, established drug profile** |

### 10.2 Key Strengths
1. **Proven efficacy**: 60+ years of clinical use with robust trial data
2. **Favorable safety**: Low hypoglycemia risk, potential cardiovascular benefits
3. **Cost-effective**: Generic availability, low cost
4. **Additional benefits**: Weight neutral/loss, potential anti-cancer properties under investigation

### 10.3 Key Concerns/Limitations
1. **Lactic acidosis risk**: Requires monitoring, contraindicated in renal impairment
2. **GI tolerability**: ~25% of patients experience GI side effects
3. **B12 deficiency**: Long-term use associated with vitamin B12 malabsorption
4. **Renal clearance**: Dose adjustment required for eGFR <45

### 10.4 Research Gaps
1. **Cancer prevention**: Clinical trials ongoing but definitive evidence lacking
2. **Aging/longevity**: TAME trial results pending
```

### Step 11: Update Data Sources

**Update Section 11** with all tools used and their parameters.

### Final Step: Write Executive Summary

```markdown
## Executive Summary

**Metformin** (PubChem CID: 4091, ChEMBL: CHEMBL1431) is a biguanide antidiabetic 
agent and the first-line pharmacological treatment for type 2 diabetes mellitus. 
It works primarily through AMPK activation, reducing hepatic glucose production 
and improving insulin sensitivity.

The drug has an extensive clinical evidence base spanning 60+ years with 500+ 
registered clinical trials. Key efficacy data shows HbA1c reductions of 1.0-1.5% 
as monotherapy [★★★]. The safety profile is generally favorable, though a boxed 
warning exists for lactic acidosis risk in patients with renal impairment. FAERS 
data (45,234 reports) shows GI effects as the most common adverse reactions, 
consistent with labeling.

Pharmacogenomic data from PharmGKB identifies SLC22A1 (OCT1) as the key 
transporter affecting metformin response, though no CPIC dosing guideline 
currently exists. The drug shows excellent ADMET properties with good 
oral bioavailability and minimal CYP-mediated metabolism.

**Bottom Line**: Metformin remains a well-validated, cost-effective first-line 
therapy for T2DM with a favorable benefit-risk profile when renal function is 
monitored. Active research continues into potential benefits in cancer prevention 
and longevity.
```

---

## Example 2: Investigational Compound (ChEMBL ID)

### User Query
"What do we know about compound CHEMBL4303291?"

### Approach Differences

1. **More emphasis on preclinical data** - Chemistry, targets, ADMET predictions
2. **Clinical section may be sparse** - No or few trials
3. **No FAERS data** - Not yet marketed
4. **No PGx data** - Not yet characterized
5. **Label section**: "Not approved - investigational compound"

### Key Tool Adjustments

```python
# Start with ChEMBL ID directly
compound = tu.tools.ChEMBL_get_compound_by_chemblid(chembl_id="CHEMBL4303291")
smiles = compound['molecule_structures']['canonical_smiles']

# Get PubChem CID from SMILES
cid_result = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)

# Heavy emphasis on ADMET predictions (no clinical data)
# All 8 ADMET-AI tools...

# Search for any trials
trials = tu.tools.search_clinical_trials(intervention="CHEMBL4303291")
# → Likely 0 results

# Literature may be primary data source
lit = tu.tools.PubMed_search_articles(query='"CHEMBL4303291"', limit=20)
```

### Report Differences

- **Section 5 (Clinical)**: "No clinical trials registered as of [date]. Compound is in preclinical development."
- **Section 6 (Safety)**: "No post-marketing safety data (not approved). Preclinical toxicity data: [from ChEMBL/literature]"
- **Section 7 (PGx)**: "No pharmacogenomic data available (investigational compound)"
- **Section 8 (Regulatory)**: "Not approved. Development stage: Preclinical"
- **Scorecard**: Adjust criteria for investigational compound assessment

---

## Example 3: Safety-Focused Review

### User Query
"What are the safety concerns with fluoroquinolone antibiotics like ciprofloxacin?"

### Approach Differences

1. **Deep FAERS analysis** - Multiple queries, stratified analysis
2. **Black box warnings emphasis** - Known serious effects
3. **Drug interactions detailed** - QT prolongation, etc.
4. **PGx for safety** - Variants affecting toxicity
5. **Literature focused on safety** - Adverse event publications

### Key Tool Sequence

```python
# Full FAERS analysis
reactions = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="CIPROFLOXACIN"
)

# Filter for serious reactions
serious_cardiac = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="CIPROFLOXACIN",
    serious="Yes",
    reactionmeddraverse="cardiac"  # Will need specific MedDRA terms
)

# Age stratification
age_dist = tu.tools.FAERS_count_patient_age_distribution(
    medicinalproduct="CIPROFLOXACIN"
)

# Death-related
deaths = tu.tools.FAERS_count_death_related_by_drug(
    medicinalproduct="CIPROFLOXACIN"
)

# Label for black box warnings
label = tu.tools.PubChem_get_drug_label_info_by_CID(cid=2764)  # Ciprofloxacin CID

# Literature on safety
safety_lit = tu.tools.PubMed_search_articles(
    query='"ciprofloxacin" AND (safety OR "adverse event" OR toxicity OR "side effect")',
    limit=50
)
```

### Report Emphasis

- **Section 6 expanded** with multiple subsections for:
  - Tendon rupture/tendinitis
  - QT prolongation
  - CNS effects
  - Peripheral neuropathy
  - Aortic dissection/aneurysm
- **Safety scorecard** instead of general scorecard
- **Risk mitigation strategies** section added

---

## Example 4: ADMET Assessment (SMILES Input)

### User Query
"Evaluate this compound's drug-likeness: CC(=O)Nc1ccc(O)cc1"

### Approach

1. **Identify the compound first**
2. **Heavy chemistry/ADMET focus**
3. **Minimal clinical sections** (unless identified as known drug)

### Workflow

```python
smiles = "CC(=O)Nc1ccc(O)cc1"  # Paracetamol/Acetaminophen

# Try to identify
cid = tu.tools.PubChem_get_CID_by_SMILES(smiles=smiles)
# → CID: 1983 (Acetaminophen)

# If identified, proceed with full profile
# If not identified, focus on predictions only

# Full ADMET battery
physchem = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=[smiles])
bioavail = tu.tools.ADMETAI_predict_bioavailability(smiles=[smiles])
bbb = tu.tools.ADMETAI_predict_BBB_penetrance(smiles=[smiles])
cyp = tu.tools.ADMETAI_predict_CYP_interactions(smiles=[smiles])
clearance = tu.tools.ADMETAI_predict_clearance_distribution(smiles=[smiles])
toxicity = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
nuclear = tu.tools.ADMETAI_predict_nuclear_receptor_activity(smiles=[smiles])
stress = tu.tools.ADMETAI_predict_stress_response(smiles=[smiles])
```

### Report Focus

- **Sections 2 and 4 are primary** - Detailed ADMET analysis
- **Drug-likeness verdict prominent** - Lead-like, drug-like, or beyond Rule of 5
- **Structure-activity insights** if related compounds found
- **Other sections**: Brief if compound identified; "N/A - SMILES query" if unknown

---

## Example 5: Clinical Development Landscape

### User Query
"What trials are ongoing for KRAS inhibitors?"

### Approach

1. **ClinicalTrials.gov focused**
2. **Multiple drugs in class** - Not single compound
3. **Competitive landscape emphasis**
4. **Pipeline analysis**

### Workflow

```python
# Search for KRAS inhibitors
kras_trials = tu.tools.search_clinical_trials(
    condition="cancer",
    intervention="KRAS",
    pageSize=100
)

# Specific drugs
sotorasib_trials = tu.tools.search_clinical_trials(intervention="sotorasib")
adagrasib_trials = tu.tools.search_clinical_trials(intervention="adagrasib")

# Get trial details
nct_ids = [t['NCT ID'] for t in kras_trials['studies'][:20]]
conditions = tu.tools.get_clinical_trial_conditions_and_interventions(nct_ids=nct_ids)
status = tu.tools.get_clinical_trial_status_and_dates(nct_ids=nct_ids)

# Outcomes from completed trials
completed = [nct for nct in nct_ids if "Completed" in status[nct]]
outcomes = tu.tools.extract_clinical_trial_outcomes(nct_ids=completed)
```

### Report Differences

- **Class-level analysis** rather than single drug
- **Competitive landscape table** - All KRAS inhibitors in development
- **Indication mapping** - Which cancers, which mutations
- **Pipeline by phase chart**
- **Less emphasis on individual ADMET/chemistry** (covered per drug if needed)

---

## Summary: Adjusting by Use Case

| Use Case | Primary Sections | Light Sections |
|----------|------------------|----------------|
| Approved Drug Profile | All 11 sections | None |
| Investigational Compound | 1, 2, 3, 4, 9 | 5, 6, 7, 8 |
| Safety Review | 1, 5, 6, 7, 9 | 2, 3, 4, 8 |
| ADMET Assessment | 1, 2, 4 | 3, 5, 6, 7, 8, 9 |
| Clinical Landscape | 1, 5, 9 | 2, 3, 4, 6, 7, 8 |

Always maintain all section headers but adjust depth based on query focus and data availability.
