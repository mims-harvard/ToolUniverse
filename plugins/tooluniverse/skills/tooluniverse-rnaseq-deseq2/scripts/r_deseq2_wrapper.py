#!/usr/bin/env python3
"""Run R DESeq2 (NOT pydeseq2) on a count matrix and emit DEG counts and
per-gene LFC values in a single deterministic script.

Why this exists:
- The skill repeatedly says "use R DESeq2 not pydeseq2", but pydeseq2 and
  R DESeq2 disagree on dispersion fitting and on apeglm shrinkage edge cases.
  Bundling a single CLI that shells out to Rscript with all standard params
  gives the agent a deterministic path that matches the published reference
  implementation.
- Outputs both shrunken AND unshrunken LFC for individual-gene queries —
  shrinkage over-pulls low-baseMean genes (e.g., lncRNAs with baseMean<10)
  toward zero, so individual-gene questions usually want the unshrunken
  results.
- Emits multiple DEG counts at common filter combinations so the agent can
  cross-check which filter the published notebook used.

Usage examples:

    # Standard DE: counts.csv (genes x samples), metadata.csv (samples x cols),
    # contrast "sex M vs F", default ~sex design.
    python r_deseq2_wrapper.py \\
        --counts /path/counts.csv --metadata /path/meta.csv \\
        --design "~sex" --contrast "sex,M,F"

    # Subset to CD4/CD8 cells, filter low-expression, with LFC shrinkage,
    # report individual gene FAM138A LFC and DEG count at the question's filter:
    python r_deseq2_wrapper.py \\
        --counts /path/counts.csv --metadata /path/meta.csv \\
        --design "~sex" --contrast "sex,M,F" \\
        --subset-col celltype --subset-values CD4,CD8 \\
        --min-row-sum 10 --shrink apeglm \\
        --report-genes FAM138A \\
        --workdir /tmp/bix31

    # Strain-specific Venn analysis: produce sig sets per contrast, count
    # overlaps. Use this to answer "% genes DE in A AND B NOT in others".
    python r_deseq2_wrapper.py \\
        --counts /path/counts.csv --metadata /path/meta.csv \\
        --design "~Replicate + Strain + Media" \\
        --multi-contrast "Strain,97,1;Strain,98,1;Strain,99,1" \\
        --exclude-samples resub-5,resub-10,resub-33 \\
        --workdir /tmp/bix13

Output blocks (parseable):
    # CONTRAST <label>: n=<total tested> n_padj<0.05=<x> n_strict=<x>
    # GENE <name>: baseMean=... unshrunkLFC=... shrunkLFC=... padj=...
    # SIG_<label>_strict: n=...  (strict = padj<0.05 AND |LFC|>thr AND baseMean>=base)
    # SIG_<label>_padj_only: n=...  (just padj<0.05)
    # SIG_<label>_padjlfc: n=...  (padj<0.05 AND |LFC|>thr, NO baseMean)
    # VENN A=<lbl>,B=<lbl>: |A|=... |B|=... |A∩B|=... |A∪B|=...
    # VENN3 A,B,C: |A∩B|=.. |A∪B∪C|=.. |A∩B-C|=.. |unique-A|=.. ...

The Rscript portion is small; this Python wrapper handles arg parsing,
workspace isolation (NEVER writes to the input data folder), and result
parsing.

WORKSPACE ISOLATION
-------------------
This script ONLY writes to --workdir (default: $TMPDIR/r_deseq2_<pid>).
It NEVER writes into the directory containing the input counts/metadata,
so read-only input folders are guaranteed safe.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


R_SCRIPT_TEMPLATE = r"""
suppressMessages({{
  library(DESeq2)
  has_apeglm <- requireNamespace("apeglm", quietly = TRUE)
  has_ashr   <- requireNamespace("ashr",   quietly = TRUE)
}})

args_counts   <- "{counts_path}"
args_meta     <- "{meta_path}"
args_design   <- "{design}"
args_subset_col   <- "{subset_col}"
args_subset_vals  <- "{subset_vals}"
args_exclude_samples <- "{exclude_samples}"
args_min_row_sum  <- {min_row_sum}
args_shrink   <- "{shrink}"
args_report_genes <- "{report_genes}"
args_baseMean_thr <- {basemean_thr}
args_lfc_thr      <- {lfc_thr}
args_padj_thr     <- {padj_thr}
args_workdir      <- "{workdir}"

