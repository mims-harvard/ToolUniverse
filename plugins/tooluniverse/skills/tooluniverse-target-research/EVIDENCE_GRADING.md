# Evidence Grading & Completeness Audit

Evidence grading system and completeness requirements for target intelligence reports.

## Evidence Tiers

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | three stars | Direct mechanistic evidence, human genetic proof | CRISPR KO, patient mutations, crystal structure with mechanism |
| **T2** | two stars | Functional studies, model organism validation | siRNA phenotype, mouse KO, biochemical assay |
| **T3** | one star | Association, screen hits, computational | GWAS hit, DepMap essentiality, expression correlation |
| **T4** | no stars | Mention, review, text-mined, predicted | Review article, database annotation, computational prediction |

## Required Evidence Grading Locations

Evidence grades MUST appear in:
1. **Executive Summary** - Key disease claims graded
2. **Section 8.2 Disease Associations** - Every disease link graded with source type
3. **Section 11 Literature** - Key papers table with evidence tier
4. **Section 13 Recommendations** - Scorecard items reference evidence quality

## Per-Section Evidence Summary Format

```markdown
---
**Evidence Quality for this Section**: Strong
- Mechanistic (T1): 12 papers
- Functional (T2): 8 papers
- Association (T3): 15 papers
- Mention (T4): 23 papers
**Data Gaps**: No CRISPR data; mouse KO phenotypes limited
---
```

## Citation Format

Every piece of information MUST include its source:

```markdown
EGFR mutations cause lung adenocarcinoma [three stars: PMID:15118125, activating mutations
in patients]. *Source: ClinVar, CIViC*
```

## ClinVar SNV vs CNV Separation

Always separate single nucleotide variants from copy number variants:

```markdown
### 8.3 Clinical Variants (ClinVar)

#### Single Nucleotide Variants (SNVs)
| Variant | Clinical Significance | Condition | Review Status | PMID |
|---------|----------------------|-----------|---------------|------|
| p.L858R | Pathogenic | Lung cancer | 4 stars | 15118125 |

**Total Pathogenic SNVs**: 47

#### Copy Number Variants (CNVs) - Reported Separately
| Type | Region | Clinical Significance | Frequency |
|------|--------|----------------------|-----------|
| Amplification | 7p11.2 | Pathogenic | Common in cancer |

*Note: CNV data separated as it represents different mutation mechanism*
```

## DisGeNET Evidence Tier Assignment

- DisGeNET Score >= 0.7 -> Consider T2 evidence (multiple validated sources)
- DisGeNET Score 0.4-0.7 -> Consider T3 evidence
- DisGeNET Score < 0.4 -> T4 evidence only

---

## Minimum Data Requirements (Enforced)

| Section | Minimum Data | If Not Met |
|---------|--------------|------------|
| **6. PPIs** | >= 20 interactors | Document which tools failed + why |
| **7. Expression** | Top 10 tissues with TPM + HPA RNA summary | Note "limited data" with specific gaps |
| **8. Disease** | Top 10 OT diseases + gnomAD constraints + ClinVar summary | Separate SNV/CNV; note if constraint unavailable |
| **9. Druggability** | OT tractability + probes + drugs + DGIdb + GtoPdb fallback | "No drugs/probes" is valid data |
| **11. Literature** | Total count + 5-year trend + 3-5 key papers with evidence tiers | Note if sparse (<50 papers) |

## Post-Run Completeness Audit

Before finalizing the report, run this checklist:

### Data Minimums Check
- [ ] PPIs: >= 20 interactors OR explanation why fewer
- [ ] Expression: Top 10 tissues with values OR explicit "unavailable"
- [ ] Diseases: Top 10 associations with scores OR "no associations"
- [ ] Constraints: All 4 scores (pLI, LOEUF, missense Z, pRec) OR "unavailable"
- [ ] Druggability: All modalities assessed; probes + drugs listed OR "none"

### Negative Results Documented
- [ ] Empty tool results noted explicitly (not left blank)
- [ ] Failed tools with fallbacks documented
- [ ] "No data" sections have implications noted

### Evidence Quality
- [ ] T1-T4 grades in Executive Summary disease claims
- [ ] T1-T4 grades in Disease Associations table
- [ ] Key papers table has evidence tiers
- [ ] Per-section evidence summaries included

### Source Attribution
- [ ] Every data point has source tool/database cited
- [ ] Section-end source summaries present

## Data Gap Table (Required if minimums not met)

```markdown
## 15. Data Gaps & Limitations

| Section | Expected Data | Actual | Reason | Alternative Source |
|---------|---------------|--------|--------|-------------------|
| 6. PPIs | >= 20 interactors | 8 | Novel target, limited studies | Literature review needed |
| 7. Expression | GTEx TPM | None | Versioned ID not recognized | See HPA data |
| 9. Probes | Chemical probes | None | No validated probes exist | Consider tool compound dev |

**Recommendations for Data Gaps**:
1. For PPIs: Query BioGRID with broader parameters; check yeast-2-hybrid studies
2. For Expression: Query GEO directly for tissue-specific datasets
```
