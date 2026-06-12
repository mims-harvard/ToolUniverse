# Antibody Engineering - Checklists & Scoring

Evidence grading, completeness checklists, and special consideration notes for the antibody engineering workflow.

---

## Evidence Grading System

| Tier | Criteria |
|------|----------|
| **T1** | Humanness >85%, KD <2 nM, Developability >75, Low immunogenicity |
| **T2** | Humanness 70-85%, KD 2-10 nM, Developability 60-75, Medium immunogenicity |
| **T3** | Humanness <70%, KD >10 nM, Developability <60, or High immunogenicity |
| **T4** | Failed validation or major liabilities |

---

## Completeness Checklist

### Phase 1: Input Analysis
- [ ] Sequence annotated (CDRs, frameworks)
- [ ] Species identified
- [ ] Target antigen characterized
- [ ] Clinical precedents identified

### Phase 2: Humanization
- [ ] Germline genes identified (IMGT)
- [ ] Framework selected
- [ ] CDR grafting designed
- [ ] Backmutations analyzed
- [ ] At least 2 humanized variants designed

### Phase 3: Structure
- [ ] AlphaFold structure predicted
- [ ] CDR conformations analyzed
- [ ] Epitope mapped
- [ ] Structural quality assessed

### Phase 4: Affinity
- [ ] Current affinity estimated
- [ ] Affinity mutations proposed
- [ ] CDR optimization strategies identified
- [ ] Testing plan outlined

### Phase 5: Developability
- [ ] Aggregation assessed
- [ ] PTM sites identified
- [ ] Stability predicted
- [ ] Expression predicted
- [ ] Overall score calculated (0-100)

### Phase 6: Immunogenicity
- [ ] T-cell epitopes predicted (IEDB)
- [ ] Immunogenicity score calculated
- [ ] Deimmunization strategy proposed
- [ ] Clinical precedent comparison

### Phase 7: Manufacturing
- [ ] Expression system assessed
- [ ] Purification strategy outlined
- [ ] Formulation recommended
- [ ] CMC timeline estimated

### Phase 8: Final Report
- [ ] Ranked variant list
- [ ] Top candidate recommended
- [ ] Experimental validation plan
- [ ] Backup variants identified
- [ ] Next steps outlined

---

## Special Considerations

### Bispecific Antibody Engineering
- Use STRING tools to identify co-expressed targets
- Design separate binding arms for each target
- Consider asymmetric formats (e.g., CrossMAb, DuoBody)
- Assess aggregation risk (higher for bispecifics)

### pH-Dependent Binding
- Add His residues at interface (pKa ~6.0)
- Target: Bind at pH 7.4, release at pH 6.0
- Improves PK via FcRn recycling
- Useful for tumor targeting (acidic microenvironment)

### Affinity Ceiling
- Most therapeutic antibodies: KD 0.1-10 nM
- <0.1 nM: May cause target-mediated clearance
- 1-5 nM: Sweet spot for most targets
- Balance affinity vs. developability

### Developability Scoring Weights
| Component | Weight | Description |
|-----------|--------|-------------|
| Aggregation | 0.30 | Most critical factor |
| PTM liability | 0.25 | Deamidation, isomerization, oxidation, glycosylation |
| Stability | 0.20 | Thermal stability (Tm target >70C) |
| Expression | 0.15 | CHO expression level |
| Solubility | 0.10 | Formulation concentration |

### Immunogenicity Risk Scoring
- T-cell epitope count x 10 points each
- Non-human residues x 5 points each
- Aggregation-related: overall_risk x 20
- Total 0-100 (lower is better): Low <30, Medium 30-60, High >60

### Key PTM Motifs to Check
| Motif | PTM Type | Risk |
|-------|----------|------|
| NG | Deamidation | High |
| NS | Deamidation | Medium |
| DG, DS | Isomerization | High |
| Met, Trp | Oxidation | Medium |
| N-X-S/T (X!=P) | N-glycosylation | Variable |
