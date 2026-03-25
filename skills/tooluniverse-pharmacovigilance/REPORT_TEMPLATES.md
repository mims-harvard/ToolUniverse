# Report Templates

Templates and examples for pharmacovigilance safety report output.

---

## Report File Template

**File**: `[DRUG]_safety_report.md`

```markdown
# Pharmacovigilance Safety Report: [DRUG]

**Generated**: [Date] | **Query**: [Original query] | **Status**: In Progress

---

## Executive Summary
[Researching...]

---

## 1. Drug Identification
### 1.1 Drug Information
[Researching...]

---

## 2. Adverse Event Profile (FAERS)
### 2.1 Top Adverse Events
[Researching...]
### 2.2 Serious Adverse Events
[Researching...]
### 2.3 Signal Analysis
[Researching...]

---

## 3. FDA Label Safety Information
### 3.1 Boxed Warnings
[Researching...]
### 3.2 Contraindications
[Researching...]
### 3.3 Warnings and Precautions
[Researching...]

---

## 4. Pharmacogenomic Risk Factors
### 4.1 Actionable Variants
[Researching...]
### 4.2 Testing Recommendations
[Researching...]

---

## 5. Clinical Trial Safety
### 5.1 Trial Summary
[Researching...]
### 5.2 Adverse Events in Trials
[Researching...]

---

## 6. Prioritized Safety Signals
### 6.1 Critical Signals
[Researching...]
### 6.2 Moderate Signals
[Researching...]

---

## 7. Risk-Benefit Assessment
[Researching...]

---

## 8. Clinical Recommendations
### 8.1 Monitoring Recommendations
[Researching...]
### 8.2 Patient Counseling Points
[Researching...]
### 8.3 Contraindication Checklist
[Researching...]

---

## 9. Data Gaps & Limitations
[Researching...]

---

## 10. Data Sources
[Will be populated as research progresses...]
```

---

## Citation Format

Every safety signal MUST include source:

```markdown
### Signal: Hepatotoxicity
- **PRR**: 3.2 (95% CI: 2.8-3.7)
- **Cases**: 1,247 reports
- **Serious**: 892 (71.5%)
- **Fatal**: 23

*Source: FAERS via `FAERS_count_reactions_by_drug_event` (Q1 2020 - Q4 2025)*
```

---

## Phase Output Examples

### Drug Identification Output

```markdown
## 1. Drug Identification

| Property | Value |
|----------|-------|
| **Generic Name** | Metformin |
| **Brand Names** | Glucophage, Fortamet, Glumetza |
| **Drug Class** | Biguanide antidiabetic |
| **ChEMBL ID** | CHEMBL1431 |
| **Mechanism** | AMPK activator, hepatic gluconeogenesis inhibitor |
| **First Approved** | 1994 (US) |

*Source: DailyMed via `DailyMed_search_spls`, ChEMBL*
```

### FAERS Output

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

### Serious Adverse Events Only

| Adverse Event | Serious Reports | Fatal | PRR | Signal |
|---------------|-----------------|-------|-----|--------|
| Lactic acidosis | 1,110 | 156 | 15.2 | **STRONG** |
| Acute kidney injury | 678 | 34 | 4.2 | Moderate |

*Source: FAERS via `FAERS_count_reactions_by_drug_event`*
```

### Label Warnings Output

```markdown
## 3. FDA Label Safety Information

### 3.1 Boxed Warning

**LACTIC ACIDOSIS**
> Metformin can cause lactic acidosis, a rare but serious complication.
> Risk increases with renal impairment, sepsis, dehydration, excessive
> alcohol intake, hepatic impairment, and acute heart failure.
> **Contraindicated in patients with eGFR <30 mL/min/1.73m2**

### 3.2 Contraindications

| Contraindication | Rationale |
|------------------|-----------|
| eGFR <30 mL/min/1.73m2 | Lactic acidosis risk |
| Acute/chronic metabolic acidosis | May worsen acidosis |
| Hypersensitivity to metformin | Allergic reaction |

### 3.3 Warnings and Precautions

| Warning | Clinical Action |
|---------|-----------------|
| Vitamin B12 deficiency | Monitor B12 levels annually |
| Hypoglycemia with insulin | Reduce insulin dose |
| Radiologic contrast | Hold 48h around procedure |

*Source: DailyMed via `DailyMed_search_spls`*
```

### Pharmacogenomics Output

```markdown
## 4. Pharmacogenomic Risk Factors

### Clinically Actionable Variants

| Gene | Variant | Phenotype | Recommendation | Level |
|------|---------|-----------|----------------|-------|
| SLC22A1 | rs628031 | Reduced OCT1 | Reduced metformin response | 2A |
| SLC22A1 | rs36056065 | Loss of function | Consider alternative | 2A |

