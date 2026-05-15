# SV Classification Guide: ACMG-Adapted Criteria

Reference material for structural variant pathogenicity classification using ACMG-adapted criteria.

---

## SV Types

| Type | Abbreviation | Description | Molecular Effect |
|------|--------------|-------------|------------------|
| **Deletion** | DEL | Loss of genomic segment | Haploinsufficiency, gene disruption |
| **Duplication** | DUP | Gain of genomic segment | Triplosensitivity, gene dosage imbalance |
| **Inversion** | INV | Segment flipped in orientation | Gene disruption at breakpoints, position effects |
| **Translocation** | TRA | Segment moved to different chromosome | Gene fusions, disruption, position effects |
| **Complex** | CPX | Multiple rearrangement types | Variable effects |

---

## ClinGen Dosage Sensitivity Scores

| Score | Haploinsufficiency (HI) | Triplosensitivity (TS) | Interpretation |
|-------|------------------------|------------------------|----------------|
| **3** | Sufficient evidence | Sufficient evidence | Gene IS dosage-sensitive |
| **2** | Emerging evidence | Emerging evidence | Likely dosage-sensitive |
| **1** | Little evidence | Little evidence | Insufficient evidence |
| **0** | No evidence | No evidence | No established dosage sensitivity |

## pLI Score Interpretation (gnomAD)

| pLI Range | Interpretation | LoF Intolerance |
|-----------|----------------|-----------------|
| **>=0.9** | Extremely intolerant | High - likely haploinsufficient |
| **0.5-0.9** | Moderately intolerant | Moderate |
| **<0.5** | Tolerant | Low - likely NOT haploinsufficient |

---

## Population Frequency Interpretation

| SV Frequency | ACMG Code | Interpretation |
|--------------|-----------|----------------|
| **>=1% in gnomAD SVs** | BA1 (Stand-alone Benign) | Too common for rare disease |
| **0.1-1%** | BS1 (Strong Benign) | Likely benign common variant |
| **<0.01%** | PM2 (Supporting Pathogenic) | Rare, supports pathogenicity |
| **Absent** | PM2 (Supporting) | Very rare, supports pathogenicity |

### Reciprocal Overlap Calculation

For proper comparison, calculate reciprocal overlap between query SV and population SV:

```
Reciprocal Overlap = min(overlap_with_A, overlap_with_B)
where:
  overlap_with_A = (overlap length) / (SV_A length)
  overlap_with_B = (overlap length) / (SV_B length)

Threshold: >=70% reciprocal overlap = "same" SV
```

---

## Pathogenicity Scoring (0-10 Scale)

### Scoring Components

1. **Gene Content (40 points max / scaled to 4)**:
   - 10 points per dosage-sensitive gene (HI/TS score 3)
   - 5 points per likely dosage-sensitive gene (score 2)
   - 2 points per gene with disease association
   - Cap at 40 points

2. **Dosage Sensitivity Evidence (30 points max / scaled to 3)**:
   - 30 points: Multiple genes with definitive HI/TS (score 3)
   - 20 points: One gene with definitive HI/TS
   - 10 points: Genes with emerging evidence (score 2)
   - 5 points: Predicted haploinsufficiency (pLI >0.9)

3. **Population Frequency (20 points max / scaled to 2)**:
   - 20 points: Absent from gnomAD, DGV
   - 10 points: Rare (<0.01%)
   - 0 points: Common (>0.1%)
   - -20 points: Very common (>1%) - likely benign

4. **Clinical Evidence (10 points max / scaled to 1)**:
   - 10 points: Matching ClinVar pathogenic SV
   - 8 points: DECIPHER cases with matching phenotype
   - 5 points: Literature support for gene dosage effects
   - 3 points: Phenotype consistent with genes

### Score to Classification Mapping

| Score | Classification | Confidence |
|-------|----------------|------------|
| **9-10** | Pathogenic | High |
| **7-8** | Likely Pathogenic | Moderate-High |
| **4-6** | VUS | Low |
| **2-3** | Likely Benign | Moderate-High |
| **0-1** | Benign | High |

---

## ACMG Evidence Codes

### Pathogenic Evidence

