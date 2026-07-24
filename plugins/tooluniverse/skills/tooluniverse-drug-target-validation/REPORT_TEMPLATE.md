# Drug Target Validation - Report Template

Use this template to create the validation report file: `[TARGET]_[DISEASE]_validation_report.md`

---

## Report Structure

```markdown
# Drug Target Validation Report: [TARGET]

**Target**: [Gene Symbol] ([Full Name])
**Disease Context**: [Disease Name] (if provided)
**Modality**: [Small molecule / Antibody / etc.] (if specified)
**Generated**: [Date]
**Status**: In Progress

---

## Executive Summary

**Target Validation Score**: [XX/100]
**Priority Tier**: [Tier X] - [Description]
**Recommendation**: [GO / CONDITIONAL GO / CAUTION / NO-GO]

**Key Findings**:
- [1-sentence disease association strength with evidence grade]
- [1-sentence druggability assessment]
- [1-sentence safety profile]
- [1-sentence clinical precedent]

**Critical Risks**:
- [Top risk 1]
- [Top risk 2]

---

## Validation Scorecard

| Dimension | Score | Max | Assessment | Key Evidence |
|-----------|-------|-----|------------|--------------|
| **Disease Association** | | 30 | | |
| - Genetic evidence | | 10 | | |
| - Literature evidence | | 10 | | |
| - Pathway evidence | | 10 | | |
| **Druggability** | | 25 | | |
| - Structural tractability | | 10 | | |
| - Chemical matter | | 10 | | |
| - Target class | | 5 | | |
| **Safety Profile** | | 20 | | |
| - Expression selectivity | | 5 | | |
| - Genetic validation | | 10 | | |
| - Known ADRs | | 5 | | |
| **Clinical Precedent** | | 15 | | |
| **Validation Evidence** | | 10 | | |
| - Functional studies | | 5 | | |
| - Disease models | | 5 | | |
| **TOTAL** | **XX** | **100** | **[Tier]** | |

---

## 1. Target Identity
[Researching...]

## 2. Disease Association Evidence
### 2.1 OpenTargets Disease Associations
[Researching...]
### 2.2 GWAS Genetic Evidence
[Researching...]
### 2.3 Constraint Scores (gnomAD)
[Researching...]
### 2.4 Literature Evidence
[Researching...]

## 3. Druggability Assessment
### 3.1 Tractability (OpenTargets)
[Researching...]
### 3.2 Target Classification
[Researching...]
### 3.3 Structural Tractability
[Researching...]
### 3.4 Chemical Probes & Enabling Packages
[Researching...]

## 4. Known Modulators & Chemical Matter
### 4.1 Approved/Clinical Drugs
[Researching...]
### 4.2 ChEMBL Bioactivity
[Researching...]
### 4.3 BindingDB Ligands
[Researching...]
### 4.4 PubChem Bioassays
[Researching...]
### 4.5 Chemical Probes
[Researching...]

## 5. Clinical Precedent
### 5.1 FDA-Approved Drugs
[Researching...]
### 5.2 Clinical Trial Landscape
[Researching...]
### 5.3 Failed Programs & Lessons
[Researching...]

## 6. Safety & Toxicity Profile
### 6.1 OpenTargets Safety Liabilities
[Researching...]
### 6.2 Expression in Critical Tissues
[Researching...]
### 6.3 Knockout Phenotypes
[Researching...]
### 6.4 Known Adverse Events
[Researching...]
### 6.5 Paralog & Off-Target Risks
[Researching...]

## 7. Pathway Context & Network Analysis
### 7.1 Biological Pathways
[Researching...]
### 7.2 Protein-Protein Interactions
[Researching...]
### 7.3 Functional Enrichment
[Researching...]
### 7.4 Pathway Redundancy Assessment
[Researching...]

## 8. Validation Evidence
### 8.1 Target Essentiality (DepMap)
[Researching...]
### 8.2 Functional Studies
[Researching...]
### 8.3 Animal Models
[Researching...]
### 8.4 Biomarker Potential
[Researching...]

## 9. Structural Insights
### 9.1 Experimental Structures (PDB)
[Researching...]
### 9.2 AlphaFold Prediction
[Researching...]
### 9.3 Binding Pocket Analysis
[Researching...]
### 9.4 Domain Architecture
[Researching...]

## 10. Literature Landscape
### 10.1 Publication Metrics
[Researching...]
### 10.2 Key Publications
[Researching...]
### 10.3 Research Trend
[Researching...]

## 11. Validation Roadmap
### 11.1 Recommended Validation Experiments
[Researching...]
### 11.2 Tool Compounds for Testing
[Researching...]
### 11.3 Biomarker Strategy
[Researching...]
### 11.4 Clinical Biomarker Candidates
[Researching...]
### 11.5 Disease Models to Test
[Researching...]

## 12. Risk Assessment
### 12.1 Key Risks
[Researching...]
### 12.2 Mitigation Strategies
[Researching...]
### 12.3 Competitive Landscape
[Researching...]

## 13. Completeness Checklist
[To be populated post-audit...]

## 14. Data Sources & Methodology
[Will be populated as research progresses...]
```

