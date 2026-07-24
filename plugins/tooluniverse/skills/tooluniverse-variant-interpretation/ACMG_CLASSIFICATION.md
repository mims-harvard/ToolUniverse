# ACMG Classification Reference

## Evidence Codes

### Pathogenic Evidence

| Code | Strength | Description |
|------|----------|-------------|
| PVS1 | Very Strong | Null variant in gene where LOF is mechanism |
| PS1 | Strong | Same amino acid change as known pathogenic |
| PS3 | Strong | Well-established functional studies |
| PM1 | Moderate | Mutational hot spot / functional domain |
| PM2 | Moderate | Absent from controls |
| PM5 | Moderate | Different missense at same residue as pathogenic |
| PP3 | Supporting | Multiple computational predictions |
| PP5 | Supporting | Reputable source reports pathogenic |

### Benign Evidence

| Code | Strength | Description |
|------|----------|-------------|
| BA1 | Stand-alone | MAF >5% |
| BS1 | Strong | MAF greater than expected |
| BS3 | Strong | Functional studies show no effect |
| BP4 | Supporting | Multiple computational predictions benign |
| BP7 | Supporting | Synonymous with no splice impact |

## Classification Algorithm

| Classification | Evidence Required |
|----------------|-------------------|
| Pathogenic | 1 Very Strong + 1 Strong; OR 2 Strong; OR 1 Strong + 3 Moderate |
| Likely Pathogenic | 1 Very Strong + 1 Moderate; OR 1 Strong + 2 Moderate; OR 1 Strong + 2 Supporting |
| Likely Benign | 1 Strong + 1 Supporting; OR 2 Supporting |
| Benign | 1 Stand-alone; OR 2 Strong |
| VUS | Criteria not met |

## Classification Confidence

| Symbol | Classification | Evidence Level |
|--------|----------------|----------------|
| 3 stars | High confidence | Multiple independent lines |
| 2 stars | Moderate confidence | Some supporting evidence |
| 1 star | Limited confidence | Minimal evidence |
| VUS | Uncertain | Insufficient data |

## ClinVar Classification Map

| ClinVar | Interpretation |
|---------|----------------|
| Pathogenic | Disease-causing |
| Likely pathogenic | 90%+ confidence pathogenic |
| VUS | Uncertain significance |
| Likely benign | 90%+ confidence benign |
| Benign | Not disease-causing |
| Conflicting | Multiple interpretations |

## gnomAD Frequency Thresholds (Rare Disease)

| Frequency | ACMG Code | Interpretation |
|-----------|-----------|----------------|
| Absent | PM2_Supporting | Absent from controls |
| <0.00001 | PM2_Supporting | Extremely rare |
| <0.0001 | - | Rare (use with caution) |
| >0.01 | BS1/BA1 | Too common for rare disease |

## COSMIC Somatic Evidence

| COSMIC Finding | Interpretation | ACMG Support |
|----------------|----------------|--------------|
| Recurrent hotspot (>100 samples) | Known oncogenic driver | PS3 (functional) |
| Moderate frequency (10-100) | Likely oncogenic | PM1 (hotspot) |
| Rare somatic (<10) | Unknown significance | No support |

## DisGeNET Score Interpretation

| GDA Score | Evidence Level | ACMG Support |
|-----------|----------------|--------------|
| >0.7 | Strong | PP4 (phenotype) |
| 0.4-0.7 | Moderate | Supporting |
| <0.4 | Weak | Insufficient |

## ClinGen Validity Levels (for ACMG PM1/PP4)

| Classification | Meaning | ACMG Impact |
|----------------|---------|-------------|
| **Definitive** | Multiple concordant studies | Strong gene-disease support |
| **Strong** | Extensive evidence | Moderate-strong support |
| **Moderate** | Some evidence | Moderate support |
| **Limited** | Minimal evidence | Weak support, use caution |
| **Disputed** | Conflicting evidence | Do not use for classification |
| **Refuted** | Evidence against | Gene NOT associated |

## ClinGen Dosage Sensitivity Scores (for CNV interpretation)

| Score | Meaning | Interpretation |
|-------|---------|----------------|
| **3** | Sufficient evidence | Haploinsufficiency/triplosensitivity established |
| **2** | Emerging evidence | Some support, not definitive |
| **1** | Little evidence | Minimal support |
| **0** | No evidence | Unknown |

## Structural Impact Categories

| Impact Level | Description | ACMG Support |
|--------------|-------------|--------------|
| **Critical** | Active site, catalytic residue | PM1 (strong) |
| **High** | Buried residue, disulfide, structural core | PM1 (moderate) |
| **Moderate** | Domain interface, binding site | PM1 (supporting) |
| **Low** | Surface, flexible region | No support |

## Structural Impact Confidence (AlphaFold pLDDT)

| pLDDT Range | Interpretation |
|-------------|----------------|
| >90 | Very high confidence in position |
| 70-90 | High confidence |
| 50-70 | Moderate (often loops) |
| <50 | Low confidence (disorder) |

## Prediction Thresholds

| Predictor | Damaging | Benign |
|-----------|----------|--------|
| **AlphaMissense** | >0.564 | <0.34 |
| **CADD PHRED** | >=20 (top 1%) | <15 |
| **EVE** | >0.5 | <=0.5 |
| SIFT | <0.05 | >=0.05 |
| PolyPhen2 | >0.85 (probably) | <0.15 (benign) |

## PP3/BP4 Application Notes

- **PP3**: Multiple concordant damaging predictions (AlphaMissense + CADD + EVE agreement = strong PP3)
- **BP4**: Multiple concordant benign predictions
- **Note**: AlphaMissense alone achieves ~90% accuracy on ClinVar pathogenic variants

## SpliceAI Thresholds

| Max Delta Score | Interpretation | ACMG Support |
|-----------------|----------------|--------------|
| >=0.8 | High pathogenicity | PP3 (strong) for splice-altering |
| 0.5-0.8 | Moderate | PP3 (supporting) |
| 0.2-0.5 | Low | Weak evidence |
| <0.2 | Likely benign | BP7 (if synonymous) |

## Literature Evidence Weights

| Evidence | ACMG Code | Weight |
|----------|-----------|--------|
| Functional study (null) | PS3 | Strong |
| Functional study (reduced) | PS3_Moderate | Moderate |
| Case reports with segregation | PP1 | Supporting to Moderate |
| Co-occurrence with pathogenic | BP2 | Supporting against |

## Regulatory Impact Categories

| Category | Criteria | ACMG Support |
|----------|----------|--------------|
| **High impact** | Disrupts known TF binding motif | PP3 (supporting) |
| **Moderate impact** | In active regulatory region | Consider context |
| **Low impact** | No regulatory annotation | No support |

## PVS1 Application for Truncating Variants

| Scenario | PVS1 Strength |
|----------|---------------|
| Canonical LOF gene, NMD predicted | Very Strong |
| LOF gene, last exon | Moderate |
| Non-LOF gene | Not applicable |