| Code | Strength | Criteria | SV Application |
|------|----------|----------|----------------|
| **PVS1** | Very Strong | Null variant in HI gene | Complete deletion of HI gene |
| **PS1** | Strong | Same SV as known pathogenic | >=70% reciprocal overlap with ClinVar pathogenic |
| **PS2** | Strong | De novo (confirmed) | De novo SV with matching phenotype |
| **PS3** | Strong | Functional studies | Gene dosage effects demonstrated |
| **PS4** | Strong | Case-control enrichment | SV enriched in cases vs controls |
| **PM1** | Moderate | Critical region | Deletion of exons in HI gene |
| **PM2** | Moderate | Absent from controls | Not in gnomAD SVs, DGV |
| **PM3** | Moderate | Recessive: homozygous/compound het | Both alleles affected |
| **PM4** | Moderate | Protein length change | In-frame deletion/duplication |
| **PM5** | Moderate | Similar SVs pathogenic | Nearby SVs in ClinVar pathogenic |
| **PM6** | Moderate | De novo (no confirmation) | De novo SV, phenotype consistent |
| **PP1** | Supporting | Segregation in family | SV segregates with phenotype |
| **PP2** | Supporting | Gene/pathway relevant | Genes in SV match phenotype |
| **PP3** | Supporting | Computational evidence | Multiple predictors support haploinsufficiency |
| **PP4** | Supporting | Phenotype consistent | Patient phenotype matches gene-disease |

### Benign Evidence

| Code | Strength | Criteria | SV Application |
|------|----------|----------|----------------|
| **BA1** | Stand-Alone | MAF >5% | SV frequency >5% in gnomAD |
| **BS1** | Strong | MAF too high for disease | SV frequency >1% |
| **BS2** | Strong | Healthy adult with genotype | SV in healthy individual (watch for reduced penetrance) |
| **BS3** | Strong | No functional effect | No dosage sensitivity demonstrated |
| **BS4** | Strong | Non-segregation | SV doesn't segregate with phenotype |
| **BP2** | Supporting | In trans with pathogenic | SV + pathogenic SNV compound het (patient unaffected) |
| **BP4** | Supporting | Computational benign | Predictors suggest no haploinsufficiency |
| **BP5** | Supporting | Alternative cause | Phenotype explained by different variant |

### Classification Rules

| Classification | Evidence Required |
|----------------|-------------------|
| **Pathogenic** | PVS1 + PS1; OR 2 Strong; OR 1 Strong + 3 Moderate |
| **Likely Pathogenic** | 1 Very Strong + 1 Moderate; OR 1 Strong + 2 Moderate; OR 3 Moderate |
| **VUS** | Criteria not met; OR conflicting evidence |
| **Likely Benign** | 1 Strong + 1 Supporting; OR 2 Supporting |
| **Benign** | BA1; OR BS1 + BS2; OR 2 Strong |

---

## Evidence Grading System

| Symbol | Confidence | Criteria |
|--------|------------|----------|
| High | High | ClinGen definitive, ClinVar expert reviewed, multiple independent studies |
| Moderate | Moderate | ClinGen strong/moderate, single good study, DECIPHER cohort support |
| Limited | Limited | Computational predictions only, case reports, emerging evidence |

---

## Special Scenarios

### Recurrent Microdeletion Syndrome
- Check for recurrence mechanism (LCRs, NAHR)
- Look for founder effects
- Population-specific frequencies
- Incomplete penetrance and variable expressivity
- Examples: 22q11.2 deletion, 17q21.31 deletion (Koolen-De Vries)

### Balanced Translocation (No Gene Disruption)
- If no genes disrupted: Likely benign (in most cases)
- Check for cryptic imbalances
- Consider position effects (rare)
- Reproductive risk (unbalanced offspring)
- Classification: Usually VUS or Likely Benign unless offspring affected

### Complex Rearrangement
- Break down into component SVs
- Assess each breakpoint independently
- Look for chromothripsis pattern
- Consider cumulative gene dosage effects
- Check for DNA repair defects

### Small In-Frame Deletion/Duplication
- May not cause haploinsufficiency
- Check if critical domain affected
- Look for similar variants in ClinVar
- Consider protein structural impact
- May need functional studies

---

## Clinical Recommendations Framework

### For Pathogenic/Likely Pathogenic SVs

| SV Type | Recommendations |
|---------|-----------------|
| **Deletion (HI gene)** | Genetic counseling, cascade testing, phenotype-specific surveillance |
| **Duplication (TS gene)** | Same as deletion; check for dosage-specific syndrome |
| **Translocation (disruption)** | Assess both breakpoints, consider reproductive counseling |
| **Complex** | Multidisciplinary evaluation, research enrollment |

### For VUS

| Action | Details |
|--------|---------|
| Clinical management | Base on phenotype, not genotype |
| Follow-up | Reinterpret in 1-2 years or when phenotype evolves |
| Research | Functional studies if research-grade samples available |
| Family studies | Segregation analysis can reclassify |

### For Benign/Likely Benign

| Action | Details |
|--------|---------|
| Clinical | Not expected to cause rare disease |
| Family | No cascade testing needed (unless recurrent/reproductive risk) |
| Reproductive | Balanced translocation carriers may have offspring risk |
