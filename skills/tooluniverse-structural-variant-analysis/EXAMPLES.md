# Structural Variant Analysis - Examples

## Example 1: Large Deletion Disrupting Tumor Suppressor (NF1)

### User Query
"Interpret this deletion: chr17:31094927-31377677 (GRCh38), 283 kb deletion including NF1 gene. Patient has café-au-lait spots and neurofibromas."

### Expected Output

```markdown
# Structural Variant Analysis Report: NF1 Deletion

**Generated**: 2026-02-09 | **Analyst**: ToolUniverse SV Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Deletion (heterozygous) |
| **Coordinates** | chr17:31094927-31377677 (GRCh38) |
| **Size** | 283 kb |
| **Gene Content** | 1 gene fully contained (NF1), 0 partially disrupted |
| **Classification** | **PATHOGENIC** ★★★ |
| **Pathogenicity Score** | 9.5 / 10 |
| **Confidence** | High (multiple lines of strong evidence) |
| **Key Finding** | Complete deletion of NF1, established haploinsufficient tumor suppressor |

**Clinical Action Required**: Genetic counseling, cascade family testing, neurofibromatosis type 1 surveillance protocol

---

## 1. SV Identity & Classification

| Property | Value |
|----------|-------|
| **SV Type** | Deletion (loss) |
| **Chromosome** | 17 |
| **Start** | 31,094,927 |
| **End** | 31,377,677 |
| **Size** | 282,750 bp (283 kb) |
| **Build** | GRCh38/hg38 |
| **Breakpoint Precision** | ±5 kb (array CGH resolution) |
| **Inheritance** | Unknown (testing recommended for parents) |
| **Detection Method** | Chromosomal microarray |

**SV Notation**: arr[GRCh38] 17q11.2(31094927_31377677)x1

*Coordinates validated against GRCh38*

---

## 2. Gene Content Analysis

### 2.1 Fully Contained Genes (Complete Dosage Effect)

| Gene | Start | End | Size | Function | Disease Association |
|------|-------|-----|------|----------|---------------------|
| **NF1** | 31,094,927 | 31,377,677 | 283 kb | RAS GTPase-activating protein | Neurofibromatosis type 1 (AD) |

**Gene Details - NF1**:
- **Full Name**: Neurofibromin 1
- **Function**: Negative regulator of RAS signaling pathway; tumor suppressor
- **Critical Domains**:
  - GTPase-activating protein (GAP) domain
  - Sec14p domain
  - Pleckstrin homology domain
- **Expression**: Ubiquitous; highest in nervous system, adrenal gland
- **OMIM Gene**: #613113
- **OMIM Disease**: Neurofibromatosis type 1 (#162200)

**Molecular Consequence**: Complete deletion of NF1 gene → haploinsufficiency → loss of RAS-GAP activity → RAS pathway hyperactivation → tumor predisposition

*Sources: `Ensembl_lookup_gene`, `NCBIGene_search`, `OMIM_get_entry`*

### 2.2 Partially Disrupted Genes

**None** - Deletion breakpoints do not disrupt additional genes

### 2.3 Flanking Genes (Within 1 Mb)

| Gene | Distance | Direction | Regulatory Risk |
|------|----------|-----------|-----------------|
| SUZ12 | 800 kb | Centromeric | Low |
| ATAD5 | 650 kb | Telomeric | Low |

**Assessment**: No high-risk position effects expected. NF1 deletion fully explains phenotype.

---

## 3. Dosage Sensitivity Assessment

### 3.1 Haploinsufficient Genes (Critical for Deletions)

| Gene | ClinGen HI Score | pLI (gnomAD) | Inheritance | Disease Mechanism | Evidence |
|------|-----------------|--------------|-------------|-------------------|----------|
| **NF1** | **3 (Sufficient)** | 1.00 | Autosomal Dominant | Haploinsufficiency | ★★★ |

**ClinGen Dosage Sensitivity Details - NF1**:
- **Haploinsufficiency Score**: 3 (Sufficient evidence)
- **Evidence**:
  - Numerous whole-gene deletions reported in NF1 patients
  - Loss-of-function variants cause neurofibromatosis type 1
  - Tumor suppressor gene - one functional copy insufficient
- **Curation Date**: 2023-06-15
- **ISCA ID**: ISCA-37448

**pLI Score**: 1.00 (highest intolerance to loss-of-function)
- Indicates extreme constraint against heterozygous LoF
- Only 1.3 expected LoF variants in gnomAD vs 0 observed
- Confirms haploinsufficiency mechanism

**Gene-Disease Validity (ClinGen)**:
| Disease | Classification | MOI | Evidence |
|---------|----------------|-----|----------|
| Neurofibromatosis type 1 | **Definitive** | AD | ★★★ |

**Interpretation**: NF1 has the highest level of evidence for haploinsufficiency. Deletion of one copy is sufficient to cause neurofibromatosis type 1 with high penetrance (>95%).

*Sources: `ClinGen_search_dosage_sensitivity`, `ClinGen_search_gene_validity`, gnomAD*

### 3.2 Triplosensitive Genes

**Not applicable** - This is a deletion, not duplication. NF1 triplosensitivity is not established.

---

## 4. Population Frequency Context

### 4.1 ClinVar Matches (Known Pathogenic/Benign SVs)

**Search Strategy**: Queried ClinVar for overlapping deletions in chr17:31094927-31377677

| VCV ID | Classification | Size | Overlap | Genes | Review Status | Condition |
|--------|----------------|------|---------|-------|---------------|-----------|
| VCV000001621 | Pathogenic | 1.4 Mb | NF1 contained | NF1 + adjacent | ★★★★ Expert panel | Neurofibromatosis type 1 |
| VCV000145678 | Pathogenic | 350 kb | 100% NF1 | NF1 only | ★★★ Criteria provided | NF1 |
| VCV000234891 | Pathogenic | 180 kb | Exons 1-10 | NF1 partial | ★★ Single submitter | NF1 |

**Key Finding**: Multiple pathogenic NF1 deletions in ClinVar, ranging from partial gene deletions to larger microdeletions encompassing adjacent genes. All classified as pathogenic.

**ACMG Code**: **PS1** (Strong) - Multiple established pathogenic deletions encompass NF1

*Source: `ClinVar_search_variants`*

### 4.2 gnomAD SV Database

**Search Result**: No NF1 loss-of-function deletions found in gnomAD v4.0 (76,156 genomes)

**Interpretation**:
- Complete absence from large population database supports pathogenicity
- NF1 LoF variants extremely rare in general population (constraint score = 1.00)
- Consistent with high disease penetrance

**ACMG Code**: **PM2** (Moderate) - Absent from population databases

*Note: gnomAD queried via browser; NF1 LoF count = 0 in 152,312 alleles*

### 4.3 DECIPHER Patient Cases

**Query**: NF1 deletion cases in DECIPHER database

**Results**: 87 patients with NF1 deletions/disruptions

**Phenotype Frequency in DECIPHER NF1 Cohort (n=87)**:

| HPO Term | Phenotype | Frequency | Patient Match |
|----------|-----------|-----------|---------------|
| HP:0007565 | Multiple café-au-lait spots | 78/87 (90%) | ✓ **Yes** |
| HP:0009732 | Plexiform neurofibroma | 45/87 (52%) | ✓ **Yes** |
| HP:0009737 | Lisch nodules (iris hamartomas) | 56/87 (64%) | Not assessed |
| HP:0000252 | Microcephaly | 23/87 (26%) | Unknown |
| HP:0001250 | Seizures | 8/87 (9%) | No |
| HP:0001263 | Developmental delay | 34/87 (39%) | Unknown |

**Phenotype Match Analysis**:
- Patient presents with café-au-lait spots (90% in DECIPHER cohort) ✓
- Patient has neurofibromas (52% in cohort) ✓
- 2/2 assessed features match NF1 phenotype

**ACMG Code**: **PP4** (Supporting) - Patient phenotype highly specific for NF1-related disorder

*Source: `ClinGen_search_dosage_sensitivity` (accessed 2026-02-09)*

---

## 5. Pathogenicity Scoring

### 5.1 Quantitative Assessment (0-10 Scale)

| Component | Points Earned | Max Points | Weight | Rationale |
|-----------|--------------|------------|--------|-----------|
| **Gene Content** | 4.0 | 4 | 40% | Complete deletion of definitive HI gene (NF1) |
| **Dosage Sensitivity** | 3.0 | 3 | 30% | ClinGen HI score 3, pLI = 1.00, definitive gene-disease |
| **Population Frequency** | 2.0 | 2 | 20% | Absent from gnomAD, extremely constrained |
| **Clinical Evidence** | 0.5 | 1 | 10% | ClinVar pathogenic matches, phenotype consistent |

**Total Pathogenicity Score**: **9.5 / 10**

**Classification**: **Pathogenic** (★★★ High Confidence)

### 5.2 Score Breakdown Visualization

```
Gene Content:        ████████████████████████████████████████ 4.0/4
Dosage Sensitivity:  ████████████████████████████████████████ 3.0/3
Population Freq:     ████████████████████████████████████████ 2.0/2
Clinical Evidence:   ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0.5/1
                     ─────────────────────────────────────────
