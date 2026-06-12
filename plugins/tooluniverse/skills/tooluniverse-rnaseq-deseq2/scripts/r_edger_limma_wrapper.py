#!/usr/bin/env python3
"""Run edgeR or limma-voom differential expression on a count matrix as an
alternative DE route alongside DESeq2 — a single deterministic, run-if-available
wrapper.

Why this exists
---------------
The skill's primary DE route is DESeq2 (`r_deseq2_wrapper.py`). edgeR and
limma-voom are the two other standard bulk RNA-seq DE frameworks; published
pipelines route across all three depending on sample size and design (see the
"Choosing DESeq2 vs edgeR vs limma-voom" section of SKILL.md and
references/edger_limma_voom.md). This wrapper mirrors `r_deseq2_wrapper.py` so
the agent has a deterministic edgeR / limma-voom path with the same arg parsing,
the same workspace-isolation guarantees, and a parseable ranked-table output.

Run-if-available preflight (NEVER fabricates results)
-----------------------------------------------------
This script PREFLIGHTS its external dependencies before doing any work:
  - `Rscript` must be on PATH,
  - the requested method's Bioconductor packages must be installed
    (edgeR + limma for --method edger; limma + edgeR for --method limma —
    limma-voom uses edgeR's DGEList/calcNormFactors).
If anything is missing it prints a clear, copy-pasteable install plan and
exits 0 WITHOUT producing a results table. It never invents numbers. The
agent reading this output knows to either install the packages or fall back
to the DESeq2 route / `read_executed_notebook`.

Methods
-------
--method edger  : classic edgeR QL-F pipeline
    DGEList -> filterByExpr -> calcNormFactors(TMM) -> estimateDisp(design)
    -> glmQLFit(design) -> glmQLFTest(coef/contrast) -> topTags
    Columns: logFC, logCPM, F, PValue, FDR

--method limma  : limma-voom pipeline
    DGEList -> filterByExpr -> calcNormFactors(TMM) -> voom(design)
    -> lmFit(design) -> contrasts.fit (if contrast) -> eBayes -> topTable
    Columns: logFC, AveExpr, t, P.Value, adj.P.Val, B

Both write a full ranked table to --workdir and print parseable DEG-count
summaries at the same three filter combinations as r_deseq2_wrapper.py
(padj_only / padj+|LFC| / padj+|LFC|+expression), so counts are directly
comparable to the DESeq2 route.

Usage examples
--------------
    # edgeR QL-F, condition treated vs control (ref = control)
    python r_edger_limma_wrapper.py \\
        --count-matrix /path/counts.csv --sample-metadata /path/meta.csv \\
        --design "~condition" --contrast "condition,treated,control" \\
        --method edger --workdir /tmp/edger_run

    # limma-voom, multi-factor design with a covariate
    python r_edger_limma_wrapper.py \\
        --count-matrix /path/counts.csv --sample-metadata /path/meta.csv \\
        --design "~batch + condition" --contrast "condition,treated,control" \\
        --method limma --workdir /tmp/limma_run

Output blocks (parseable)
-------------------------
    # METHOD edger|limma
    # CONTRAST <factor>_<lvl1>_vs_<lvl2>: n_genes=<after filter> n_tested=<x>
    # SIG_<label>_padj_only (FDR<thr): n=...
    # SIG_<label>_padjlfc (FDR<thr AND |logFC|>thr): n=...
    # SIG_<label>_strict (FDR<thr AND |logFC|>thr AND AveExpr/logCPM>thr): n=...
    # GENE <name> [<label>]: logFC=... FDR=...
    # TABLE <abs path to ranked CSV>

WORKSPACE ISOLATION
-------------------
This script ONLY writes to --workdir (default: $TMPDIR/r_edger_limma_<pid>).
It NEVER writes into the directory containing the input count matrix /
metadata, so read-only input folders are guaranteed safe.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Bioconductor packages each method needs. limma-voom relies on edgeR's
# DGEList/calcNormFactors, so both methods require both packages in practice.
METHOD_PACKAGES = {
    "edger": ["edgeR", "limma"],
    "limma": ["limma", "edgeR"],
}


def emit_install_plan(missing_rscript: bool, missing_pkgs: list[str], method: str) -> None:
    """Print a clear, copy-pasteable install plan. Caller exits 0 afterwards."""
    print("# PREFLIGHT: required dependencies are missing — NO results were computed.")
    print(f"# METHOD requested: {method}")
    if missing_rscript:
        print("# MISSING: Rscript (R is not installed or not on PATH)")
        print("#   Install R, then re-run. Install options:")
        print("#     conda:  conda install -c conda-forge r-base")
        print("#     macOS:  brew install r")
        print("#     debian: sudo apt-get install r-base")
    if missing_pkgs:
        print(f"# MISSING Bioconductor packages: {', '.join(missing_pkgs)}")
        print("#   Install with (one option):")
        pkg_vec = ", ".join(f'"{p}"' for p in missing_pkgs)
        print('#     conda:  conda install -c bioconda '
              + " ".join(f"bioconductor-{p.lower()}" for p in missing_pkgs))
        print('#     R/BiocManager:')
        print('#       Rscript -e \'if (!requireNamespace("BiocManager", quietly=TRUE)) '
              'install.packages("BiocManager"); '
              f'BiocManager::install(c({pkg_vec}))\'')
    print("# NEXT STEPS: install the above, then re-run this command. "
          "If installation is not possible in this environment, fall back to "
          "the DESeq2 route (r_deseq2_wrapper.py) or read the executed notebook "
          "(read_executed_notebook) for the published DE result.")
    print("# PREFLIGHT_RESULT: install_plan_emitted (exit 0, no fabricated results)")


def check_r_packages(packages: list[str]) -> list[str]:
    """Return the subset of `packages` that Rscript reports as NOT installed.

    Runs a tiny Rscript that prints one line per package. If Rscript itself
    errors, conservatively treat all packages as missing (caller already
    confirmed Rscript is on PATH before calling this).
    """
    checks = "; ".join(
        f'cat("PKG {p}", as.integer(requireNamespace("{p}", quietly=TRUE)), "\\n")'
        for p in packages
    )
    try:
        proc = subprocess.run(
            ["Rscript", "-e", checks],
            capture_output=True, text=True, timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return list(packages)
    installed = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "PKG" and parts[2] == "1":
            installed.add(parts[1])
    return [p for p in packages if p not in installed]


R_SCRIPT_TEMPLATE = r"""
suppressMessages({{
  library(edgeR)
  library(limma)
}})