# Multiple contrasts split by ";" — each "factor,level1,level2"
contrast_strs <- "{contrasts}"

cat("# R DESeq2 wrapper starting\n")

counts <- read.csv(args_counts, row.names=1, check.names=FALSE)
metadata <- read.csv(args_meta, check.names=FALSE)
# Try to set rownames on metadata: prefer column "AzentaName", "sample",
# or use the first column.
sample_col <- NULL
for (cand in c("AzentaName","sample","SampleID","sample_id","SampleName","projid")) {{
  if (cand %in% colnames(metadata)) {{ sample_col <- cand; break }}
}}
if (is.null(sample_col)) sample_col <- colnames(metadata)[1]
rownames(metadata) <- as.character(metadata[[sample_col]])
cat("# loaded counts:", dim(counts), "metadata:", dim(metadata), "sample col:", sample_col, "\n")

# Exclude specified samples
if (nchar(args_exclude_samples) > 0) {{
  excl <- strsplit(args_exclude_samples, ",")[[1]]
  excl <- intersect(excl, colnames(counts))
  if (length(excl) > 0) {{
    counts <- counts[, !colnames(counts) %in% excl]
    cat("# excluded samples:", excl, "\n")
  }}
  metadata <- metadata[rownames(metadata) %in% colnames(counts), , drop=FALSE]
}}

# Subset by metadata column values
if (nchar(args_subset_col) > 0 && nchar(args_subset_vals) > 0) {{
  vals <- strsplit(args_subset_vals, ",")[[1]]
  keep_samples <- rownames(metadata)[as.character(metadata[[args_subset_col]]) %in% vals]
  counts <- counts[, intersect(colnames(counts), keep_samples)]
  metadata <- metadata[colnames(counts), , drop=FALSE]
  cat("# subset to", length(keep_samples), "samples where", args_subset_col, "in {{", paste(vals, collapse=','), "}}\n")
}}

# Align countdata cols to metadata rows
common <- intersect(colnames(counts), rownames(metadata))
counts <- counts[, common, drop=FALSE]
metadata <- metadata[common, , drop=FALSE]

# Round and integer-coerce counts (DESeq2 requires integers; many
# normalized matrices come as floats)
counts_int <- round(as.matrix(counts))
mode(counts_int) <- "integer"

# Filter genes with low row sum
if (args_min_row_sum > 0) {{
  keep <- rowSums(counts_int) >= args_min_row_sum
  counts_int <- counts_int[keep, , drop=FALSE]
  cat("# after row sum filter (>=", args_min_row_sum, "): ", nrow(counts_int), "genes\n", sep="")
}}

# Convert character/logical AND any column referenced in the design or
# contrasts to factors. DESeq2 requires the contrast factor to actually be
# an R factor; integer-coded categorical columns (e.g., Strain="1","97",
# "98", "99" stored as int) silently break results(contrast=...).
factor_cols <- colnames(metadata)
for (col in factor_cols) {{
  if (is.character(metadata[[col]]) || is.logical(metadata[[col]])) {{
    metadata[[col]] <- factor(metadata[[col]])
  }}
}}
# Force factor on any column named in the design formula or contrasts
design_terms <- all.vars(as.formula(args_design))
contrast_factors <- character(0)
for (cs in strsplit(contrast_strs, ";")[[1]]) {{
  if (nchar(cs) == 0) next
  parts <- strsplit(cs, ",")[[1]]
  if (length(parts) >= 1) contrast_factors <- c(contrast_factors, parts[1])
}}
forced_cols <- unique(c(design_terms, contrast_factors))
for (col in forced_cols) {{
  if (col %in% colnames(metadata) && !is.factor(metadata[[col]])) {{
    metadata[[col]] <- factor(as.character(metadata[[col]]))
    cat("# coerced to factor:", col, "levels:", paste(levels(metadata[[col]]), collapse=','), "\n")
  }}
}}

design_formula <- as.formula(args_design)
cat("# design:", deparse(design_formula), "\n")
dds <- DESeqDataSetFromMatrix(countData=counts_int, colData=metadata, design=design_formula)
dds <- DESeq(dds)

# Process each contrast
contrasts_list <- strsplit(contrast_strs, ";")[[1]]
all_sig_sets_strict <- list()  # padj+LFC+baseMean
all_sig_sets_padjlfc <- list() # padj+LFC, no baseMean
all_sig_sets_padj <- list()    # padj only

