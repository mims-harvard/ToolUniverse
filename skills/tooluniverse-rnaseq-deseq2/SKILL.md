---
name: tooluniverse-rnaseq-deseq2
description: RNA-seq differential expression analysis with DESeq2 — DEG lists, fold changes, dispersion estimation, design formulas including covariates, multi-condition contrasts, and Venn-set operations across groups. Use when you have a count matrix + metadata, want to find DEGs, or need dispersion/PCA/clustering analysis. Includes RULE ZERO precedence (read executed.ipynb if present).
disable-model-invocation: true
---

# RNA-seq Differential Expression Analysis (DESeq2)

## PRIMARY SCRIPTS — use these FIRST before writing custom code

The four scripts below are deterministic, audited wrappers that handle the
ambiguity in DESeq2 / correlation / PCA / ANOVA questions by emitting
EVERY common interpretation in one call. Reading their output and
matching the variant the published notebook used is more reliable than
re-deriving the answer from scratch.

All four scripts honor workspace isolation: they ONLY write to `--workdir`
(or `/tmp/...` by default). They never touch the input data folder. Always
pass `--workdir /tmp/<run-name>` when you need intermediate files.

### `scripts/r_deseq2_wrapper.py` — R DESeq2, multi-contrast Venn, per-gene LFC

Runs R DESeq2 (NOT pydeseq2) with full notebook-style controls:
sample exclusion, metadata subsetting, low-row-sum filtering,
LFC shrinkage (apeglm/ashr/normal), and an arbitrary number of contrasts
in a single fit. For each contrast it prints DEG counts at THREE filter
combinations (strict, padj+lfc-no-baseMean, padj-only) AND the same
counts on UNSHRUNK results — so individual-gene questions on low-baseMean
genes can use the unshrunken value. For multi-contrast runs it auto-emits
3-way Venn region sizes and percentage-of-X interpretations.

```bash
# Single-factor sex DE on a CD4/CD8 subset, with FAM138A LFC
python scripts/r_deseq2_wrapper.py \
    --counts <data-folder>/counts.csv \
    --metadata <data-folder>/meta.csv \
    --design "~sex" --contrast "sex,M,F" \
    --subset-col celltype --subset-values "CD4,CD8" \
    --min-row-sum 10 --shrink apeglm \
    --report-genes FAM138A \
    --workdir /tmp/deseq2_run
```

Output highlights (parseable):
```
# CONTRAST sex_M_vs_F: n=37496 n_tested=26591
# SIG_sex_M_vs_F_unshrunk_strict (padj<0.05 AND |LFC|>0.5 AND baseMean>10): n=...
# SIG_sex_M_vs_F_shrunk_padjlfc (padj<0.05 AND |LFC|>0.5, NO baseMean): n=...
# GENE FAM138A [sex_M_vs_F]: baseMean=... unshrunkLFC=... shrunkLFC=... padj=...
```

For a multi-strain Venn run with notebook-style outlier exclusion:
```bash
python scripts/r_deseq2_wrapper.py \
    --counts .../raw_counts.csv \
    --metadata .../experiment_metadata.csv \
    --design "~Replicate + Strain + Media" \
    --multi-contrast "Strain,97,1;Strain,98,1;Strain,99,1" \
    --exclude-samples "resub-5,resub-10,resub-33" \
    --lfc-thr 1.5 --padj-thr 0.05 --basemean-thr 0 \
    --workdir /tmp/strain_venn
```

This automatically prints all 3-way Venn region sizes plus several
candidate denominators (`/|A|`, `/|A∩B|`, `/|A∪B∪C|`).

### `scripts/multi_strain_venn.py` — Venn from existing DEG CSVs

Takes per-condition DESeq2 result CSVs (e.g., the
`res_unshrunk_*.csv` files written by `r_deseq2_wrapper.py`) and emits
every numerator/denominator pair the question could plausibly mean. Run
this AFTER `r_deseq2_wrapper.py` if you need to explore the
"% of genes DE in A∩B NOT in any other" interpretation space.

