# Rare Disease Diagnosis - Examples

## Example 1: Connective Tissue Disorder

### User Query
"23-year-old male with tall stature (6'5"), long fingers, joint hypermobility, and recent echo showing aortic root dilation 4.2cm. Father had similar build and died suddenly at age 45. What could this be?"

### Expected Output

```markdown
# Rare Disease Diagnostic Report

**Patient ID**: Example-001 | **Date**: 2026-02-04

---

## Executive Summary

This patient presents with a classic phenotype highly suggestive of **Marfan syndrome** (★★★). Key findings include tall stature, arachnodactyly, joint hypermobility, and aortic root dilation with a positive family history of sudden death. The phenotype match is 89% for Marfan syndrome. **Immediate FBN1 genetic testing is recommended**, along with urgent cardiology referral given the aortic dilation and family history of sudden death.

---

## 1. Phenotype Analysis

### 1.1 Standardized HPO Terms

| Clinical Feature | HPO Term | HPO ID | Category |
|------------------|----------|--------|----------|
| Tall stature (6'5") | Tall stature | HP:0000098 | Core |
| Long fingers | Arachnodactyly | HP:0001166 | Core |
| Joint hypermobility | Joint hypermobility | HP:0001382 | Core |
| Aortic root dilation | Aortic root aneurysm | HP:0002616 | Core |
| Family history of sudden death | Sudden cardiac death | HP:0001645 | Family |

**Total HPO Terms**: 5
**Age of Onset**: Childhood (stature)
**Family History**: Father deceased age 45, sudden death, similar phenotype
**Suspected Inheritance**: Autosomal dominant

*Source: HPO via `HPO_search_terms`*

---

## 2. Differential Diagnosis

### 2.1 Ranked Candidate Diseases

| Rank | Disease | ORPHA | OMIM | Match | Inheritance | Genes |
|------|---------|-------|------|-------|-------------|-------|
| 1 | Marfan syndrome | 558 | 154700 | 89% ★★★ | AD | FBN1 |
| 2 | Loeys-Dietz syndrome | 60030 | 609192 | 72% ★★☆ | AD | TGFBR1, TGFBR2, SMAD3 |
| 3 | Vascular EDS | 286 | 130050 | 58% ★☆☆ | AD | COL3A1 |
| 4 | Familial TAAD | 91387 | 607086 | 52% ★☆☆ | AD | ACTA2, MYH11 |
| 5 | Homocystinuria | 394 | 236200 | 45% ☆☆☆ | AR | CBS |

### 2.2 Disease Details

#### 1. Marfan Syndrome (★★★)

**ORPHA**: 558 | **OMIM**: 154700 | **Prevalence**: 1-5/10,000

**Phenotype Comparison**:
| Patient Feature | Marfan Feature | Frequency | Match |
|-----------------|----------------|-----------|-------|
| Tall stature | Tall stature | 95% | ✓ |
| Arachnodactyly | Arachnodactyly | 90% | ✓ |
| Joint hypermobility | Joint hypermobility | 85% | ✓ |
| Aortic root dilation | Aortic root dilation | 80% | ✓ |
| Family sudden death | Aortic dissection | 30% | ✓ |
| Ectopia lentis | Ectopia lentis | 60% | Not assessed |

**Ghent Criteria Assessment**:
- Aortic root Z-score: Likely ≥2 (4.2cm at age 23)
- Systemic score: ≥7 points (tall, arachnodactyly, joint hypermobility)
- FBN1 mutation: Pending testing
- **Clinical diagnosis likely met even without genetic testing**

**Gene**: FBN1 (fibrillin-1)
- ClinGen validity: Definitive
- Inheritance: AD (25% de novo)

*Source: Orphanet via `Orphanet_558`, OMIM via `OMIM_get_entry`*

#### 2. Loeys-Dietz Syndrome (★★☆)

**ORPHA**: 60030 | **OMIM**: 609192

**Key Distinguishing Features** (not present in patient):
- Hypertelorism (wide-set eyes)
- Bifid uvula or cleft palate
- Arterial tortuosity
- Translucent skin

**Consider if**: FBN1 negative AND craniofacial features present

*Source: Orphanet, OMIM*

---

## 3. Recommended Gene Panel

### 3.1 Prioritized Genes

| Priority | Gene | Disease | Evidence | pLI | Expression |
|----------|------|---------|----------|-----|------------|
| ★★★ | FBN1 | Marfan | Definitive | 1.00 | Aorta, heart |
| ★★☆ | TGFBR1 | LDS1 | Definitive | 0.98 | Ubiquitous |
| ★★☆ | TGFBR2 | LDS2 | Definitive | 0.99 | Ubiquitous |
| ★★☆ | SMAD3 | LDS3 | Definitive | 0.89 | Ubiquitous |
| ★☆☆ | COL3A1 | vEDS | Definitive | 1.00 | Connective |
| ★☆☆ | ACTA2 | FTAAD | Definitive | 0.97 | Smooth muscle |

### 3.2 Testing Strategy

**Recommended Approach**:
1. **Immediate**: FBN1 sequencing + deletion/duplication analysis
   - Highest pre-test probability
   - Expected turnaround: 2-4 weeks
   
2. **If FBN1 negative**: Aortopathy gene panel
   - TGFBR1, TGFBR2, SMAD3, COL3A1, ACTA2, MYH11
   
3. **If panel negative**: Consider WES with phenotype-guided analysis

*Source: ClinGen gene-disease validity, GTEx expression*

---

## 4. Variant Interpretation

**No variants provided for interpretation.**

Genetic testing recommended - see Section 3.

---

## 5. Structural Analysis

**Not applicable** - No VUS requiring structural analysis.

---

## 6. Clinical Recommendations

### 6.1 Diagnostic Next Steps

| Priority | Action | Rationale | Timeline |
|----------|--------|-----------|----------|
| 1 | **Urgent cardiology referral** | Aortic root 4.2cm + family history | This week |
| 2 | **FBN1 genetic testing** | Confirm diagnosis, family cascade | Order now |
| 3 | **Ophthalmology exam** | Ectopia lentis screening | Within 1 month |
| 4 | **Full skeletal assessment** | Document systemic features | Within 1 month |

### 6.2 Specialist Referrals

- **Cardiology** (URGENT): Aortic surveillance, beta-blocker consideration
- **Medical Genetics**: Genetic counseling, testing coordination
- **Ophthalmology**: Slit-lamp exam for ectopia lentis
- **Orthopedics**: Scoliosis screening if indicated

### 6.3 Family Screening

**High priority given family history**:
- Father deceased (autopsy results if available)
- Any siblings should be offered:
  - Clinical screening (echo, skeletal exam)
  - Genetic testing once proband result available
- Extended family (paternal) should be informed

### 6.4 Urgent Considerations

⚠️ **URGENT**: Given aortic root dilation AND family history of sudden death:
- Avoid competitive sports and isometric exercise
- Discuss blood pressure management
- Review for aortic dissection symptoms
- Cardiology referral within 1 week

---

## 7. Data Gaps & Limitations

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No ophthalmology exam | Cannot assess ectopia lentis | Schedule exam |
| Echo Z-score not calculated | Need BSA-adjusted measurement | Request from cardiology |
| Father's autopsy unknown | Cannot confirm aortic dissection | Obtain records |
| No genetic testing yet | Diagnosis presumptive | Order FBN1 testing |

---

## 8. Data Sources

| Tool | Query | Data Retrieved |
|------|-------|----------------|
| HPO_search_terms | Patient symptoms | HPO term mapping |
| Orphanet_558 | Marfan syndrome | Disease details |
| OMIM_get_entry | 154700 | Clinical synopsis |
| ClinGen | FBN1-Marfan | Gene-disease validity |
| GTEx | FBN1 expression | Tissue expression |
```

