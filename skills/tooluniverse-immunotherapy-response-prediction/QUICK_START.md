# Immunotherapy Response Prediction - Quick Start

## Basic Usage

### Predict ICI response for a melanoma patient
```
Patient has melanoma with BRAF V600E and TP53 R175H mutations, TMB 18 mut/Mb, PD-L1 60%, MSS status. Predict immunotherapy response.
```

### NSCLC with high PD-L1
```
Predict ICI response: NSCLC, PD-L1 TPS 90%, TMB 12 mut/Mb, no STK11 or EGFR mutations.
```

### MSI-high colorectal cancer
```
Colorectal cancer patient, MSI-high, TMB 45 mut/Mb. What checkpoint inhibitor should be used?
```

### Low biomarker NSCLC (resistance scenario)
```
NSCLC patient with TMB 3 mut/Mb, PD-L1 <1%, STK11 loss of function mutation. Predict immunotherapy response and recommend alternatives.
```

### Bladder cancer with moderate biomarkers
```
Predict ICI response for urothelial carcinoma: TMB 14 mut/Mb, PD-L1 CPS 12, no resistance mutations detected.
```

### ICI drug selection query
```
Which checkpoint inhibitor should I use for NSCLC with PD-L1 TPS 55% and TMB 22? Patient has no resistance mutations.
```

## What You Get

The skill produces a comprehensive report with:

1. **ICI Response Score** (0-100) with transparent component breakdown
2. **Response Likelihood** tier (HIGH/MODERATE/LOW)
3. **Biomarker Analysis** for each component (TMB, MSI, PD-L1, neoantigens)
4. **Mutation Analysis** including resistance and sensitivity factors
5. **ICI Drug Recommendation** with specific agents and evidence
6. **Clinical Trial Evidence** for this cancer + biomarker profile
7. **Monitoring Plan** for treatment response
8. **Alternative Strategies** if ICI response predicted to be low

## Input Requirements

### Required
- **Cancer type**: Melanoma, NSCLC, bladder, RCC, HNSCC, CRC, etc.
- **At least one of**: Mutation list OR TMB value

### Optional (improves accuracy)
- PD-L1 expression (% TPS or CPS)
- MSI status (MSI-H, MSS, unknown)
- Specific ICI drug being considered
- Prior treatments
- Immune cell infiltration data

## Score Interpretation

| Score | Response Likelihood | Expected ORR | Action |
|-------|-------------------|-------------|--------|
| 70-100 | HIGH | 50-80% | Strong ICI candidate |
| 40-69 | MODERATE | 20-50% | Consider ICI, combo preferred |
| 0-39 | LOW | <20% | Alternatives recommended |
