"""R DESeq2 differential expression analysis tool.

Runs DESeq2 via Rscript for accurate differential expression analysis.
Handles count matrix + metadata → DEG list with proper design formulas,
dispersion estimation, and LFC shrinkage.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from .base_tool import BaseTool
from .r_literals import r_formula, r_identifier, r_level, r_number, r_string
from .tool_registry import register_tool


@register_tool("DESeq2Tool")
class DESeq2Tool(BaseTool):
    """Run R DESeq2 differential expression analysis."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "deseq2")
        if operation == "deseq2":
            return self._run_deseq2(arguments)
        elif operation == "enrichgo":
            return self._run_enrichgo(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    @staticmethod
    def _run_rscript(r_script: str, timeout: int = 300) -> subprocess.CompletedProcess:
        r"""Execute an R script by writing it to a temp file and running it.

        We deliberately run ``Rscript <file>`` rather than ``Rscript -e <string>``.
        The ``-e`` form collapses one backslash level before the R parser sees the
        code, so a regex literal such as the Ensembl-version strip ``sub("\\..*", ...)``
        (two backslashes in the generated R source) is mangled down to ``sub("\..*", ...)``
        and R aborts with "'\.' is an unrecognized escape in character string". A
        script file is parsed verbatim and is immune to this. The temp file is always
        removed, including on timeout.
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".R", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(r_script)
            tmp.close()
            return subprocess.run(
                ["Rscript", tmp.name],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    @staticmethod
    def _result_dir(prefix: str, name: str) -> str:
        """Create a private directory for one run's result CSV.

        R deletes its session ``tempdir()`` when ``Rscript`` exits, so the CSV
        has to be written elsewhere to stay readable. The shared temporary root
        is world-readable, and expression results are not ours to expose, so
        Python makes the directory (mode 0700) instead of letting R drop the
        file straight into the root.
        """
        return os.path.join(tempfile.mkdtemp(prefix=prefix), name)

    @staticmethod
    def _discard_empty_result_dir(out_file: str) -> None:
        """Drop the result directory when R never wrote into it.

        ``os.rmdir`` only succeeds while the directory is empty, so a result
        that was produced is never removed.
        """
        try:
            os.rmdir(os.path.dirname(out_file))
        except OSError:
            pass

    def _run_deseq2(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run DESeq2 differential expression analysis."""
        counts_file = arguments.get("counts_file", "")
        metadata_file = arguments.get("metadata_file", "")
        design = arguments.get("design", "~ condition")
        contrast = arguments.get("contrast", "")
        ref_level = arguments.get("ref_level", "")
        alpha = arguments.get("alpha", 0.05)
        lfc_threshold = arguments.get("lfc_threshold", 0)
        lfc_shrinkage = arguments.get("lfc_shrinkage", False)
        refit_cooks = arguments.get("refit_cooks", False)

        if not counts_file or not os.path.exists(counts_file):
            return {"status": "error", "error": f"Counts file not found: {counts_file}"}
        if not metadata_file or not os.path.exists(metadata_file):
            return {
                "status": "error",
                "error": f"Metadata file not found: {metadata_file}",
            }

        # These values reach us from a model or an upstream request and are
        # pasted into R source, where a bare one is code rather than data. Each
        # becomes a quoted literal or is refused by name.
        try:
            design_literal = r_formula(design, "design")
            alpha_literal = r_number(alpha, "alpha")
            lfc_literal = r_number(lfc_threshold, "lfc_threshold")
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        # Build R script
        r_script = f"""
suppressMessages({{
  library(DESeq2)
}})

counts <- read.csv({r_string(counts_file)}, row.names=1, check.names=FALSE)
meta <- read.csv({r_string(metadata_file)})

# Try to match sample IDs
if ("AzentaName" %in% colnames(meta)) {{
  rownames(meta) <- meta$AzentaName
}} else if ("sample" %in% colnames(meta)) {{
  rownames(meta) <- meta$sample
}} else {{
  rownames(meta) <- meta[,1]
}}

common <- intersect(colnames(counts), rownames(meta))
if (length(common) == 0) {{
  # Try matching without the first column
  for (col in colnames(meta)) {{
    if (length(intersect(as.character(meta[[col]]), colnames(counts))) > 2) {{
      rownames(meta) <- as.character(meta[[col]])
      common <- intersect(colnames(counts), rownames(meta))
      break
    }}
  }}
}}
counts <- counts[, common]
meta <- meta[common, ]

# Factorize design variables
for (v in all.vars(as.formula({design_literal}))) {{
  if (v %in% colnames(meta)) {{
    meta[[v]] <- factor(meta[[v]])
  }}
}}
"""
        if ref_level:
            parts = str(ref_level).split(",")
            if len(parts) == 2:
                # `meta[[name]]` instead of `meta$name`: the column is then
                # looked up by a string rather than spelled into the source, so
                # a factor name is data like every other argument.
                try:
                    column = r_level(parts[0], "ref_level factor")
                    level = r_level(parts[1], "ref_level reference level")
                except ValueError as e:
                    return {"status": "error", "error": str(e)}
                r_script += f"""
if (!({column} %in% colnames(meta))) {{
  stop(paste("ref_level names a column the metadata does not have:", {column}))
}}
meta[[{column}]] <- relevel(meta[[{column}]], ref={level})
"""

        r_script += f"""
dds <- DESeqDataSetFromMatrix(
  round(as.matrix(counts)), meta, as.formula({design_literal})
)
dds <- DESeq(dds{", quiet=TRUE" if not refit_cooks else ""})
"""
        if refit_cooks:
            r_script += "dds <- DESeq(dds, quiet=TRUE)\n"

        if contrast:
            parts = [p.strip().strip('"').strip("'") for p in str(contrast).split(",")]
            if len(parts) == 3:
                terms = ", ".join(r_string(p) for p in parts)
                r_script += (
                    f"res <- results(dds, contrast=c({terms}), alpha={alpha_literal})\n"
                )
            else:
                r_script += f"res <- results(dds, alpha={alpha_literal})\n"
        else:
            r_script += f"res <- results(dds, alpha={alpha_literal})\n"

        if lfc_shrinkage:
            r_script += """
res_shrunk <- lfcShrink(dds, coef=resultsNames(dds)[2], type="apeglm", quiet=TRUE)
res$log2FoldChange_shrunk <- res_shrunk$log2FoldChange
"""

        r_script += f"""
# Summary
sig <- res[!is.na(res$padj) & res$padj < {alpha_literal}, ]
cat("RESULT_JSON_START\\n")
result <- list(
  total_genes = nrow(res),
  sig_genes = nrow(sig),
  sig_up = sum(sig$log2FoldChange > 0, na.rm=TRUE),
  sig_down = sum(sig$log2FoldChange < 0, na.rm=TRUE),
  dispersion_below_1e5 = sum(mcols(dds)$dispGeneEst < 1e-05, na.rm=TRUE)
)
"""
        if float(lfc_threshold) > 0:
            r_script += f"""
sig_lfc <- res[!is.na(res$padj) & res$padj < {alpha_literal} & abs(res$log2FoldChange) > {lfc_literal}, ]
result$sig_with_lfc_filter <- nrow(sig_lfc)
"""

        out_file = self._result_dir("deseq2_results_", "deseq2_results.csv")
        r_script += f"""
cat(jsonlite::toJSON(result, auto_unbox=TRUE))
cat("\\nRESULT_JSON_END\\n")

# Save full results
out_file <- {json.dumps(out_file)}
write.csv(as.data.frame(res), out_file)
cat("RESULTS_FILE:", out_file, "\\n")
"""

        try:
            r = self._run_rscript(r_script)
            if r.returncode != 0:
                return {
                    "status": "error",
                    "error": f"R DESeq2 failed: {r.stderr[:500]}",
                }

            # Parse JSON from output
            output = r.stdout
            json_match = output.split("RESULT_JSON_START\n")
            if len(json_match) > 1:
                json_str = json_match[1].split("\nRESULT_JSON_END")[0]
                result_data = json.loads(json_str)
            else:
                result_data = {"raw_output": output[:1000]}

            # Get results file path
            results_file = ""
            for line in output.split("\n"):
                if line.startswith("RESULTS_FILE:"):
                    results_file = line.split(":", 1)[1].strip()

            if not results_file or not Path(results_file).is_file():
                return {
                    "status": "error",
                    "error": f"Results file not found: {results_file}",
                }

            result_data["results_file"] = results_file

            return {"status": "success", "data": result_data}

        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "DESeq2 timed out after 300s"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:500]}
        finally:
            self._discard_empty_result_dir(out_file)

    def _run_enrichgo(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run clusterProfiler enrichGO + simplify."""
        gene_list_file = arguments.get("gene_list_file", "")
        background_file = arguments.get("background_file", "")
        ont = arguments.get("ontology", "BP")
        simplify_cutoff = arguments.get("simplify_cutoff", 0.7)
        id_type = arguments.get("id_type", "ENSEMBL")
        organism = arguments.get("organism", "org.Hs.eg.db")

        if not gene_list_file or not os.path.exists(gene_list_file):
            return {
                "status": "error",
                "error": f"Gene list file not found: {gene_list_file}",
            }

        # `organism` names an annotation package, so it is the one argument that
        # has to stay unquoted R code -- hence it is checked to be a plain R
        # name. Everything else becomes a literal.
        try:
            org_name = r_identifier(organism, "organism")
            id_literal = r_string(id_type)
            ont_literal = r_string(ont)
            cutoff_literal = r_number(simplify_cutoff, "simplify_cutoff")
        except ValueError as e:
            return {"status": "error", "error": str(e)}

        r_script = f"""
suppressMessages({{
  library(clusterProfiler)
  library({org_name})
}})

genes <- readLines({r_string(gene_list_file)})
genes <- sub("\\\\..*", "", genes)  # Strip Ensembl version

gene_entrez <- bitr(genes, fromType={id_literal}, toType="ENTREZID", OrgDb={org_name})
"""
        if background_file and os.path.exists(background_file):
            r_script += f"""
bg <- readLines({r_string(background_file)})
bg <- sub("\\\\..*", "", bg)
bg_entrez <- bitr(bg, fromType={id_literal}, toType="ENTREZID", OrgDb={org_name})
universe_ids <- bg_entrez$ENTREZID
"""
        else:
            r_script += "universe_ids <- NULL\n"

        out_file = self._result_dir("enrichgo_simplified_", "enrichgo_simplified.csv")
        r_script += f"""
ego <- enrichGO(
  gene = gene_entrez$ENTREZID,
  universe = universe_ids,
  OrgDb = {org_name},
  ont = {ont_literal},
  pAdjustMethod = "BH",
  pvalueCutoff = 0.05,
  qvalueCutoff = 0.2,
  readable = TRUE
)
cat("enrichGO terms:", nrow(ego), "\\n")

ego2 <- clusterProfiler::simplify(ego, cutoff={cutoff_literal}, by="p.adjust", select_fun=min)
cat("Simplified terms:", nrow(ego2), "\\n")

df <- as.data.frame(ego2)

cat("RESULT_JSON_START\\n")
# Top 20 terms
top <- head(df[, c("ID","Description","pvalue","p.adjust","qvalue","Count")], 20)
cat(jsonlite::toJSON(top, auto_unbox=TRUE))
cat("\\nRESULT_JSON_END\\n")

# Save full results
out_file <- {json.dumps(out_file)}
write.csv(df, out_file, row.names=FALSE)
cat("RESULTS_FILE:", out_file, "\\n")
"""

        try:
            r = self._run_rscript(r_script)
            if r.returncode != 0:
                return {
                    "status": "error",
                    "error": f"enrichGO failed: {r.stderr[:500]}",
                }

            output = r.stdout
            json_match = output.split("RESULT_JSON_START\n")
            if len(json_match) > 1:
                json_str = json_match[1].split("\nRESULT_JSON_END")[0]
                terms = json.loads(json_str)
            else:
                terms = []

            results_file = ""
            for line in output.split("\n"):
                if line.startswith("RESULTS_FILE:"):
                    results_file = line.split(":", 1)[1].strip()

            if not results_file or not Path(results_file).is_file():
                return {
                    "status": "error",
                    "error": f"Results file not found: {results_file}",
                }

            return {
                "status": "success",
                "data": {
                    "n_terms_before_simplify": int(
                        next(
                            (
                                ln.split(":")[1].strip()
                                for ln in output.split("\n")
                                if "enrichGO terms:" in ln
                            ),
                            "0",
                        )
                    ),
                    "n_terms_after_simplify": int(
                        next(
                            (
                                ln2.split(":")[1].strip()
                                for ln2 in output.split("\n")
                                if "Simplified terms:" in ln2
                            ),
                            "0",
                        )
                    ),
                    "top_terms": terms,
                    "results_file": results_file,
                },
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "enrichGO timed out after 300s"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:500]}
        finally:
            self._discard_empty_result_dir(out_file)