---

## Example 2: Pediatric Neurological Phenotype

### User Query
"5-year-old with developmental delay, hypotonia, seizures starting at age 2, and MRI showing periventricular white matter changes. WES found a VUS: GFAP c.1186C>T (p.Arg396Cys). What's the diagnosis?"

### Expected Output (Key Sections)

```markdown
# Rare Disease Diagnostic Report

**Patient ID**: Example-002 | **Date**: 2026-02-04

---

## Executive Summary

This patient's phenotype and VUS in GFAP are highly consistent with **Alexander disease** (★★★). The combination of developmental delay, hypotonia, seizures, and frontal-predominant white matter changes in a young child matches infantile/juvenile Alexander disease. The GFAP p.Arg396Cys variant affects a highly conserved residue in the rod domain. **Structural analysis and segregation studies are recommended to support reclassification of this VUS to Likely Pathogenic.**

---

## 1. Phenotype Analysis

| Clinical Feature | HPO Term | HPO ID | Category |
|------------------|----------|--------|----------|
| Developmental delay | Global developmental delay | HP:0001263 | Core |
| Hypotonia | Muscular hypotonia | HP:0001252 | Core |
| Seizures (age 2) | Seizures | HP:0001250 | Core |
| White matter changes | Leukoencephalopathy | HP:0002352 | Core |
| Frontal predominance | Frontal white matter abnormality | HP:0012762 | Specific |

---

## 2. Differential Diagnosis

| Rank | Disease | ORPHA | Match | Key Features |
|------|---------|-------|-------|--------------|
| 1 | Alexander disease | 58 | 92% ★★★ | GFAP, frontal WM, macrocephaly |
| 2 | Vanishing white matter | 135 | 68% ★★☆ | eIF2B genes, progressive |
| 3 | Canavan disease | 141 | 55% ★☆☆ | ASPA, NAA elevated |
| 4 | Metachromatic leukodystrophy | 512 | 48% ★☆☆ | ARSA, progressive |

### Alexander Disease Details

**Diagnostic Criteria**:
1. Clinical: Macrocephaly, seizures, developmental delay ✓
2. MRI: Frontal-predominant white matter changes ✓
3. Genetic: Heterozygous GFAP variant ✓ (VUS)

*Source: Orphanet via `Orphanet_58`*

---

## 4. Variant Interpretation

### Variant: GFAP c.1186C>T (p.Arg396Cys)

| Property | Value | Interpretation |
|----------|-------|----------------|
| Gene | GFAP | Alexander disease gene |
| Consequence | Missense | Amino acid change |
| ClinVar | VUS | 1 submission |
| gnomAD AF | 0.0000032 | Absent (PM2) |
| CADD | 29.2 | Deleterious |
| REVEL | 0.89 | Likely damaging |

### ACMG Evidence

| Criterion | Evidence | Strength |
|-----------|----------|----------|
| PM2 | Absent from gnomAD | Moderate |
| PP3 | CADD=29.2, REVEL=0.89 | Supporting |
| PP4 | Phenotype specific for Alexander | Supporting |
| PM1 | Located in rod domain (critical) | Moderate |

**Current Classification**: VUS (2 Moderate + 2 Supporting)
**With segregation (PS2) or functional data**: Would become Likely Pathogenic

---

## 5. Structural Analysis

### 5.1 Structure Prediction

**Method**: AlphaFold2 via NVIDIA NIM
**Protein**: Glial fibrillary acidic protein (GFAP)
**Sequence Length**: 432 amino acids

| Metric | Value |
|--------|-------|
| Mean pLDDT | 78.4 |
| Position 396 pLDDT | 89.2 (high confidence) |
| Domain | Rod domain, coil 2B |

### 5.2 Variant Impact

**p.Arg396Cys Analysis**:

| Feature | Finding |
|---------|---------|
| Location | Rod domain (coiled-coil) |
| Wild-type | Arginine (positive, polar) |
| Mutant | Cysteine (neutral, potential disulfide) |
| Conservation | 100% across vertebrates |
| Nearby pathogenic | p.Arg398Trp (Pathogenic) |

**Structural Interpretation**:
- Arginine at position 396 participates in coiled-coil interactions
- Cysteine substitution disrupts ionic interactions
- Adjacent residue 398 has pathogenic variants
- **Strong structural support for pathogenicity**

*Source: NVIDIA NIM via `NvidiaNIM_alphafold2`, InterPro*

---

## 6. Clinical Recommendations

### Immediate Actions
1. **Clinical genetics consultation** - Discuss VUS implications
2. **Parental testing** - De novo status would upgrade variant (PS2)
3. **Neurology follow-up** - Seizure management, prognosis discussion

### Supporting Studies
- Obtain parental samples for GFAP c.1186C>T
- If not in parents → add PS2 (strong evidence) → Likely Pathogenic
```