Total Score:         ████████████████████████████████████████ 9.5/10

Classification: PATHOGENIC ★★★
```

### 5.3 Key Drivers of Pathogenicity

1. **Complete deletion of NF1** - Established haploinsufficient tumor suppressor
2. **ClinGen definitive evidence** - HI score 3, gene-disease validity definitive
3. **Extreme LoF constraint** - pLI = 1.00, no LoF variants in 76k genomes
4. **Phenotype match** - Café-au-lait spots and neurofibromas diagnostic for NF1
5. **Population absence** - Not found in gnomAD or DGV

**Confidence Factors**:
- ✓ Gold-standard gene-disease curation (ClinGen definitive)
- ✓ Well-characterized molecular mechanism (RAS-GAP loss)
- ✓ >95% penetrance for NF1 features
- ✓ Phenotype present in patient

---

## 6. Literature & Clinical Evidence

### 6.1 Key Publications on NF1 Deletions

| Study | Design | Key Finding | PMID |
|-------|--------|-------------|------|
| Kehrer-Sawatzki et al., 2017 | Review (n=1,300) | Type-1 NF1 deletions (1.4 Mb) in 5-10% of NF1 patients | 28301757 |
| Pasmant et al., 2010 | Cohort (n=65) | Whole-gene NF1 deletions → more severe phenotype | 19862833 |
| Mautner et al., 2010 | Clinical series | NF1 microdeletions associated with earlier onset, more neurofibromas | 20513137 |
| Upadhyaya et al., 1998 | Molecular study | Identified recurrent deletion breakpoints (NF1-REP repeats) | 9806547 |

**Key Findings from Literature**:
- NF1 deletions account for 5-11% of all NF1 cases
- Type-1 deletions (1.4 Mb) mediated by nonallelic homologous recombination (NAHR) between NF1-REP repeats
- Patients with large deletions often have more severe phenotypes (earlier onset, more tumors)
- 100% penetrance for NF1 diagnostic criteria by adulthood

**ACMG Code**: **PS3_Supporting** - Well-established in literature that NF1 deletions cause NF1

*Source: `PubMed_search_articles` - query: "NF1 deletion neurofibromatosis"*

### 6.2 NF1 Molecular Mechanism (Functional Evidence)

**RAS-GAP Activity Loss**:
- NF1 encodes neurofibromin, which acts as a GTPase-activating protein (GAP) for RAS
- Neurofibromin converts active RAS-GTP → inactive RAS-GDP
- Loss of one NF1 copy → reduced RAS-GAP activity → RAS pathway hyperactivation
- Consequence: Increased cell proliferation, tumor formation, learning deficits

**Evidence Strength**: ★★★ (Definitive) - Molecular mechanism fully characterized

### 6.3 Genotype-Phenotype Correlation

**Whole-Gene Deletions vs Point Mutations**:
| Feature | Large Deletions | Point Mutations | Difference |
|---------|----------------|-----------------|------------|
| Café-au-lait spots | 95% | 99% | Similar |
| Neurofibromas | 100% | 85% | More frequent |
| Facial dysmorphism | 40% | 10% | More common in deletions |
| Cognitive impairment | 50% | 30% | Increased risk |

**Patient Implications**: Deletion patients may have more severe manifestations compared to point mutation carriers.

---

## 7. ACMG-Adapted Classification

### 7.1 Evidence Codes Applied

**Pathogenic Evidence**:

| Code | Strength | Rationale |
|------|----------|-----------|
| **PVS1** | Very Strong | Complete deletion of established haploinsufficient gene (NF1) causing loss of function |
| **PS1** | Strong | Same region as multiple known pathogenic NF1 deletions in ClinVar |
| **PM2** | Moderate | Absent from gnomAD (76,156 genomes) and DGV; extreme LoF constraint (pLI=1.0) |
| **PP4** | Supporting | Patient's phenotype (café-au-lait spots, neurofibromas) highly specific for NF1 |

**Benign Evidence**: None

### 7.2 Evidence Summary

| Category | Evidence Codes | Count |
|----------|----------------|-------|
| **Pathogenic** | PVS1, PS1, PM2, PP4 | 4 codes |
| Very Strong | PVS1 | 1 |
| Strong | PS1 | 1 |
| Moderate | PM2 | 1 |
| Supporting | PP4 | 1 |
| **Benign** | None | 0 |

### 7.3 Classification: **PATHOGENIC** ★★★

**ACMG Criteria Met**:
- 1 Very Strong (PVS1) + 1 Strong (PS1) + 1 Moderate (PM2) + 1 Supporting (PP4)
- Meets criteria: "1 Very Strong + 1 Strong" = **Pathogenic**

**Rationale**:
Complete deletion of NF1, an established haploinsufficient tumor suppressor with definitive gene-disease validity. Multiple independent lines of strong evidence support pathogenic classification. Patient phenotype consistent with neurofibromatosis type 1.

**Confidence**: ★★★ (High)
- ClinGen definitive gene-disease curation
- Well-established molecular mechanism
- Phenotype matches expected
- No conflicting evidence

### 7.4 Classification Certainty Factors

**Strengths**:
- ✓ Gold-standard curation (ClinGen HI score 3, Definitive validity)
- ✓ Complete gene deletion (unambiguous loss of function)
- ✓ Well-characterized disease (>5,000 NF1 patients documented)
- ✓ Phenotype present and specific
- ✓ No tolerance for LoF in population (pLI = 1.00)

**Limitations**:
- Breakpoint precision limited to ±5 kb (array resolution)
- Inheritance unknown (recommend parental testing)
- Penetrance incomplete for some features (e.g., optic glioma ~15%)

**Certainty**: Very high - no significant limitations affecting classification

---

## 8. Clinical Recommendations

### 8.1 For Affected Individual

| Category | Recommendation | Urgency |
|----------|----------------|---------|
| **Diagnosis Confirmation** | Molecular diagnosis confirmed; no additional testing needed | N/A |
| **Genetic Counseling** | Comprehensive genetic counseling regarding NF1, inheritance, management | **Immediate** |
| **Surveillance Protocol** | Initiate NF1 surveillance per NIH criteria (annual exams) | **Immediate** |
| **Ophthalmology** | Annual eye exams (risk of optic glioma, especially in children) | **Immediate** |
| **Neurology** | Assess for learning disabilities, ADHD; MRI if neurological symptoms | Within 3 months |
| **Dermatology** | Monitor café-au-lait spots and neurofibromas; document baseline | Within 3 months |
| **Cardiovascular** | Blood pressure monitoring (risk of renovascular hypertension) | Annual |
| **Oncology Referral** | Low-threshold imaging for any masses; risk of malignant peripheral nerve sheath tumors (MPNST) | As needed |

**NIH Diagnostic Criteria for NF1** (≥2 required):
1. ≥6 café-au-lait macules (>5mm prepubertal, >15mm postpubertal) ✓
2. ≥2 neurofibromas or 1 plexiform neurofibroma ✓
3. Freckling in axillary or inguinal regions
4. Optic glioma
5. ≥2 Lisch nodules (iris hamartomas)
6. Distinctive osseous lesion (sphenoid dysplasia, tibial pseudarthrosis)
7. First-degree relative with NF1

**Patient Status**: Meets 2/7 criteria (café-au-lait spots, neurofibromas); molecular diagnosis confirms NF1.

### 8.2 For Family Members

| Relationship | Recommendation | Priority |
|--------------|----------------|----------|
| **Parents** | Test for NF1 deletion to determine if de novo or inherited | **High** |
| **Siblings** | If parent positive, offer predictive testing; if de novo, low risk | Medium |
| **Children (current/future)** | 50% risk if inherited; 50% if patient is parent; prenatal/preimplantation testing available | High |

**Inheritance Pattern**:
- Autosomal dominant
- 50% risk to offspring if patient has children
- 50% of cases are de novo (new mutation)
- Recommend parental testing to determine if inherited or de novo

**Recurrence Risk**:
- If de novo: Low recurrence risk for siblings (<1% due to germline mosaicism)
- If inherited from parent: 50% for each sibling

### 8.3 Reproductive Considerations

| Option | Details |
|--------|---------|
| **Prenatal Testing** | Available via amniocentesis or CVS (microarray or targeted testing) |
| **Preimplantation Genetic Testing (PGT)** | Available via IVF with PGT-M for at-risk embryo selection |
| **Genetic Counseling** | Discuss reproductive options, natural history, variable expressivity |

**Key Points**:
- Variable expressivity: Some NF1 patients mildly affected, others severely
- Anticipation does NOT occur (severity not increased in next generation)
- Prenatal ultrasound cannot reliably detect NF1

---

## 9. Limitations & Uncertainties

### 9.1 Technical Limitations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Breakpoint Precision** | ±5 kb uncertainty in exact breakpoint location | Not clinically significant; NF1 fully deleted |
| **Array Resolution** | Cannot detect balanced rearrangements or inversions | Unlikely given clear deletion; confirmatory FISH/MLPA if needed |
| **Mosaicism** | Cannot rule out low-level mosaicism | If clinical features mild, consider tissue-specific testing |

### 9.2 Clinical Uncertainties

| Factor | Uncertainty | Plan |
|--------|-------------|------|
| **Phenotype Severity** | Cannot predict exact severity (variable expressivity) | Close surveillance; manage symptoms as they arise |
| **Malignancy Risk** | 8-13% lifetime risk of malignant peripheral nerve sheath tumor (MPNST) | Low-threshold imaging for rapidly growing or painful neurofibromas |
| **Cognitive Impact** | 30-50% have learning disabilities; cannot predict for individual | Neuropsychological testing; early educational interventions |
| **Inheritance** | Unknown if de novo or inherited until parents tested | Parental testing to inform recurrence risk |

### 9.3 Knowledge Gaps

- **Genotype-phenotype correlation**: Deletion size does not perfectly predict severity
- **Modifier genes**: Other genetic factors may influence phenotype
- **Environmental factors**: Unknown modifiers of disease expression

### 9.4 Classification Certainty

**Overall Certainty**: Very High ★★★

No significant uncertainties affect the Pathogenic classification. NF1 haploinsufficiency is definitive, mechanism well-understood, and patient phenotype consistent.

---

## 10. Data Sources & Tool Usage

### 10.1 Genomic Databases

| Database | Tool | Query | Result |
|----------|------|-------|--------|
| Ensembl | `Ensembl_lookup_gene` | NF1 gene coordinates | chr17:31094927-31377677 confirmed |
| NCBI Gene | `NCBIGene_search` | NF1 function | GeneID: 4763, RAS-GAP function confirmed |
| ClinVar | `ClinVar_search_variants` | chr17:31094927-31377677 DEL | 3 pathogenic matches found |
| gnomAD | Browser query | NF1 LoF variants | 0 LoF in 152,312 alleles; pLI=1.00 |

### 10.2 Clinical Databases

| Database | Tool | Query | Result |
|----------|------|-------|--------|
| ClinGen | `ClinGen_search_dosage_sensitivity` | NF1 | HI score 3 (Sufficient evidence) |
| ClinGen | `ClinGen_search_gene_validity` | NF1 - Neurofibromatosis 1 | Definitive |
| OMIM | `OMIM_search` | NF1 | Gene #613113, Disease #162200 |
| OMIM | `OMIM_get_entry` | 162200 | Neurofibromatosis type 1 details |
| DECIPHER | `ClinGen_search_dosage_sensitivity` | NF1 deletions | 87 patients, phenotype frequencies |
| DisGeNET | `DisGeNET_search_gene` | NF1 | Score 0.8 for neurofibromatosis |

### 10.3 Literature

| Database | Tool | Query | Results |
|----------|------|-------|---------|
| PubMed | `PubMed_search_articles` | "NF1 deletion neurofibromatosis" | 245 articles, top 20 reviewed |
| PubMed | `PubMed_search_articles` | "NF1 haploinsufficiency mechanism" | 78 articles |

### 10.4 Quality Control

- ✓ All genes in SV region annotated
- ✓ ClinGen dosage scores retrieved
- ✓ Population frequency assessed (gnomAD, ClinVar)
- ✓ Literature search completed (PubMed, DECIPHER)
- ✓ All ACMG codes applied with rationale
- ✓ Evidence grading assigned
- ✓ Clinical recommendations provided

---

**Report Completed**: 2026-02-09
**Analyst**: ToolUniverse Structural Variant Analysis Skill
**Classification**: PATHOGENIC ★★★
**Clinical Action**: Immediate genetic counseling and NF1 surveillance protocol
```

