#!/usr/bin/env python3
"""Deterministic clusterProfiler::enrichGO + simplify(cutoff=0.7) wrapper.

Why this exists:
- enrichGO + simplify is the standard "GO enrichment with redundancy
  reduction" workflow used by many published RNA-seq notebooks. The
  agent's failure mode: it runs simplify but reports p.adjust from the
  RAW enrichment data frame, OR misses that simplify changes the
  p.adjust denominator and thus the values for surviving terms.
- This script runs enrichGO + simplify and emits BOTH the raw and
  simplified frames so the agent can pick the one the question asks for.
  When the question references "simplified" or "after simplify" or the
  notebook calls clusterProfiler::simplify, use the simplified column.

Usage:
    python enrichgo_runner.py \\
        --gene-list /tmp/sig_ensembl.txt \\
        --background /tmp/all_ensembl.txt \\
        --keytype ENSEMBL \\
        --ontology BP \\
        --simplify-cutoff 0.7 \\
        --candidate "regulation of T cell activation" \\
        --candidate "potassium ion transmembrane transport" \\
        --workdir /tmp/enrichgo_run

Output blocks (parseable):
    # ENRICHGO_RAW: n_terms=X
    # TOP10_RAW:
    #   1. <ID> | <Description> | p=... p.adjust=... q=... count=...
    # ENRICHGO_SIMPLIFIED (cutoff=0.7): n_terms=X
    # TOP10_SIMPLIFIED:
    #   1. <ID> | <Description> | p=... p.adjust=... q=...
    # CANDIDATE '<term>': raw_rank=R raw_padj=... simp_rank=R simp_padj=...
    # NOTE: simplify changes p.adjust because the multiple-testing
    #   denominator shrinks. Use the SIMPLIFIED p.adjust if the question
    #   says "in the simplified results" or "after simplify".

Required R packages: clusterProfiler, org.Hs.eg.db (or org.Mm.eg.db
for mouse). Install via skills/evals/install_r_packages.R.

WORKSPACE ISOLATION
-------------------
This script writes only to --workdir. NEVER writes to the gene-list dir.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


R_TEMPLATE = r"""
suppressMessages({{
  ok_cp <- requireNamespace("clusterProfiler", quietly = TRUE)
  ok_org <- requireNamespace("{org_db}", quietly = TRUE)
  if (!ok_cp || !ok_org) {{
    cat("# ERROR: required R packages not installed.\n")
    cat("#   Need: clusterProfiler, {org_db}\n")
    cat("#   Install: Rscript skills/evals/install_r_packages.R\n")
    quit(save="no", status=1)
  }}
  library(clusterProfiler)
  library({org_db})
}})

gene_file <- "{gene_file}"
bg_file   <- "{bg_file}"
keytype   <- "{keytype}"
ontology  <- "{ontology}"
pAdjust   <- "{p_adjust}"
pcutoff   <- {p_cutoff}
qcutoff   <- {q_cutoff}
simplify_cutoff <- {simplify_cutoff}
workdir   <- "{workdir}"

genes <- readLines(gene_file)
genes <- genes[nchar(genes) > 0]
# Strip header if first line looks non-ID
first <- genes[1]
if (length(genes) >= 2) {{
  if (toupper(first) %in% c("GENE","GENE_ID","GENEID","SYMBOL","ID","ENSEMBL","ENTREZ")) {{
    genes <- genes[-1]
  }}
}}
# For ENSEMBL: strip version suffix (ENSG00000123456.7 -> ENSG00000123456)
if (keytype == "ENSEMBL") {{
  genes <- sub("\\\\..*$", "", genes)
}}
cat("# input genes:", length(genes), "first 3:", head(genes, 3), "\n")