**No CPIC/DPWG guidelines currently exist for metformin**

*Source: PharmGKB via `PharmGKB_search_drugs`*
```

### Clinical Trial Safety Output

```markdown
## 5. Clinical Trial Safety Data

### Phase 3 Trial Summary

| Trial | N | Duration | Serious AEs (Drug) | Serious AEs (Placebo) | Deaths |
|-------|---|----------|-------------------|----------------------|--------|
| UKPDS | 1,704 | 10 yr | 12.3% | 14.1% | 8.2% vs 9.1% |

### Common Adverse Events in Trials

| Adverse Event | Drug (%) | Placebo (%) | Difference |
|---------------|----------|-------------|------------|
| Diarrhea | 53% | 12% | +41% |
| Nausea | 26% | 8% | +18% |

*Source: ClinicalTrials.gov via `search_clinical_trials`*
```

### Prioritized Signals Output

```markdown
## 6. Prioritized Safety Signals

### Critical Signals (Immediate Attention)

| Signal | PRR | Fatal | Score | Action |
|--------|-----|-------|-------|--------|
| Lactic acidosis | 15.2 | 156 | 482 | Boxed warning exists |

### Moderate Signals (Monitor)

| Signal | PRR | Serious | Score | Action |
|--------|-----|---------|-------|--------|
| Hepatotoxicity | 3.1 | 234 | 52 | Check LFTs if symptoms |

### Known/Expected (Manage Clinically)

| Signal | PRR | Frequency | Management |
|--------|-----|-----------|------------|
| Diarrhea | 2.3 | 18% | Start low, titrate slow |
```

### Pathway & Mechanism Output

```markdown
## 5.5 Pathway & Mechanism Context

### Drug Metabolism Pathways (KEGG)

| Pathway | Relevance | Safety Implication |
|---------|-----------|-------------------|
| Drug metabolism - cytochrome P450 | Primary metabolism | CYP2C9 interactions |
| Gluconeogenesis inhibition | MOA | Lactic acidosis mechanism |

### Mechanistic Basis for Key AEs

| Adverse Event | Pathway Mechanism |
|---------------|-------------------|
| Lactic acidosis | Mitochondrial complex I inhibition |
| GI intolerance | Serotonin release in gut |
| B12 deficiency | Intrinsic factor interference |

*Source: KEGG, Reactome*
```

### Literature Evidence Output

```markdown
## 5.6 Literature Evidence

### Key Safety Studies

| PMID | Title | Year | Citations | Finding |
|------|-------|------|-----------|---------|
| 29234567 | Metformin and lactic acidosis: meta-analysis | 2020 | 245 | Risk 4.3/100,000 |

### Recent Preprints (Not Peer-Reviewed)

| Source | Title | Posted | Relevance |
|--------|-------|--------|-----------|
| MedRxiv | Novel metformin safety signal in elderly | 2024-01 | Age-related risk |

**Note**: Preprints have NOT undergone peer review.

*Source: PubMed, BioRxiv, MedRxiv, OpenAlex*
```

---

## Completeness Checklist

### Phase 1: Drug Identification
- [ ] Generic name resolved
- [ ] Brand names listed
- [ ] Drug class identified
- [ ] ChEMBL/DrugBank ID obtained
- [ ] Mechanism of action stated

### Phase 2: FAERS Analysis
- [ ] >=20 adverse events queried
- [ ] PRR calculated for top events
- [ ] Serious/fatal counts included
- [ ] Signal thresholds applied
- [ ] Time period stated

### Phase 3: Label Warnings
- [ ] Boxed warnings extracted (or "None")
- [ ] Contraindications listed
- [ ] Key warnings summarized
- [ ] Drug interactions noted

### Phase 4: Pharmacogenomics
- [ ] PharmGKB queried
- [ ] Actionable variants listed (or "None")
- [ ] Evidence levels provided
- [ ] Testing recommendations stated

### Phase 5: Clinical Trials
- [ ] Phase 3/4 trials searched
- [ ] Serious AE rates compared
- [ ] Discontinuation rates noted

### Phase 6: Signal Prioritization
- [ ] Signals ranked by score
- [ ] Critical signals flagged
- [ ] Actions recommended

### Phase 7-8: Synthesis
- [ ] Risk-benefit assessment provided
- [ ] Monitoring recommendations listed
- [ ] Patient counseling points included

---

## Data File Outputs

In addition to the report, generate:
- `[DRUG]_adverse_events.csv` - Ranked AEs with counts/signals
- `[DRUG]_pharmacogenomics.csv` - PGx variants and recommendations
