---
name: tooluniverse-cancer-genomics-tcga
description: >
  TCGA/GDC cancer genomics analysis -- cohort construction, clinical metadata retrieval,
  somatic mutation profiling, copy number variation analysis, survival analysis, and
  clinical variant interpretation. Use when users ask about TCGA data, GDC cancer cohorts,
  somatic mutation frequencies, Kaplan-Meier survival, CNV profiles in cancer, or OncoKB
  interpretation of cancer variants.
triggers:
  - keywords: [TCGA, GDC, cancer cohort, somatic mutation, Kaplan-Meier, survival analysis, CNV, copy number variation, Progenetix, OncoKB, tumor, cancer genomics, mutation frequency]
  - patterns: ["TCGA-", "survival analysis for", "mutation frequency in", "copy number", "GDC project", "cancer cases", "overall survival"]
---

# Cancer Genomics / TCGA Analysis

**TCGA analysis starts with: what cancer type? what data type?** Build your cohort FIRST (GDC filters), then analyze. Don't query mutations without defining the cohort — pan-cancer counts from `GDC_get_mutation_frequency` are uninformative without cancer-type context. A mutation frequency of 10% in one cancer type may be 0.5% in another; always specify `project_id`. Survival analysis (Kaplan-Meier) is hypothesis-generating in retrospective TCGA data — always report sample size and p-value, and note that TCGA cohorts are not treatment-stratified.

**LOOK UP DON'T GUESS**: never assume TCGA project IDs, NCIt codes, or gene coordinates — use `GDC_list_projects` to confirm project IDs and `Progenetix_list_filtering_terms` for NCIt codes.

Systematic TCGA/GDC analysis: define cohorts, retrieve clinical data, profile somatic
mutations, query copy number variations, run survival analysis, and interpret variants
with OncoKB.

## When to Use

- "What is the mutation frequency of TP53 in TCGA-BRCA?"
- "Get survival data for TCGA-LUAD patients"
- "Find clinical data for breast cancer cases in GDC"
- "Which TCGA projects have KRAS G12C mutations?"
- "Show CNV amplifications of EGFR in glioblastoma"
- "Annotate BRAF V600E for clinical significance in melanoma"

## NOT for (use other skills instead)

- Precision oncology treatment recommendations -> Use `tooluniverse-precision-oncology`
- Rare disease gene discovery -> Use `tooluniverse-rare-disease-genomics`
- GWAS variant interpretation -> Use `tooluniverse-gwas-snp-interpretation`

---

## Workflow Overview

```
Input (cancer type / gene / TCGA project ID)
  |
  v
Phase 1: Study Selection  -- GDC_list_projects, GDC_search_cases
  |
  v
Phase 2: Clinical Data    -- GDC_get_clinical_data
  |
  v
Phase 3: Somatic Mutations -- GDC_get_ssm_by_gene, GDC_get_mutation_frequency
  |
  v
Phase 4: CNV Analysis     -- Progenetix_cnv_search, Progenetix_search_biosamples
  |
  v
Phase 5: Survival Analysis -- GDC_get_survival
  |
  v
Phase 6: Variant Interpretation -- OncoKB_annotate_variant
```

---

## Key Identifiers

| Data Type | Format | Example |
|-----------|--------|---------|
| GDC project | TCGA-{ABBREV} | TCGA-BRCA, TCGA-LUAD, TCGA-SKCM |
| GDC case | UUID | 3c6ef4c1-... |
| NCIt cancer code | NCIT:C###### | NCIT:C4017 (breast), NCIT:C3058 (GBM) |
| RefSeq chromosome | refseq:NC_###### | refseq:NC_000007.14 (chr7) |

### Common TCGA Project IDs

| Cancer | Project ID | NCIt Code |
|--------|-----------|-----------|
| Breast | TCGA-BRCA | NCIT:C4017 |
| Lung adenocarcinoma | TCGA-LUAD | NCIT:C3512 |
| Glioblastoma | TCGA-GBM | NCIT:C3058 |
| Melanoma | TCGA-SKCM | NCIT:C3510 |
| Colorectal | TCGA-COAD | NCIT:C4349 |
| Ovarian | TCGA-OV | NCIT:C4908 |
| Prostate | TCGA-PRAD | NCIT:C7378 |

