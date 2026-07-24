# SV Analysis Report Template

Use this template when generating `SV_analysis_report.md` files. Create the report first, then populate progressively as each phase completes.

## File Naming Convention

```
SV_analysis_[TYPE]_chr[CHR]_[START]_[END]_[GENES].md

Examples:
SV_analysis_DEL_chr17_44039927_44352659_KANSL1_MAPT.md
SV_analysis_DUP_chr22_17400000_17800000_TBX1.md
SV_analysis_INV_chr11_2100000_2400000_complex.md
```

---

## Report Template

```markdown
# Structural Variant Analysis Report: [SV_IDENTIFIER]

**Generated**: [Date] | **Analyst**: ToolUniverse SV Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **SV Type** | Deletion / Duplication / Inversion / Translocation |
| **Coordinates** | chr_:________-________ (GRCh38) |
| **Size** | ___ kb |
| **Gene Content** | X genes fully contained, Y partially disrupted |
| **Classification** | Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign |
| **Pathogenicity Score** | X.X / 10 |
| **Confidence** | High / Moderate / Limited |
| **Key Finding** | [One-sentence summary] |

**Clinical Action**: [Required / Recommended / None]

---

## 1. SV Identity & Classification

{SV type, coordinates, size, breakpoint precision, inheritance}

---

## 2. Gene Content Analysis

### 2.1 Fully Contained Genes

| Gene | Function | Disease Association | Inheritance | Evidence |
|------|----------|---------------------|-------------|----------|
| | | | | |

**Interpretation**: [Summary of dosage effect for contained genes]

*Sources: OMIM, DisGeNET, Ensembl*

### 2.2 Partially Disrupted Genes

| Gene | Breakpoint Location | Effect | Critical Domains Lost |
|------|-------------------|--------|----------------------|
| | | | |

**Interpretation**: [Impact of breakpoint on gene function]

### 2.3 Flanking Genes (Potential Position Effects)

| Gene | Distance from SV | Regulatory Risk | Evidence |
|------|------------------|-----------------|----------|
| | | | |

---

## 3. Dosage Sensitivity Assessment

### 3.1 Haploinsufficient Genes (Deletions/Disruptions)

| Gene | ClinGen HI Score | pLI | Validity | Disease | Evidence |
|------|-----------------|-----|----------|---------|----------|
| | | | | | |

### 3.2 Triplosensitive Genes (Duplications)

| Gene | ClinGen TS Score | Disease Mechanism | Evidence |
|------|-----------------|-------------------|----------|
| | | | |

### 3.3 Non-Dosage-Sensitive Genes

| Gene | HI Score | TS Score | Interpretation |
|------|----------|----------|----------------|
| | | | |

---

## 4. Population Frequency Context

### 4.1 ClinVar Matches (Overlapping SVs)

| VCV ID | Classification | Size | Overlap | Review Status | Genes |
|--------|----------------|------|---------|---------------|-------|
| | | | | | |

**ACMG Code**: [PS1 / PM2 / BA1 / BS1]

### 4.2 gnomAD SV Database

**Search Result**: [Frequency or absent]

### 4.3 DECIPHER Patient Cases

| Case ID | Phenotype | SV Type | Size | Overlap | Similarity |
|---------|-----------|---------|------|---------|------------|
| | | | | | |

---

## 5. Pathogenicity Scoring

### 5.1 Quantitative Assessment (0-10 Scale)

| Component | Points | Max | Contribution | Rationale |
|-----------|--------|-----|-------------|-----------|
| **Gene Content** | | 4 | 40% | |
| **Dosage Sensitivity** | | 3 | 30% | |
| **Population Frequency** | | 2 | 20% | |
| **Clinical Evidence** | | 1 | 10% | |
| **Total Score** | **X.X** | 10 | 100% | |

**Classification**: [Classification] ([Confidence])

---

## 6. Literature & Clinical Evidence

### 6.1 Key Publications

| Study | Finding | Evidence Type | PMID |
|-------|---------|---------------|------|
| | | | |

### 6.2 DECIPHER Cohort Analysis

| Feature | Frequency | Match to Patient |
|---------|-----------|------------------|
| | | |

### 6.3 Functional Evidence

| Study | Model | Finding | PMID |
|-------|-------|---------|------|
| | | | |

---

## 7. ACMG-Adapted Classification

### 7.1 Evidence Codes Applied

**Pathogenic Evidence**:

| Code | Strength | Rationale |
|------|----------|-----------|
| | | |

**Benign Evidence**:

| Code | Strength | Rationale |
|------|----------|-----------|
| | | |

### 7.2 Evidence Summary

| Pathogenic | Benign |
|------------|--------|
| | |

### 7.3 Classification: **[CLASSIFICATION]** [Confidence]

**Rationale**: [Why this classification was reached]

### 7.4 Certainty Factors

**Strengths**: [What supports the classification]

**Limitations**: [What could change the classification]

---

## 8. Clinical Recommendations

### 8.1 For Affected Individual
{Testing, management, surveillance}

### 8.2 For Family Members
{Cascade testing, genetic counseling}

### 8.3 Reproductive Considerations
{Recurrence risk, prenatal testing}

---

## 9. Limitations & Uncertainties

{Missing data, conflicting evidence, knowledge gaps}

---

## Data Sources

{All tools and databases queried with results}
```