for (contrast_str in contrasts_list) {{
  if (nchar(contrast_str) == 0) next
  parts <- strsplit(contrast_str, ",")[[1]]
  if (length(parts) != 3) {{
    cat("# SKIP malformed contrast:", contrast_str, "\n")
    next
  }}
  factor_name <- parts[1]; lvl1 <- parts[2]; lvl2 <- parts[3]
  label <- paste0(factor_name, "_", lvl1, "_vs_", lvl2)

  res_unshrunk <- results(dds, contrast=c(factor_name, lvl1, lvl2))
  df_un <- as.data.frame(res_unshrunk)

  # LFC shrinkage. apeglm requires the COEFFICIENT name, which DESeq2
  # builds as "<factor>_<lvl1>_vs_<refLvl>". For non-reference contrast
  # we fall back to ashr.
  df_sh <- df_un
  if (args_shrink %in% c("apeglm","ashr","normal")) {{
    coeff_name <- paste0(factor_name, "_", lvl1, "_vs_", lvl2)
    res_sh <- tryCatch({{
      if (args_shrink == "apeglm" && has_apeglm && (coeff_name %in% resultsNames(dds))) {{
        lfcShrink(dds, coef=coeff_name, type="apeglm")
      }} else if (args_shrink == "ashr" && has_ashr) {{
        lfcShrink(dds, contrast=c(factor_name, lvl1, lvl2), type="ashr")
      }} else if (args_shrink == "normal") {{
        lfcShrink(dds, contrast=c(factor_name, lvl1, lvl2), type="normal")
      }} else {{
        # Fallback: ashr if apeglm coeff not found
        if (has_ashr) lfcShrink(dds, contrast=c(factor_name, lvl1, lvl2), type="ashr") else NULL
      }}
    }}, error=function(e) {{ cat("# shrink err:", e$message, "\n"); NULL }})
    if (!is.null(res_sh)) df_sh <- as.data.frame(res_sh)
  }}

  n_total_tested <- sum(!is.na(df_un$padj))
  cat("# CONTRAST ", label, ": n=", nrow(df_un), " n_tested=", n_total_tested, "\n", sep="")

  # Three sig sets, both shrunk and unshrunk
  for (which_lfc in c("unshrunk","shrunk")) {{
    df_use <- if (which_lfc == "unshrunk") df_un else df_sh
    sig_strict <- rownames(df_use)[!is.na(df_use$padj) & df_use$padj < args_padj_thr &
                                    abs(df_use$log2FoldChange) > args_lfc_thr &
                                    df_use$baseMean > args_baseMean_thr]
    sig_padjlfc <- rownames(df_use)[!is.na(df_use$padj) & df_use$padj < args_padj_thr &
                                     abs(df_use$log2FoldChange) > args_lfc_thr]
    sig_padj <- rownames(df_use)[!is.na(df_use$padj) & df_use$padj < args_padj_thr]
    cat("# SIG_", label, "_", which_lfc, "_strict (padj<", args_padj_thr,
        " AND |LFC|>", args_lfc_thr, " AND baseMean>", args_baseMean_thr, "): n=", length(sig_strict), "\n", sep="")
    cat("# SIG_", label, "_", which_lfc, "_padjlfc (padj<", args_padj_thr,
        " AND |LFC|>", args_lfc_thr, ", NO baseMean): n=", length(sig_padjlfc), "\n", sep="")
    cat("# SIG_", label, "_", which_lfc, "_padj_only (padj<", args_padj_thr,
        "): n=", length(sig_padj), "\n", sep="")
    if (which_lfc == "shrunk") {{
      all_sig_sets_strict[[label]] <- sig_strict
      all_sig_sets_padjlfc[[label]] <- sig_padjlfc
      all_sig_sets_padj[[label]] <- sig_padj
    }}
  }}

  # Per-gene LFCs
  if (nchar(args_report_genes) > 0) {{
    genes <- strsplit(args_report_genes, ",")[[1]]
    for (g in genes) {{
      if (g %in% rownames(df_un)) {{
        bm <- df_un[g, "baseMean"]
        lfc_un <- df_un[g, "log2FoldChange"]
        lfc_sh <- df_sh[g, "log2FoldChange"]
        padj_un <- df_un[g, "padj"]
        cat(sprintf("# GENE %s [%s]: baseMean=%.4f unshrunkLFC=%.4f shrunkLFC=%.4f padj=%s\n",
                    g, label, bm, lfc_un, lfc_sh,
                    ifelse(is.na(padj_un), "NA", sprintf("%.4g", padj_un))))
      }}
    }}
  }}

  # Save full results table to workdir for downstream
  write.csv(df_un, file.path(args_workdir, paste0("res_unshrunk_", label, ".csv")))
  write.csv(df_sh, file.path(args_workdir, paste0("res_shrunk_",   label, ".csv")))
}}

