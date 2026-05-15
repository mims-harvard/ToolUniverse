# Drug Research Tools Reference

Complete reference for 50+ tools used in drug research, organized by use case.

---

## Quick Reference: Tools by Use Case

| Use Case | Primary Tool | Fallback |
|----------|--------------|----------|
| Name → CID | `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` |
| SMILES → CID | `PubChem_get_CID_by_SMILES` | - |
| Properties | `PubChem_get_compound_properties_by_CID` | ADMET-AI |
| 2D Image | `PubChem_get_compound_2D_image_by_CID` | - |
| Drug-likeness | `ADMETAI_predict_physicochemical_properties` | PubChem properties |
| Targets | `ChEMBL_get_target` | `DGIdb_get_drug_info` |
| Bioactivity | `ChEMBL_get_activity` | `PubChem_get_bioactivity_summary_by_CID` |
| Absorption | `ADMETAI_predict_bioavailability` | Literature |
| BBB | `ADMETAI_predict_BBB_penetrance` | Literature |
| CYP | `ADMETAI_predict_CYP_interactions` | PharmGKB |
| Toxicity | `ADMETAI_predict_toxicity` | FAERS |
| Trials | `search_clinical_trials` | - |
| Trial outcomes | `extract_clinical_trial_outcomes` | - |
| Trial AEs | `extract_clinical_trial_adverse_events` | - |
| FAERS counts | `FAERS_count_reactions_by_drug_event` | - |
| **🆕 FAERS stats** | **`FAERS_calculate_disproportionality`** | **ROR/PRR/IC** |
| **🆕 FAERS stratify** | **`FAERS_stratify_by_demographics`** | **Age/sex/country** |
| **🆕 FAERS serious** | **`FAERS_filter_serious_events`** | **Deaths/hospitalizations** |
| **🆕 Label parsing** | **`DailyMed_parse_adverse_reactions`** | **Structured AE tables** |
| **🆕 Label dosing** | **`DailyMed_parse_dosing`** | **Dose tables** |
| **🆕 Label DDI** | **`DailyMed_parse_drug_interactions`** | **Interaction tables** |
| **🆕 FDA approvals** | **`FDA_OrangeBook_get_approval_history`** | **Timeline** |
| **🆕 FDA patents** | **`FDA_OrangeBook_get_patent_info`** | **Patent guidance** |
| **🆕 FDA generics** | **`FDA_OrangeBook_check_generic_availability`** | **Generic count** |
| Label search | `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` |
| PGx Drug | `PharmGKB_search_drugs` | - |
| CPIC | `PharmGKB_get_dosing_guidelines` | - |
| Literature | `PubMed_search_articles` | `EuropePMC_search_articles` |
| Similar compounds | `PubChem_search_compounds_by_similarity` | ChEMBL |
| Patents | `PubChem_get_associated_patents_by_CID` | `FDA_OrangeBook_get_patent_info` |

---

## Compound Identity & Chemistry

### PubChem Tools
| Tool | Purpose | Key Output |
|------|---------|------------|
| `PubChem_get_CID_by_compound_name` | Name → CID | CID, canonical name |
| `PubChem_get_CID_by_SMILES` | Structure → CID | CID |
| `PubChem_get_compound_properties_by_CID` | Molecular properties | MW, formula, XLogP, TPSA, HBD, HBA |
| `PubChem_get_compound_2D_image_by_CID` | Structure image | PNG image |
| `PubChem_get_bioactivity_summary_by_CID` | Activity overview | Active/inactive counts, assay types |
| `PubChem_get_drug_label_info_by_CID` | FDA label info | Indications, warnings, dosing |
| `PubChem_get_associated_patents_by_CID` | Patent data | Patent numbers, titles |
| `PubChem_search_compounds_by_similarity` | Find analogs | Similar CIDs with scores |
| `PubChem_search_compounds_by_substructure` | Substructure search | Matching CIDs |

### ChEMBL Tools
| Tool | Purpose | Key Output |
|------|---------|------------|
| `ChEMBL_search_drugs` | Name/structure search | ChEMBL ID, pref_name |
| `ChEMBL_get_molecule` | Compound details | SMILES, properties, synonyms |
| `ChEMBL_get_activity` | Activity data | IC50, Ki, EC50 values |
| `ChEMBL_get_target` | Protein targets | Target ChEMBL IDs, UniProt |
| `ChEMBL_get_assays` | Assay metadata | Assay types, organisms |
| `ChEMBL_search_targets` | Target search | Target ChEMBL IDs |