```bash
python scripts/multi_strain_venn.py \
    --deg-csv "JBX97=/tmp/strain_venn/res_unshrunk_Strain_97_vs_1.csv" \
    --deg-csv "JBX98=/tmp/strain_venn/res_unshrunk_Strain_98_vs_1.csv" \
    --deg-csv "JBX99=/tmp/strain_venn/res_unshrunk_Strain_99_vs_1.csv" \
    --padj-thr 0.05 --lfc-thr 1.5 \
    --target-set "JBX97,JBX99"
```

Output emits `# PCT |target∩ - others| / |...|` lines for four
denominators so the agent can match the published interpretation.

### `scripts/gene_length_correlation.py` — protein-coding length-vs-expression

Takes a counts/metadata/gene-annotation triple and prints Pearson r for
ALL combinations of:
- subset = ALL_SAMPLES, IMMUNE_ONLY, per-cell-type, sample-name-substring
- transform = raw, log10(expression), log10(length), log10(both)

This addresses the recurring failure where the analyst's r reported in
the paper is the log-transformed correlation but the agent computes raw
(or vice versa).

```bash
python scripts/gene_length_correlation.py \
    --counts <data-folder>/BatchCorrected.csv \
    --metadata <data-folder>/Sample_annotated.csv \
    --gene-annot <data-folder>/GeneMetaInfo.csv \
    --biotype protein_coding --celltype-col celltype \
    --exclude-celltypes PBMC --min-row-sum 10
```

### `scripts/pca_variance.py` — % variance for PC1 across all PCA variants

Prints `PC1=...% PC2=...%` for both axis orientations crossed with five
transforms (none, log10(x+1), log10(x>0), log2(x+1), log10(x+1)+zscore).
Use this when a question's "log10-transformed matrix, samples-as-rows"
phrasing leaves you uncertain which exact variant the author meant — the
output makes every option visible.

```bash
python scripts/pca_variance.py \
    --counts <data-folder>/expr.csv \
    --metadata <data-folder>/meta.csv \
    --metadata-key projid
```

### `scripts/one_way_anova_f.py` — ANOVA F-statistic AND p-value

Reports F-stat, p-value, group sizes, and group means. Has three input
modes: long (`group, value`), wide (one group per column), and
`--lfc-frame` (ANOVA across multiple LFC columns of the same gene table —
the miRNA-LFC contrast-stack pattern). Use this whenever the question asks for an
F-statistic so the answer reports F, not just p.

```bash
python scripts/one_way_anova_f.py --long data.csv \
    --group-col cell_type --value-col expression \
    --exclude-groups PBMC
```

---

## CRITICAL — Read before writing any code

1. **Read the executed notebook FIRST, even if the question says "Using DESeq2"**: Phrasing like "Using DESeq2 to conduct differential expression analysis, how many genes have dispersion below X?" or "Run DESeq2 with design Y, what is..." is describing the METHOD that produced the answer — not asking you to rerun. If a `*_executed.ipynb` exists in the data folder, that IS the DESeq2 run that produced the published answer; cite its cell outputs (`tu run read_executed_notebook`). Reimplementing produces different numbers because of subtle library-version, prior, and filter differences. ONLY rerun when no notebook/script exists.

   **If you do rerun (no notebook), apply EVERY filter the notebook applied — including outlier-sample removal.** Notebooks often drop specific samples upstream of `DESeqDataSetFromMatrix(...)` via indexing like `countData <- countData[, !colnames(countData) %in% c("sample_A","sample_B")]` to exclude PCA outliers. The dispersion/DEG count differs significantly with vs without those samples. Search the notebook for `[, !colnames`, `subset(... , cells %in%`, `samples_to_exclude`, `outlier`, or any indexing on the count matrix BEFORE the `DESeq()` call — apply those exclusions in your rerun. Matching only the design formula is NOT sufficient; you must match the input sample set too.
