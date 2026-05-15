# Clinical Variant Interpreter Checklist

Pre-delivery verification checklist for variant interpretation reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `{GENE}_{VARIANT}_interpretation_report.md`
- [ ] All 9 main sections present
- [ ] Executive summary completed (not `[Interpreting...]`)
- [ ] Data sources section populated

### Phase 1: Variant Identity
- [ ] Gene symbol identified
- [ ] HGVS c. notation provided
- [ ] HGVS p. notation (if applicable)
- [ ] Transcript ID (MANE Select preferred)
- [ ] Consequence type identified
- [ ] Exon/intron location stated
- [ ] Amino acid change (for missense)

### Phase 2: Population Data
- [ ] gnomAD queried
- [ ] Overall allele frequency reported
- [ ] ≥3 ancestry-specific frequencies
- [ ] Homozygote count reported
- [ ] Hemizygote count (X-linked genes)
- [ ] Frequency interpreted vs. disease prevalence

### Phase 3: Clinical Database Evidence
- [ ] ClinVar searched
- [ ] Classification reported (or "Not in ClinVar")
- [ ] Review status noted (gold stars)
- [ ] Number of submissions documented
- [ ] Conflicting interpretations noted (if any)
- [ ] OMIM gene-disease associations checked
- [ ] ClinGen gene validity (if available)

### Phase 4: Computational Predictions
- [ ] ≥3 predictors reported
- [ ] SIFT score and interpretation
- [ ] PolyPhen-2 score and interpretation
- [ ] CADD score (raw and phred)
- [ ] Concordance assessed (agree/disagree)
- [ ] PP3 or BP4 applied appropriately

### Phase 5: Structural Analysis (for missense)
- [ ] Protein structure source identified (PDB/AlphaFold)
- [ ] pLDDT at variant position (if AlphaFold)
- [ ] Residue location (buried/surface)
- [ ] Secondary structure context
- [ ] Domain/functional site proximity
- [ ] PM1 consideration documented

### Phase 6: Literature Evidence
- [ ] PubMed searched with ≥2 strategies
- [ ] Functional studies documented (or "None found")
- [ ] Case reports documented
- [ ] PS3 consideration documented
- [ ] PP1 (segregation) documented if available

### Phase 7: ACMG Classification
- [ ] All evidence codes explicitly listed
- [ ] Each code has strength modifier
- [ ] Code justification provided
- [ ] Classification calculated correctly
- [ ] Classification stated in executive summary

### Phase 8: Clinical Recommendations
- [ ] Recommendations appropriate to classification
- [ ] VUS: No medical decisions
- [ ] Pathogenic: Specific follow-up
- [ ] Family screening addressed

### Phase 9: Limitations
- [ ] Missing data acknowledged
- [ ] Conflicting evidence noted
- [ ] Uncertainty quantified

---

## Citation Requirements

### Every Evidence Statement Must Include
- [ ] Source database/tool in backticks
- [ ] Specific identifier (ClinVar ID, PMID)
- [ ] Date of access (for changing databases)

### Format Examples
```markdown
*Source: ClinVar VCV000012345, reviewed 4-star, accessed 2026-02-04*
*Source: gnomAD v4.0, overall AF=0.00001, accessed 2026-02-04*
*Source: PMID 12345678 - functional study showed loss of activity*
*Source: AlphaFold DB via `alphafold_get_prediction`, pLDDT=92 at position*
```

---

## ACMG Code Verification

### For Each Code Applied
- [ ] Code abbreviation correct (PVS1, PM2, PP3, etc.)
- [ ] Strength appropriate (VeryStrong/Strong/Moderate/Supporting)
- [ ] Evidence clearly supports application
- [ ] Not double-counted

### Common Errors to Avoid
- [ ] PM2 without checking gnomAD
- [ ] PP3 without multiple concordant predictions
- [ ] PVS1 for non-null variants
- [ ] PS3 without true functional evidence
- [ ] Applying same evidence to multiple codes

---

## Classification Calculation

### Verify Math
| Classification | Minimum Evidence |
|----------------|-----------------|
| Pathogenic | ≥1 VeryStrong + ≥1 Strong/Moderate |
| Likely Pathogenic | ≥1 Strong + ≥2 Moderate |
| VUS | Insufficient evidence |
| Likely Benign | ≥1 Strong + ≥1 Supporting (benign) |
| Benign | ≥1 StandAlone OR ≥2 Strong (benign) |

### Classification Cross-Check
- [ ] Evidence codes align with final classification
- [ ] No conflicting codes ignored
- [ ] Classification matches standard algorithms