---

## ADMET Predictions

All ADMET-AI tools require SMILES input in list format: `smiles=["CC(=O)Oc1ccccc1C(=O)O"]`

### Physicochemical
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_physicochemical_properties` | MW, logP, HBD, HBA, Lipinski, QED, stereo_centers, TPSA |
| `ADMETAI_predict_solubility_lipophilicity_hydration` | Solubility_AqSolDB, Lipophilicity_AstraZeneca, HydrationFreeEnergy |

### Absorption
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_bioavailability` | Bioavailability_Ma, HIA_Hou, PAMPA_NCATS, Caco2_Wang, Pgp_Broccatelli |

### Distribution
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_BBB_penetrance` | BBB_Martins (0-1 probability) |
| `ADMETAI_predict_clearance_distribution` | VDss_Lombardo, PPBR_AZ |

### Metabolism
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_CYP_interactions` | CYP1A2_Veith, CYP2C9_Veith/Substrate, CYP2C19_Veith, CYP2D6_Veith/Substrate, CYP3A4_Veith/Substrate |

### Excretion
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_clearance_distribution` | Clearance_Hepatocyte_AZ, Clearance_Microsome_AZ, Half_Life_Obach |

### Toxicity
| Tool | Endpoints |
|------|-----------|
| `ADMETAI_predict_toxicity` | AMES, Carcinogens_Lagunin, ClinTox, DILI, LD50_Zhu, Skin_Reaction, hERG |
| `ADMETAI_predict_nuclear_receptor_activity` | NR-AR, NR-AR-LBD, NR-AhR, NR-Aromatase, NR-ER, NR-ER-LBD, NR-PPAR-gamma |
| `ADMETAI_predict_stress_response` | SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53 |

---

## Drug-Gene Interactions

### DGIdb Tools
| Tool | Purpose | Key Output |
|------|---------|------------|
| `DGIdb_get_drug_gene_interactions` | Drug → gene interactions | Gene names, interaction types, sources |
| `DGIdb_get_gene_druggability` | Gene druggability categories | Kinase, GPCR, ion channel, etc. |
| `DGIdb_get_drug_info` | Drug targets and details | Target genes, interaction types |
| `DGIdb_get_gene_info` | Gene details | Aliases, categories |

---

## Clinical Trials (ClinicalTrials.gov)

### Search & Overview
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_clinical_trials` | Search trials | condition, intervention, query_term, pageSize |
| `get_clinical_trial_descriptions` | Trial titles, summaries | nct_ids, description_type (brief/full) |
| `get_clinical_trial_status_and_dates` | Status, dates | nct_ids |

### Details
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_clinical_trial_conditions_and_interventions` | Conditions, arms | nct_ids |
| `get_clinical_trial_eligibility_criteria` | Inclusion/exclusion | nct_ids |
| `get_clinical_trial_locations` | Trial sites | nct_ids |
| `get_clinical_trial_outcome_measures` | Primary/secondary endpoints | nct_ids, outcome_measures |
| `get_clinical_trial_references` | Related publications | nct_ids |

### Results Extraction
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `extract_clinical_trial_outcomes` | Efficacy results | nct_ids, outcome_measure |
| `extract_clinical_trial_adverse_events` | Safety data | nct_ids, organ_systems, adverse_event_type |

---

## Adverse Events (FDA FAERS)

### Single Drug Analysis
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `FAERS_count_reactions_by_drug_event` | AEs by MedDRA term | medicinalproduct, filters |
| `FAERS_count_seriousness_by_drug_event` | Serious vs non-serious | medicinalproduct |
| `FAERS_count_outcomes_by_drug_event` | Recovered, fatal, etc. | medicinalproduct |
| `FAERS_count_death_related_by_drug` | Fatal outcomes | medicinalproduct |
| `FAERS_count_patient_age_distribution` | Age groups | medicinalproduct |
| `FAERS_count_drug_routes_by_event` | Administration routes | medicinalproduct |
| `FAERS_count_country_by_drug_event` | Country distribution | medicinalproduct |

### Multi-Drug Analysis
| Tool | Purpose |
|------|---------|
| `FAERS_count_additive_adverse_reactions` | Combined AEs across drugs |
| `FAERS_count_additive_seriousness_classification` | Combined seriousness |
| `FAERS_count_additive_reaction_outcomes` | Combined outcomes |

### Filter Options (FAERS)
| Filter | Values |
|--------|--------|
| patientsex | "Male", "Female" |
| patientagegroup | "Neonate", "Infant", "Child", "Adolescent", "Adult", "Elderly" |
| occurcountry | ISO2 code (e.g., "US", "GB") |
| serious | "Yes", "No" |
| seriousnessdeath | "Yes", "No" |

---

## 🆕 FAERS Analytics (Statistical Signal Detection)

**NEW**: Priority 1 tools for pharmacovigilance with regulatory-grade statistics.

### Disproportionality Analysis
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_calculate_disproportionality` | Calculate ROR, PRR, IC with 95% CI | Signal strength, contingency table, statistical measures |