---

## Example 2: Duplication of Dosage-Sensitive Gene (MECP2)

### User Query
"Analyze this duplication: chrX:154021599-154137217 (GRCh38), 115 kb duplication including MECP2. Male patient with intellectual disability, seizures, and regression."

### Expected Output (Key Sections)

```markdown
# SV Analysis Report: MECP2 Duplication

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Duplication (hemizygous in male) |
| **Coordinates** | chrX:154021599-154137217 (GRCh38) |
| **Size** | 115 kb |
| **Gene Content** | MECP2, IRAK1 (fully contained) |
| **Classification** | **PATHOGENIC** ★★★ |
| **Pathogenicity Score** | 9.0 / 10 |
| **Key Finding** | MECP2 duplication syndrome in hemizygous male |

---

## 3. Dosage Sensitivity Assessment

### 3.1 Triplosensitive Genes (Critical for Duplications)

| Gene | ClinGen TS Score | pLI | Disease | Mechanism | Evidence |
|------|-----------------|-----|---------|-----------|----------|
| **MECP2** | **3 (Sufficient)** | 0.96 | MECP2 duplication syndrome | Triplosensitivity | ★★★ |
| IRAK1 | 0 (No evidence) | 0.31 | None established | N/A | ★☆☆ |

**MECP2 Dosage Sensitivity**:
- **Triplosensitivity Score**: 3 (Definitive evidence)
- **Mechanism**: MECP2 encodes methyl-CpG-binding protein 2, critical for neuronal function
- **Dosage Effect**: Extra copy in males → overexpression → severe neurodevelopmental disorder
- **Gene-Disease Validity**: Definitive (ClinGen)

**Why Triplosensitivity Matters**:
- MECP2 expression is tightly regulated; dosage-critical
- Loss of function → Rett syndrome (females)
- Gain of function → MECP2 duplication syndrome (males)
- Goldilocks gene: "just right" dosage required

*Sources: `ClinGen_search_dosage_sensitivity`, `ClinGen_search_gene_validity`*

---

## 5. Pathogenicity Scoring

**Total Score**: 9.0 / 10

| Component | Points | Rationale |
|-----------|--------|-----------|
| Gene Content | 4.0/4 | MECP2 TS score 3 (definitive triplosensitive) |
| Dosage Sensitivity | 3.0/3 | Established triplosensitivity with clear mechanism |
| Population Frequency | 2.0/2 | Absent from gnomAD; not found in healthy males |
| Clinical Evidence | 0.0/1 | Phenotype consistent (pending detailed assessment) |

**Classification**: PATHOGENIC (★★★)

---

## 7. ACMG Classification

**Pathogenic Evidence**:
| Code | Strength | Rationale |
|------|----------|-----------|
| **PVS1** | Very Strong | Complete duplication of triplosensitive gene (MECP2) in hemizygous male |
| **PS1** | Strong | Multiple pathogenic MECP2 duplications in ClinVar |
| **PM2** | Moderate | Absent from male population in gnomAD |
| **PP4** | Supporting | Male with ID, seizures, regression typical for MECP2 duplication syndrome |

**Classification**: **PATHOGENIC** (PVS1 + PS1 meets criteria)

**Sex-Specific Considerations**:
- Males hemizygous (one X chromosome) → more severe phenotype
- Females heterozygous → may be asymptomatic or mildly affected (X-inactivation)
- This patient is male → full MECP2 duplication syndrome expected

---

## 8. Clinical Recommendations

**For Patient** (Male with MECP2 duplication):
- Diagnosis: MECP2 duplication syndrome confirmed
- Neurology: Manage seizures aggressively (often drug-resistant)
- Pulmonology: Monitor for respiratory infections (high risk)
- Gastroenterology: Assess for constipation, GERD
- Infectious disease: Increased susceptibility to infections
- Physical therapy: Address hypotonia, motor delays
- Special education: Severe-to-profound intellectual disability expected

**For Family**:
- Mother: MUST be tested - likely carrier (90% inherited maternally)
- If mother is carrier: 50% risk to male offspring, variable risk to females
- If mother is NOT carrier: De novo in patient; low recurrence risk
- Future pregnancies: Prenatal testing available

**Prognosis**:
- Life expectancy: Often reduced (median survival unclear; serious infections common)
- Developmental: Severe ID, most non-verbal
- Medical complexity: High (seizures, infections, GI issues)
```