args_counts   <- "{counts_path}"
args_meta     <- "{meta_path}"
args_design   <- "{design}"
args_method   <- "{method}"
args_exclude_samples <- "{exclude_samples}"
args_report_genes    <- "{report_genes}"
args_lfc_thr  <- {lfc_thr}
args_fdr_thr  <- {fdr_thr}
args_expr_thr <- {expr_thr}
args_workdir  <- "{workdir}"

# Contrast "factor,level1,level2"
contrast_str <- "{contrast}"

cat("# METHOD", args_method, "\n")

counts <- read.csv(args_counts, row.names=1, check.names=FALSE)
metadata <- read.csv(args_meta, check.names=FALSE)

# Resolve the metadata sample-name column (mirror r_deseq2_wrapper.py).
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
    counts <- counts[, !colnames(counts) %in% excl, drop=FALSE]
    cat("# excluded samples:", excl, "\n")
  }}
}}

# Align counts columns to metadata rows
common <- intersect(colnames(counts), rownames(metadata))
if (length(common) < 2) stop("fewer than 2 samples align between counts and metadata")
counts <- counts[, common, drop=FALSE]
metadata <- metadata[common, , drop=FALSE]

# Round/integer-coerce (edgeR expects integer-like counts)
counts_int <- round(as.matrix(counts))
mode(counts_int) <- "integer"

# Coerce design-formula columns to factors
design_terms <- all.vars(as.formula(args_design))
for (col in design_terms) {{
  if (col %in% colnames(metadata) && !is.factor(metadata[[col]])) {{
    metadata[[col]] <- factor(as.character(metadata[[col]]))
    cat("# coerced to factor:", col, "levels:", paste(levels(metadata[[col]]), collapse=','), "\n")
  }}
}}

design_formula <- as.formula(args_design)
design_mat <- model.matrix(design_formula, data=metadata)
cat("# design:", deparse(design_formula), "-> columns:", paste(colnames(design_mat), collapse=','), "\n")

# Resolve the contrast to a coefficient name in the design matrix.
parts <- strsplit(contrast_str, ",")[[1]]
if (length(parts) != 3) stop(paste("contrast must be 'factor,level1,level2', got:", contrast_str))
factor_name <- parts[1]; lvl1 <- parts[2]; lvl2 <- parts[3]
label <- paste0(factor_name, "_", lvl1, "_vs_", lvl2)

