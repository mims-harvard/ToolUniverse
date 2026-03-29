---
name: tooluniverse-rnaseq-deseq2
description: Production-ready RNA-seq differential expression analysis using PyDESeq2. Performs DESeq2 normalization, dispersion estimation, Wald testing, LFC shrinkage, and result filtering. Handles multi-factor designs, multiple contrasts, batch effects, and integrates with gene enrichment (gseapy) and ToolUniverse annotation tools (UniProt, Ensembl, OpenTargets). Supports CSV/TSV/H5AD input formats and any organism. Use when analyzing RNA-seq count matrices, identifying DEGs, performing differential expression with statistical rigor, or answering questions about gene expression changes.
---

# RNA-seq Differential Expression Analysis (DESeq2)

Differential expression analysis of RNA-seq count data using PyDESeq2, with enrichment analysis (gseapy) and gene annotation via ToolUniverse.

**BixBench Coverage**: Validated on 53 BixBench questions across 15 computational biology projects.

## Domain Reasoning

DESeq2 assumes that most genes are NOT differentially expressed — this is its normalization assumption. If this assumption is violated (e.g., global transcriptional shutdown, where the majority of genes genuinely decrease), size factor normalization will inflate expression in the treatment group and produce artifactually upregulated genes. Always check the MA plot: the fold-change cloud should be centered on zero across all expression levels. A systematic upward or downward shift indicates a normalization problem, not biology.

## LOOK UP DON'T GUESS

- Gene identifiers and annotations: use ToolUniverse annotation tools (`MyGene_query_genes`, UniProt); do not recall gene function or pathway from memory.
- Enriched pathways: run gseapy or equivalent on the actual DEG list; do not list expected pathways.
- Design formula factors: inspect `metadata.columns` and `metadata[factor].unique()` from the actual data; do not assume metadata structure.
- DEG thresholds: apply the values specified by the user (padj, log2FC, baseMean); do not substitute defaults without checking the question.

---

## Core Principles

1. **Data-first** - Load and validate count data and metadata BEFORE any analysis
2. **Statistical rigor** - Proper normalization, dispersion estimation, multiple testing correction
3. **Flexible design** - Single-factor, multi-factor, and interaction designs
4. **Threshold awareness** - Apply user-specified thresholds exactly (padj, log2FC, baseMean)
5. **Reproducible** - Set random seeds, document all parameters
6. **Question-driven** - Parse what the user is actually asking; extract the specific answer
7. **Enrichment integration** - Chain DESeq2 results into pathway/GO enrichment when requested

## When to Use

- RNA-seq count matrices needing differential expression analysis
- DESeq2, DEGs, padj, log2FC questions
- Dispersion estimates or diagnostics
- GO, KEGG, Reactome enrichment on DEGs
- Specific gene expression changes between conditions
- Batch effect correction in RNA-seq

## Required Packages

```python
import pandas as pd, numpy as np
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
import gseapy as gp          # enrichment (optional)
from tooluniverse import ToolUniverse  # annotation (optional)
```

## Analysis Workflow

### Step 1: Parse the Question

Extract: data files, thresholds (padj/log2FC/baseMean), design factors, contrast, direction, enrichment type, specific genes. See [question_parsing.md](references/question_parsing.md).

### Step 2: Load & Validate Data

Load counts + metadata, ensure samples-as-rows/genes-as-columns, verify integer counts, align sample names, remove zero-count genes. See [data_loading.md](references/data_loading.md).

### Step 2.5: Inspect Metadata (REQUIRED)

List ALL metadata columns and levels. Categorize as biological interest vs batch/block. Build design formula with covariates first, factor of interest last. See [design_formula_guide.md](references/design_formula_guide.md).

### Step 3: Run PyDESeq2

Set reference level via `pd.Categorical`, create `DeseqDataSet`, call `dds.deseq2()`, extract `DeseqStats` with contrast, run Wald test, optionally apply LFC shrinkage. See [pydeseq2_workflow.md](references/pydeseq2_workflow.md).

**Tool boundaries**:
- **Python (PyDESeq2)**: ALL DESeq2 analysis
- **ToolUniverse**: ONLY gene annotation (ID conversion, pathway context)
- **gseapy**: Enrichment analysis (GO/KEGG/Reactome)

### Step 4: Filter Results

Apply padj, log2FC, baseMean thresholds. Split by direction if needed. See [result_filtering.md](references/result_filtering.md).

### Step 5: Dispersion Analysis (if asked)

