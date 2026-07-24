# Precision Oncology Report Template

**File naming**: `[PATIENT_ID]_oncology_report.md`

---

## Template Structure

```markdown
# Precision Oncology Report

**Patient ID**: [ID] | **Date**: [Date]

## Patient Profile
- **Diagnosis**: [Cancer type, stage]
- **Molecular Profile**: [Mutations, fusions]
- **Prior Therapy**: [Previous treatments]

---

## Executive Summary
[2-3 sentence summary of key findings and recommendation]

---

## 1. Variant Interpretation
[Table with variants, significance, evidence levels]

### COSMIC Mutation Frequency

| Gene | Mutation | COSMIC Count | Primary Cancer Types | FATHMM Prediction |
|------|----------|--------------|---------------------|-------------------|
| EGFR | L858R | 15,234 | Lung (85%), Colorectal (5%) | Pathogenic |
| EGFR | T790M | 8,567 | Lung (95%) | Pathogenic |
| BRAF | V600E | 45,678 | Melanoma (50%), Colorectal (15%) | Pathogenic |

### TCGA/GDC Patient Tumor Data

| Gene | TCGA Project | SSM Cases | CNV Amp | CNV Del | % Samples |
|------|-------------|-----------|---------|---------|-----------|
| EGFR | TCGA-LUAD | 156 | 89 | 5 | 28% |
| EGFR | TCGA-GBM | 45 | 312 | 2 | 57% |
| KRAS | TCGA-PAAD | 134 | 8 | 1 | 92% |

*Source: GDC via `GDC_get_mutation_frequency`, `GDC_get_cnv_data`*

### DepMap Target Essentiality

| Gene | Mean Effect (All) | Mean Effect (Cancer Type) | Selectivity | Interpretation |
|------|-------------------|---------------------------|-------------|----------------|
| EGFR | -0.15 | -0.45 (lung) | Cancer-selective | Good target |
| KRAS | -0.82 | -0.91 (pancreatic) | Essential | Hard to target |
| MYC | -0.95 | -0.93 | Pan-essential | Challenging target |

*Effect score <-0.5 = strongly essential for cell survival*
*Source: DepMap via `DepMap_get_gene_dependencies`*

### Expression Validation (Human Protein Atlas)

| Gene | Tumor Cell Line | Expression | Normal Tissue | Differential |
|------|-----------------|------------|---------------|--------------|
| EGFR | A549 (lung) | High | Low-Medium | Tumor-elevated |
| ALK | H3122 (lung) | High | Not detected | Tumor-specific |
| HER2 | MCF7 (breast) | Medium | Low | Elevated |

*Source: Human Protein Atlas via `HPA_get_comparative_expression_by_gene_and_cellline`*

## 2. Tumor Expression Context

### Target Expression in Tumor Microenvironment (CELLxGENE)

| Gene | Tumor Cells | Normal Cells | Tumor/Normal Ratio | Interpretation |
|------|-------------|--------------|-------------------|----------------|
| EGFR | High (TPM=85) | Medium (TPM=25) | 3.4x | Good target |
| MET | Medium (TPM=35) | Low (TPM=8) | 4.4x | Potential bypass |
| AXL | High (TPM=120) | Low (TPM=15) | 8.0x | Resistance marker |

### Cell Type Distribution

- **EGFR-high cells**: Tumor epithelial (85%), CAFs (10%), immune (5%)
- **MET-high cells**: Tumor epithelial (70%), endothelial (20%), immune (10%)

## 3. Treatment Recommendations
### First-Line Options
[Prioritized list with evidence]

### Second-Line Options
[Alternative approaches]

## 4. Pathway & Network Analysis

### Signaling Pathway Context (KEGG)

| Pathway | Genes Involved | Relevance | Drug Targets |
|---------|---------------|-----------|--------------|
| EGFR signaling (hsa04012) | EGFR, MET, ERBB3 | Primary pathway | Osimertinib, Capmatinib |
| PI3K-AKT (hsa04151) | PIK3CA, AKT1 | Downstream | Alpelisib |
| RAS-MAPK (hsa04010) | KRAS, BRAF, MEK | Bypass potential | Sotorasib, Trametinib |

### Protein Interaction Network (IntAct)

| Target | Direct Interactors | Key Partners | Relevance |
|--------|-------------------|--------------|-----------|
| EGFR | 156 | MET, ERBB2, ERBB3, GRB2 | Bypass pathways |
| MET | 89 | EGFR, HGF, GAB1 | Resistance mediator |

## 5. Resistance Analysis (if applicable)
[Mechanism explanation, strategies to overcome]

## 6. Clinical Trial Options
[Matched trials with eligibility]

## 7. Literature Evidence

### Key Clinical Studies

| PMID | Title | Year | Citations | Evidence Type |
|------|-------|------|-----------|---------------|
| 27959700 | AURA3: Osimertinib vs chemotherapy... | 2017 | 2,450 | Phase 3 trial |
| 30867819 | Mechanisms of osimertinib resistance... | 2019 | 680 | Review |

### Recent Preprints (Not Peer-Reviewed)

| Source | Title | Posted | Key Finding |
|--------|-------|--------|-------------|
| MedRxiv | Novel C797S resistance strategy... | 2024-01 | Fourth-gen TKI |
| BioRxiv | scRNA-seq reveals resistance... | 2024-02 | Cell state switch |

**Note**: Preprints have NOT undergone peer review. Interpret with caution.

## 8. Next Steps
1. [Specific actionable recommendation]
2. [Follow-up testing if needed]
3. [Referral if appropriate]

---

## Data Sources
| Source | Query | Data Retrieved |
|--------|-------|----------------|
| CIViC | [gene] [variant] | Evidence items |
| ClinicalTrials.gov | [condition] | Active trials |
| COSMIC | [gene] | Somatic mutation frequency |
| GDC/TCGA | [gene] [project] | Patient tumor data |
| DepMap | [gene] | Target essentiality |
| OncoKB | [gene] [variant] | Actionability level |
| cBioPortal | [study] [genes] | Cross-study mutations |
| HPA | [gene] | Expression validation |
| CELLxGENE | [gene] [tissue] | Cell-type expression |
| KEGG/Reactome | [gene] | Pathway context |
| IntAct | [gene] | Protein interactions |
| PubMed | [query] | Published evidence |
| BioRxiv/MedRxiv | [query] | Preprints |
| OpenAlex | [paper] | Citation analysis |
```

---

## Completeness Checklist

Before finalizing report:

- [ ] All variants interpreted with evidence levels
- [ ] >= 1 first-line recommendation with evidence (or explain why none)
- [ ] Resistance mechanism addressed (if prior therapy failed)
- [ ] >= 3 clinical trials listed (or "no matching trials")
- [ ] Executive summary is actionable (says what to DO)
- [ ] All recommendations have source citations
- [ ] COSMIC hotspot analysis included
- [ ] TCGA/GDC real patient data included
- [ ] DepMap target essentiality assessed
- [ ] Expression validation (HPA + CELLxGENE) performed
- [ ] Pathway context provided for combination rationale