---

## Example 3: Balanced Translocation (No Gene Disruption)

### User Query
"Interpret balanced translocation t(2;11)(p16.3;q23.3) in healthy adult with recurrent miscarriages. Breakpoints: chr2:50,234,567 and chr11:118,345,234. No genes disrupted."

### Expected Output (Key Sections)

```markdown
# SV Analysis Report: Balanced Translocation t(2;11)

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Balanced reciprocal translocation |
| **Breakpoints** | chr2:50,234,567; chr11:118,345,234 |
| **Size** | N/A (balanced rearrangement) |
| **Gene Content** | 0 genes disrupted |
| **Classification** | **LIKELY BENIGN** ★★☆ (for carrier health) |
| **Reproductive Risk** | High (unbalanced offspring) |
| **Key Finding** | Balanced translocation, no dosage imbalance, explains recurrent pregnancy loss |

---

## 2. Gene Content Analysis

### 2.1 Breakpoint Analysis

**Chromosome 2 Breakpoint** (2p16.3 - 50,234,567):
- **Location**: Intergenic region
- **Nearest genes**:
  - NRXN1 (500 kb downstream) - neurexin gene
  - Regulatory desert region
- **No gene disruption**

**Chromosome 11 Breakpoint** (11q23.3 - 118,345,234):
- **Location**: Intergenic region
- **Nearest genes**:
  - LARGE1 (350 kb upstream) - glycosyltransferase
  - No coding genes within 1 Mb
- **No gene disruption**

**Critical Finding**: Both breakpoints fall in gene-desert regions. No protein-coding genes are disrupted.

---

## 3. Dosage Sensitivity Assessment

**N/A** - Balanced translocation maintains normal gene dosage (2 copies of all genes).

---

## 5. Pathogenicity Scoring

**Total Score**: 2.0 / 10 (Likely Benign range)

| Component | Points | Rationale |
|-----------|--------|-----------|
| Gene Content | 0.0/4 | No genes disrupted or affected by dosage |
| Dosage Sensitivity | 0.0/3 | Balanced rearrangement; normal copy number |
| Population Frequency | 1.0/2 | Balanced translocations occur in ~1/500 population |
| Clinical Evidence | 1.0/1 | Carrier is healthy; no phenotype |

**Classification for Carrier Health**: **LIKELY BENIGN** (★★☆)

**Note**: Although benign for the carrier, this translocation poses HIGH REPRODUCTIVE RISK due to unbalanced segregation in offspring.

---

## 7. ACMG Classification

**For Carrier Phenotype**:

**Benign Evidence**:
| Code | Strength | Rationale |
|------|----------|-----------|
| **BP5** | Supporting | Carrier is healthy adult with no features of genetic disorder |
| **BP4** | Supporting | No genes disrupted; no predicted haploinsufficiency |

**Classification**: **LIKELY BENIGN** for carrier health ★★☆

**However - Reproductive Risk Assessment**:
- Balanced translocation carriers are typically healthy
- Risk for UNBALANCED offspring with duplications/deletions: 5-30%
- Explains recurrent miscarriages (likely due to unbalanced conceptions)

---

## 8. Clinical Recommendations

### 8.1 For Carrier (Patient)

| Category | Recommendation |
|----------|----------------|
| **Carrier Health** | No medical surveillance needed; translocation benign for carrier |
| **Genetic Counseling** | Comprehensive reproductive counseling **ESSENTIAL** |
| **Pregnancy Management** | Prenatal diagnosis (amniocentesis/CVS) recommended for ALL pregnancies |
| **Family Planning** | Consider preimplantation genetic testing (PGT-SR) via IVF |

### 8.2 Reproductive Risk Assessment

**Segregation Outcomes** (theoretical):
1. **Balanced (normal or translocation carrier)**: 50% - Healthy
2. **Unbalanced (partial trisomy/monosomy)**: 50% - Usually nonviable or severe

**Empiric Risks**:
- Miscarriage risk: 25-50% (higher than general population)
- Unbalanced live birth: 5-10% (varies by breakpoint locations)
- Balanced carrier offspring: ~25% (healthy like parent)
- Normal (non-carrier) offspring: ~25%

**Recommendations**:
1. **Prenatal Diagnosis**: Amniocentesis or CVS with karyotype + microarray
2. **Preimplantation Genetic Testing (PGT-SR)**: IVF with embryo testing
   - Test embryos for balanced vs unbalanced translocations
   - Transfer only balanced/normal embryos
   - Success rate: 40-60% per cycle
3. **Partner Testing**: Partner should have normal karyotype (already confirmed)

### 8.3 For Family Members

| Relationship | Recommendation |
|--------------|----------------|
| **Parents** | Karyotype testing to determine if inherited or de novo |
| **Siblings** | If parent positive → 50% risk; offer testing if planning pregnancy |
| **Children** | If patient has balanced carrier children → test before they reproduce |

**Inheritance Pattern**:
- If inherited: 50% of siblings may also be carriers
- If de novo: Low risk to siblings

---

## 9. Explanation of Recurrent Miscarriages

**Mechanism**:

During meiosis (egg/sperm formation), chromosomes pair up. With balanced translocation:
- Normal pairing disrupted
- Multiple segregation outcomes possible
- ~50% of gametes carry unbalanced chromosome complement

**Unbalanced Conceptions**:
- Partial trisomy 2p + monosomy 11q
- Partial trisomy 11q + monosomy 2p
- Other imbalances
- Most result in early miscarriage (embryonic lethality)
- Rarely, live birth with severe congenital anomalies

**Patient's Miscarriages**:
- Likely due to unbalanced conceptions
- Not due to other maternal factors
- Recurrence risk remains high (~25-50% per pregnancy) without intervention

**Recommendations**:
- PGT-SR (preimplantation genetic testing) offers best chance for healthy baby
- Prenatal diagnosis in natural pregnancies
- Genetic counseling for informed decision-making
```

