#!/usr/bin/env python3
"""Suggest which nf-core pipeline (rnaseq / sarek / atacseq) fits a directory
of sequencing files, based on filenames only.

This is a STARTING POINT for the confirm-with-user decision point in Step 2
of the skill, not a final answer. Filenames alone cannot reliably distinguish
WGS from WES, or a mislabeled ATAC-seq run from ChIP-seq -- always confirm
the assay type with the user before committing to a pipeline.
"""

import argparse
import re
import sys
from pathlib import Path

FASTQ_RE = re.compile(r"\.(fastq|fq)(\.gz)?$", re.IGNORECASE)
BAM_RE = re.compile(r"\.(bam|cram)$", re.IGNORECASE)

# Keyword hints in filenames (case-insensitive), scored per pipeline.
KEYWORD_HINTS = {
    "rnaseq": ["rna", "rnaseq", "mrna", "transcriptome", "cdna"],
    "sarek": ["wgs", "wes", "exome", "germline", "somatic", "tumor", "normal", "variant"],
    "atacseq": ["atac", "atacseq", "chromatin", "accessib"],
}


def classify(files):
    names = [f.name.lower() for f in files]
    fastq_files = [f for f in files if FASTQ_RE.search(f.name)]
    bam_files = [f for f in files if BAM_RE.search(f.name)]

    scores = {"rnaseq": 0, "sarek": 0, "atacseq": 0}
    for pipeline, keywords in KEYWORD_HINTS.items():
        for name in names:
            if any(kw in name for kw in keywords):
                scores[pipeline] += 1

    evidence = []
    evidence.append(f"{len(fastq_files)} FASTQ file(s), {len(bam_files)} BAM/CRAM file(s) found")
    for pipeline, score in scores.items():
        if score:
            evidence.append(f"{score} filename(s) matched '{pipeline}' keywords")

    if max(scores.values()) == 0:
        return None, evidence + [
            "No pipeline-specific keywords found in filenames. Cannot suggest "
            "a pipeline from filenames alone -- ask the user what assay this is "
            "(bulk RNA-seq, WGS/WES, or ATAC-seq)."
        ]

    best = max(scores, key=scores.get)
    tied = [p for p, s in scores.items() if s == scores[best] and s > 0]
    if len(tied) > 1:
        return None, evidence + [
            f"Ambiguous: {', '.join(tied)} scored equally. Ask the user directly."
        ]
    return best, evidence


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data_dir", help="Directory containing FASTQ/BAM/CRAM files")
    args = ap.parse_args()

    root = Path(args.data_dir)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 1

    files = [p for p in root.rglob("*") if p.is_file()]
    seq_files = [
        f for f in files if FASTQ_RE.search(f.name) or BAM_RE.search(f.name)
    ]
    if not seq_files:
        print(f"No FASTQ/BAM/CRAM files found under {root}.")
        return 1

    suggestion, evidence = classify(seq_files)

    print(f"Scanned {len(seq_files)} sequencing file(s) under {root}")
    for line in evidence:
        print(f"  - {line}")
    print()
    if suggestion:
        print(f"Suggested pipeline: {suggestion}")
        print("(This is a filename-based guess. Confirm the assay type with the "
              "user before proceeding -- see Step 2 in SKILL.md.)")
    else:
        print("Suggested pipeline: UNKNOWN -- ask the user which assay this is.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
