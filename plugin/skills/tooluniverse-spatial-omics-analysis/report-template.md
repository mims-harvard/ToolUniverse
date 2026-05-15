# Spatial Omics Analysis - Report Template

## Report File Structure

Create this file at the start: `{tissue}_{disease}_spatial_omics_report.md`

```markdown
# Spatial Multi-Omics Analysis Report: {Tissue Type}

**Report Generated**: {date}
**Technology**: {platform}
**Tissue**: {tissue_type}
**Disease Context**: {disease or "Normal tissue"}
**Total SVGs Analyzed**: {count}
**Spatial Domains**: {count}
**Spatial Omics Integration Score**: (to be calculated)

---

## Executive Summary

(2-3 sentence synthesis of key spatial findings - fill after all phases complete)

---

## 1. Tissue & Disease Context

### Tissue Information
| Property | Value | Source |
|----------|-------|--------|
| Tissue type | | |
| Disease | | |
| Expected cell types | | HPA |

### Disease Identifiers (if applicable)
| System | ID | Source |
|--------|-----|--------|

**Sources**: (tools used)

---

## 2. Spatially Variable Gene Characterization

### 2.1 Gene ID Resolution
| Gene Symbol | Ensembl ID | Entrez ID | UniProt | Function | Source |
|-------------|------------|-----------|---------|----------|--------|

### 2.2 Tissue Expression Patterns
| Gene | Tissue Expression | Specificity | Source |
|------|-------------------|-------------|--------|

### 2.3 Subcellular Localization
| Gene | Location | Confidence | Source |
|------|----------|------------|--------|

### 2.4 Disease Associations
| Gene | Disease | Score | Evidence | Source |
|------|---------|-------|----------|--------|

**Sources**: (tools used)

---

## 3. Pathway Enrichment Analysis

### 3.1 STRING Functional Enrichment
| Category | Term | Description | P-value | FDR | Genes | Source |
|----------|------|-------------|---------|-----|-------|--------|

### 3.2 Reactome Pathway Analysis
| Pathway ID | Name | P-value | FDR | Genes Found | Total Genes | Source |
|------------|------|---------|-----|-------------|-------------|--------|

### 3.3 GO Biological Processes
| GO Term | Description | P-value | FDR | Genes | Source |
|---------|-------------|---------|-----|-------|--------|

### 3.4 GO Molecular Functions
| GO Term | Description | P-value | FDR | Genes | Source |
|---------|-------------|---------|-----|-------|--------|

### 3.5 GO Cellular Components
| GO Term | Description | P-value | FDR | Genes | Source |
|---------|-------------|---------|-----|-------|--------|

### Pathway Summary
- Top enriched pathways:
- Key biological processes:
- Spatial pathway implications:

**Sources**: (tools used)

---

## 4. Spatial Domain Characterization

### Domain: {domain_name}

#### Marker Genes
| Gene | Function | Pathways | Source |
|------|----------|----------|--------|

#### Enriched Pathways (domain-specific)
| Pathway | P-value | FDR | Genes | Source |
|---------|---------|-----|-------|--------|

#### Cell Type Signature
| Cell Type | Marker Genes Present | Confidence |
|-----------|---------------------|------------|

#### Biological Interpretation
(Narrative interpretation of this domain)

(Repeat for each domain)

### 4.N Domain Comparison
| Feature | Domain 1 | Domain 2 | Domain 3 |
|---------|----------|----------|----------|
| Top pathway | | | |
| Cell types | | | |
| Disease relevance | | | |

**Sources**: (tools used)

---

## 5. Cell-Cell Interaction Inference

### 5.1 Protein-Protein Interactions (STRING)
| Protein A | Protein B | Score | Type | Source |
|-----------|-----------|-------|------|--------|

### 5.2 Ligand-Receptor Pairs
| Ligand | Receptor | Domain (Ligand) | Domain (Receptor) | Evidence | Source |
|--------|----------|-----------------|-------------------|----------|--------|

### 5.3 Signaling Pathways
| Pathway | Components in Data | Spatial Distribution | Source |
|---------|--------------------|---------------------|--------|

### 5.4 Interaction Network Summary
- Key interaction hubs:
- Cross-domain interactions:
- Predicted cell-cell communication axes:

**Sources**: (tools used)

---

## 6. Disease & Therapeutic Context

### 6.1 Disease Gene Overlap
| Gene | Disease Association Score | Evidence Type | Source |
|------|--------------------------|---------------|--------|

### 6.2 Druggable Targets in Spatial Domains
| Gene | Domain | Tractability | Modality | Approved Drugs | Source |
|------|--------|-------------|----------|----------------|--------|

### 6.3 Drug Mechanisms Relevant to Spatial Targets
| Drug | Target | Mechanism | Phase | Source |
|------|--------|-----------|-------|--------|

### 6.4 Clinical Trials
| NCT ID | Title | Target Gene | Phase | Status | Source |
|--------|-------|-------------|-------|--------|--------|

### Therapeutic Summary
- Druggable genes in disease regions:
- Approved therapies:
- Pipeline drugs:
- Novel opportunities:

**Sources**: (tools used)

---

## 7. Multi-Modal Integration

### 7.1 Protein-RNA Concordance (if protein data available)
| Gene/Protein | RNA Pattern | Protein Pattern | Concordance | Source |
|-------------|-------------|-----------------|-------------|--------|

### 7.2 Subcellular Context
| Gene | mRNA Location (spatial) | Protein Location (HPA) | Concordance | Source |
|------|------------------------|----------------------|-------------|--------|

### 7.3 Metabolic Context (if metabolomics available)
| Gene | Metabolic Pathway | Metabolites Detected | Spatial Pattern | Source |
|------|-------------------|---------------------|-----------------|--------|

**Sources**: (tools used)

---

## 8. Immune Microenvironment (if relevant)

### 8.1 Immune Cell Markers
| Cell Type | Marker Genes | Spatial Domain | Source |
|-----------|-------------|----------------|--------|

### 8.2 Immune Checkpoint Expression
| Checkpoint | Gene | Expression Pattern | Source |
|------------|------|--------------------|--------|

### 8.3 Tumor-Immune Interface (if cancer)
| Feature | Finding | Evidence | Source |
|---------|---------|----------|--------|

### Immune Summary
- Immune infiltration pattern:
- Key immune checkpoints:
- Immunotherapy implications:

**Sources**: (tools used)

---

## 9. Literature & Validation Context

### 9.1 Literature Evidence
| PMID | Title | Relevance | Year | Source |
|------|-------|-----------|------|--------|

### 9.2 Known Spatial Patterns
(Known tissue architecture/zonation from literature)

### 9.3 Validation Recommendations
| Priority | Gene/Target | Method | Rationale |
|----------|-------------|--------|-----------|
| High | | IHC / smFISH | |
| Medium | | IF / ISH | |

**Sources**: (tools used)

---

## Spatial Omics Integration Score

| Component | Points | Max | Details |
|-----------|--------|-----|---------|
| SVGs provided | | 5 | |
| Disease context | | 5 | |
| Spatial domains | | 5 | |
| Cell types | | 5 | |
| Multi-modal data | | 5 | |
| Literature context | | 5 | |
| Pathway enrichment | | 10 | |
| Cell-cell interactions | | 10 | |
| Disease mechanism | | 10 | |
| Druggable targets | | 10 | |
| Cross-database validation | | 10 | |
| Clinical validation | | 10 | |
| Literature support | | 10 | |
| **TOTAL** | | **100** | |

**Score**: XX/100 - [Tier]

---

## Completeness Checklist

- [ ] Gene ID resolution complete
- [ ] Tissue expression patterns analyzed (HPA)
- [ ] Subcellular localization checked (HPA)
- [ ] Pathway enrichment complete (STRING + Reactome)
- [ ] GO enrichment complete (BP + MF + CC)
- [ ] Spatial domains characterized individually
- [ ] Domain comparison performed
- [ ] Protein-protein interactions analyzed (STRING)
- [ ] Ligand-receptor pairs identified
- [ ] Disease associations checked (OpenTargets)
- [ ] Druggable targets identified (OpenTargets tractability)
- [ ] Drug mechanisms reviewed
- [ ] Multi-modal integration performed (if data available)
- [ ] Immune microenvironment characterized (if relevant)
- [ ] Literature search completed
- [ ] Validation recommendations provided
- [ ] Spatial Omics Integration Score calculated
- [ ] Executive summary written
- [ ] All sections have source citations

---

## References

### Data Sources Used
| # | Tool | Parameters | Section | Items Retrieved |
|---|------|------------|---------|-----------------|

### Database Versions
- OpenTargets: (current)
- STRING: v12.0
- Reactome: (current)
- HPA: (current)
- GTEx: v10
```