---

## Phase 1: Study Selection

**GDC_list_projects**: No params required. Returns all GDC/TCGA projects with case counts.
- Use to browse available projects and map cancer types to project IDs.

**GDC_search_cases**: `project_id` (string, e.g., "TCGA-BRCA"), `size` (int, default 10), `offset` (int).
Returns case UUIDs and basic metadata.
- Use to confirm a project exists and retrieve case counts before deeper queries.

---

## Phase 2: Clinical Data

**GDC_get_clinical_data**: `project_id` (string), `primary_site` (string, e.g., "Breast"), `disease_type` (string), `vital_status` ("Alive" or "Dead"), `gender` ("female"/"male"), `size` (int, 1-100), `offset` (int).
Returns `{status, data: [{case_id, demographics: {gender, race, ethnicity, vital_status, age_at_index}, diagnoses: [{primary_diagnosis, tumor_stage, age_at_diagnosis, days_to_last_follow_up}], treatments: [{therapeutic_agents, treatment_type}]}]}`.
- Use `project_id` + optional filters to retrieve patient-level clinical attributes.
- `age_at_diagnosis` is in days; divide by 365.25 for years.
- Multiple diagnoses or treatments per case are possible.

```python
# Get clinical data for deceased BRCA patients
result = tu.tools.GDC_get_clinical_data(
    project_id="TCGA-BRCA", vital_status="Dead", size=50
)
```

---

## Phase 3: Somatic Mutations

**GDC_get_mutation_frequency**: `gene_symbol` (string REQUIRED, alias: `gene`). Returns pan-cancer SSM occurrence count.
- Returns TOTAL count across all TCGA; no per-project breakdown.
- For cancer-specific data, use `GDC_get_ssm_by_gene` with `project_id`.

**GDC_get_ssm_by_gene**: `gene_symbol` (string REQUIRED), `project_id` (string, optional), `size` (int, 1-100).
Returns `{status, data: [{ssm_id, mutation_type, genomic_dna_change, aa_change, consequence_type}]}`.
- `mutation_type`: "Single base substitution", "Insertion", "Deletion".
- `aa_change`: amino acid change notation (e.g., "Val600Glu").

```python
# TP53 mutations in lung adenocarcinoma
mutations = tu.tools.GDC_get_ssm_by_gene(
    gene_symbol="TP53", project_id="TCGA-LUAD", size=50
)
```

---

## Phase 4: CNV Analysis (Progenetix)

**Progenetix_search_biosamples**: `filters` (string REQUIRED, NCIt code e.g., "NCIT:C4017"), `limit` (int), `skip` (int).
Returns `{status, data: {biosamples: [{biosample_id, histological_diagnosis, pathological_stage, external_references}]}}`.
- Use to find samples with CNV profiles for a given cancer type.

**Progenetix_cnv_search**: `reference_name` (string REQUIRED, RefSeq accession), `start` (int REQUIRED, GRCh38 1-based), `end` (int REQUIRED), `variant_type` ("DUP"/"DEL"), `filters` (string, NCIt code), `limit` (int).
Returns biosamples with CNV in the specified genomic region.
- `variant_type="DUP"` for amplification, `"DEL"` for deletion.
- Use `filters` to restrict to a cancer type.

```python
# EGFR amplifications (chr7:55019017-55211628) in breast cancer
result = tu.tools.Progenetix_cnv_search(
    reference_name="refseq:NC_000007.14",
    start=55019017, end=55211628,
    variant_type="DUP", filters="NCIT:C4017", limit=10
)
```

**Progenetix_list_filtering_terms**: No params. Returns all available NCIt codes and labels.
- Use when you need to find the NCIt code for a cancer type.

**Progenetix_list_cohorts**: No params. Returns named cohorts available in Progenetix.

---

## Phase 5: Survival Analysis

**GDC_get_survival**: `project_id` (string REQUIRED, e.g., "TCGA-BRCA"), `gene_symbol` (string, optional -- filters to mutated cases).
Returns `{status, data: {donors: [{id, time, censored, survivalEstimate}], overallStats: {pValue}}}`.
- Each donor has `time` (days), `censored` (bool: False=death event, True=censored), and `survivalEstimate`.
- `overallStats.pValue`: log-rank p-value (present when `gene_symbol` splits cohort).
- Without `gene_symbol`: returns full-cohort survival curve.
- With `gene_symbol`: returns survival split by mutation status (mutated vs. wild-type).

