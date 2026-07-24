# Report Templates: Chemical Safety Assessment

## Output Report Structure

All analyses generate a structured markdown report:

```markdown
# Chemical Safety & Toxicology Report: [Compound Name]

**Generated**: YYYY-MM-DD HH:MM
**Compound**: [Name] | SMILES: [SMILES] | CID: [CID]

## Executive Summary
[2-3 sentence overview with risk classification and key findings, all graded]

## 1. Compound Identity
[Phase 0 results - disambiguation table]

## 2. Predictive Toxicology
[Phase 1 results - ADMET-AI toxicity endpoints]

## 3. ADMET Profile
[Phase 2 results - absorption, distribution, metabolism, excretion]

## 4. Toxicogenomics
[Phase 3 results - CTD chemical-gene-disease relationships]

## 5. Regulatory Safety
[Phase 4 results - FDA label information]

## 6. Drug Safety Profile
[Phase 5 results - DrugBank data]

## 7. Chemical-Protein Interactions
[Phase 6 results - STITCH network]

## 8. Structural Alerts
[Phase 7 results - ChEMBL alerts]

## 9. Integrated Risk Assessment
[Synthesis - risk classification, evidence summary, data gaps, recommendations]

## Appendix: Methods and Data Sources
[Tool versions, databases queried, date of access]
```

---

## Completeness Checklist

Before finalizing any report, verify:

- [ ] **Phase 0**: Compound fully disambiguated (SMILES + CID at minimum)
- [ ] **Phase 1**: At least 5 toxicity endpoints reported or "prediction unavailable" noted
- [ ] **Phase 2**: ADMET profile with A/D/M/E sections or "not available" noted
- [ ] **Phase 3**: CTD queried; gene interactions and disease associations reported or "no data in CTD"
- [ ] **Phase 4**: FDA labels queried; results or "not an FDA-approved drug" noted
- [ ] **Phase 5**: DrugBank queried; results or "not found in DrugBank" noted
- [ ] **Phase 6**: STITCH queried; results or "no STITCH data available" noted
- [ ] **Phase 7**: Structural alerts checked or "ChEMBL ID not available" noted
- [ ] **Synthesis**: Risk classification provided with evidence summary
- [ ] **Evidence Grading**: All findings have [T1]-[T4] annotations
- [ ] **Data Gaps**: Explicitly listed in synthesis section

---

## Example Tables

### Compound Identity
```markdown
| Property | Value |
|----------|-------|
| **Name** | Acetaminophen |
| **PubChem CID** | 1983 |
| **SMILES** | CC(=O)Nc1ccc(O)cc1 |
| **Formula** | C8H9NO2 |
| **Molecular Weight** | 151.16 |
```

### Toxicity Predictions [T3]
```markdown
| Endpoint | Prediction | Interpretation | Concern Level |
|----------|-----------|---------------|---------------|
| AMES Mutagenicity | Inactive | No mutagenic signal | Low |
| ClinTox | Active | Clinical toxicity signal | HIGH |
| DILI | Active | Drug-induced liver injury risk | HIGH |
| LD50 (Zhu) | 2.45 log(mg/kg) | ~282 mg/kg (moderate) | Medium |
| hERG Inhibition | Active | Cardiac arrhythmia risk | HIGH |
```

### ADMET Profile
```markdown
#### Absorption
| Property | Value | Interpretation |
|----------|-------|----------------|
| BBB Penetrance | Yes | Crosses blood-brain barrier |
| Bioavailability (F20%) | 85% | Good oral absorption |

#### Metabolism
| CYP Enzyme | Substrate | Inhibitor |
|------------|-----------|-----------|
| CYP1A2 | No | No |
| CYP3A4 | Yes | Yes (DDI risk) |
```

### Integrated Risk Assessment
```markdown
### Overall Risk Classification: [HIGH]

| Dimension | Finding | Evidence Tier | Concern |
|-----------|---------|--------------|---------|
| ADMET Toxicity | DILI active, hERG active | [T3] | HIGH |
| FDA Label | Boxed warning for hepatotoxicity | [T1] | CRITICAL |
| CTD Toxicogenomics | 156 gene interactions | [T2] | HIGH |

### Key Safety Concerns
1. **Hepatotoxicity** [T1]: FDA boxed warning + ADMET-AI DILI + CTD liver associations
2. **Cardiac Risk** [T3]: hERG prediction + STITCH hERG interaction

### Data Gaps
- [ ] No in vivo genotoxicity data
- [ ] STITCH scores moderate (700-900)

### Recommendations
1. Avoid doses >4g/day [T1]
2. Monitor liver function in chronic use [T1]
3. Screen for CYP3A4 interactions [T3]
```

---

## Common Use Patterns

| Pattern | Input | Key Phases |
|---------|-------|-----------|
| Novel Compound | SMILES string | 0, 1, 2, 7, Synthesis |
| Approved Drug Review | Drug name | All phases (0-7) |
| Environmental Chemical | Chemical name | 0, 1, 2, 3 (CTD key), 6, Synthesis |
| Batch Screening | Multiple SMILES | 0, 1 (batch), 2 (batch), Synthesis |
| Toxicogenomic Deep-Dive | Chemical + gene/disease | 0, 3 (expanded), Synthesis |