bg <- NULL
if (nchar(bg_file) > 0) {{
  bg <- readLines(bg_file)
  bg <- bg[nchar(bg) > 0]
  fb <- bg[1]
  if (length(bg) >= 2) {{
    if (toupper(fb) %in% c("GENE","GENE_ID","GENEID","SYMBOL","ID","ENSEMBL","ENTREZ")) {{
      bg <- bg[-1]
    }}
  }}
  if (keytype == "ENSEMBL") bg <- sub("\\\\..*$", "", bg)
  cat("# background genes:", length(bg), "\n")
}}

ego <- enrichGO(
  gene = genes,
  universe = bg,
  keyType = keytype,
  OrgDb = {org_db},
  ont = ontology,
  pAdjustMethod = pAdjust,
  pvalueCutoff = pcutoff,
  qvalueCutoff = qcutoff,
  readable = TRUE
)

if (is.null(ego)) {{
  cat("# ENRICHGO_RAW: NULL — no enrichment returned\n")
  quit(save="no")
}}

raw_df <- as.data.frame(ego)
cat("# ENRICHGO_RAW: n_terms=", nrow(raw_df), "\n", sep="")
write.csv(raw_df, file.path(workdir, "enrichgo_raw.csv"), row.names=FALSE)

# Top 10 raw
cat("# TOP10_RAW:\n")
n_show_raw <- min(10, nrow(raw_df))
if (n_show_raw > 0) {{
  for (i in 1:n_show_raw) {{
    cat(sprintf("#   %d. %s | %s | p=%.4g p.adjust=%.4g q=%.4g count=%d\n",
                i, raw_df$ID[i], raw_df$Description[i],
                raw_df$pvalue[i], raw_df$p.adjust[i], raw_df$qvalue[i],
                raw_df$Count[i]))
  }}
}}

# Run simplify
ego_simp <- tryCatch({{
  clusterProfiler::simplify(ego, cutoff=simplify_cutoff, by="p.adjust", select_fun=min)
}}, error=function(e) {{
  cat("# SIMPLIFY ERR:", e$message, "\n")
  NULL
}})

if (!is.null(ego_simp)) {{
  simp_df <- as.data.frame(ego_simp)
  cat("# ENRICHGO_SIMPLIFIED (cutoff=", simplify_cutoff, "): n_terms=", nrow(simp_df), "\n", sep="")
  write.csv(simp_df, file.path(workdir, "enrichgo_simplified.csv"), row.names=FALSE)

  cat("# TOP10_SIMPLIFIED:\n")
  n_show_s <- min(10, nrow(simp_df))
  if (n_show_s > 0) {{
    for (i in 1:n_show_s) {{
      cat(sprintf("#   %d. %s | %s | p=%.4g p.adjust=%.4g q=%.4g count=%d\n",
                  i, simp_df$ID[i], simp_df$Description[i],
                  simp_df$pvalue[i], simp_df$p.adjust[i], simp_df$qvalue[i],
                  simp_df$Count[i]))
    }}
  }}
}} else {{
  simp_df <- raw_df[0, , drop=FALSE]
  cat("# ENRICHGO_SIMPLIFIED: skipped (simplify returned NULL)\n")
}}

# Candidate terms
candidates <- strsplit("{candidates}", "\\|\\|\\|")[[1]]
candidates <- candidates[nchar(candidates) > 0]
for (cand in candidates) {{
  cand_l <- tolower(cand)
  raw_idx <- which(grepl(cand_l, tolower(raw_df$Description), fixed=TRUE) |
                   grepl(cand_l, tolower(raw_df$ID), fixed=TRUE))
  raw_part <- if (length(raw_idx) > 0) {{
    sprintf("raw_rank=%d raw_padj=%.4g raw_p=%.4g", raw_idx[1],
            raw_df$p.adjust[raw_idx[1]], raw_df$pvalue[raw_idx[1]])
  }} else {{ "raw_rank=NA (not in raw)" }}

  if (!is.null(ego_simp) && nrow(simp_df) > 0) {{
    simp_idx <- which(grepl(cand_l, tolower(simp_df$Description), fixed=TRUE) |
                      grepl(cand_l, tolower(simp_df$ID), fixed=TRUE))
    simp_part <- if (length(simp_idx) > 0) {{
      sprintf("simp_rank=%d simp_padj=%.4g simp_p=%.4g", simp_idx[1],
              simp_df$p.adjust[simp_idx[1]], simp_df$pvalue[simp_idx[1]])
    }} else {{ "simp_rank=NA (collapsed by simplify)" }}
  }} else {{
    simp_part <- "simp_rank=NA (simplify unavailable)"
  }}
  cat(sprintf("# CANDIDATE '%s': %s %s\n", cand, raw_part, simp_part))
}}