# model.matrix names a treatment-coded coefficient "<factor><level>".
coef_name <- paste0(factor_name, lvl1)
ref_coef_name <- paste0(factor_name, lvl2)
use_contrast_vec <- FALSE
contrast_vec <- NULL
if (coef_name %in% colnames(design_mat) && ref_coef_name %in% colnames(design_mat)) {{
  # Both levels are non-reference columns -> build an explicit contrast.
  contrast_vec <- rep(0, ncol(design_mat))
  names(contrast_vec) <- colnames(design_mat)
  contrast_vec[coef_name] <- 1
  contrast_vec[ref_coef_name] <- -1
  use_contrast_vec <- TRUE
  cat("# contrast: explicit", coef_name, "-", ref_coef_name, "\n")
}} else if (coef_name %in% colnames(design_mat)) {{
  # lvl2 is the model's reference level -> single coefficient.
  cat("# contrast: coefficient", coef_name, "(", lvl2, "is reference)\n")
}} else {{
  stop(paste("cannot locate coefficient for contrast; available columns:",
             paste(colnames(design_mat), collapse=',')))
}}

dge <- DGEList(counts=counts_int)
keep <- filterByExpr(dge, design_mat)
dge <- dge[keep, , keep.lib.sizes=FALSE]
cat("# after filterByExpr:", nrow(dge), "genes\n")
dge <- calcNormFactors(dge)  # TMM

if (args_method == "edger") {{
  dge <- estimateDisp(dge, design_mat)
  fit <- glmQLFit(dge, design_mat)
  if (use_contrast_vec) {{
    qlf <- glmQLFTest(fit, contrast=contrast_vec)
  }} else {{
    qlf <- glmQLFTest(fit, coef=coef_name)
  }}
  tt <- topTags(qlf, n=Inf, sort.by="PValue")$table
  res <- as.data.frame(tt)
  lfc_col <- "logFC"; fdr_col <- "FDR"; expr_col <- "logCPM"
}} else if (args_method == "limma") {{
  v <- voom(dge, design_mat)
  fit <- lmFit(v, design_mat)
  if (use_contrast_vec) {{
    cm <- matrix(contrast_vec, ncol=1, dimnames=list(colnames(design_mat), label))
    fit <- contrasts.fit(fit, cm)
    fit <- eBayes(fit)
    res <- topTable(fit, coef=1, number=Inf, sort.by="P")
  }} else {{
    fit <- eBayes(fit)
    res <- topTable(fit, coef=coef_name, number=Inf, sort.by="P")
  }}
  res <- as.data.frame(res)
  lfc_col <- "logFC"; fdr_col <- "adj.P.Val"; expr_col <- "AveExpr"
}} else {{
  stop(paste("unknown method:", args_method))
}}

n_tested <- sum(!is.na(res[[fdr_col]]))
cat("# CONTRAST ", label, ": n_genes=", nrow(res), " n_tested=", n_tested, "\n", sep="")

# Three DEG counts at the same filter combinations as r_deseq2_wrapper.py.
fdr_ok  <- !is.na(res[[fdr_col]]) & res[[fdr_col]] < args_fdr_thr
lfc_ok  <- abs(res[[lfc_col]]) > args_lfc_thr
expr_ok <- res[[expr_col]] > args_expr_thr

n_padj_only <- sum(fdr_ok)
n_padjlfc   <- sum(fdr_ok & lfc_ok)
n_strict    <- sum(fdr_ok & lfc_ok & expr_ok)
cat("# SIG_", label, "_padj_only (FDR<", args_fdr_thr, "): n=", n_padj_only, "\n", sep="")
cat("# SIG_", label, "_padjlfc (FDR<", args_fdr_thr, " AND |logFC|>", args_lfc_thr, "): n=", n_padjlfc, "\n", sep="")
cat("# SIG_", label, "_strict (FDR<", args_fdr_thr, " AND |logFC|>", args_lfc_thr,
    " AND ", expr_col, ">", args_expr_thr, "): n=", n_strict, "\n", sep="")