---

## Example 4: Complex Rearrangement (Multiple SVs)

### User Query
"Patient has complex rearrangement on chromosome 17: deletion 17q12 (1.4 Mb), inversion 17q21.31 (500 kb), duplication 17q23.3 (200 kb). How do I interpret this?"

### Expected Output (Key Sections)

```markdown
# SV Analysis Report: Complex Chr17 Rearrangement

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Complex rearrangement (deletion + inversion + duplication) |
| **Chromosome** | 17 |
| **Total Affected** | ~2.1 Mb across 3 regions |
| **Gene Content** | 15 genes affected (7 deleted, 3 inverted, 5 duplicated) |
| **Classification** | **PATHOGENIC** ★★★ |
| **Pathogenicity Score** | 8.5 / 10 |
| **Key Finding** | Deletion includes HNF1B (17q12 deletion syndrome); additional complexity worsens prognosis |

---

## 1. SV Identity & Classification

**Component SVs**:

| SV# | Type | Region | Coordinates | Size | Genes Affected |
|-----|------|--------|-------------|------|----------------|
| SV1 | Deletion | 17q12 | chr17:36,000,000-37,400,000 | 1.4 Mb | HNF1B, LHX1, ACACA, + 4 others (7 genes) |
| SV2 | Inversion | 17q21.31 | chr17:43,500,000-44,000,000 | 500 kb | MAPT, KANSL1, + 1 other (3 genes) |
| SV3 | Duplication | 17q23.3 | chr17:61,000,000-61,200,000 | 200 kb | BRCA1 partial, + 4 others (5 genes) |

**Classification**: **Complex genomic rearrangement** - likely chromothripsis or multiple-event rearrangement

---

## 2. Gene Content Analysis (Aggregated)

### 2.1 Deleted Genes (SV1 - 17q12 deletion)

| Gene | Function | Dosage Sensitivity | Disease Association |
|------|----------|-------------------|---------------------|
| **HNF1B** | Transcription factor | HI score 3 | RCAD syndrome (renal cysts, diabetes) |
| **LHX1** | Transcription factor | HI score 2 | Developmental defects |
| ACACA | Fatty acid synthesis | Low | Obesity (rare) |

**Primary Pathogenic Driver**: HNF1B deletion → 17q12 deletion syndrome

### 2.2 Inverted Genes (SV2 - 17q21.31 inversion)

| Gene | Disruption Status | Effect |
|------|------------------|--------|
| MAPT | Breakpoint in intron 3 | Likely loss-of-function |
| KANSL1 | Intact (inverted orientation) | Position effect possible |

**Effect**: MAPT disrupted (but MAPT haploinsufficiency not established); KANSL1 orientation change (uncertain effect)

### 2.3 Duplicated Genes (SV3 - 17q23.3 duplication)

| Gene | Duplication Extent | TS Evidence | Effect |
|------|-------------------|-------------|--------|
| BRCA1 | Exons 1-8 only | No TS | Partial duplication; unclear effect |
| Other genes | Full duplication | No TS for any | Unknown significance |

**Effect**: Uncertain - no established triplosensitivity for these genes

---

## 5. Pathogenicity Scoring

**Total Score**: 8.5 / 10

| Component | Points | Rationale |
|-----------|--------|-----------|
| Gene Content | 3.5/4 | HNF1B deletion (HI score 3); MAPT disruption (unclear significance) |
| Dosage Sensitivity | 2.5/3 | One definitive HI gene; others uncertain |
| Population Frequency | 2.0/2 | Complex rearrangement extremely rare; not in gnomAD |
| Clinical Evidence | 0.5/1 | 17q12 deletion known pathogenic; rest uncertain |

**Classification**: **PATHOGENIC** - driven primarily by 17q12 deletion (HNF1B)

---

## 7. ACMG Classification

**Evidence Codes**:

| Code | Strength | Rationale |
|------|----------|-----------|
| **PVS1** | Very Strong | Complete deletion of HNF1B (HI score 3) |
| **PM2** | Moderate | Complex rearrangement not in population databases |
| **PP3** | Supporting | Multiple gene disruptions compound pathogenicity |

**Classification**: **PATHOGENIC** (PVS1 sufficient for reclassification with supporting evidence)

**Additional Complexity**:
- Inversion and duplication add uncertainty
- May contribute to more severe or atypical phenotype
- Reclassification may be needed as patient phenotype evolves

---

## 8. Clinical Recommendations

**For Patient**:

**Primary Diagnosis**: 17q12 deletion syndrome (due to HNF1B deletion)

**Expected Features**:
1. **Renal**: Cysts, malformations (80-90% of cases)
2. **Diabetes**: MODY5 (maturity-onset diabetes of the young) - onset teens to 30s
3. **Developmental**: Mild ID or learning disabilities (30%)
4. **Other**: Genital anomalies, pancreatic hypoplasia

**Additional Considerations** (due to complex rearrangement):
- Phenotype may be atypical or more severe
- MAPT disruption: Monitor for neurological symptoms (though MAPT haploinsufficiency rare)
- BRCA1 partial duplication: Uncertain effect; not expected to affect cancer risk

**Recommended Surveillance**:
1. **Renal ultrasound** - baseline and periodic monitoring
2. **Glucose monitoring** - screen for diabetes starting age 10
3. **Developmental assessment** - neuropsychological testing
4. **Genetic counseling** - discuss complex rearrangement, recurrence risk

**Recurrence Risk**:
- Likely de novo (complex rearrangements usually sporadic)
- Low recurrence risk for parents' future pregnancies (<1%)
- 50% risk to patient's offspring (if complex rearrangement transmissible)
- Parental testing recommended

---

## 9. Interpretation Challenges

**Challenges with Complex Rearrangements**:
1. **Mechanism unclear**: Chromothripsis? Multiple events? Timing?
2. **Additive effects**: Do multiple SVs compound pathogenicity?
3. **Inversion significance**: Position effects hard to predict
4. **Partial duplication**: BRCA1 exons 1-8 only - gain or loss of function?

**Approach**:
- Prioritize known pathogenic SV (17q12 deletion)
- Consider other SVs as modifiers of phenotype
- Phenotype-first interpretation (let clinical features guide)
- Reclassify as more data emerges

**Recommendation**: Consider research enrollment to characterize this rare complex rearrangement.
```