```python
# Survival for TCGA-BRCA split by TP53 mutation
surv = tu.tools.GDC_get_survival(project_id="TCGA-BRCA", gene_symbol="TP53")
pval = surv["data"]["overallStats"]["pValue"]
```

---

## Phase 6: Variant Interpretation (OncoKB)

**OncoKB_annotate_variant**: `gene` (string, alias `gene_symbol`), `variant` (string, alias `alteration`, e.g., "V600E"), `tumor_type` (string, OncoTree code e.g., "MEL").
Returns `{status, data: {oncogenic, mutationEffect, highestSensitiveLevel, treatments: [{drugs, level, indication}]}}`.
- `oncogenic`: "Oncogenic", "Likely Oncogenic", "Neutral", "Inconclusive", "Unknown".
- `highestSensitiveLevel`: FDA approval level ("LEVEL_1"=FDA-approved, "LEVEL_2"=standard of care, etc.).
- Demo mode available for BRAF, TP53, ROS1 without API key.
- Set ONCOKB_API_TOKEN for full access.

```python
# Annotate KRAS G12C in lung adenocarcinoma
result = tu.tools.OncoKB_annotate_variant(
    gene="KRAS", variant="G12C", tumor_type="LUAD"
)
```

---

## Tool Quick Reference

| Tool | Key Params | Returns |
|------|-----------|---------|
| GDC_list_projects | (none) | All TCGA/GDC projects with counts |
| GDC_search_cases | `project_id`, `size`, `offset` | Case UUIDs + metadata |
| GDC_get_clinical_data | `project_id`, `vital_status`, `gender`, `size` | Demographics + diagnoses + treatments |
| GDC_get_mutation_frequency | `gene_symbol` (alias: `gene`) | Pan-cancer SSM count |
| GDC_get_ssm_by_gene | `gene_symbol`, `project_id`, `size` | Per-mutation records with aa_change |
| GDC_get_survival | `project_id`, `gene_symbol` (optional) | Kaplan-Meier donor array + pValue |
| Progenetix_search_biosamples | `filters` (NCIt code), `limit` | Biosample records |
| Progenetix_cnv_search | `reference_name`, `start`, `end`, `variant_type`, `filters` | Biosamples with CNV in region |
| Progenetix_list_filtering_terms | (none) | All NCIt codes in Progenetix |
| OncoKB_annotate_variant | `gene`, `variant`, `tumor_type` | Oncogenicity + treatments |

---

## Example Workflows

### Workflow 1: Gene-Centric Mutation + Survival Analysis

```
1. GDC_get_mutation_frequency(gene_symbol="KRAS")
   -> Pan-cancer mutation count

2. GDC_get_ssm_by_gene(gene_symbol="KRAS", project_id="TCGA-LUAD", size=50)
   -> Specific amino acid changes in lung adenocarcinoma

3. GDC_get_survival(project_id="TCGA-LUAD", gene_symbol="KRAS")
   -> Survival split by KRAS mutation status + p-value

4. OncoKB_annotate_variant(gene="KRAS", variant="G12C", tumor_type="LUAD")
   -> Clinical significance + approved therapies (sotorasib)
```

### Workflow 2: Cohort Clinical Summary

```
1. GDC_list_projects()  -> confirm TCGA-OV exists

2. GDC_get_clinical_data(project_id="TCGA-OV", size=100)
   -> Demographics, tumor stage, treatment history

3. GDC_get_survival(project_id="TCGA-OV")
   -> Baseline overall survival curve for the cohort
```

### Workflow 3: CNV Analysis for a Gene

```
1. Progenetix_search_biosamples(filters="NCIT:C3058", limit=10)
   -> GBM biosamples with CNV data

2. Progenetix_cnv_search(
       reference_name="refseq:NC_000007.14",
       start=55019017, end=55211628,
       variant_type="DUP", filters="NCIT:C3058"
   )
   -> GBM samples with EGFR amplification
```

