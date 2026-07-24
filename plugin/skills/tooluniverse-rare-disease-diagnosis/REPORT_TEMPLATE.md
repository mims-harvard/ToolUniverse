# Report Template & Output Examples

Templates and example outputs for each phase of the rare disease diagnosis workflow.

---

## Report File Template

**File**: `[PATIENT_ID]_rare_disease_report.md`

```markdown
# Rare Disease Diagnostic Report

**Patient ID**: [ID] | **Date**: [Date] | **Status**: In Progress

---

## Executive Summary
[Researching...]

---

## 1. Phenotype Analysis
### 1.1 Standardized HPO Terms
[Researching...]
### 1.2 Key Clinical Features
[Researching...]

---

## 2. Differential Diagnosis
### 2.1 Ranked Candidate Diseases
[Researching...]
### 2.2 Disease Details
[Researching...]

---

## 3. Recommended Gene Panel
### 3.1 Prioritized Genes
[Researching...]
### 3.2 Testing Strategy
[Researching...]

---

## 4. Variant Interpretation (if applicable)
### 4.1 Variant Details
[Researching...]
### 4.2 ACMG Classification
[Researching...]

---

## 5. Structural Analysis (if applicable)
### 5.1 Structure Prediction
[Researching...]
### 5.2 Variant Impact
[Researching...]

---

## 6. Clinical Recommendations
### 6.1 Diagnostic Next Steps
[Researching...]
### 6.2 Specialist Referrals
[Researching...]
### 6.3 Family Screening
[Researching...]

---

## 7. Data Gaps & Limitations
[Researching...]

---

## 8. Data Sources
[Will be populated as research progresses...]
```

---

## Phase Output Examples

### Phase 1: Phenotype Analysis Output

```markdown
## 1. Phenotype Analysis

### 1.1 Standardized HPO Terms

| Clinical Feature | HPO Term | HPO ID | Category |
|------------------|----------|--------|----------|
| Tall stature | Tall stature | HP:0000098 | Core |
| Long fingers | Arachnodactyly | HP:0001166 | Core |
| Heart murmur | Cardiac murmur | HP:0030148 | Variable |
| Joint hypermobility | Joint hypermobility | HP:0001382 | Core |

**Total HPO Terms**: 8
**Onset**: Childhood
**Family History**: Father with similar features (AD suspected)

*Source: HPO via `HPO_search_terms`*
```

### Phase 2: Differential Diagnosis Output

```markdown
## 2. Differential Diagnosis

### Top Candidate Diseases (Ranked by Phenotype Match)

| Rank | Disease | ORPHA | OMIM | Match | Inheritance | Key Gene(s) |
|------|---------|-------|------|-------|-------------|-------------|
| 1 | Marfan syndrome | 558 | 154700 | 85% | AD | FBN1 |
| 2 | Loeys-Dietz syndrome | 60030 | 609192 | 72% | AD | TGFBR1, TGFBR2 |
| 3 | Ehlers-Danlos, vascular | 286 | 130050 | 65% | AD | COL3A1 |
| 4 | Homocystinuria | 394 | 236200 | 58% | AR | CBS |

### DisGeNET Gene-Disease Evidence

| Gene | Associated Diseases | GDA Score | Evidence |
|------|---------------------|-----------|----------|
| FBN1 | Marfan syndrome, MASS phenotype | 0.95 | Curated |
| TGFBR1 | Loeys-Dietz syndrome | 0.89 | Curated |
| COL3A1 | vascular EDS | 0.91 | Curated |

*Source: DisGeNET via `DisGeNET_search_gene`*

### Disease Details

#### 1. Marfan Syndrome

**ORPHA**: 558 | **OMIM**: 154700 | **Prevalence**: 1-5/10,000

**Phenotype Match Analysis**:
| Patient Feature | Disease Feature | Match |
|-----------------|-----------------|-------|
| Tall stature | Present in 95% | Yes |
| Arachnodactyly | Present in 90% | Yes |
| Joint hypermobility | Present in 85% | Yes |
| Cardiac murmur | Aortic root dilation (70%) | Partial |

**OMIM Clinical Synopsis** (via `OMIM_get_clinical_synopsis`):
- **Cardiovascular**: Aortic root dilation, mitral valve prolapse
- **Skeletal**: Scoliosis, pectus excavatum, tall stature
- **Ocular**: Ectopia lentis, myopia

**Diagnostic Criteria**: Ghent nosology (2010)
- Aortic root dilation/dissection + FBN1 mutation = Diagnosis
- Without genetic testing: systemic score >=7 + ectopia lentis

**Inheritance**: Autosomal dominant (25% de novo)

*Source: Orphanet via `Orphanet_get_disease`, OMIM via `OMIM_get_entry`, DisGeNET*
```