---

## Example 5: Common Benign CNV (15q11.2 BP1-BP2 Microdeletion)

### User Query
"My patient has a 500 kb deletion at 15q11.2 (BP1-BP2 region) including NIPA1 and CYFIP1. Is this pathogenic?"

### Expected Output (Key Sections)

```markdown
# SV Analysis Report: 15q11.2 BP1-BP2 Microdeletion

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Deletion |
| **Coordinates** | chr15:22,770,421-23,282,798 (GRCh38) |
| **Size** | 512 kb |
| **Region** | 15q11.2 BP1-BP2 |
| **Gene Content** | NIPA1, NIPA2, CYFIP1, TUBGCP5 |
| **Classification** | **VUS** ★☆☆ |
| **Pathogenicity Score** | 5.0 / 10 (Uncertain range) |
| **Key Finding** | Recurrent microdeletion with unclear pathogenicity; seen in 1% of population but enriched in neurodevelopmental disorders |

---

## 2. Gene Content Analysis

| Gene | Function | Dosage Sensitivity | Disease Association |
|------|----------|-------------------|---------------------|
| CYFIP1 | Cytoskeleton regulation, FMRP interactor | HI score 1 (Little evidence) | Autism, ID (uncertain) |
| NIPA1 | Magnesium transporter | HI score 0 | Spastic paraplegia (AR, not deletion) |
| NIPA2 | Magnesium transporter | HI score 0 | None established |
| TUBGCP5 | Microtubule complex | HI score 0 | None established |

**Key Gene: CYFIP1**
- Interacts with fragile X mental retardation protein (FMRP)
- Haploinsufficiency proposed but NOT definitive
- ClinGen HI score: 1 (Little evidence)

---

## 4. Population Frequency Context

### 4.1 gnomAD SV Database

**Frequency**: ~1% (1 in 100 individuals)
- Found in 750+ individuals in gnomAD v4.0 (76,156 genomes)
- Present in healthy controls without neurodevelopmental disorders

**ACMG Code**: Does NOT meet BA1 (>5%) but frequency is high

### 4.2 ClinVar Matches

| VCV ID | Classification | Review Status |
|--------|----------------|---------------|
| VCV000004267 | **VUS** | ★★ Criteria provided, multiple submitters |
| VCV000145982 | **Uncertain significance** | ★★ |

**No consensus pathogenic classification** in ClinVar.

### 4.3 Clinical Literature

**Key Studies**:
1. **Burnside et al., 2011 (PMID: 21841781)**:
   - 15q11.2 deletion found in 1.27% of cases vs 0.72% of controls
   - Odds ratio: 1.77 (modest enrichment)
   - Associated with variable neurodevelopmental phenotypes

2. **Cox & Butler, 2015 (PMID: 25849863)**:
   - Phenotype highly variable: 20-30% with developmental delay
   - But also found in 1% of healthy individuals
   - Incomplete penetrance and variable expressivity

**Interpretation**:
- Modest enrichment in neurodevelopmental disorders
- BUT also common in healthy population
- Suggests susceptibility locus, not Mendelian pathogenic variant

---

## 5. Pathogenicity Scoring

**Total Score**: 5.0 / 10 (VUS range)

| Component | Points | Rationale |
|-----------|--------|-----------|
| Gene Content | 1.5/4 | CYFIP1 haploinsufficiency uncertain; no definitive HI genes |
| Dosage Sensitivity | 0.5/3 | ClinGen HI scores all 0-1; limited evidence |
| Population Frequency | -1.0/2 | Found in 1% of population (too common for high penetrance) |
| Clinical Evidence | 1.0/1 | If patient has neurodevelopmental features, modest support |

**Classification**: **VUS** (Variant of Uncertain Significance)

---

## 7. ACMG Classification

**Pathogenic Evidence**:
| Code | Strength | Rationale |
|------|----------|-----------|
| **PM2** | Moderate → Downgraded to Supporting | Present but rare (1%); not definitive rarity |
| **PP3** | NOT applied | No strong computational predictions for haploinsufficiency |

**Benign Evidence**:
| Code | Strength | Rationale |
|------|----------|-----------|
| **BS1** | NOT applied | 1% is high but not >5% (BA1 threshold) |
| **BP2** | Supporting | Seen in healthy individuals in gnomAD |

**Evidence Summary**:
- 1 Supporting pathogenic (downgraded PM2)
- 1 Supporting benign (BP2)
- **Conflicting / Insufficient evidence**

**Classification**: **VUS** (Variant of Uncertain Significance) ★☆☆

**Rationale**:
- Insufficient evidence for Likely Pathogenic (would need gene-disease definitive curation + rarity)
- Insufficient evidence for Likely Benign (found in neurodevelopmental cases at higher rate than controls)
- High population frequency (1%) argues against high-penetrance pathogenic variant
- Variable phenotype and incomplete penetrance consistent with susceptibility factor

---

## 8. Clinical Recommendations

### 8.1 For Patient

**DO NOT use this finding to make clinical decisions**

| Category | Recommendation |
|----------|----------------|
| **Diagnosis** | 15q11.2 BP1-BP2 deletion is **VUS**; cannot confirm/rule out genetic diagnosis |
| **Clinical Management** | Manage phenotype based on symptoms, NOT genotype |
| **Additional Testing** | Consider: <br>- Exome sequencing (look for second hit)<br>- Array on parents (determine inheritance) |
| **Genetic Counseling** | Discuss uncertainty, variable expressivity, population frequency |

**Key Points**:
- **Not diagnostic** of specific genetic condition
- May be **susceptibility factor** (modest effect)
- Also found in **healthy individuals** (1%)
- Cannot predict if patient's features caused by deletion or other factors

### 8.2 Interpretation Based on Inheritance

**If Deletion is De Novo**:
- Slightly higher likelihood of contributing to phenotype
- But still found in 0.7% of healthy controls, so not definitive
- Consider: PP1_Supporting (de novo)

**If Deletion is Inherited from Healthy Parent**:
- Argues against high-penetrance pathogenic variant
- More consistent with benign or low-penetrance susceptibility
- Consider: BS2_Supporting (inherited from healthy parent)

**Recommendation**: Test parents to determine inheritance

### 8.3 Family Counseling

- **If inherited from healthy parent**: Low likelihood of pathogenicity; reassure family
- **If de novo**: Slightly higher concern, but still uncertain
- **Recurrence risk**:
  - If inherited: 50% to siblings (but may be asymptomatic)
  - If de novo: Low (<1%) recurrence risk

### 8.4 Reclassification Potential

**This VUS may be reclassified if**:
1. **New evidence**: ClinGen revises CYFIP1 haploinsufficiency score
2. **Large studies**: Meta-analysis definitively associates 15q11.2 with disorder
3. **Functional studies**: CYFIP1 dosage sensitivity proven in models
4. **Phenotype evolution**: Patient develops features strongly linked to 15q11.2

**Recommendation**: Reanalyze in 2-3 years or if phenotype changes

---

## 9. Scientific Controversy: 15q11.2 BP1-BP2 Deletion

**Why is this controversial?**

1. **Population frequency**: 1% is high for a pathogenic variant
2. **Incomplete penetrance**: 70-80% of carriers are healthy
3. **Variable expressivity**: When phenotype present, highly variable
4. **Modest effect size**: OR ~1.8 in case-control studies (weak association)

**Competing Models**:
- **Model 1**: Benign variant (incidental finding, no causation)
- **Model 2**: Susceptibility locus (contributes risk in polygenic model)
- **Model 3**: Pathogenic with low penetrance (20-30%)

**Current Consensus**: VUS pending further evidence

**Implication for Patient**:
- May contribute to phenotype in combination with other factors
- Alone, insufficient to explain clinical features
- Continue phenotype-based diagnostic workup

---

## 10. Comparison: VUS vs Pathogenic SVs

**What makes an SV Pathogenic?** (for contrast)

| Feature | 15q11.2 BP1-BP2 (VUS) | 17q21.31 KANSL1 DEL (Pathogenic) |
|---------|----------------------|----------------------------------|
| **Gene HI Score** | 0-1 (Little evidence) | 3 (Definitive) |
| **Population Freq** | 1% | <0.01% |
| **Penetrance** | 20-30% | >95% |
| **ClinVar** | VUS | Pathogenic (expert panel) |
| **Clinical** | Variable, nonspecific | Specific syndrome |

**Take-Home**: 15q11.2 BP1-BP2 lacks definitive evidence required for Pathogenic classification.

---

**Report Completed**: 2026-02-09
**Classification**: VUS ★☆☆
**Clinical Action**: Manage based on phenotype; do not use deletion for diagnosis
**Reclassification**: Reanalyze in 2-3 years
```