---

## Reasoning Framework

### Evidence Grading

| Tier | Description | Example |
|------|-------------|---------|
| **T1** | FDA-recognized biomarker with approved therapy | BRAF V600E in melanoma (vemurafenib) |
| **T2** | Well-powered clinical study, standard-of-care relevance | KRAS G12C in NSCLC (sotorasib), OncoKB Level 2 |
| **T3** | Preclinical/small cohort evidence, biological plausibility | Recurrent hotspot in TCGA but no approved therapy |
| **T4** | Computational prediction or variant of unknown significance | Low-frequency mutation, no functional data |

### Interpretation Guidance

**Mutation frequency**: A gene mutated in >10% of a TCGA cohort is likely a driver candidate (e.g., TP53 in 36% of all TCGA). Mutations at <1% frequency are typically passengers unless they occur at known hotspots. Always cross-reference with OncoKB oncogenicity annotation.

**Survival analysis (Kaplan-Meier)**: A log-rank p-value < 0.05 suggests the gene mutation is associated with differential survival. Hazard ratio (HR) > 1 indicates worse prognosis for the mutated group. Interpret cautiously: TCGA cohorts are retrospective and not treatment-stratified. Small subgroups (n < 20) produce unreliable survival estimates.

**Copy number variation**: Focal amplifications (narrow peaks) of oncogenes (EGFR, MYC, ERBB2) are more likely functionally relevant than broad arm-level events. Homozygous deletions of tumor suppressors (CDKN2A, PTEN, RB1) are strong loss-of-function signals. DUP count from Progenetix reflects sample frequency, not copy number magnitude.

### Synthesis Questions

A complete cancer genomics report should answer:
1. What are the most frequently mutated genes in this cancer type, and which are known drivers?
2. Does mutation status of the queried gene associate with survival (p < 0.05)?
3. Are recurrent CNV events (amplifications or deletions) present at known oncogene/tumor suppressor loci?
4. What is the OncoKB clinical actionability level for identified variants?
5. How does the mutation landscape compare across TCGA cancer types (pan-cancer context)?

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return truncated results or you need bulk data, use the GDC API directly:

```python
import requests, pandas as pd

# Bulk clinical data for a TCGA project
filters = {"op":"and","content":[
    {"op":"=","content":{"field":"project.project_id","value":"TCGA-BRCA"}}
]}
all_cases = []
offset = 0
while True:
    resp = requests.post("https://api.gdc.cancer.gov/cases", json={
        "filters": filters, "size": 500, "from": offset,
        "fields": "submitter_id,demographic.vital_status,demographic.days_to_death,diagnoses.tumor_stage"
    }).json()
    hits = resp["data"]["hits"]
    if not hits: break
    all_cases.extend(hits)
    offset += len(hits)
df = pd.json_normalize(all_cases)

# Download MAF mutation file by UUID
file_uuid = "abc123-..."  # from GDC_list_files result
url = f"https://api.gdc.cancer.gov/data/{file_uuid}"
content = requests.get(url, headers={"Content-Type": "application/json"}).content

# Gene expression: query files endpoint for HTSeq counts
expr_filters = {"op":"and","content":[
    {"op":"=","content":{"field":"cases.project.project_id","value":"TCGA-BRCA"}},
    {"op":"=","content":{"field":"data_type","value":"Gene Expression Quantification"}}
]}
```

See `tooluniverse-data-wrangling` skill for pagination, error handling, and format parsing patterns.

---

## Limitations

- `GDC_get_survival` with `gene_symbol` splits on mutation presence only; no multi-gene or stage-based stratification.
- `GDC_get_mutation_frequency` returns pan-cancer total only; per-cancer frequencies require `GDC_get_ssm_by_gene` per project.
- `GDC_get_clinical_data` returns up to 100 cases per call; use `offset` for pagination.
- Progenetix uses GRCh38 coordinates; provide GRCh38 positions for `Progenetix_cnv_search`.
- `OncoKB_annotate_variant` without ONCOKB_API_TOKEN operates in demo mode (limited to BRAF, TP53, ROS1).
- Progenetix `filters` param requires NCIt CURIE format (e.g., "NCIT:C4017"), not free text.