**Example**:
```python
result = tu.tools.FAERS_calculate_disproportionality(
    operation="calculate_disproportionality",
    drug_name="IBUPROFEN",
    adverse_event="Gastrointestinal haemorrhage"
)
# Returns: ROR 2.8 [2.71-2.89], "Moderate signal"
```

**Interpretation**:
- **ROR > 1**: Positive association (higher reporting than expected)
- **Signal detected**: ROR lower CI > 1.0 AND case count ≥ 3
- **Signal strength**: Strong (ROR ≥4), Moderate (ROR ≥2), Weak (ROR <2)
- ⚠️ **Caution**: Disproportionality ≠ causation (association only)

### Demographic Stratification
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_stratify_by_demographics` | Stratify by sex, age, country | Counts and percentages by group |

**Example**:
```python
result = tu.tools.FAERS_stratify_by_demographics(
    operation="stratify_by_demographics",
    drug_name="IBUPROFEN",
    adverse_event="Gastrointestinal haemorrhage",
    stratify_by="sex"  # Options: sex, age, country
)
# Returns: Female 60%, Male 40%
```

### Serious Events Filtering
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_filter_serious_events` | Filter by FDA seriousness criteria | Top serious reactions with counts |

**Example**:
```python
result = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events",
    drug_name="IBUPROFEN",
    seriousness_type="death"  # Options: all, death, hospitalization, disability, life_threatening
)
# Returns: Total deaths, top fatal reactions
```

### Drug Comparison
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_compare_drugs` | Compare safety signals between drugs | Side-by-side ROR/PRR/IC comparison |

**Example**:
```python
result = tu.tools.FAERS_compare_drugs(
    operation="compare_drugs",
    drug1="IBUPROFEN",
    drug2="NAPROXEN",
    adverse_event="Gastrointestinal haemorrhage"
)
# Returns: Comparative analysis with ROR for both drugs
```

### Temporal Trend Analysis
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_analyze_temporal_trends` | Analyze reporting trends over time | Yearly counts, trend direction, percent change |

**Example**:
```python
result = tu.tools.FAERS_analyze_temporal_trends(
    operation="analyze_temporal_trends",
    drug_name="IBUPROFEN",
    adverse_event="Gastrointestinal haemorrhage"
)
# Returns: Increasing/Decreasing/Stable trend with percent change
```

### MedDRA Hierarchy
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FAERS_rollup_meddra_hierarchy` | Aggregate by Preferred Term level | Top 50 PTs with counts |

**Example**:
```python
result = tu.tools.FAERS_rollup_meddra_hierarchy(
    operation="rollup_meddra_hierarchy",
    drug_name="IBUPROFEN"
)
# Returns: List of PTs with case counts
```

---

## 🆕 DailyMed SPL Parser (Structured Label Extraction)

**NEW**: Priority 1 tools for extracting structured data from FDA product labels.

### Parse Operations
| Tool | Purpose | Key Output |
|------|---------|------------|
| `DailyMed_parse_adverse_reactions` | Extract AE frequency tables | Tables with headers, rows, and text sections |
| `DailyMed_parse_dosing` | Extract dosing tables | Dosing regimens, administration instructions |
| `DailyMed_parse_contraindications` | Extract contraindication lists | Contraindication items and text |
| `DailyMed_parse_drug_interactions` | Extract interaction tables | Drug-drug interactions with severity |
| `DailyMed_parse_clinical_pharmacology` | Extract PK/PD data | Pharmacokinetic parameters, mechanism |

**Requirements**: Install `lxml` with `pip install lxml`

**Example**:
```python
# First, get setid from search
search = tu.tools.DailyMed_search_spls(drug_name="ibuprofen")
setid = search['data']['results'][0]['setid']