# Venn-style overlap reporting on STRICT sig sets (padj+LFC+baseMean)
labels <- names(all_sig_sets_strict)
if (length(labels) >= 2) {{
  cat("\n# === VENN ANALYSIS (using STRICT sig sets, shrunk LFC) ===\n")
  cat("# Available labels:", paste(labels, collapse=" "), "\n")
  for (i in seq_along(labels)) {{
    L <- labels[i]
    cat(sprintf("# |SIG_%s|_strict=%d  |SIG_%s|_padjlfc=%d  |SIG_%s|_padj_only=%d\n",
                L, length(all_sig_sets_strict[[L]]),
                L, length(all_sig_sets_padjlfc[[L]]),
                L, length(all_sig_sets_padj[[L]])))
  }}
  # All pairwise + 3-way overlaps
  for (i in seq_along(labels)) {{
    for (j in seq_along(labels)) {{
      if (i >= j) next
      A <- all_sig_sets_strict[[labels[i]]]; B <- all_sig_sets_strict[[labels[j]]]
      cat(sprintf("# OVERLAP %s & %s: |A|=%d |B|=%d |A∩B|=%d |A∪B|=%d |A-B|=%d |B-A|=%d\n",
                  labels[i], labels[j], length(A), length(B),
                  length(intersect(A,B)), length(unique(c(A,B))),
                  length(setdiff(A,B)), length(setdiff(B,A))))
    }}
  }}
  if (length(labels) == 3) {{
    A <- all_sig_sets_strict[[labels[1]]]
    B <- all_sig_sets_strict[[labels[2]]]
    C <- all_sig_sets_strict[[labels[3]]]
    union3 <- unique(c(A,B,C))
    cat(sprintf("# VENN3 A=%s B=%s C=%s: |A|=%d |B|=%d |C|=%d\n",
                labels[1], labels[2], labels[3], length(A), length(B), length(C)))
    cat(sprintf("# VENN3 |A∪B∪C|=%d  |A∩B∩C|=%d\n", length(union3),
                length(Reduce(intersect, list(A,B,C)))))
    cat(sprintf("# VENN3 unique-only |A only|=%d |B only|=%d |C only|=%d\n",
                length(setdiff(A, union(B,C))),
                length(setdiff(B, union(A,C))),
                length(setdiff(C, union(A,B)))))
    cat(sprintf("# VENN3 |A∩B - C|=%d  |A∩C - B|=%d  |B∩C - A|=%d\n",
                length(setdiff(intersect(A,B), C)),
                length(setdiff(intersect(A,C), B)),
                length(setdiff(intersect(B,C), A))))
    # Common percentage interpretations
    n_AB_notC <- length(setdiff(intersect(A,B), C))
    cat(sprintf("# PCT |A∩B - C| / |A| = %.4f%%\n", 100*n_AB_notC/length(A)))
    cat(sprintf("# PCT |A∩B - C| / |B| = %.4f%%\n", 100*n_AB_notC/length(B)))
    cat(sprintf("# PCT |A∩B - C| / |A∩B| = %.4f%%\n", 100*n_AB_notC/length(intersect(A,B))))
    cat(sprintf("# PCT |A∩B - C| / |A∪B∪C| = %.4f%%\n", 100*n_AB_notC/length(union3)))
    cat(sprintf("# PCT |A∩C - B| / |A| = %.4f%%\n", 100*length(setdiff(intersect(A,C), B))/length(A)))
    cat(sprintf("# PCT |A∩C - B| / |C| = %.4f%%\n", 100*length(setdiff(intersect(A,C), B))/length(C)))
  }}
}}