cat("# DONE\n")
"""


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--gene-list", required=True,
                    help="Significant gene list (one per line).")
    ap.add_argument("--background", default="",
                    help="Background gene list (one per line). Default: enrichGO universe.")
    ap.add_argument("--keytype", default="ENSEMBL",
                    choices=["ENSEMBL", "SYMBOL", "ENTREZID", "UNIPROT"],
                    help="Gene ID type. Default ENSEMBL.")
    ap.add_argument("--ontology", default="BP",
                    choices=["BP", "MF", "CC", "ALL"],
                    help="GO sub-ontology. Default BP.")
    ap.add_argument("--organism", default="human",
                    choices=["human", "mouse", "rat", "fly", "worm", "yeast", "zebrafish"],
                    help="Default human.")
    ap.add_argument("--simplify-cutoff", type=float, default=0.7,
                    help="clusterProfiler::simplify similarity cutoff (default 0.7).")
    ap.add_argument("--p-adjust", default="BH",
                    help="enrichGO pAdjustMethod (default BH).")
    ap.add_argument("--p-cutoff", type=float, default=0.05,
                    help="enrichGO pvalueCutoff (default 0.05).")
    ap.add_argument("--q-cutoff", type=float, default=0.05,
                    help="enrichGO qvalueCutoff (default 0.05).")
    ap.add_argument("--candidate", action="append", default=[],
                    help="Candidate term name (substring) to report rank for. Repeatable.")
    ap.add_argument("--workdir", default="",
                    help="Output dir (default $TMPDIR/enrichgo_<pid>).")
    args = ap.parse_args()

    org_db_map = {
        "human": "org.Hs.eg.db",
        "mouse": "org.Mm.eg.db",
        "rat": "org.Rn.eg.db",
        "fly": "org.Dm.eg.db",
        "worm": "org.Ce.eg.db",
        "yeast": "org.Sc.sgd.db",
        "zebrafish": "org.Dr.eg.db",
    }
    org_db = org_db_map[args.organism]

    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path(tempfile.mkdtemp(prefix="enrichgo_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"# workdir: {workdir}", file=sys.stderr)

    # Refuse to write into the input data folder
    workdir_r = workdir.resolve()
    for src in (args.gene_list, args.background or None):
        if not src:
            continue
        input_dir = Path(src).resolve().parent
        if workdir_r == input_dir or input_dir in workdir_r.parents:
            sys.exit(
                f"ERROR: workdir {workdir} is inside the input data folder "
                f"{input_dir}. Use --workdir /tmp/... to keep input data read-only."
            )

    candidates = "|||".join(args.candidate)
    r_script = R_TEMPLATE.format(
        org_db=org_db,
        gene_file=str(Path(args.gene_list).resolve()),
        bg_file=str(Path(args.background).resolve()) if args.background else "",
        keytype=args.keytype,
        ontology=args.ontology,
        p_adjust=args.p_adjust,
        p_cutoff=args.p_cutoff,
        q_cutoff=args.q_cutoff,
        simplify_cutoff=args.simplify_cutoff,
        workdir=str(workdir),
        candidates=candidates,
    )

    r_path = workdir / "run_enrichgo.R"
    r_path.write_text(r_script)
    print(f"# R script: {r_path}", file=sys.stderr)

    result = subprocess.run(
        ["Rscript", str(r_path)],
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
