# Signal Analysis Reference: Pharmacovigilance

## Disproportionality Analysis

### Proportional Reporting Ratio (PRR)

```
PRR = (A/B) / (C/D)

Where:
A = Reports of drug X with event Y
B = Reports of drug X with any event
C = Reports of event Y with any drug (excluding X)
D = Total reports (excluding drug X)
```

### Signal Thresholds

| Measure | Signal Threshold | Strong Signal |
|---------|------------------|---------------|
| PRR | >2.0 | >3.0 |
| Chi-squared | >4.0 | >10.0 |
| N (case count) | >=3 | >=10 |

### Signal Scoring Formula

```
Signal Score = PRR x Severity_Weight x log10(Case_Count + 1)

Severity Weights:
- Fatal: 10
- Life-threatening: 8
- Hospitalization: 5
- Disability: 5
- Other serious: 3
- Non-serious: 1
```

## Severity Classification

| Category | Definition | Priority |
|----------|------------|----------|
| **Fatal** | Death outcome | Highest |
| **Life-threatening** | Immediate death risk | Very High |
| **Hospitalization** | Required/prolonged hospitalization | High |
| **Disability** | Persistent impairment | High |
| **Congenital anomaly** | Birth defect | High |
| **Other serious** | Medical intervention required | Medium |
| **Non-serious** | No serious criteria | Low |

## Warning Severity Categories

| Category | Symbol | Description |
|----------|--------|-------------|
| **Boxed Warning** | Black box | Most serious, life-threatening |
| **Contraindication** | Red | Must not use |
| **Warning** | Orange | Significant risk |
| **Precaution** | Yellow | Use caution |

## Example Output: Adverse Event Profile

```markdown
## 2. Adverse Event Profile (FAERS)

**Data Period**: Q1 2020 - Q4 2025
**Total Reports for Drug**: 45,234

### Top Adverse Events by Frequency

| Rank | Adverse Event | Reports | PRR | 95% CI | Serious (%) | Fatal |
|------|---------------|---------|-----|--------|-------------|-------|
| 1 | Diarrhea | 8,234 | 2.3 | 2.1-2.5 | 12% | 3 |
| 2 | Nausea | 6,892 | 1.8 | 1.6-2.0 | 8% | 0 |
| 3 | Lactic acidosis | 1,247 | 15.2 | 12.8-17.9 | 89% | 156 |
| 4 | Hypoglycemia | 2,341 | 2.1 | 1.9-2.4 | 34% | 8 |
| 5 | Vitamin B12 deficiency | 892 | 8.4 | 7.2-9.8 | 23% | 0 |
```

## Example Output: Signal Prioritization

```markdown
## 6. Prioritized Safety Signals

### Critical Signals (Immediate Attention)

| Signal | PRR | Fatal | Score | Action |
|--------|-----|-------|-------|--------|
| Lactic acidosis | 15.2 | 156 | 482 | Boxed warning exists |
| Acute kidney injury | 4.2 | 34 | 89 | Monitor renal function |

### Moderate Signals (Monitor)

| Signal | PRR | Serious | Score | Action |
|--------|-----|---------|-------|--------|
| Hepatotoxicity | 3.1 | 234 | 52 | Check LFTs if symptoms |
| Pancreatitis | 2.8 | 178 | 41 | Monitor lipase |

### Known/Expected (Manage Clinically)

| Signal | PRR | Frequency | Management |
|--------|-----|-----------|------------|
| Diarrhea | 2.3 | 18% | Start low, titrate slow |
| Nausea | 1.8 | 12% | Take with food |
| B12 deficiency | 8.4 | 2% | Annual monitoring |
```

## Example Output: Label Warnings

```markdown
## 3. FDA Label Safety Information

### Boxed Warning
**LACTIC ACIDOSIS**
> Metformin can cause lactic acidosis, a rare but serious complication.
> Risk increases with renal impairment, sepsis, dehydration, excessive
> alcohol intake, hepatic impairment, and acute heart failure.
> **Contraindicated in patients with eGFR <30 mL/min/1.73m2**

### Contraindications
| Contraindication | Rationale |
|------------------|-----------|
| eGFR <30 mL/min/1.73m2 | Lactic acidosis risk |
| Acute/chronic metabolic acidosis | May worsen acidosis |
| Hypersensitivity to metformin | Allergic reaction |

### Warnings and Precautions
| Warning | Clinical Action |
|---------|-----------------|
| Vitamin B12 deficiency | Monitor B12 levels annually |
| Hypoglycemia with insulin | Reduce insulin dose |
| Radiologic contrast | Hold 48h around procedure |
| Surgical procedures | Hold day of surgery |
```

## Example Output: Pharmacogenomics

```markdown
## 4. Pharmacogenomic Risk Factors

### Clinically Actionable Variants
| Gene | Variant | Phenotype | Recommendation | Level |
|------|---------|-----------|----------------|-------|
| SLC22A1 | rs628031 | Reduced OCT1 | Reduced metformin response | 2A |
| SLC22A1 | rs36056065 | Loss of function | Consider alternative | 2A |
| ATM | rs11212617 | Increased response | Standard dosing | 3 |
```

## Example Output: Clinical Trial Safety

```markdown
## 5. Clinical Trial Safety Data

### Phase 3 Trial Summary
| Trial | N | Duration | Serious AEs (Drug) | Serious AEs (Placebo) | Deaths |
|-------|---|----------|-------------------|----------------------|--------|
| UKPDS | 1,704 | 10 yr | 12.3% | 14.1% | 8.2% vs 9.1% |
| DPP | 1,073 | 3 yr | 4.2% | 3.8% | 0.1% |

### Common Adverse Events in Trials
| Adverse Event | Drug (%) | Placebo (%) | Difference |
|---------------|----------|-------------|------------|
| Diarrhea | 53% | 12% | +41% |
| Nausea | 26% | 8% | +18% |
| Flatulence | 12% | 6% | +6% |
```

## Example Output: Pathway Context

```markdown
## 5.5 Pathway & Mechanism Context

### Drug Metabolism Pathways (KEGG)
| Pathway | Relevance | Safety Implication |
|---------|-----------|-------------------|
| Drug metabolism - cytochrome P450 | Primary metabolism | CYP2C9 interactions |
| Gluconeogenesis inhibition | MOA | Lactic acidosis mechanism |
| Mitochondrial complex I | Off-target | Lactic acid accumulation |

### Mechanistic Basis for Key AEs
| Adverse Event | Pathway Mechanism |
|---------------|-------------------|
| Lactic acidosis | Mitochondrial complex I inhibition |
| GI intolerance | Serotonin release in gut |
| B12 deficiency | Intrinsic factor interference |
```

## Example Output: Literature

```markdown
## 5.6 Literature Evidence

### Key Safety Studies
| PMID | Title | Year | Citations | Finding |
|------|-------|------|-----------|---------|
| 29234567 | Metformin and lactic acidosis: meta-analysis | 2020 | 245 | Risk 4.3/100,000 |
| 28765432 | Long-term cardiovascular outcomes... | 2019 | 567 | CV benefit confirmed |

### Recent Preprints (Not Peer-Reviewed)
| Source | Title | Posted | Relevance |
|--------|-------|--------|-----------|
| MedRxiv | Novel metformin safety signal in elderly | 2024-01 | Age-related risk |

Note: Preprints have NOT undergone peer review.
```