Key columns: `genewise_dispersions`, `fitted_dispersions`, `MAP_dispersions`, `dispersions`. See [dispersion_analysis.md](references/dispersion_analysis.md).

### Step 6: Enrichment (optional)

Use gseapy `enrich()` with appropriate gene set library. See [enrichment_analysis.md](references/enrichment_analysis.md).

### Step 7: Gene Annotation (optional)

Use ToolUniverse for ID conversion and gene context only. See [output_formatting.md](references/output_formatting.md).

## Common Patterns

| Pattern | Type | Key Operation |
|---------|------|---------------|
| 1 | DEG count | `len(results[(padj<0.05) & (abs(lfc)>0.5)])` |
| 2 | Gene value | `results.loc['GENE', 'log2FoldChange']` |
| 3 | Direction | Filter `log2FoldChange > 0` or `< 0` |
| 4 | Set ops | `degs_A - degs_B` for unique DEGs |
| 5 | Dispersion | `(dds.var['genewise_dispersions'] < thr).sum()` |

See [bixbench_examples.md](references/bixbench_examples.md) for all 10 patterns with examples.

## Error Quick Reference

| Error | Fix |
|-------|-----|
| No matching samples | Transpose counts; strip whitespace |
| Dispersion trend no converge | `fit_type='mean'` |
| Contrast not found | Check `metadata['factor'].unique()` |
| Non-integer counts | Round to int OR use t-test |
| NaN in padj | Independent filtering removed genes |

See [troubleshooting.md](references/troubleshooting.md) for full debugging guide.

## Interpretation Framework

### DESeq2 Result Interpretation

| Metric | Threshold | Interpretation |
|--------|-----------|---------------|
| **padj** | < 0.05 | Statistically significant after multiple testing correction |
| **log2FoldChange** | > 1 or < -1 | Biologically meaningful fold change (2x up or down) |
| **baseMean** | > 10 | Gene is expressed at detectable levels |
| **lfcSE** | < 1.0 | Fold change estimate is precise |

### Evidence Grading for DEGs

| Grade | Criteria | Action |
|-------|---------|--------|
| **Strong DEG** | padj < 0.01, |LFC| > 1.5, baseMean > 100 | High-confidence; report and annotate |
| **Moderate DEG** | padj < 0.05, |LFC| > 1.0, baseMean > 10 | Standard cutoff; include in enrichment |
| **Weak DEG** | padj < 0.1 or |LFC| 0.5-1.0 | Suggestive; note but don't prioritize |
| **Not significant** | padj >= 0.1 | Do not report as differentially expressed |

### Synthesis Questions

1. **How many DEGs and in which direction?** (up vs down ratio indicates biological response type)
2. **What pathways are enriched?** (GO/KEGG enrichment of DEGs reveals mechanism)
3. **Are the top DEGs biologically plausible?** (known markers for the condition?)
4. **Is the fold change magnitude realistic?** (LFC > 5 is unusual; check for outlier-driven effects)
5. **Are there batch effects?** (PCA should separate by condition, not by batch)

---

## Known Limitations

- **PyDESeq2 vs R DESeq2**: Numerical differences exist for very low dispersion genes (<1e-05). For exact R reproducibility, use rpy2.
- **gseapy vs R clusterProfiler**: Results may differ. See [r_clusterprofiler_guide.md](references/r_clusterprofiler_guide.md).

## Reference Files

- [question_parsing.md](references/question_parsing.md) - Extract parameters from questions
- [data_loading.md](references/data_loading.md) - Data loading and validation
- [design_formula_guide.md](references/design_formula_guide.md) - Multi-factor design decision tree
- [pydeseq2_workflow.md](references/pydeseq2_workflow.md) - Complete PyDESeq2 code examples
- [result_filtering.md](references/result_filtering.md) - Advanced filtering and extraction
- [dispersion_analysis.md](references/dispersion_analysis.md) - Dispersion diagnostics
- [enrichment_analysis.md](references/enrichment_analysis.md) - GO/KEGG/Reactome workflows
- [output_formatting.md](references/output_formatting.md) - Format answers correctly
- [bixbench_examples.md](references/bixbench_examples.md) - All 10 question patterns
- [troubleshooting.md](references/troubleshooting.md) - Common issues and debugging
- [r_clusterprofiler_guide.md](references/r_clusterprofiler_guide.md) - R clusterProfiler via rpy2

## Utility Scripts

- [format_deseq2_output.py](scripts/format_deseq2_output.py) - Output formatters
- [load_count_matrix.py](scripts/load_count_matrix.py) - Data loading utilities
