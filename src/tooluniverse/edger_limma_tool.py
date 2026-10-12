"""edgeR / limma-voom differential-expression analysis tool.

Runs edgeR (QL-F) or limma-voom via Rscript on a count matrix + metadata —
the two standard bulk RNA-seq DE frameworks alongside DESeq2 (`run_deseq2_analysis`).
Mirrors the `DESeq2Tool` R-subprocess pattern; the R pipeline is ported from the
rnaseq-deseq2 skill's validated `r_edger_limma_wrapper.py`. Returns DEG counts at
the standard filter combinations plus the full ranked table on disk.

Requires Rscript with the Bioconductor `edgeR` + `limma` packages installed; the
tool returns a clean error (it never raises) if R or the packages are missing.
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict

from .base_tool import BaseTool
from .r_literals import r_formula, r_number, r_string
from .tool_registry import register_tool

# Ported verbatim from r_edger_limma_wrapper.py (validated), with a structured
# RESULT_JSON block appended for the tool. `.format()` substitution: literal R
# braces are doubled, `{name}` are parameters.
#
# Every `{name}` below is an *already quoted* R literal, not a bare value: the
# string parameters arrive as `_r_string(...)` output, so the template carries no
# quotes of its own. A path or a design formula containing a quote would
# otherwise close the literal and the rest of it would be read as R code.
_R_TEMPLATE = r"""
suppressMessages({{
  library(edgeR)
  library(limma)
}})

args_counts   <- {counts_path}
args_meta     <- {meta_path}
args_design   <- {design}
args_method   <- {method}
args_exclude_samples <- {exclude_samples}
args_report_genes    <- {report_genes}
args_lfc_thr  <- {lfc_thr}
args_fdr_thr  <- {fdr_thr}
args_expr_thr <- {expr_thr}
args_workdir  <- {workdir}
contrast_str  <- {contrast}

counts <- read.csv(args_counts, row.names=1, check.names=FALSE)
metadata <- read.csv(args_meta, check.names=FALSE)

sample_col <- NULL
for (cand in c("AzentaName","sample","SampleID","sample_id","SampleName","projid")) {{
  if (cand %in% colnames(metadata)) {{ sample_col <- cand; break }}
}}
if (is.null(sample_col)) sample_col <- colnames(metadata)[1]
rownames(metadata) <- as.character(metadata[[sample_col]])

if (nchar(args_exclude_samples) > 0) {{
  excl <- strsplit(args_exclude_samples, ",")[[1]]
  excl <- intersect(excl, colnames(counts))
  if (length(excl) > 0) counts <- counts[, !colnames(counts) %in% excl, drop=FALSE]
}}

common <- intersect(colnames(counts), rownames(metadata))
if (length(common) < 2) stop("fewer than 2 samples align between counts and metadata")
counts <- counts[, common, drop=FALSE]
metadata <- metadata[common, , drop=FALSE]

counts_int <- round(as.matrix(counts))
mode(counts_int) <- "integer"

design_terms <- all.vars(as.formula(args_design))
for (col in design_terms) {{
  if (col %in% colnames(metadata) && !is.factor(metadata[[col]])) {{
    metadata[[col]] <- factor(as.character(metadata[[col]]))
  }}
}}
design_formula <- as.formula(args_design)
design_mat <- model.matrix(design_formula, data=metadata)

parts <- strsplit(contrast_str, ",")[[1]]
if (length(parts) != 3) stop(paste("contrast must be 'factor,level1,level2', got:", contrast_str))
factor_name <- parts[1]; lvl1 <- parts[2]; lvl2 <- parts[3]
label <- paste0(factor_name, "_", lvl1, "_vs_", lvl2)
coef_name <- paste0(factor_name, lvl1)
ref_coef_name <- paste0(factor_name, lvl2)
use_contrast_vec <- FALSE
contrast_vec <- NULL
if (coef_name %in% colnames(design_mat) && ref_coef_name %in% colnames(design_mat)) {{
  contrast_vec <- rep(0, ncol(design_mat))
  names(contrast_vec) <- colnames(design_mat)
  contrast_vec[coef_name] <- 1
  contrast_vec[ref_coef_name] <- -1
  use_contrast_vec <- TRUE
}} else if (!(coef_name %in% colnames(design_mat))) {{
  stop(paste("cannot locate coefficient for contrast; available columns:",
             paste(colnames(design_mat), collapse=',')))
}}

dge <- DGEList(counts=counts_int)
keep <- filterByExpr(dge, design_mat)
dge <- dge[keep, , keep.lib.sizes=FALSE]
dge <- calcNormFactors(dge)