### Phase 3: Gene Panel Output

```markdown
## 3. Recommended Gene Panel

### 3.1 Prioritized Genes for Testing

| Priority | Gene | Diseases | Evidence | Constraint (pLI) | Expression |
|----------|------|----------|----------|------------------|------------|
| High | FBN1 | Marfan syndrome | Definitive | 1.00 | Heart, aorta |
| High | TGFBR1 | Loeys-Dietz 1 | Definitive | 0.98 | Ubiquitous |
| High | TGFBR2 | Loeys-Dietz 2 | Definitive | 0.99 | Ubiquitous |
| Medium | COL3A1 | EDS vascular | Definitive | 1.00 | Connective tissue |
| Low | CBS | Homocystinuria | Definitive | 0.00 | Liver |

### 3.2 Panel Design Recommendation

**Minimum Panel** (high yield): FBN1, TGFBR1, TGFBR2, COL3A1
**Extended Panel** (+differential): Add CBS, SMAD3, ACTA2

**Testing Strategy**:
1. Start with FBN1 sequencing (highest pre-test probability)
2. If negative, proceed to full connective tissue panel
3. Consider WES if panel negative

*Source: ClinGen via gene-disease validity, GTEx expression*
```

### Phase 3.5: Expression & Regulatory Context Output

```markdown
## 3.5 Expression & Regulatory Context

### Cell-Type Specific Expression (CELLxGENE)

| Gene | Top Expressing Cell Types | Expression Level | Tissue Relevance |
|------|---------------------------|------------------|------------------|
| FBN1 | Fibroblasts, Smooth muscle | High (TPM=45) | Connective tissue |
| TGFBR1 | Endothelial, Fibroblasts | Medium (TPM=12) | Vascular |
| COL3A1 | Fibroblasts, Myofibroblasts | Very High (TPM=120) | Connective tissue |

**Interpretation**: All top candidate genes show high expression in disease-relevant cell types.

### Regulatory Context (ChIPAtlas)

| Gene | Key TF Regulators | Regulatory Significance |
|------|-------------------|------------------------|
| FBN1 | TGFb pathway (SMAD2/3), AP-1 | TGFb-responsive |
| TGFBR1 | STAT3, NF-kB | Inflammation-responsive |

*Source: CELLxGENE Census, ChIPAtlas*
```

### Phase 3.6: Pathway & Network Context Output

```markdown
## 3.6 Pathway & Network Context

### KEGG Pathways

| Gene | Key Pathways | Biological Process |
|------|--------------|-------------------|
| FBN1 | ECM-receptor interaction (hsa04512) | Extracellular matrix |
| TGFBR1/2 | TGF-beta signaling (hsa04350) | Cell signaling |
| COL3A1 | Focal adhesion (hsa04510) | Cell-matrix adhesion |

### Shared Pathway Analysis

**Convergent pathways** (>=2 candidate genes):
- TGF-beta signaling pathway: FBN1, TGFBR1, TGFBR2, SMAD3
- ECM organization: FBN1, COL3A1

**Interpretation**: Candidate genes converge on TGF-beta signaling and extracellular matrix pathways, consistent with connective tissue disorder etiology.

### Protein-Protein Interactions (IntAct)

| Gene | Direct Interactors | Notable Partners |
|------|-------------------|------------------|
| FBN1 | 42 | LTBP1, TGFB1, ADAMTS10 |
| TGFBR1 | 68 | TGFBR2, SMAD2, SMAD3 |

*Source: KEGG, IntAct, Reactome*
```

### Phase 4: Variant Interpretation Output

```markdown
## 4. Variant Interpretation

### 4.1 Variant: FBN1 c.4621G>A (p.Glu1541Lys)

| Property | Value | Interpretation |
|----------|-------|----------------|
| Gene | FBN1 | Marfan syndrome gene |
| Consequence | Missense | Amino acid change |
| ClinVar | VUS | Uncertain significance |
| gnomAD AF | 0.000004 | Ultra-rare (PM2) |

### 4.2 Computational Predictions

| Predictor | Score | Classification | ACMG Support |
|-----------|-------|----------------|--------------|
| **AlphaMissense** | 0.78 | Pathogenic | PP3 (strong) |
| **CADD PHRED** | 28.5 | Top 0.1% deleterious | PP3 |
| **EVE** | 0.72 | Likely pathogenic | PP3 |

**Consensus**: 3/3 predictors concordant damaging -> **Strong PP3 support**

*Source: AlphaMissense, CADD API, EVE via Ensembl VEP*

### 4.3 ACMG Evidence Summary

| Criterion | Evidence | Strength |
|-----------|----------|----------|
| PM2 | Absent from gnomAD (AF < 0.00001) | Moderate |
| PP3 | AlphaMissense + CADD + EVE concordant | Supporting (strong) |
| PP4 | Phenotype highly specific for Marfan | Supporting |
| PS4 | Multiple affected family members | Strong |

**Preliminary Classification**: Likely Pathogenic (1 Strong + 1 Moderate + 2 Supporting)

*Source: ClinVar, gnomAD, AlphaMissense, CADD, EVE*
```

