---
name: tooluniverse-multi-omics-integration
description: Integrate and analyze multiple omics datasets (transcriptomics, proteomics, epigenomics, genomics, metabolomics) for systems biology and precision medicine. Performs cross-omics correlation, multi-omics clustering (MOFA+, NMF), pathway-level integration, and sample matching. Coordinates ToolUniverse skills for expression data (RNA-seq), epigenomics (methylation, ChIP-seq), variants (SNVs, CNVs), protein interactions, and pathway enrichment. Use when analyzing multi-omics datasets, performing integrative analysis, discovering multi-omics biomarkers, studying disease mechanisms across molecular layers, or conducting systems biology research that requires coordinated analysis of transcriptome, genome, epigenome, proteome, and metabolome data.
---

# Multi-Omics Integration

Coordinate and integrate multiple omics datasets for comprehensive systems biology analysis. Orchestrates specialized ToolUniverse skills to perform cross-omics correlation, multi-omics clustering, pathway-level integration, and unified interpretation.

---

## Domain Reasoning

Multi-omics integration asks whether different molecular layers tell a concordant story. If a gene is upregulated in RNA-seq AND its protein is elevated in proteomics, that is concordant evidence of true biological change. Discordance — high mRNA but low protein, or elevated protein without matching mRNA — may indicate post-transcriptional regulation (miRNA silencing, protein degradation, translational control) and is itself a meaningful finding worth reporting. Not every discordance is noise; some are the most interesting biology.

## LOOK UP DON'T GUESS

- Expected RNA-protein correlation ranges: compute Spearman r from the actual data; the typical range (0.4-0.6) is a guide, not a guarantee.
- Pathway enrichment results: run `ReactomeAnalysis_pathway_enrichment` or gseapy on the actual gene lists; never list enriched pathways from memory.
- eQTL associations: query GTEx or eQTL databases for the specific variant and tissue; do not assume regulatory relationships.
- Methylation-expression directionality at specific loci: retrieve experimental data; promoter repression is the canonical model but exceptions exist.

---

## When to Use This Skill

- User has multiple omics datasets (RNA-seq + proteomics, methylation + expression, etc.)
- Cross-omics correlation queries (e.g., "How does methylation affect expression?")
- Multi-omics biomarker discovery or patient subtyping
- Systems biology questions requiring multiple molecular layers
- Precision medicine applications with multi-omics patient data

---

## Workflow Overview

```
Phase 1: Data Loading & QC
  Load each omics type, format-specific QC, normalize
  Supported: RNA-seq, proteomics, methylation, CNV/SNV, metabolomics

Phase 2: Sample Matching
  Harmonize sample IDs, find common samples, handle missing omics

Phase 3: Feature Mapping
  Map features to common gene-level identifiers
  CpG->gene (promoter), CNV->gene, metabolite->enzyme

Phase 4: Cross-Omics Correlation
  RNA vs Protein (translation efficiency)
  Methylation vs Expression (epigenetic regulation)
  CNV vs Expression (dosage effect)
  eQTL variants vs Expression (genetic regulation)

Phase 5: Multi-Omics Clustering
  MOFA+, NMF, SNF for patient subtyping

Phase 6: Pathway-Level Integration
  Aggregate omics evidence at pathway level
  Score pathway dysregulation with combined evidence

Phase 7: Biomarker Discovery
  Feature selection across omics, multi-omics classification

Phase 8: Integrated Report
  Summary, correlations, clusters, pathways, biomarkers
```

See: phase_details.md for complete code and implementation details.

---

## Supported Data Types

| Omics | Formats | QC Focus |
|-------|---------|----------|
| Transcriptomics | CSV/TSV, HDF5, h5ad | Low-count filter, normalize (TPM/DESeq2), log-transform |
| Proteomics | MaxQuant, Spectronaut, DIA-NN | Missing value imputation, median/quantile normalization |
| Methylation | IDAT, beta matrices | Failed probes, batch correction, cross-reactive filter |
| Genomics | VCF, SEG (CNV) | Variant QC, CNV segmentation |
| Metabolomics | Peak tables | Missing values, normalization |