if (args_method == "edger") {{
  dge <- estimateDisp(dge, design_mat)
  fit <- glmQLFit(dge, design_mat)
  if (use_contrast_vec) {{
    qlf <- glmQLFTest(fit, contrast=contrast_vec)
  }} else {{
    qlf <- glmQLFTest(fit, coef=coef_name)
  }}
  res <- as.data.frame(topTags(qlf, n=Inf, sort.by="PValue")$table)
  lfc_col <- "logFC"; fdr_col <- "FDR"; expr_col <- "logCPM"
}} else if (args_method == "limma") {{
  v <- voom(dge, design_mat)
  fit <- lmFit(v, design_mat)
  if (use_contrast_vec) {{
    cm <- matrix(contrast_vec, ncol=1, dimnames=list(colnames(design_mat), label))
    fit <- eBayes(contrasts.fit(fit, cm))
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
fdr_ok  <- !is.na(res[[fdr_col]]) & res[[fdr_col]] < args_fdr_thr
lfc_ok  <- abs(res[[lfc_col]]) > args_lfc_thr
expr_ok <- res[[expr_col]] > args_expr_thr
n_padj_only <- sum(fdr_ok)
n_padjlfc   <- sum(fdr_ok & lfc_ok)
n_strict    <- sum(fdr_ok & lfc_ok & expr_ok)

gene_report <- list()
if (nchar(args_report_genes) > 0) {{
  for (g in strsplit(args_report_genes, ",")[[1]]) {{
    if (g %in% rownames(res)) {{
      gene_report[[g]] <- list(logFC=unname(res[g, lfc_col]), FDR=unname(res[g, fdr_col]))
    }}
  }}
}}

out_csv <- file.path(args_workdir, paste0("res_", args_method, "_", label, ".csv"))
write.csv(res, out_csv)

cat("RESULT_JSON_START\n")
result <- list(
  method = args_method, contrast = label,
  n_genes = nrow(res), n_tested = n_tested,
  sig_padj_only = n_padj_only, sig_padjlfc = n_padjlfc, sig_strict = n_strict,
  fdr_threshold = args_fdr_thr, lfc_threshold = args_lfc_thr,
  gene_report = gene_report
)
cat(jsonlite::toJSON(result, auto_unbox=TRUE, null="null"))
cat("\nRESULT_JSON_END\n")
cat("RESULTS_FILE:", normalizePath(out_csv), "\n")
"""


@register_tool("EdgeRLimmaTool")
class EdgeRLimmaTool(BaseTool):
    """Run edgeR (QL-F) or limma-voom differential expression via Rscript."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        counts_file = arguments.get("counts_file", "")
        metadata_file = arguments.get("metadata_file", "")
        method = (arguments.get("method") or "edger").lower()
        contrast = arguments.get("contrast", "")
        design = arguments.get("design") or "~ condition"

        if method not in ("edger", "limma"):
            return {"status": "error", "error": "method must be 'edger' or 'limma'."}
        if not counts_file or not os.path.exists(counts_file):
            return {"status": "error", "error": f"Counts file not found: {counts_file}"}
        if not metadata_file or not os.path.exists(metadata_file):
            return {
                "status": "error",
                "error": f"Metadata file not found: {metadata_file}",
            }
        if len(str(contrast).split(",")) != 3:
            return {
                "status": "error",
                "error": "contrast must be 'factor,level1,level2'.",
            }

        # Every argument becomes a quoted R literal here rather than in the
        # template: these values reach us from a model or an upstream request,
        # and a bare one would be R code.
        try:
            substitutions = dict(
                design=r_formula(design, "design"),
                method=r_string(method),
                exclude_samples=r_string(arguments.get("exclude_samples", "") or ""),
                report_genes=r_string(arguments.get("report_genes", "") or ""),
                lfc_thr=r_number(arguments.get("lfc_threshold", 0.5), "lfc_threshold"),
                fdr_thr=r_number(arguments.get("fdr_threshold", 0.05), "fdr_threshold"),
                expr_thr=r_number(
                    arguments.get("expr_threshold", 0.0), "expr_threshold"
                ),
                contrast=r_string(contrast),
            )
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        workdir = tempfile.mkdtemp(prefix=f"{method}_de_")
        r_script = _R_TEMPLATE.format(
            counts_path=r_string(counts_file),
            meta_path=r_string(metadata_file),
            workdir=r_string(workdir),
            **substitutions,
        )

        try:
            return self._run(r_script, method)
        finally:
            # Only an empty directory is removed, so a run that produced the
            # ranked table keeps it; a run that failed leaves nothing behind.
            try:
                os.rmdir(workdir)
            except OSError:
                pass

    def _run(self, r_script: str, method: str) -> Dict[str, Any]:
        try:
            r = subprocess.run(
                ["Rscript", "-e", r_script],
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            return {"status": "error", "error": "Rscript not found. Install R."}
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"{method} timed out after 600s"}
        except Exception as e:  # pragma: no cover - defensive
            return {"status": "error", "error": str(e)[:500]}

        if r.returncode != 0:
            msg = (r.stderr or "").strip()
            hint = ""
            if "there is no package" in msg or "could not find function" in msg:
                hint = " (install Bioconductor edgeR + limma)"
            return {"status": "error", "error": f"R {method} failed{hint}: {msg[:500]}"}

        out = r.stdout
        if "RESULT_JSON_START\n" not in out:
            return {"status": "error", "error": f"no result parsed: {out[-500:]}"}
        json_block = out.split("RESULT_JSON_START\n", 1)[1].split("\nRESULT_JSON_END")[
            0
        ]
        try:
            data = json.loads(json_block)
        except ValueError:
            return {
                "status": "error",
                "error": f"unreadable result: {json_block[:500]}",
            }

        results_file = ""
        for line in out.splitlines():
            if line.startswith("RESULTS_FILE:"):
                results_file = line.split(":", 1)[1].strip()
        # The ranked table is most of what a caller asked for, so a run that did
        # not leave it on disk is not a success -- without this check the path
        # is simply absent from the result and the caller finds out by KeyError.
        if not results_file or not os.path.isfile(results_file):
            return {
                "status": "error",
                "error": f"Results file not found: {results_file}",
            }
        data["results_file"] = results_file
        return {"status": "success", "data": data}