### Phase 5: Structure Analysis Output

```markdown
## 5. Structural Analysis

### 5.1 Structure Prediction

**Method**: AlphaFold2 via NVIDIA NIM
**Protein**: Fibrillin-1 (FBN1)
**Sequence Length**: 2,871 amino acids

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Mean pLDDT | 85.3 | High confidence overall |
| Variant position pLDDT | 92.1 | Very high confidence |
| Nearby domain | cbEGF-like domain 23 | Calcium-binding |

### 5.2 Variant Location Analysis

**Variant**: p.Glu1541Lys

| Feature | Finding | Impact |
|---------|---------|--------|
| Domain | cbEGF-like domain 23 | Critical for calcium binding |
| Conservation | 100% conserved across vertebrates | High constraint |
| Structural role | Calcium coordination residue | Likely destabilizing |
| Nearby pathogenic | p.Glu1540Lys (Pathogenic) | Adjacent residue |

### 5.3 Structural Interpretation

The variant p.Glu1541Lys:
1. **Located in cbEGF domain** - Critical for fibrillin-1 function
2. **Glutamate to Lysine** - Charge reversal (negative to positive)
3. **Calcium binding** - Glutamate at this position coordinates Ca2+
4. **Adjacent pathogenic variant** - p.Glu1540Lys is classified Pathogenic

**Structural Evidence**: Strong support for pathogenicity (PM1 - critical domain)

*Source: NVIDIA NIM via `NvidiaNIM_alphafold2`, InterPro*
```

### Phase 6: Literature Evidence Output

```markdown
## 6. Literature Evidence

### 6.1 Key Published Studies

| PMID | Title | Year | Citations | Relevance |
|------|-------|------|-----------|-----------|
| 32123456 | FBN1 variants in Marfan syndrome... | 2023 | 45 | Direct |
| 31987654 | TGF-beta signaling in connective... | 2022 | 89 | Pathway |
| 30876543 | Novel diagnostic criteria for... | 2021 | 156 | Diagnostic |

### 6.2 Recent Preprints (Not Yet Peer-Reviewed)

| Source | Title | Posted | Relevance |
|--------|-------|--------|-----------|
| BioRxiv | Novel FBN1 splice variant causes... | 2024-01 | Case report |
| MedRxiv | Machine learning for Marfan... | 2024-02 | Diagnostic |

**Note**: Preprints have not undergone peer review. Use with caution.

### 6.3 Evidence Summary

| Evidence Type | Count | Strength |
|---------------|-------|----------|
| Case reports | 12 | Supporting |
| Functional studies | 5 | Strong |
| Clinical trials | 2 | Strong |
| Reviews | 8 | Context |

*Source: PubMed, BioRxiv, OpenAlex*
```

---

## Additional Output Files

### Gene Panel CSV

**File**: `[PATIENT_ID]_gene_panel.csv`

```csv
priority,gene,diseases,evidence_level,pLI,expression,clingen_classification,actionable
1,FBN1,Marfan syndrome,Definitive,1.00,"Heart, aorta",Definitive,Yes
2,TGFBR1,Loeys-Dietz 1,Definitive,0.98,Ubiquitous,Definitive,Yes
3,TGFBR2,Loeys-Dietz 2,Definitive,0.99,Ubiquitous,Definitive,Yes
4,COL3A1,EDS vascular,Definitive,1.00,Connective tissue,Definitive,Yes
5,CBS,Homocystinuria,Definitive,0.00,Liver,Definitive,No
```

### Variant Interpretation CSV

**File**: `[PATIENT_ID]_variant_interpretation.csv`

```csv
gene,variant,consequence,clinvar,gnomad_af,cadd,alphamissense,eve,acmg_class
FBN1,c.4621G>A,Missense,VUS,0.000004,28.5,0.78,0.72,Likely Pathogenic
```
