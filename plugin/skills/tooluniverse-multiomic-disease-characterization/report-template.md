# Multi-Omics Disease Characterization Report Template

Create this file at the start: `{disease_name}_multiomic_report.md`

```markdown
# Multi-Omics Disease Characterization: {Disease Name}

**Report Generated**: {date}
**Disease Identifiers**: (to be filled)
**Multi-Omics Confidence Score**: (to be calculated)

---

## Executive Summary

(2-3 sentence disease mechanism synthesis - fill after all layers complete)

---

## 1. Disease Definition & Context

### Disease Identifiers
| System | ID | Source |
|--------|-----|--------|

### Description
### Synonyms
### Disease Hierarchy (parents/children)
### Affected Tissues/Organs
### Therapeutic Areas

**Sources**: (tools used)

---

## 2. Genomics Layer

### 2.1 GWAS Associations
| SNP | P-value | Effect | Gene | Study | Source |
|-----|---------|--------|------|-------|--------|

### 2.2 GWAS Studies Summary
| Study ID | Trait | Sample Size | Year | Source |
|----------|-------|-------------|------|--------|

### 2.3 Associated Genes (Genetic Evidence)
| Gene | Ensembl ID | Association Score | Evidence Type | Source |
|------|------------|-------------------|---------------|--------|

### 2.4 Rare Variants (ClinVar)
| Variant | Gene | Clinical Significance | Source |
|---------|------|-----------------------|--------|

### Genomics Layer Summary
- Total GWAS hits:
- Top genes by genetic evidence:
- Genetic architecture:

**Sources**: (tools used)

---

## 3. Transcriptomics Layer

### 3.1 Differential Expression Studies
| Experiment | Condition | Up-regulated | Down-regulated | Source |
|------------|-----------|--------------|----------------|--------|

### 3.2 Expression Atlas Disease Evidence
| Gene | Score | Source |
|------|-------|--------|

### 3.3 Tissue Expression Patterns (GTEx/HPA)
| Gene | Tissue | Expression Level | Source |
|------|--------|-----------------|--------|

### 3.4 Biomarker Candidates (Expression-Based)
| Gene | Tissue Specificity | Fold Change | Evidence | Source |
|------|-------------------|-------------|----------|--------|

### Transcriptomics Layer Summary
- Differential expression datasets:
- Top DEGs:
- Tissue-specific patterns:

**Sources**: (tools used)

---

## 4. Proteomics & Interaction Layer

### 4.1 Protein-Protein Interactions (STRING)
| Protein A | Protein B | Score | Source |
|-----------|-----------|-------|--------|

### 4.2 Hub Genes (Network Centrality)
| Gene | Degree | Betweenness | Role | Source |
|------|--------|-------------|------|--------|

### 4.3 Protein Complexes (IntAct)
| Complex | Members | Function | Source |
|---------|---------|----------|--------|

### 4.4 Tissue-Specific PPI Network
| Gene | Interaction Score | Tissue | Source |
|------|-------------------|--------|--------|

### Proteomics Layer Summary
- Total PPIs:
- Hub genes:
- Network modules:

**Sources**: (tools used)

---

## 5. Pathway & Network Layer

### 5.1 Enriched Pathways (Enrichr/Reactome)
| Pathway | Database | P-value | Genes | Source |
|---------|----------|---------|-------|--------|

### 5.2 Reactome Pathway Details
| Pathway ID | Name | Genes Involved | Source |
|------------|------|----------------|--------|

### 5.3 KEGG Pathways
| Pathway ID | Name | Description | Source |
|------------|------|-------------|--------|

### 5.4 WikiPathways
| Pathway ID | Name | Organism | Source |
|------------|------|----------|--------|

### Pathway Layer Summary
- Top enriched pathways:
- Key pathway nodes:
- Cross-pathway connections:

**Sources**: (tools used)

---

## 6. Gene Ontology & Functional Annotation

### 6.1 Biological Processes
| GO Term | Name | P-value | Genes | Source |
|---------|------|---------|-------|--------|

### 6.2 Molecular Functions
| GO Term | Name | P-value | Genes | Source |
|---------|------|---------|-------|--------|

### 6.3 Cellular Components
| GO Term | Name | P-value | Genes | Source |
|---------|------|---------|-------|--------|

**Sources**: (tools used)

---

## 7. Therapeutic Landscape

### 7.1 Approved Drugs
| Drug | ChEMBL ID | Mechanism | Target | Phase | Source |
|------|-----------|-----------|--------|-------|--------|

### 7.2 Druggable Targets
| Gene | Tractability | Modality | Clinical Precedent | Source |
|------|-------------|----------|-------------------|--------|

### 7.3 Drug Repurposing Candidates
| Drug | Original Indication | Mechanism | Target | Source |
|------|---------------------|-----------|--------|--------|

### 7.4 Clinical Trials
| NCT ID | Title | Phase | Status | Intervention | Source |
|--------|-------|-------|--------|--------------|--------|

### Therapeutic Summary
- Approved drugs:
- Clinical pipeline:
- Novel targets:

**Sources**: (tools used)

---

## 8. Multi-Omics Integration

### 8.1 Cross-Layer Gene Concordance
| Gene | Genomics | Transcriptomics | Proteomics | Pathways | Layers | Evidence Tier |
|------|----------|-----------------|------------|----------|--------|---------------|

### 8.2 Multi-Omics Hub Genes (Top 20)
| Rank | Gene | Layers Found | Key Evidence | Druggable | Source |
|------|------|-------------|--------------|-----------|--------|

### 8.3 Biomarker Candidates
| Biomarker | Type | Evidence Layers | Confidence | Source |
|-----------|------|-----------------|------------|--------|

### 8.4 Mechanistic Hypotheses
1. (Hypothesis with supporting evidence from multiple layers)
2. ...

### 8.5 Systems-Level Insights
- Key disrupted processes:
- Critical pathway nodes:
- Therapeutic intervention points:
- Testable hypotheses:

---

## Multi-Omics Confidence Score

| Component | Points | Max | Details |
|-----------|--------|-----|---------|
| Genomics data | | 10 | |
| Transcriptomics data | | 10 | |
| Protein data | | 5 | |
| Pathway data | | 10 | |
| Clinical data | | 5 | |
| Multi-layer genes | | 20 | |
| Direction concordance | | 10 | |
| Pathway-gene concordance | | 10 | |
| Genetic evidence quality | | 10 | |
| Clinical validation | | 10 | |
| **TOTAL** | | **100** | |

**Score**: XX/100 - [Tier]

---

## Data Availability Checklist

| Omics Layer | Data Available | Tools Used | Findings |
|-------------|---------------|------------|----------|
| Genomics (GWAS) | Yes/No | | |
| Genomics (Rare Variants) | Yes/No | | |
| Transcriptomics (DEGs) | Yes/No | | |
| Transcriptomics (Expression) | Yes/No | | |
| Proteomics (PPI) | Yes/No | | |
| Proteomics (Expression) | Yes/No | | |
| Pathways (Enrichment) | Yes/No | | |
| Pathways (KEGG/Reactome) | Yes/No | | |
| Gene Ontology | Yes/No | | |
| Drugs/Therapeutics | Yes/No | | |
| Clinical Trials | Yes/No | | |
| Literature | Yes/No | | |

---

## Completeness Checklist

- [ ] Disease disambiguation complete (IDs resolved)
- [ ] Genomics layer analyzed (GWAS + variants)
- [ ] Transcriptomics layer analyzed (DEGs + expression)
- [ ] Proteomics layer analyzed (PPI + interactions)
- [ ] Pathway layer analyzed (enrichment + mapping)
- [ ] Gene Ontology analyzed (BP + MF + CC)
- [ ] Therapeutic landscape analyzed (drugs + targets + trials)
- [ ] Cross-layer integration complete (concordance analysis)
- [ ] Multi-Omics Confidence Score calculated
- [ ] Biomarker candidates identified
- [ ] Hub genes identified
- [ ] Mechanistic hypotheses generated
- [ ] Executive summary written
- [ ] All sections have source citations

---

## References

### Data Sources Used
| # | Tool | Parameters | Section | Items Retrieved |
|---|------|------------|---------|-----------------|

### Database Versions
- OpenTargets: (current)
- GWAS Catalog: (current)
- STRING: (current)
- Reactome: (current)
```
