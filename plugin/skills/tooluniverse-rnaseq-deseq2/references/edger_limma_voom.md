# edgeR and limma-voom — alternative DE routes to DESeq2

DESeq2 is this skill's default route, but edgeR and limma-voom are the two
other standard bulk RNA-seq differential-expression frameworks. Published
pipelines routinely route across all three.
This doc gives the concrete R command sequences, the input/output contracts,
and how to read each framework's output relative to DESeq2's.

The bundled `scripts/r_edger_limma_wrapper.py` runs both of these for you with
the same workspace-isolation and parseable-output conventions as
`r_deseq2_wrapper.py`. Use the wrapper first; the raw command sequences below
are for when you need a variant the wrapper does not expose.

---

## When to use which (see also the routing subsection in SKILL.md)

| Situation | Prefer | Why |
|---|---|---|
| Standard 2-group, modest n, default ask | **DESeq2** | The most widely-published reference; shrinkage + independent filtering tuned for small n. |
| Very small replicate counts (n=2-3/group), simple 2-group | **edgeR** (exact test or QL-F) | Empirical-Bayes dispersion moderation is robust at tiny n; QL-F controls the FDR well. |
| Large n, complex/multi-factor designs, many contrasts, speed matters | **limma-voom** | Fits a linear model per gene (fast, flexible); `duplicateCorrelation` handles repeated measures; trivially extends to interaction terms and many contrasts. |
| You need precise weights for heteroscedastic counts at scale | **limma-voom** | `voom()` models the mean-variance trend explicitly as observation weights. |

These are reasoned defaults, not hard rules. When an authoritative script or
executed notebook in the data folder already ran one framework, match it —
the published ground-truth number comes from whichever the pipeline used.
The three frameworks usually agree on the strongly-DE genes but differ by a
few percent on borderline counts at the same threshold.

---

## edgeR — quasi-likelihood F-test (QL-F) pipeline

Recommended modern edgeR route (preferred over the classic exact test for
anything beyond a single 2-group comparison):

```r
library(edgeR)
# counts: integer matrix, genes x samples. group/design from metadata.
dge <- DGEList(counts = counts_int)
design <- model.matrix(~ condition, data = metadata)   # or ~ batch + condition
keep <- filterByExpr(dge, design)                       # standard low-count filter
dge  <- dge[keep, , keep.lib.sizes = FALSE]
dge  <- calcNormFactors(dge)                            # TMM normalization
dge  <- estimateDisp(dge, design)                       # NB dispersions (trended + tagwise)
fit  <- glmQLFit(dge, design)                           # quasi-likelihood GLM
qlf  <- glmQLFTest(fit, coef = "conditiontreated")      # test one coefficient
# ...or an explicit contrast between two non-reference levels:
# con <- makeContrasts(grpB - grpC, levels = design)
# qlf <- glmQLFTest(fit, contrast = con)
res  <- topTags(qlf, n = Inf, sort.by = "PValue")$table
```

Classic exact test (only valid for a single one-way grouping, no covariates):

```r
dge <- DGEList(counts = counts_int, group = metadata$condition)
dge <- calcNormFactors(dge)
dge <- estimateDisp(dge)
et  <- exactTest(dge, pair = c("control", "treated"))
res <- topTags(et, n = Inf)$table
```

**edgeR output columns**: `logFC`, `logCPM`, `F` (QL-F) or `logFC`/`logCPM`/`PValue`
(exact test), `PValue`, `FDR`.

---

## limma-voom pipeline

```r
library(limma); library(edgeR)
dge <- DGEList(counts = counts_int)
design <- model.matrix(~ batch + condition, data = metadata)
keep <- filterByExpr(dge, design)
dge  <- dge[keep, , keep.lib.sizes = FALSE]
dge  <- calcNormFactors(dge)                 # TMM (from edgeR)
v    <- voom(dge, design)                    # mean-variance weights -> logCPM
fit  <- lmFit(v, design)
# single coefficient:
fit  <- eBayes(fit)
res  <- topTable(fit, coef = "conditiontreated", number = Inf, sort.by = "P")
# ...or an explicit contrast:
# cm  <- makeContrasts(conditiontreated, levels = design)
# fit <- eBayes(contrasts.fit(lmFit(v, design), cm))
# res <- topTable(fit, coef = 1, number = Inf, sort.by = "P")
```