---

## Example 3: Limited Data Scenario

### User Query
"6-month-old with severe hypotonia and feeding difficulties. No genetic testing done yet. Where do we start?"

### Expected Output (Key Sections)

```markdown
## Executive Summary

This infant presents with a non-specific phenotype (hypotonia + feeding difficulties) that could represent numerous conditions. Given the limited phenotypic information, **a broad approach is recommended**: either chromosomal microarray + trio WES, or a comprehensive neuromuscular panel. Additional clinical information (neuroimaging, EMG, metabolic workup) would help narrow the differential.

---

## 2. Differential Diagnosis

**Note**: With only 2 phenotypic features, differential diagnosis is broad.

### Top Categories to Consider

| Category | Examples | Key Tests |
|----------|----------|-----------|
| **SMA/Neuromuscular** | SMA type 1, CMD | SMN1 del/dup, CK |
| **Congenital myopathy** | RYR1, MTM1 | Muscle biopsy, EMG |
| **Chromosomal** | Prader-Willi, 1p36 del | CMA |
| **Metabolic** | Pompe, mitochondrial | GAA enzyme, lactate |
| **Syndromic** | Various | Dysmorphology exam |

### Priority Testing

| Test | Yield | Rationale |
|------|-------|-----------|
| Chromosomal microarray | 15-20% | Screen for CNVs |
| SMN1 deletion | 8-10% if SMA | Treatable if positive |
| Trio WES | 25-40% | Broad diagnostic screen |

---

## 3. Recommended Additional Workup

Before genetic testing, consider:

| Test | Purpose | Urgency |
|------|---------|---------|
| CK level | Myopathy vs neuropathy | High |
| Lactate | Metabolic disease | Medium |
| Brain MRI | Structural vs metabolic | Medium |
| EMG/NCS | Localize lesion | Medium |
| Dysmorphology exam | Syndromic features | High |

---

## 6. Recommendations

### Immediate
1. **Genetics referral** for comprehensive evaluation
2. **CK and metabolic labs** as first-line screening
3. **SMN1 testing** - treatable condition, high impact

### Diagnostic Strategy Options

**Option A**: Targeted approach
- SMN1 → CMA → Neuromuscular panel → WES

**Option B**: Broad approach (recommended if resources allow)
- Trio WES + CMA concurrently

---

## 7. Data Gaps

| Gap | Impact | Action Needed |
|-----|--------|---------------|
| Limited phenotype | Broad differential | Detailed clinical exam |
| No neuroimaging | Cannot assess CNS | Order brain MRI |
| No metabolic studies | May miss treatable | Order basic metabolic |
| No family history | Cannot assess inheritance | Take detailed pedigree |

*Note: This case has significant diagnostic uncertainty due to limited phenotypic information.*
```