---

## Summary of Examples

| Example | SV Type | Size | Key Genes | Classification | Key Teaching Point |
|---------|---------|------|-----------|----------------|-------------------|
| 1. NF1 Deletion | Deletion | 283 kb | NF1 | Pathogenic ★★★ | Complete deletion of HI gene with definitive gene-disease curation |
| 2. MECP2 Duplication | Duplication | 115 kb | MECP2 | Pathogenic ★★★ | Triplosensitivity in males; sex-specific interpretation |
| 3. t(2;11) Translocation | Translocation | N/A | None | Likely Benign ★★☆ | Balanced rearrangement benign for carrier; reproductive risk high |
| 4. Chr17 Complex | Complex | 2.1 Mb | HNF1B, MAPT, others | Pathogenic ★★★ | Complex rearrangement; prioritize known pathogenic component |
| 5. 15q11.2 BP1-BP2 | Deletion | 512 kb | CYFIP1, NIPA1 | VUS ★☆☆ | High population frequency; incomplete penetrance; susceptibility not Mendelian |

**Key Principles Illustrated**:
1. **Dosage sensitivity is critical** - HI/TS scores drive classification
2. **Population frequency matters** - Common CNVs (>1%) unlikely to be highly penetrant pathogenic variants
3. **Balanced translocations** - Benign for carrier but reproductive risk
4. **Complex SVs** - Break down into components; identify primary driver
5. **VUS requires humility** - Don't over-interpret; manage phenotype, not genotype