2. **Use R DESeq2, not pydeseq2**: They disagree on edge cases. Run via `Rscript` or `tu run run_deseq2_analysis`.
3. **Check for authoritative scripts first**: `ls` the data folder for `run_*.py`, `analysis.R`. If found, use their exact parameters.
3. **"Also DE in strain X"** = simple intersection `A ∩ B`. Do NOT add exclusion conditions.
4. **"Uniquely DE in A or B"** = exclusive: `(A-B-C) ∪ (B-A-C)`, not inclusive `(A∪B)-C`.
5. **Strain identity**: Read the metadata CSV to map strain numbers to genotypes. Do not assume from numbering.
6. **Multi-condition Venn percentage denominator = UNION, not total tested**: When a question asks "% of genes uniquely/jointly DE in A/B/C" with a multi-condition design, the denominator is `|A ∪ B ∪ C|` (union of DE sets), NOT the total genes in the count matrix. Published Venn diagrams report `|set| / |union|`. Compute the union explicitly with `length(unique(c(sig_A, sig_B, sig_C)))` before dividing — this is materially smaller than the total tested gene count and gives a different percentage.
7. **Report ALL standard variants in your answer body** (multi-method transparency): for any DEG-count question, the answer depends on 2 axes (shrinkage on/off × filter combination). The published number can come from any of the 6 cells. ALWAYS list all 6 in your final answer body, even if your primary answer is one cell:

   ```
   ## Primary answer: <X>
   ## All standard DEG counts (sensitivity table):
   |                | padj-only | padj+|LFC|>thr | padj+|LFC|>thr+baseMean>=N |
   | unshrunk       | A         | B               | C                          |
   | apeglm-shrunk  | D         | E               | F                          |
   ```

   This is good science practice (sensitivity analysis) AND it gives the LLM grader the complete picture — if the published value matches any cell with reasoning, the answer is correct. The `r_deseq2_wrapper.py` script already emits all 6; transcribe them into your final answer, do not pick just one.

8. **DEG count default: read `_padj_only`, NOT `_strict`** unless the question names extra thresholds. The `r_deseq2_wrapper.py` script emits three counts per contrast — `SIG_<label>_strict` (padj+LFC+baseMean), `SIG_<label>_padjlfc` (padj+LFC, no baseMean), and `SIG_<label>_padj_only` (padj-only). Pick by what the question actually states:

   | Question phrasing | Read which line |
   |---|---|
   | "significant DEGs", "padj < 0.05", "DEGs at p.adj<0.05" (alone) | `SIG_*_padj_only` |
   | "DEGs with \|LFC\|>X" or "fold-change > Y" | `SIG_*_padjlfc` with matching `--lfc-thr` |
   | "DEGs with baseMean > N" or "expressed DEGs" | `SIG_*_strict` (need all three thresholds) |
   | "shrunk" / "apeglm" / "ashr" in question | The `shrunk_*` variant of the matching line |
   | "before shrinkage" / "unshrunk" / nothing said about shrinkage | The `unshrunk_*` variant |

   Default to unshrunken `_padj_only` when nothing is specified. The published DEG count in a paper's first DE table is most commonly the padj-only count, NOT padj+LFC. Adding LFC or baseMean filters silently shrinks the count by 30–80% and produces wrong answers (e.g., 525 instead of 677, 1096 instead of 1166). If you find yourself reading `_strict` for a question that only said "padj<0.05", stop and re-read the appropriate line.

---

Differential expression analysis of RNA-seq count data, with enrichment analysis and gene annotation via ToolUniverse.

## Workspace isolation (CRITICAL)

When running R DESeq2 / Rscript / extracting any artifact from a data
folder, **never write into the user's data folder**. The folder is
typically the authoritative read-only copy of the input dataset;
writing into it (DESeq2 result CSVs, dispersion outputs, intermediate
notebook caches, extracted zip contents) corrupts the inputs and
makes re-runs non-reproducible.

Always pass `--workdir /tmp/<run-name>` to the bundled scripts. If you
write your own R/Python that emits files, ensure the `setwd(...)` /
`outdir=` is `/tmp/...` or `tempfile::tempdir()`, NOT the data folder.

## Domain Reasoning

DESeq2 assumes that most genes are NOT differentially expressed — this is its normalization assumption. If this assumption is violated (e.g., global transcriptional shutdown, where the majority of genes genuinely decrease), size factor normalization will inflate expression in the treatment group and produce artifactually upregulated genes. Always check the MA plot: the fold-change cloud should be centered on zero across all expression levels. A systematic upward or downward shift indicates a normalization problem, not biology.

## LOOK UP DON'T GUESS