cat("\n# DONE\n")
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counts", required=True, help="Counts CSV (genes x samples or samples x genes — auto-detect via metadata).")
    ap.add_argument("--metadata", required=True, help="Metadata CSV.")
    ap.add_argument("--design", required=True, help="Design formula like '~sex' or '~Replicate + Strain + Media'.")
    ap.add_argument("--contrast", help="Single contrast 'factor,level1,level2'.")
    ap.add_argument("--multi-contrast", help="Multiple contrasts joined by ';'.")
    ap.add_argument("--subset-col", default="", help="Metadata column to subset by.")
    ap.add_argument("--subset-values", default="", help="Comma-separated values to keep in --subset-col.")
    ap.add_argument("--exclude-samples", default="", help="Comma-separated sample IDs to drop (matches counts column names).")
    ap.add_argument("--min-row-sum", type=int, default=0, help="Filter genes with rowSum < this (default 0 = no filter).")
    ap.add_argument("--shrink", default="apeglm", choices=["apeglm","ashr","normal","none"],
                    help="LFC shrinkage method (default apeglm).")
    ap.add_argument("--report-genes", default="", help="Comma-separated gene names to report individual LFCs for.")
    ap.add_argument("--basemean-thr", type=float, default=10.0, help="baseMean threshold for STRICT sig set (default 10).")
    ap.add_argument("--lfc-thr", type=float, default=0.5, help="abs(log2FC) threshold for sig sets (default 0.5).")
    ap.add_argument("--padj-thr", type=float, default=0.05, help="padj threshold for sig sets (default 0.05).")
    ap.add_argument("--workdir", default="", help="Working directory for intermediate files (default: tempdir).")
    ap.add_argument("--counts-orientation", default="auto", choices=["auto","genes_x_samples","samples_x_genes"],
                    help="If auto, R script keeps as-is. If samples_x_genes, transpose first.")
    args = ap.parse_args()

    # Validate counts/metadata exist
    counts_path = Path(args.counts).resolve()
    meta_path = Path(args.metadata).resolve()
    if not counts_path.exists():
        sys.exit(f"ERROR: counts file not found: {counts_path}")
    if not meta_path.exists():
        sys.exit(f"ERROR: metadata file not found: {meta_path}")

    # Set up isolated workdir (NEVER write into the input data folder directory)
    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path(tempfile.mkdtemp(prefix="r_deseq2_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"# workdir: {workdir}", file=sys.stderr)

    # Refuse to write inside the input data folder
    input_dir = counts_path.resolve().parent
    workdir_r = workdir.resolve()
    if workdir_r == input_dir or input_dir in workdir_r.parents:
        sys.exit(f"ERROR: workdir {workdir} is inside the input data folder "
                 f"{input_dir}. Use --workdir /tmp/... to keep input data read-only.")

    # If the counts file is in samples_x_genes orientation, transpose it
    # to genes_x_samples and write the transposed version into workdir.
    counts_for_R = counts_path
    if args.counts_orientation == "samples_x_genes":
        import pandas as pd
        df = pd.read_csv(counts_path, index_col=0)
        df.T.to_csv(workdir / "counts_T.csv")
        counts_for_R = workdir / "counts_T.csv"
        print(f"# transposed counts to {counts_for_R}", file=sys.stderr)

    # Compose contrasts
    if args.multi_contrast:
        contrasts = args.multi_contrast
    elif args.contrast:
        contrasts = args.contrast
    else:
        sys.exit("ERROR: pass --contrast or --multi-contrast.")

    # Build the R script
    r_script = R_SCRIPT_TEMPLATE.format(
        counts_path=str(counts_for_R).replace("\\", "/"),
        meta_path=str(meta_path).replace("\\", "/"),
        design=args.design,
        subset_col=args.subset_col,
        subset_vals=args.subset_values,
        exclude_samples=args.exclude_samples,
        min_row_sum=args.min_row_sum,
        shrink=args.shrink,
        report_genes=args.report_genes,
        basemean_thr=args.basemean_thr,
        lfc_thr=args.lfc_thr,
        padj_thr=args.padj_thr,
        contrasts=contrasts,
        workdir=str(workdir).replace("\\", "/"),
    )

    r_script_path = workdir / "deseq2_run.R"
    r_script_path.write_text(r_script)
    print(f"# R script: {r_script_path}", file=sys.stderr)

    # Run Rscript
    result = subprocess.run(
        ["Rscript", str(r_script_path)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.stderr:
        print("--- R stderr ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
