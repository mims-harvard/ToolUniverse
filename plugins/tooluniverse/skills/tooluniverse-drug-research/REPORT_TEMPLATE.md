# Drug Research Report Template

Initial report template to create before any tool calls. File name: `[DRUG]_drug_report.md`

---

## Template

```markdown
# Drug Research Report: [DRUG NAME]

**Generated**: [Date] | **Query**: [Original query] | **Status**: In Progress

---

## Executive Summary
[Researching...]

---

## 1. Compound Identity
### 1.1 Database Identifiers
[Researching...]
### 1.2 Structural Information
[Researching...]
### 1.3 Names & Synonyms
[Researching...]

---

## 2. Chemical Properties
### 2.1 Physicochemical Profile
[Researching...]
### 2.2 Drug-Likeness Assessment
[Researching...]
### 2.3 Solubility & Permeability
[Researching...]
### 2.4 Salt Forms & Polymorphs
[Researching...]
### 2.5 Structure Visualization
[Researching...]

---

## 3. Mechanism & Targets
### 3.1 Primary Mechanism of Action
[Researching...]
### 3.2 Primary Target(s)
[Researching...]
### 3.3 Target Selectivity & Off-Targets
[Researching...]
### 3.4 Bioactivity Profile (ChEMBL)
[Researching...]

---

## 4. ADMET Properties
### 4.1 Absorption
[Researching...]
### 4.2 Distribution
[Researching...]
### 4.3 Metabolism
[Researching...]
### 4.4 Excretion
[Researching...]
### 4.5 Toxicity Predictions
[Researching...]

---

## 5. Clinical Development
### 5.1 Development Status
[Researching...]
### 5.2 Clinical Trial Landscape
[Researching...]
### 5.3 Approved Indications
[Researching...]
### 5.4 Investigational Indications
[Researching...]
### 5.5 Key Efficacy Data
[Researching...]
### 5.6 Biomarkers & Companion Diagnostics
[Researching...]

---

## 6. Safety Profile
### 6.1 Clinical Adverse Events
[Researching...]
### 6.2 Post-Marketing Safety (FAERS)
[Researching...]
### 6.3 Black Box Warnings
[Researching...]
### 6.4 Contraindications
[Researching...]
### 6.5 Drug-Drug Interactions
[Researching...]
### 6.5.2 Drug-Food Interactions
[Researching...]
### 6.6 Dose Modification Guidance
[Researching...]
### 6.7 Drug Combinations & Regimens
[Researching...]

---

## 7. Pharmacogenomics
### 7.1 Relevant Pharmacogenes
[Researching...]
### 7.2 Clinical Annotations
[Researching...]
### 7.3 Dosing Guidelines (CPIC/DPWG)
[Researching...]
### 7.4 Actionable Variants
[Researching...]

---

## 8. Regulatory & Labeling
### 8.1 Approval Status
[Researching...]
### 8.2 Label Highlights
[Researching...]
### 8.3 Patents & Exclusivity
[Researching...]
### 8.4 Label Changes & Warnings
[Researching...]
### 8.5 Special Populations
[Researching...]
### 8.6 Regulatory Timeline & History
[Researching...]

---

## 9. Literature & Research Landscape
### 9.1 Publication Metrics
[Researching...]
### 9.2 Research Themes
[Researching...]
### 9.3 Recent Key Publications
[Researching...]
### 9.4 Real-World Evidence
[Researching...]

---

## 10. Conclusions & Assessment
### 10.1 Drug Profile Scorecard
[Researching...]
### 10.2 Key Strengths
[Researching...]
### 10.3 Key Concerns/Limitations
[Researching...]
### 10.4 Research Gaps
[Researching...]
### 10.5 Comparative Analysis
[Researching...]

---

## 11. Data Sources & Methodology
### 11.1 Primary Data Sources
[Researching...]
### 11.2 Tool Call Summary
[Researching...]
### 11.3 Quality Control Metrics
[Researching...]
```

Then progressively replace `[Researching...]` with actual findings as you query each tool.

---

## Citation Format

For each data section, include source attribution:

```markdown
*Source: PubChem via `PubChem_get_compound_properties_by_CID` (CID: 4091)*
```

Block citation at section end:

```markdown
---
**Data Sources for this section:**
- PubChem: `PubChem_get_compound_properties_by_CID` (CID: 4091)
- ChEMBL: `ChEMBL_get_activity` (CHEMBL1431)
- DGIdb: `DGIdb_get_drug_info` (metformin)
---
```

---

## Evidence Grading System

| Tier | Symbol | Description | Example |
|------|--------|-------------|---------|
| **T1** | three stars | Phase 3 RCT, meta-analysis, FDA approval | Pivotal trial, label indication |
| **T2** | two stars | Phase 1/2 trial, large case series | Dose-finding study |
| **T3** | one star | In vivo animal, in vitro cellular | Mouse PK study |
| **T4** | no stars | Review mention, computational prediction | ADMET-AI prediction |

Apply inline: `Metformin reduces hepatic glucose output via AMPK activation [T1: FDA Label].`

Include per-section quality summary:
```markdown
**Evidence Quality**: Strong (156 Phase 3 trials)
**Data Confidence**: High - mature clinical program
```

---

## Drug Profile Scorecard (Section 10.1)

```markdown
| Criterion | Score (1-5) | Rationale |
|-----------|-------------|-----------|
| **Efficacy Evidence** | 5 | Multiple Phase 3 trials, decades of use |
| **Safety Profile** | 4 | Well-tolerated; rare but serious risks |
| **PK/ADMET** | 4 | Good bioavailability; known clearance |
| **Target Validation** | 4 | Mechanism well-established |
| **Competitive Position** | 3 | First-line but alternatives exist |
| **Overall** | 4.0 | **Strong drug profile** |

**Interpretation**: 5 = Excellent, 4 = Good, 3 = Moderate, 2 = Concerning, 1 = Poor
```

---

## Completeness Audit Template (Section 11)

```markdown
## Report Completeness Audit

**Overall Completeness**: XX% (N/M minimum requirements met)

### Missing Data Items
| Section | Missing Item | Recommended Action |
|---------|--------------|-------------------|
| 2 | Salt forms | Call DailyMed chemistry section |

### Tool Failures Encountered
| Tool | Error | Fallback Used |
|------|-------|---------------|
| `PharmGKB_search_drugs` | API timeout | DailyMed label PGx sections |

### Data Confidence Assessment
| Section | Confidence | Evidence Tier |
|---------|-----------|---------------|
| 1. Identity | High | T1 |
| 4. ADMET | Medium | T2 |

### Cross-Source Validation
| Property | Source 1 | Source 2 | Agreement |
|----------|---------|---------|-----------|
| MW | 378.88 (PubChem) | 378.88 (ChEMBL) | Exact match |

### Evidence Distribution
| Tier | Count | Percentage |
|------|-------|------------|
| T1 | 45 | 65% |
| T2 | 18 | 26% |
| T3 | 5 | 7% |
| T4 | 1 | 1% |
```