---

## Evidence Grading

### All Classifications Must Have
- [ ] Classification tier: ★★★, ★★☆, ★☆☆, or VUS
- [ ] Evidence strength description
- [ ] Key supporting evidence highlighted

### Tier Definitions
| Tier | Symbol | Criteria |
|------|--------|----------|
| High confidence | ★★★ | Multiple independent lines, no conflicts |
| Moderate confidence | ★★☆ | Good evidence, minor gaps |
| Limited confidence | ★☆☆ | Minimal evidence, apply with caution |
| Uncertain | VUS | Insufficient to classify |

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Population frequencies | gnomAD + ≥3 ancestry groups |
| Computational predictors | ≥3 tools |
| Literature searches | ≥2 search strategies |
| ACMG codes | All applicable documented |
| Clinical recommendations | ≥1 per classification type |

---

## Structural Analysis Quality (for Missense)

### Must Include
- [ ] Structure source (PDB ID or "AlphaFold predicted")
- [ ] pLDDT at position (if AlphaFold)
- [ ] Residue depth/accessibility
- [ ] Structural consequence prediction

### Quality Thresholds
| Metric | Confident | Uncertain |
|--------|-----------|-----------|
| pLDDT | >70 | <70 |
| PDB Resolution | <3.0 Å | >3.0 Å |

---

## Special Scenario Checks

### Truncating Variants
- [ ] NMD prediction assessed
- [ ] LOF mechanism confirmed for gene
- [ ] PVS1 strength correctly applied
- [ ] Last exon exception considered

### Splice Variants
- [ ] Canonical splice site distance
- [ ] SpliceAI scores (if available)
- [ ] In-frame skip assessment
- [ ] PVS1 modified if warranted

### X-linked Genes
- [ ] Sex of individual considered
- [ ] Hemizygote frequency used appropriately
- [ ] Penetrance in females addressed

---

## Output Files

### Required
- [ ] `{GENE}_{VARIANT}_interpretation_report.md` - Main report

### Optional Data Export
- [ ] `{GENE}_{VARIANT}_evidence_table.csv` - Structured evidence
- [ ] `{GENE}_{VARIANT}_acmg_codes.csv` - Applied codes

---

## Final Review

### Before Delivery
- [ ] No `[Interpreting...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] Executive summary synthesizes findings
- [ ] Classification stated prominently
- [ ] Clinical recommendations actionable
- [ ] Limitations clearly stated

### Common Issues to Avoid
- [ ] Missing gnomAD frequencies
- [ ] Classification without evidence codes
- [ ] Recommendations not matching classification
- [ ] Missing literature search
- [ ] Structure analysis skipped for VUS missense
- [ ] ACMG codes without justification

---

## ClinVar-Specific Checks

### When Variant in ClinVar
- [ ] VCV ID documented
- [ ] Review status (stars) noted
- [ ] Number of submitters
- [ ] Date of last evaluation
- [ ] Concordance with our assessment

### When Variant NOT in ClinVar
- [ ] Explicitly state "Not in ClinVar as of {date}"
- [ ] Consider novel variant workflow
- [ ] Emphasize structural analysis

---

## Tool Verification Checklist

### Before Report Generation
- [ ] `clinvar_search_variants` returns results or "not found"
- [ ] `gnomad_search_variants` frequency values valid
- [ ] `MyVariant_query_variants` predictions populated
- [ ] Structure available (PDB or AlphaFold)

### NVIDIA NIM Availability
- [ ] Check if structural analysis needed
- [ ] Confirm NVIDIA_API_KEY if using NvidiaNIM_alphafold2
- [ ] Document if fallback used

---

## Recommendations Matrix

### Match Recommendations to Classification

| Classification | Testing | Management | Family |
|----------------|---------|------------|--------|
| Pathogenic | Confirm | Specific action | Cascade |
| Likely Path | Confirm | Specific action | Cascade |
| VUS | Monitor | Clinical judgment | Not for testing |
| Likely Benign | No repeat | Reassurance | Not needed |
| Benign | No repeat | Reassurance | Not needed |

---

## Report Completeness Score

Calculate before delivery:

| Section | Points |
|---------|--------|
| Variant identity complete | 10 |
| gnomAD with ancestry | 10 |
| ClinVar documented | 10 |
| ≥3 predictors | 10 |
| Structural analysis | 15 |
| Literature search | 10 |
| ACMG codes with rationale | 20 |
| Clinical recommendations | 10 |
| Limitations stated | 5 |

**Minimum passing score**: 85/100