---

## Core Operations

### Sample Matching

```python
def match_samples_across_omics(omics_data_dict):
    """Match samples across multiple omics datasets."""
    sample_ids = {k: set(df.columns) for k, df in omics_data_dict.items()}
    common_samples = set.intersection(*sample_ids.values())
    matched_data = {k: df[sorted(common_samples)] for k, df in omics_data_dict.items()}
    return sorted(common_samples), matched_data
```

### Cross-Omics Correlation

```python
from scipy.stats import spearmanr, pearsonr

# RNA vs Protein: expect positive r ~ 0.4-0.6
# Methylation vs Expression: expect negative r (promoter repression)
# CNV vs Expression: expect positive r (dosage effect)

for gene in common_genes:
    r, p = spearmanr(rna[gene], protein[gene])
```

### Pathway Integration

```python
# Score pathway dysregulation using combined evidence from all omics
# Aggregate per-gene evidence, then per-pathway
pathway_score = mean(abs(rna_fc) + abs(protein_fc) + abs(meth_diff) + abs(cnv))
```

See: phase_details.md for full implementations of each operation.

---

## Multi-Omics Clustering Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **MOFA+** | Latent factors explaining cross-omics variation | Identifying shared/omics-specific drivers |
| **Joint NMF** | Shared decomposition across omics | Patient subtype discovery |
| **SNF** | Similarity network fusion | Integrating heterogeneous data types |

---

## ToolUniverse Skills Coordination

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-rnaseq-deseq2` | RNA-seq analysis | 1, 4 |
| `tooluniverse-epigenomics` | Methylation, ChIP-seq | 1, 4 |
| `tooluniverse-variant-analysis` | CNV/SNV processing | 1, 3, 4 |
| `tooluniverse-protein-interactions` | Protein network context | 6 |
| `tooluniverse-gene-enrichment` | Pathway enrichment | 6 |
| `tooluniverse-expression-data-retrieval` | Public data retrieval | 1 |
| `tooluniverse-target-research` | Gene/protein annotation | 3, 8 |

---

## Use Cases

### Cancer Multi-Omics
Integrate TCGA RNA-seq + proteomics + methylation + CNV to identify patient subtypes, cross-omics driver genes, and multi-omics biomarkers.

### eQTL + Expression + Methylation
Identify SNP -> methylation -> expression regulatory chains (mediation analysis).

### Drug Response Multi-Omics
Predict drug response using baseline multi-omics profiles; identify resistance/sensitivity pathways.

See: phase_details.md "Use Cases" for detailed step-by-step workflows.

---

## Quantified Minimums

| Component | Requirement |
|-----------|-------------|
| Omics types | At least 2 datasets |
| Common samples | At least 10 across omics |
| Cross-correlation | Pearson/Spearman computed |
| Clustering | At least one method (MOFA+, NMF, or SNF) |
| Pathway integration | Enrichment with multi-omics evidence scores |
| Report | Summary, correlations, clusters, pathways, biomarkers |

---

## Limitations

- **Sample size**: n >= 20 recommended for integration
- **Missing data**: Pairwise integration if not all samples have all omics
- **Batch effects**: Different platforms require careful normalization
- **Computational**: Large datasets may require significant memory
- **Interpretation**: Results require domain expertise for validation

---

## References

- MOFA+: https://doi.org/10.1186/s13059-020-02015-1
- Similarity Network Fusion: https://doi.org/10.1038/nmeth.2810
- Multi-omics review: https://doi.org/10.1038/s41576-019-0093-7
- See individual ToolUniverse skill documentation for omics-specific methods

---

## Detailed Reference

- **phase_details.md** - Complete code for all phases, correlation functions, clustering, pathway integration, biomarker discovery, report template, and detailed use cases