# Per-gene reporting
if (nchar(args_report_genes) > 0) {{
  genes <- strsplit(args_report_genes, ",")[[1]]
  for (g in genes) {{
    if (g %in% rownames(res)) {{
      lfc_v <- res[g, lfc_col]
      fdr_v <- res[g, fdr_col]
      cat(sprintf("# GENE %s [%s]: logFC=%.4f FDR=%s\n",
                  g, label, lfc_v,
                  ifelse(is.na(fdr_v), "NA", sprintf("%.4g", fdr_v))))
    }} else {{
      cat(sprintf("# GENE %s [%s]: not in filtered result table\n", g, label))
    }}
  }}
}}

out_csv <- file.path(args_workdir, paste0("res_", args_method, "_", label, ".csv"))
write.csv(res, out_csv)
cat("# TABLE ", normalizePath(out_csv), "\n", sep="")
cat("\n# DONE\n")
"""


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--count-matrix", required=True,
                    help="Counts CSV (genes x samples). First column = gene IDs.")
    ap.add_argument("--sample-metadata", required=True,
                    help="Metadata CSV (one row per sample).")
    ap.add_argument("--design", required=True,
                    help="Design formula like '~condition' or '~batch + condition'.")
    ap.add_argument("--contrast", required=True,
                    help="Contrast 'factor,level1,level2' (level1 vs level2).")
    ap.add_argument("--method", required=True, choices=["edger", "limma"],
                    help="DE framework: 'edger' (QL-F) or 'limma' (limma-voom).")
    ap.add_argument("--exclude-samples", default="",
                    help="Comma-separated sample IDs to drop (match count columns).")
    ap.add_argument("--report-genes", default="",
                    help="Comma-separated gene names to report individual logFC/FDR for.")
    ap.add_argument("--lfc-thr", type=float, default=0.5,
                    help="abs(logFC) threshold for sig sets (default 0.5).")
    ap.add_argument("--fdr-thr", type=float, default=0.05,
                    help="FDR (adjusted p) threshold for sig sets (default 0.05).")
    ap.add_argument("--expr-thr", type=float, default=0.0,
                    help="Expression threshold (logCPM for edgeR / AveExpr for limma) "
                         "for the strict sig set (default 0).")
    ap.add_argument("--workdir", default="",
                    help="Working directory for outputs (default: a fresh tempdir).")
    args = ap.parse_args()

    # --- PREFLIGHT (run-if-available): never fabricate results -------------
    missing_rscript = shutil.which("Rscript") is None
    packages = METHOD_PACKAGES[args.method]
    missing_pkgs: list[str] = []
    if missing_rscript:
        # Can't probe packages without Rscript; report them all as needed.
        missing_pkgs = list(packages)
    else:
        missing_pkgs = check_r_packages(packages)

    if missing_rscript or missing_pkgs:
        emit_install_plan(missing_rscript, missing_pkgs, args.method)
        # Exit 0: a clean, expected "tool not available" outcome, NOT a crash.
        sys.exit(0)

    # --- Inputs ------------------------------------------------------------
    counts_path = Path(args.count_matrix).resolve()
    meta_path = Path(args.sample_metadata).resolve()
    if not counts_path.exists():
        sys.exit(f"ERROR: count matrix not found: {counts_path}")
    if not meta_path.exists():
        sys.exit(f"ERROR: sample metadata not found: {meta_path}")

    # --- Isolated workdir (NEVER write into the input data folder) ---------
    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path(tempfile.mkdtemp(prefix="r_edger_limma_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"# workdir: {workdir}", file=sys.stderr)

    input_dir = counts_path.parent
    if workdir == input_dir or input_dir in workdir.parents:
        sys.exit(f"ERROR: workdir {workdir} is inside the input data folder "
                 f"{input_dir}. Use --workdir /tmp/... to keep input data read-only.")

    # --- Build and run the R script ----------------------------------------
    r_script = R_SCRIPT_TEMPLATE.format(
        counts_path=str(counts_path).replace("\\", "/"),
        meta_path=str(meta_path).replace("\\", "/"),
        design=args.design,
        method=args.method,
        exclude_samples=args.exclude_samples,
        report_genes=args.report_genes,
        lfc_thr=args.lfc_thr,
        fdr_thr=args.fdr_thr,
        expr_thr=args.expr_thr,
        contrast=args.contrast,
        workdir=str(workdir).replace("\\", "/"),
    )

    r_script_path = workdir / f"{args.method}_run.R"
    r_script_path.write_text(r_script)
    print(f"# R script: {r_script_path}", file=sys.stderr)

    result = subprocess.run(["Rscript", str(r_script_path)],
                            capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("--- R stderr ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