---

## Completeness Checklist (MANDATORY)

Before finalizing the report, verify all items:

### Phase Coverage
- [ ] Phase 0: Target disambiguation (all IDs resolved)
- [ ] Phase 1: Disease association (OT + GWAS + gnomAD + literature)
- [ ] Phase 2: Druggability (tractability + class + structure + probes)
- [ ] Phase 3: Chemical matter (ChEMBL + BindingDB + PubChem + drugs)
- [ ] Phase 4: Clinical precedent (FDA + trials + failures)
- [ ] Phase 5: Safety (OT safety + expression + KO + ADRs + paralogs)
- [ ] Phase 6: Pathway context (Reactome + STRING + GO)
- [ ] Phase 7: Validation evidence (DepMap + literature + models)
- [ ] Phase 8: Structural insights (PDB + AlphaFold + pockets + domains)
- [ ] Phase 9: Literature (collision-aware + metrics + key papers)
- [ ] Phase 10: Validation roadmap (score + recommendations)

### Data Quality
- [ ] All scores justified with specific data
- [ ] Evidence grades (T1-T4) assigned to key claims
- [ ] Negative results documented (not left blank)
- [ ] Failed tools with fallbacks documented
- [ ] Source citations for all data points

### Scoring
- [ ] All 12 score components calculated
- [ ] Total score summed correctly
- [ ] Priority tier assigned
- [ ] GO/NO-GO recommendation justified

---

## Section-Specific Report Formats

### Chemical Matter Section Example

```markdown
### 4. Known Modulators & Chemical Matter

#### 4.1 Approved Drugs
| Drug | ChEMBL ID | Mechanism | Phase | Indication | Source |
|------|-----------|-----------|-------|------------|--------|
| Erlotinib | CHEMBL553 | Inhibitor | 4 | NSCLC | [T1] OpenTargets |

#### 4.2 ChEMBL Bioactivity Summary
**Total Activities**: 12,456 datapoints across 2,341 assays
**Most Potent Compound**: CHEMBL413456 (IC50 = 0.3 nM) [T1]
**Chemical Series**: 8 distinct scaffolds with pChEMBL >= 7.0

#### 4.3 BindingDB Ligands
**Total Ligands**: 856 with measured affinity
**Affinity Distribution**: <1nM: 23, 1-10nM: 89, 10-100nM: 234, 100nM-1uM: 510

#### 4.4 Chemical Probes
| Probe | Source | Potency | Selectivity | Use |
|-------|--------|---------|-------------|-----|
| SGC-1234 | SGC | IC50=5nM | >100x | In vitro |
```

### Pathway Context Section Example

```markdown
### 7. Pathway Context & Network Analysis

#### 7.1 Key Pathways
| Pathway | Reactome ID | Relevance to Disease | Evidence |
|---------|-------------|---------------------|----------|
| EGFR signaling | R-HSA-177929 | Driver pathway in NSCLC | [T1] |

#### 7.2 Protein-Protein Interactions
**Total Interactors**: 45 (STRING confidence > 0.7)
**Key Interactors**: GRB2, SHC1, PLCG1, PIK3CA, STAT3

#### 7.3 Pathway Redundancy Assessment
**Compensation Risk**: MODERATE
- Parallel pathways: HER2, HER3 can compensate
- Feedback loops: RAS activation bypasses EGFR
```

### Target Identity Section Example

```markdown
## 1. Target Identity

| Database | Identifier | Verified |
|----------|-----------|----------|
| Gene Symbol | EGFR | Yes |
| Full Name | Epidermal growth factor receptor | Yes |
| Ensembl | ENSG00000146648 | Yes |
| Ensembl (versioned) | ENSG00000146648.18 | Yes |
| UniProt | P00533 | Yes |
| Entrez Gene | 1956 | Yes |
| ChEMBL | CHEMBL203 | Yes |
| HGNC | HGNC:3236 | Yes |

**Protein Function**: [from UniProt_get_function_by_accession]
**Subcellular Location**: [from UniProt_get_subcellular_location_by_accession]
**Target Class**: [from OpenTargets_get_target_classes_by_ensemblID]
```
