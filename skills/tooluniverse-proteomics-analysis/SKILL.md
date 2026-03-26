---
name: tooluniverse-proteomics-analysis
description: Analyze mass spectrometry proteomics data including protein quantification, differential expression, post-translational modifications (PTMs), and protein-protein interactions. Processes MaxQuant, Spectronaut, DIA-NN, and other MS platform outputs. Performs normalization, statistical analysis, pathway enrichment, and integration with transcriptomics. Use when analyzing proteomics data, comparing protein abundance between conditions, identifying PTM changes, studying protein complexes, integrating protein and RNA data, discovering protein biomarkers, or conducting quantitative proteomics experiments.
---

# Proteomics Analysis

Comprehensive analysis of mass spectrometry-based proteomics data from protein identification through quantification, differential expression, post-translational modifications, and systems-level interpretation.

## When to Use This Skill

**Triggers**: User has proteomics MS output files, asks about protein abundance/expression, differential protein expression, PTM analysis, protein-RNA correlation, multi-omics integration involving proteomics, protein complex/interaction analysis, or proteomics biomarker discovery.

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Data Import** | MaxQuant, Spectronaut, DIA-NN, Proteome Discoverer, FragPipe outputs |
| **Quality Control** | Missing value analysis, intensity distributions, sample clustering |
| **Normalization** | Median, quantile, TMM, VSN normalization methods |
| **Imputation** | MinProb, KNN, QRILC for missing values |
| **Differential Expression** | Limma, DEP, MSstats for statistical testing |
| **PTM Analysis** | Phospho-site localization, PTM enrichment, kinase prediction |
| **Protein-RNA Integration** | Correlation analysis, translation efficiency |
| **Pathway Enrichment** | Over-representation and GSEA for protein sets |
| **PPI Analysis** | Protein complex detection, interaction networks via STRING/IntAct |
| **Reporting** | Comprehensive reports with volcano plots, heatmaps, pathway diagrams |

## Workflow Overview

```
Input: MS Proteomics Data
    |
Phase 1: Data Import & QC
Phase 2: Preprocessing (filter, impute, normalize)
Phase 3: Differential Expression Analysis
Phase 4: PTM Analysis (if applicable)
Phase 5: Functional Enrichment (GO, KEGG, Reactome)
Phase 6: Protein-Protein Interactions (STRING networks)
Phase 7: Multi-Omics Integration (optional, protein-RNA correlation)
Phase 8: Generate Report
```

See [PHASE_DETAILS.md](PHASE_DETAILS.md) for detailed procedures per phase.

## Integration with ToolUniverse

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-gene-enrichment` | Pathway enrichment | Phase 5 |
| `tooluniverse-protein-interactions` | PPI networks | Phase 6 |
| `tooluniverse-rnaseq-deseq2` | RNA-seq for integration | Phase 7 |
| `tooluniverse-multi-omics-integration` | Cross-omics analysis | Phase 7 |
| `tooluniverse-target-research` | Protein annotation | Phase 8 |

## Quantified Minimums

| Component | Requirement |
|-----------|-------------|
| Proteins quantified | At least 500 proteins |
| Replicates | At least 3 per condition |
| Filtering | 2+ unique peptides per protein |
| Statistical test | limma or t-test with multiple testing correction |
| Pathway enrichment | At least one method (GO, KEGG, or Reactome) |
| Report | Summary, QC, DE results, pathways, visualizations |

## Interpretation Framework

### Differential Expression Interpretation

| Metric | Strong | Moderate | Weak |
|--------|--------|----------|------|
| **padj** | < 0.01 | 0.01-0.05 | 0.05-0.1 |
| **Fold change** | > 2.0 | 1.5-2.0 | 1.2-1.5 |
| **Unique peptides** | > 5 | 2-5 | 1-2 (unreliable) |
| **Missing rate** | < 20% | 20-50% | > 50% (imputation needed) |

### Evidence Grading

| Grade | Criteria |
|-------|---------|
| **T1** | Validated by orthogonal method (Western blot, PRM) + functional study |
| **T2** | Significant DE (padj < 0.05, FC > 1.5) in 2+ biological replicates |
| **T3** | Significant DE in 1 experiment, or significant but low FC |
| **T4** | Identified but not quantified, or single peptide identification |

### Synthesis Questions

1. **How many proteins are differentially expressed?** (>500 DE proteins suggests global perturbation; <50 suggests targeted effect)
2. **Are key pathway proteins concordantly regulated?** (all subunits of a complex changing = high confidence)
3. **Do proteomics results correlate with transcriptomics?** (low correlation is common — post-translational regulation)
4. **Are PTM changes driving the phenotype?** (check phosphoproteomics if available)
5. **What is the coverage relative to the expected proteome?** (human: ~10K quantified is good; <3K is limited)

---

## Limitations

- **Platform-specific**: Optimized for MS-based proteomics (not Western blot quantification)
- **Missing values**: High missing rate (>50% per protein) limits statistical power
- **PTM analysis**: Requires enrichment protocols for comprehensive PTM profiling
- **Absolute quantification**: Relative abundance only (unless TMT/SILAC used)
- **Protein isoforms**: Typically collapsed to gene level
- **Dynamic range**: MS has limited dynamic range vs mRNA sequencing

## References

**Methods**: MaxQuant (doi:10.1038/nbt.1511), Limma for proteomics (doi:10.1093/nar/gkv007), DEP workflow (doi:10.1038/nprot.2018.107)

**Databases**: [STRING](https://string-db.org), [PhosphoSitePlus](https://www.phosphosite.org), [CORUM](https://mips.helmholtz-muenchen.de/corum)

## Reference Files

- [PHASE_DETAILS.md](PHASE_DETAILS.md) - Detailed procedures for each analysis phase, including report template