# Parse adverse reactions
result = tu.tools.DailyMed_parse_adverse_reactions(
    operation="parse_adverse_reactions",
    setid=setid
)
# Returns: {"tables": [...], "text_sections": [...]}
```

**Use Cases**:
- Systematic AE frequency extraction (no more manual PDF parsing)
- Structured dose modification rules
- Contraindication screening
- Drug-drug interaction tables for clinical decision support

---

## 🆕 FDA Orange Book (US Regulatory Intelligence)

**NEW**: Priority 1 tools for FDA approval data, patents, and generic availability.

### Search & Basic Info
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FDA_OrangeBook_search_drug` | Search by brand/generic name or NDA | Application numbers, drug info |

**Example**:
```python
result = tu.tools.FDA_OrangeBook_search_drug(
    operation="search_drug",
    brand_name="ADVIL"
)
# Or search by application number
result = tu.tools.FDA_OrangeBook_search_drug(
    operation="search_drug",
    application_number="NDA020402"
)
```

### Regulatory Timeline
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FDA_OrangeBook_get_approval_history` | Get approval timeline | Submission history, approval date, milestones |

**Example**:
```python
result = tu.tools.FDA_OrangeBook_get_approval_history(
    operation="get_approval_history",
    application_number="NDA020402"
)
# Returns: Approval date, submissions, review documents
```

### Patent & Exclusivity
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FDA_OrangeBook_get_patent_info` | Get patent information | Patent guidance, download URL |
| `FDA_OrangeBook_get_exclusivity` | Get exclusivity periods | Exclusivity types, expiry dates |

**Example**:
```python
# Patent info (guidance + download URL)
patents = tu.tools.FDA_OrangeBook_get_patent_info(
    operation="get_patent_info",
    brand_name="ADVIL"
)

# Exclusivity info
exclusivity = tu.tools.FDA_OrangeBook_get_exclusivity(
    operation="get_exclusivity",
    brand_name="ADVIL"
)
```

### Generic Availability
| Tool | Purpose | Key Output |
|------|---------|------------|
| `FDA_OrangeBook_check_generic_availability` | Compare reference vs generics | Generic products count, comparison |
| `FDA_OrangeBook_get_te_code` | Get Therapeutic Equivalence codes | TE codes with interpretation |

**Example**:
```python
# Check generic availability
generics = tu.tools.FDA_OrangeBook_check_generic_availability(
    operation="check_generic_availability",
    brand_name="ADVIL"
)
# Returns: Reference product, generic count, TE codes

# Get TE code interpretation
te_codes = tu.tools.FDA_OrangeBook_get_te_code(
    operation="get_te_code",
    brand_name="ADVIL"
)
# Returns: TE codes (e.g., "AB") with interpretation
```

**TE Code Guide**:
- **A**: Therapeutically equivalent
  - **AB**: Bioequivalence standards met
  - **AP**: Multi-source with equivalence
- **B**: NOT therapeutically equivalent
  - **BC**: Extended-release dosage form issues
  - **BN**: Active ingredient issues

**Use Cases**:
- Market entry planning (patent cliffs, exclusivity expiry)
- Generic competition landscape
- Regulatory submission timelines
- Therapeutic equivalence assessment

---

## Drug Labeling (Legacy)

### DailyMed Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DailyMed_search_spls` | Search labels | drug_name, ndc, rxcui, setid |
| `DailyMed_get_spl_by_setid` | Full label content | setid, format |

---

## Pharmacogenomics (PharmGKB)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PharmGKB_search_drugs` | Search drugs | query |
| `PharmGKB_get_drug_details` | Drug cross-references | drug_id (PA...) |
| `PharmGKB_search_genes` | Search pharmacogenes | query |
| `PharmGKB_get_gene_details` | Gene details | gene_id |
| `PharmGKB_get_clinical_annotations` | Gene-drug associations | annotation_id or gene_id |
| `PharmGKB_get_dosing_guidelines` | CPIC/DPWG guidelines | guideline_id or gene |
| `PharmGKB_search_variants` | Search by rsID | query |

---

## Literature

### Search Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Primary biomedical | query, limit |
| `PMC_search_papers` | Full-text | query, limit |
| `EuropePMC_search_articles` | European coverage | query, limit |
| `openalex_literature_search` | Broad academic | query, limit |
| `Crossref_search_works` | DOI-based | query, limit |
| `SemanticScholar_search_papers` | AI-ranked | query, limit |
| `EuropePMC_search_articles` | Preprints (use source='PPR') | query, source, pageSize |
| `BioRxiv_get_preprint` | Get by DOI | doi |
| `MedRxiv_get_preprint` | Get by DOI | doi, server |