For repeated measures / paired designs, estimate the intra-block correlation
and pass it to both `voom` and `lmFit`:

```r
corfit <- duplicateCorrelation(v, design, block = metadata$subject)
v      <- voom(dge, design, block = metadata$subject, correlation = corfit$consensus)
fit    <- lmFit(v, design, block = metadata$subject, correlation = corfit$consensus)
```

**limma-voom output columns**: `logFC`, `AveExpr`, `t`, `P.Value`,
`adj.P.Val` (BH-adjusted), `B` (log-odds of DE).

---

## Input contract (shared with the DESeq2 wrapper)

- **Count matrix**: CSV, genes as rows, samples as columns, first column = gene
  IDs. RAW integer counts (NOT normalized/TPM/CPM). The wrapper rounds and
  integer-coerces; if your matrix is already normalized, edgeR/limma results
  will be wrong — supply raw counts.
- **Sample metadata**: CSV, one row per sample. The wrapper auto-detects the
  sample-name column (`AzentaName`, `sample`, `SampleID`, `sample_id`,
  `SampleName`, `projid`, else first column) and aligns it to the count
  columns.
- **Design**: an R formula string, e.g. `~condition` or `~batch + condition`.
  Factor of interest typically last.
- **Contrast**: `factor,level1,level2` meaning level1 vs level2. If level2 is
  the model's reference level, the wrapper tests the single
  `<factor><level1>` coefficient; otherwise it builds an explicit
  `+1/-1` contrast vector between the two non-reference columns.

## Output contract

`r_edger_limma_wrapper.py` writes one ranked CSV to `--workdir`
(`res_<method>_<label>.csv`) and prints parseable lines:

```
# METHOD edger|limma
# CONTRAST <factor>_<lvl1>_vs_<lvl2>: n_genes=<after filterByExpr> n_tested=<x>
# SIG_<label>_padj_only (FDR<thr): n=...
# SIG_<label>_padjlfc (FDR<thr AND |logFC|>thr): n=...
# SIG_<label>_strict (FDR<thr AND |logFC|>thr AND logCPM/AveExpr>thr): n=...
# GENE <name> [<label>]: logFC=... FDR=...
# TABLE <abs path to ranked CSV>
```

The three `SIG_*` lines mirror `r_deseq2_wrapper.py` exactly, so DEG counts are
directly comparable across the DESeq2 / edgeR / limma-voom routes. Default to
the `_padj_only` line unless the question names an `|logFC|` or expression
threshold (same rule as the DESeq2 route).

---

## Column-name crosswalk (edgeR / limma vs DESeq2)

| Concept | DESeq2 | edgeR | limma-voom |
|---|---|---|---|
| log2 fold change | `log2FoldChange` | `logFC` | `logFC` |
| mean expression | `baseMean` (linear) | `logCPM` (log2) | `AveExpr` (log2) |
| test statistic | `stat` (Wald) | `F` (QL-F) / nothing (exact) | `t` |
| raw p-value | `pvalue` | `PValue` | `P.Value` |
| adjusted p (BH/FDR) | `padj` | `FDR` | `adj.P.Val` |
| (extra) | `lfcSE` | — | `B` (log-odds DE) |

**Interpretation notes**

- All three `logFC`/`log2FoldChange` are log2; sign convention is level1 vs
  level2 (positive = up in level1). edgeR/limma do NOT shrink the logFC by
  default, so their `logFC` is comparable to DESeq2's UNSHRUNKEN
  `log2FoldChange`, not the apeglm-shrunken value. For individual low-count
  gene queries, the edgeR/limma `logFC` behaves like the unshrunken DESeq2 LFC.
- `baseMean` (DESeq2, linear scale) and `logCPM`/`AveExpr` (log2 scale) are NOT
  the same units — do not threshold them with the same number. A
  `baseMean>10` filter has no direct edgeR/limma equivalent; `filterByExpr`
  already removes low-count genes upstream, which is the edgeR/limma analogue
  of DESeq2's independent filtering.
- "Significant DEGs" defaults to `FDR < 0.05` / `adj.P.Val < 0.05` —
  the `_padj_only` line — unless the question adds a fold-change or
  expression threshold.
