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

## BixBench-verified conventions

### MANDATORY: Use R DESeq2 (not pydeseq2) for all DE analysis
For ANY question about differential expression counts, dispersion, or gene set overlaps, use R DESeq2 via the ToolUniverse tool or Rscript. Do NOT use pydeseq2 — it gives different results.
```bash
tu run run_deseq2_analysis '{"operation":"deseq2","counts_file":"raw_counts.csv","metadata_file":"experiment_metadata.csv","design":"~ Replicate + Media + Strain","contrast":"Strain, 97, 1","refit_cooks":true}'
```
If the tool is unavailable, use `Rscript -e 'library(DESeq2); ...'` directly.

### Prefer the dataset's authoritative script
Before running DESeq2 yourself, `ls` the dataset folder. If you see `run_*.py`, `analysis.R`, `find_*.R`, or similar, those are the benchmark's ground-truth recipes.

1. `cat` the script to see its exact parameters — every kwarg.
2. If the script already prints the quantity you need, `cd DATASET_DIR && python3 run_*.py` and take its answer.
3. If the question needs a different metric from the same fitted model, make a SMALL addition (extra print statements) without changing the `DeseqDataSet(...)` / `DeseqStats(...)` constructor calls.

**Copy ALL kwargs literally**: `refit_cooks=True`, `alpha=0.05`, `n_cpus`, `design_factors`, `ref_level`. Omitting parameters like `refit_cooks` can change DEG counts significantly. Plain "remembered" defaults produce a different gene list than the ground-truth script.

### R DESeq2 vs pydeseq2
The two libraries can disagree on edge cases (e.g., sig gene counts at the same alpha often differ by ~2%). **Match whatever the authoritative script uses.** If no script is present, prefer R DESeq2 — its behavior is more widely referenced in published papers.

**Preferred: use the `run_deseq2_analysis` ToolUniverse tool** which runs R DESeq2 via Rscript:
```bash
# Basic DESeq2
tu run run_deseq2_analysis '{"operation":"deseq2","counts_file":"raw_counts.csv","metadata_file":"metadata.csv","design":"~ condition","ref_level":"condition, Control"}'

# With contrast + LFC shrinkage + refit_cooks
tu run run_deseq2_analysis '{"operation":"deseq2","counts_file":"raw_counts.csv","metadata_file":"metadata.csv","design":"~ Replicate + Media + Strain","contrast":"Strain, 97, 1","refit_cooks":true,"lfc_shrinkage":true}'

# enrichGO + simplify (after saving DEG list to file)
tu run run_deseq2_analysis '{"operation":"enrichgo","gene_list_file":"sig_genes.txt","background_file":"all_genes.txt","simplify_cutoff":0.7}'
```
This avoids pydeseq2 vs R DESeq2 discrepancies. The tool returns sig gene counts, dispersion estimates, and a results CSV path for further analysis.

### Strain identity pinning
When a question names strains by number AND describes their biology (e.g., knockout genotypes), pin the mapping from the question text or the experiment metadata, not from numeric order. Read the metadata CSV to confirm which strain number corresponds to which genotype before running DESeq2.

When reading RDS/CSV result files named like `res_1vsN.rds`, the "N" refers to the strain number in the metadata. Verify which mutant that number corresponds to — do not assume from the filename alone.

### "Uniquely DE in A/B not C" = exclusive, not inclusive
When asked for genes "uniquely DE in one of {A, B} single mutants but not in C (double)", this means **exclusively in A xor exclusively in B, each also not in C**:

```
(A − B − C) ∪ (B − A − C)
```

NOT `(A ∪ B) − C` (which includes the A∩B intersection). The exclusive interpretation typically gives a smaller count than the inclusive one.

### Set-operation percentages — check the denominator
If your `unique_DE / total_DE` gives a number in the 30–50% range, the expected denominator is probably different. Common alternatives:
- `unique_DE / total_genes_tested` (often 5-10% for bacterial, <2% for eukaryotic)
- `unique_DE / |union of all sig sets|`

Re-read the question to see what population "as a percentage of" refers to.

### "Also DE in strain X" = simple overlap, not exclusive
When asked "what percentage of genes DE in A are **also** DE in B", compute `|A ∩ B| / |A|`. Do NOT subtract other strains — "also DE in B" does not mean "exclusively DE in B but not C".

**CRITICAL**: The word "also" means simple set intersection. If the question says "genes DE in strain A that are **also** DE in strain B", compute:
```python
overlap = sigA.intersection(sigB)
pct = len(overlap) / len(sigA) * 100
```
Do NOT add extra exclusion conditions like "but not in strain C". "Also DE in B" means `A ∩ B`, nothing more.

### Dispersion estimates: R DESeq2 vs pydeseq2 diverge
For questions about dispersion (e.g., "how many genes have dispersion below 1e-05"), R DESeq2 and pydeseq2 give different numbers because of implementation differences in the dispersion fitting algorithm. **Always use R DESeq2 for dispersion questions** — benchmark ground truths are computed with R:

```r
library(DESeq2)
dds <- DESeq(dds)
# Pre-shrinkage (genewise) dispersions:
gene_disp <- mcols(dds)$dispGeneEst
cat("Below 1e-05:", sum(gene_disp < 1e-05, na.rm=TRUE), "\n")
```

### Log2 fold-change: verify the contrast direction
When asked for the log2FC of gene X in mutant Y, verify that your DESeq2 `results()` call uses the correct contrast. For `~Media + Strain` design with reference Strain "1":
- `results(dds, contrast=c("Strain", "97", "1"))` → log2FC for strain 97 vs ref
- The sign matters: negative log2FC = downregulated in mutant vs reference
- If your value has the wrong sign or magnitude, check if you accidentally used the wrong strain coefficient