### Citation Tools
| Tool | Purpose |
|------|---------|
| `PubMed_get_cited_by` | Forward citations |
| `PubMed_get_related` | Related articles |
| `EuropePMC_get_citations` | Citations (fallback) |
| `EuropePMC_get_references` | Reference list |

---

## Tool Chains by Research Path

### PATH 1: Identity Resolution
```
PubChem_get_CID_by_compound_name
  ↓
ChEMBL_search_compounds
  ↓
DailyMed_search_spls
  ↓
PharmGKB_search_drugs
```

### PATH 2: Chemistry & Drug-likeness
```
PubChem_get_compound_properties_by_CID
  ↓
ADMETAI_predict_physicochemical_properties
  ↓
ADMETAI_predict_solubility_lipophilicity_hydration
```

### PATH 3: Targets & Bioactivity
```
ChEMBL_get_bioactivity_by_chemblid
  ↓
ChEMBL_get_target_by_chemblid
  ↓
DGIdb_get_drug_info
  ↓
PubChem_get_bioactivity_summary_by_CID
```

### PATH 4: ADMET Profile
```
ADMETAI_predict_bioavailability
  ↓
ADMETAI_predict_BBB_penetrance
  ↓
ADMETAI_predict_CYP_interactions
  ↓
ADMETAI_predict_clearance_distribution
  ↓
ADMETAI_predict_toxicity
```

### PATH 5: Clinical Trials
```
search_clinical_trials
  ↓
get_clinical_trial_conditions_and_interventions
  ↓
extract_clinical_trial_outcomes
  ↓
extract_clinical_trial_adverse_events
```

### PATH 6: Post-Marketing Safety
```
FAERS_count_reactions_by_drug_event
  ↓
FAERS_count_seriousness_by_drug_event
  ↓
FAERS_count_outcomes_by_drug_event
  ↓
FAERS_count_death_related_by_drug
  ↓
FAERS_count_patient_age_distribution
```

### PATH 7: Pharmacogenomics
```
PharmGKB_search_drugs
  ↓
PharmGKB_get_drug_details
  ↓
PharmGKB_get_clinical_annotations (for each gene)
  ↓
PharmGKB_get_dosing_guidelines
```

### PATH 8: Literature
```
PubMed_search_articles (total count)
  ↓
PubMed_search_articles (recent papers)
  ↓
PubMed_search_articles (drug-focused)
  ↓
PubMed_get_cited_by (for key papers)
```

---

## Fallback Chains

| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` | Manual SMILES search |
| `ChEMBL_get_activity` | `PubChem_get_bioactivity_summary_by_CID` | Literature search |
| `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` | FDA Orange Book |
| `PharmGKB_get_dosing_guidelines` | Note "No guideline" | Literature search |
| `FAERS_count_reactions_by_drug_event` | Note "FAERS unavailable" | Trial AE data |
| `ADMETAI_*` | Note "Predictions unavailable" | Literature values |
| `PubMed_search_articles` | `EuropePMC_search_articles` | `openalex_literature_search` |

---

## Rate Limiting & Best Practices

| Database | Notes |
|----------|-------|
| PubChem | Robust, no strict limits; batch when possible |
| ChEMBL | May timeout on large bioactivity queries |
| ClinicalTrials.gov | Paginate for >100 results; use pageToken |
| FAERS | Can be slow; use minimal filters; avoid over-restriction |
| PharmGKB | Generally fast |
| ADMET-AI | Local computation; batch SMILES in single call |
| PubMed | 3 requests/second limit; use limit parameter |

---

## Input Format Requirements

### SMILES
```python
# ADMET-AI tools require list format
smiles = ["CC(=O)Oc1ccccc1C(=O)O"]  # List, not string
```

### Drug Names (FAERS)
```python
# Use uppercase, match FDA labeling
medicinalproduct = "METFORMIN"  # Not "metformin"
```

### NCT IDs
```python
# List format for batch queries
nct_ids = ["NCT01234567", "NCT02345678"]
```

### ChEMBL IDs
```python
# Full ID format
chembl_id = "CHEMBL1431"  # Not "1431"
```

### PharmGKB IDs
```python
# PA prefix for drugs
drug_id = "PA450657"  # Not "450657"
```