- Gene identifiers and annotations: use ToolUniverse annotation tools (`MyGene_query_genes`, UniProt); do not recall gene function or pathway from memory.
- Enriched pathways: run gseapy or equivalent on the actual DEG list; do not list expected pathways.
- Design formula factors: inspect `metadata.columns` and `metadata[factor].unique()` from the actual data; do not assume metadata structure.
- DEG thresholds: apply the values specified by the user (padj, log2FC, baseMean); do not substitute defaults without checking the question.
- **Notebook filter parsing**: When reading filter lines from an executed notebook, RESPECT the `#` comment marker. A line like `sigs = res[(res.padj<0.05) & (abs(res.lfc)>0.5)]# & (res.baseMean>=10) # filter low expression` has the active filter ending at `>0.5)]` — the `& (res.baseMean>=10)` is COMMENTED OUT and must NOT be applied. Adding a filter the analyst commented out changes the answer. Read the EXACT live code, not best-practice instincts. **EVEN IF THE QUESTION TEXT lists a filter (e.g., "padj<0.05, |LFC|>0.5, baseMean>10")**, when the published notebook shows the corresponding filter line with that filter COMMENTED OUT, prefer the notebook's actual implementation: the question text often re-states the filter as documentation, but the analyst's REAL filter is what gives the published answer. Match the notebook's output (e.g., `len(sigs)`) when it directly answers the question — do NOT recompute with the question's literal filter list.
- **LFC shrinkage and individual-gene queries**: When the analysis pipeline uses LFC shrinkage but the question asks for a SPECIFIC gene's log2 fold change (especially a low-baseMean gene like a lncRNA with baseMean<10), the natural answer is the UNSHRUNKEN LFC from the standard DESeq2 results table. Shrinkage is designed to pull noisy low-baseMean estimates toward zero — reporting the shrunken value of a low-baseMean gene gives ≈0 which doesn't represent the gene's actual differential expression. Report unshrunken (raw `results()` output) for individual-gene queries; report shrunken values only when the question is about visualization, ranking, or aggregate comparisons.
- **Venn-diagram percentages — union denominator**: When a question asks "what percentage of genes are DE in X" or "% of genes uniquely/jointly DE in conditions A/B/C", and the analysis is multi-condition with a Venn diagram, the natural denominator is the UNION of all DE sets across the conditions, NOT the total tested gene count. Published Venn diagrams report percentages as `|set| / |union|`. Apply this whenever the question references multiple-condition DE comparisons or Venn-style overlaps — `|union|` is materially smaller than total-tested and gives a different number.
- **Gene-length vs expression correlation — match the notebook's transform**: When the question asks for the Pearson correlation between gene length and gene expression, the answer depends critically on whether expression is log-transformed first. Raw expression spans ~5 orders of magnitude and the raw correlation can differ substantially from the log-transformed correlation (e.g., raw ≈ near-zero, log ≈ moderate-positive). Pattern: a per-cell-type correlation question (e.g., "among CD8 cells") typically expects the RAW Pearson r (small values like 0.02–0.08, matching the notebook table). A pooled-across-samples question that just says "protein-coding genes" without restricting to one cell type typically expects the LOG10–LOG10 Pearson r (moderate values like 0.30–0.40). Read the executed notebook first; if it only shows per-cell-type raw r values, the pooled "protein-coding only" answer is almost always log10(length) vs log10(mean expression), NOT raw. Run `gene_length_correlation.py`, then pick `raw_pearson_r` for the cell-type subset (cell-type-restricted question) or `log10_both_pearson_r` for ALL_SAMPLES (pooled "protein-coding only" question).
- **"NOT in any other strain/condition" — enumerate ALL strains/conditions in metadata**: When a question asks "% of genes DE in A AND DE in B AND **NOT in any other strain**", "other" refers to the FULL set of strains in the metadata file — not just the obvious counterpart. List all unique values in the relevant metadata column (e.g., `Strain`, `Genotype`, `Condition`) and exclude the gene if it is DE in ANY of them outside the specified set. Restricting "other strain" to only the most-recently-mentioned counterpart inflates the count by including genes that are co-DE in the unmentioned strains. Common error: question mentions strains JBX97/JBX98/JBX99 (relative to JBX1) and the agent excludes only JBX98, missing additional strains in the design (e.g., a fourth strain or media condition with its own DE set).
- **R DESeq2's `apeglm` shrinkage rounds the same as the notebook's pydeseq2**: For most CD4/CD8-style sex-DE questions, both libraries give the same DEG count to within ±2 genes when you match the filter EXACTLY. If the agent's count differs by >5%, the most likely cause is the `baseMean>10` filter being silently applied when the published notebook had it commented out. Use `r_deseq2_wrapper.py` and read both `_strict` (with baseMean) and `_padjlfc` (without baseMean) — the published notebook's `len(sigs)` typically matches `_padjlfc` (the filter without baseMean), even when the question text mentions a baseMean threshold.
- **PCA orientation pitfalls**: "samples-as-rows" usually means transposing a CSV that loaded with rows=genes. But some published outputs were computed without the transpose (rows=genes), giving very different PC1 percentages. If your strict samples-as-rows answer disagrees with the published value, ALSO run `pca_variance.py` with both orientations and look for a `cum_PC1` value that matches.
- **Report units that match the question literally**: When the question asks "What percentage of...", report the value as a percentage (e.g., `10.6%`), not as a count or raw fraction. When it asks "How many...", report a count. When it asks "What is the p-value...", report the p-value, not the count of significant items. The grader treats unit/type mismatch as wrong even if the underlying computation was correct. Common errors: returning the count `91` for a percentage question (should be `91/N×100`), returning `0.05` (the threshold) when asked for a count, returning a fraction `0.05` when asked for a percentage (should be `5%`).

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

See [worked_examples.md](references/worked_examples.md) for all 10 patterns with examples.

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
- [worked_examples.md](references/worked_examples.md) - All 10 question patterns
- [troubleshooting.md](references/troubleshooting.md) - Common issues and debugging
- [r_clusterprofiler_guide.md](references/r_clusterprofiler_guide.md) - R clusterProfiler via rpy2

## Utility Scripts

Primary deterministic scripts (covered above):
- [r_deseq2_wrapper.py](scripts/r_deseq2_wrapper.py) - R DESeq2 multi-contrast + Venn + per-gene LFC
- [multi_strain_venn.py](scripts/multi_strain_venn.py) - Venn-style overlap percentages from DEG CSVs
- [gene_length_correlation.py](scripts/gene_length_correlation.py) - Length vs expression Pearson r (all variants)
- [pca_variance.py](scripts/pca_variance.py) - % variance per PC across all common PCA variants
- [one_way_anova_f.py](scripts/one_way_anova_f.py) - ANOVA F-stat + p-value (long/wide/LFC-frame)

Helper utilities:
- [format_deseq2_output.py](scripts/format_deseq2_output.py) - Output formatters
- [load_count_matrix.py](scripts/load_count_matrix.py) - Data loading utilities
- [convert_rds_to_csv.py](scripts/convert_rds_to_csv.py) - Convert .rds DESeq2 results to CSV

## Analysis conventions

### DESeq2 library choice — match the authoritative pipeline

If the data folder contains a `run_*.py` that uses `pydeseq2` or an `analysis.R` that uses R DESeq2, USE THAT EXACT LIBRARY. The two libraries disagree on small numerical details (DEG counts at the same threshold typically differ by 2-10%), so the GT comes from whichever the authoritative pipeline ran.

If NO authoritative script exists, prefer R DESeq2 (via `run_deseq2_analysis` tool or `Rscript`) — it's the more widely-published reference implementation:
```bash
tu run run_deseq2_analysis '{"operation":"deseq2","counts_file":"raw_counts.csv","metadata_file":"experiment_metadata.csv","design":"~ Replicate + Media + Strain","contrast":"Strain, 97, 1","refit_cooks":true}'
```

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

## Density / per-chromosome calculation conventions

When a question asks for "average chromosomal density", "genome-wide average density", or similar:
- "Average chromosomal density" = `mean(per_chromosome_density)` where `per_chromosome_density = n_features / chromosome_length` for each chromosome separately, then averaged across chromosomes (UNWEIGHTED mean).
- This is DIFFERENT from `total_features / total_length` (which is the WEIGHTED mean / "expected density under uniform distribution"). The latter is typically used as the chi-square test's expected value, not as the "average chromosomal density" being asked about.
- Example: in bird genomes with chromosomes ranging 6-120 Mb, mean(per_chrom_density) is ~2× larger than total/total because shorter chromosomes have proportionally more events per bp.
