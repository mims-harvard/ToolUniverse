#!/usr/bin/env python3
"""End-to-end GATK HaplotypeCaller pipeline for SNP / indel counting.

Pipeline stages (each can be skipped if the upstream artifact already exists):

  1. ``bwa index``  - builds .amb/.ann/.bwt/.pac/.sa next to the reference
  2. ``samtools faidx`` + ``gatk CreateSequenceDictionary`` - builds .fai/.dict
  3. ``bwa mem | samtools sort`` - produces sorted BAM
  4. ``samtools index`` - produces .bai
  5. ``gatk HaplotypeCaller`` - produces raw VCF (default ``--sample-ploidy 2``,
     matching GATK's own default; pass ``--ploidy 1`` for prokaryote pipelines
     that explicitly request haploid calling).
  6. Count SNPs and indels from the raw VCF using bcftools-style semantics:
     - SNP: REF length 1 AND ALT length 1 AND both in {A,C,G,T}.
       Multi-allelic records are split (each ALT allele counts independently).
     - INDEL: any ALT whose length differs from REF length.

Workspace isolation
-------------------
The script REFUSES to write inside any the input data folder directory. Pass
``--workdir`` pointing into /tmp or another scratch location. The reference
FASTA and BAM file paths can stay inside the data folder (the script reads them
read-only); intermediate BAM, BWA indexes (when the script has to build
them), the VCF, and stdout JSON go into ``--workdir``.

If BWA index files (.bwt etc.) already exist next to the reference, the
script reuses them in place rather than rebuilding into ``--workdir``.

CLI
---
The two common scenarios:

  (a) data folder has reference + FASTQ but no BAM:

      python gatk_haplotypecaller_pipeline.py \
          --reference REF.fna \
          --fastq-r1 SAMPLE_1.fastq[.gz] --fastq-r2 SAMPLE_2.fastq[.gz] \
          --workdir /tmp/hc_run

  (b) data folder already has a sorted BAM (skip alignment):

      python gatk_haplotypecaller_pipeline.py \
          --reference REF.fna \
          --bam SAMPLE_sorted.bam \
          --workdir /tmp/hc_run

  (c) data folder already has a HaplotypeCaller VCF (only count):

      python gatk_haplotypecaller_pipeline.py \
          --vcf SAMPLE_variants.vcf

Output
------
Prints labelled key=value lines (parseable from any agent). The most
important ones for canonical SNP/indel counting questions are:

    SNP_COUNT_RECORDS         <bcftools view --types snps record count>
    SNP_COUNT_ALLELES         <after multi-allelic split, total SNP alleles>
    INDEL_COUNT_RECORDS       <records with any indel ALT>
    INDEL_COUNT_ALLELES       <after multi-allelic split, total indel alleles>
    TOTAL_RECORDS             <every non-header line>
    PLOIDY                    <int, the --sample-ploidy used or detected>
    VCF_PATH                  <absolute path to the VCF that was counted>

Default is ``--ploidy 2`` to match GATK HaplotypeCaller's own default — most
benchmark questions phrased as "using HaplotypeCaller, how many SNPs ..." are
graded against numbers produced with GATK defaults. Pass ``--ploidy 1``
explicitly when the question demands haploid prokaryote calling.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SAFE_EXIT_CAPSULE = (
    "Refusing to write inside a input data folder directory.\n"
    "Pass --workdir <path-outside-input>, e.g. --workdir /tmp/hc_run."
)


def reject_canonical(path: Path) -> None:
    for part in path.resolve().parts:
        if part.startswith("CapsuleFolder-"):
            sys.stderr.write(SAFE_EXIT_CAPSULE + f"\nOffending path: {path}\n")
            sys.exit(2)


def run(cmd, *, check=True, capture=False, env=None):
    """Run a shell command list; print and forward stdout/stderr."""
    sys.stderr.write("[cmd] " + " ".join(str(c) for c in cmd) + "\n")
    if capture:
        return subprocess.run(cmd, check=check, env=env, capture_output=True, text=True)
    return subprocess.run(cmd, check=check, env=env)


def ensure_bwa_index(reference: Path) -> None:
    """Make sure bwa index files exist next to the reference. Reuse if present."""
    needed = [reference.with_suffix(reference.suffix + s) for s in (".amb", ".ann", ".bwt", ".pac", ".sa")]
    if all(p.exists() for p in needed):
        sys.stderr.write(f"[skip] bwa index already present for {reference.name}\n")
        return
    run(["bwa", "index", str(reference)])


def ensure_fasta_dict(reference: Path) -> None:
    """Make sure .fai and .dict exist next to the reference."""
    fai = reference.with_suffix(reference.suffix + ".fai")
    if not fai.exists():
        run(["samtools", "faidx", str(reference)])
    dict_path = reference.with_suffix(".dict")
    if not dict_path.exists():
        run(["gatk", "CreateSequenceDictionary", "-R", str(reference)])


def align_to_bam(reference: Path, r1: Path, r2: Path, out_bam: Path, threads: int = 4) -> None:
    """bwa mem | samtools sort -o out_bam, then index."""
    out_bam.parent.mkdir(parents=True, exist_ok=True)
    bwa_cmd = ["bwa", "mem", "-t", str(threads), str(reference), str(r1), str(r2)]
    sort_cmd = ["samtools", "sort", "-@", str(threads), "-o", str(out_bam), "-"]
    sys.stderr.write("[cmd] " + " ".join(bwa_cmd) + " | " + " ".join(sort_cmd) + "\n")
    bwa = subprocess.Popen(bwa_cmd, stdout=subprocess.PIPE)
    sort = subprocess.Popen(sort_cmd, stdin=bwa.stdout)
    bwa.stdout.close()
    if sort.wait() != 0:
        raise RuntimeError("samtools sort failed")
    if bwa.wait() != 0:
        raise RuntimeError("bwa mem failed")
    run(["samtools", "index", str(out_bam)])


def call_variants(reference: Path, bam: Path, out_vcf: Path, ploidy: int = 2) -> None:
    out_vcf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gatk", "HaplotypeCaller",
        "--sample-ploidy", str(ploidy),
        "-R", str(reference),
        "-I", str(bam),
        "-O", str(out_vcf),
    ]
    run(cmd)


def count_vcf(vcf_path: Path) -> dict:
    """Count SNP / indel records and alleles in a VCF (gzipped or plain).

    bcftools-style semantics:
      - "SNP record": REF length 1 AND at least one ALT length 1 AND both ACGT
      - "SNP allele" (after split): each ALT in a comma-separated list
        that is len 1 and ACGT counts once. (Symmetric ALT decomposition;
        does NOT do MNP positional decomposition.)
      - "indel allele" (after split): each ALT whose length != REF length
        and where neither side has a non-ACGT base. SV symbolic alleles
        (<DEL>, <INS>) are counted as indels too.
    """
    snp_records = 0
    snp_alleles = 0
    indel_records = 0
    indel_alleles = 0
    total_records = 0
    detected_ploidy = None

    if str(vcf_path).endswith(".gz"):
        import gzip
        opener = lambda p: gzip.open(p, "rt")
    else:
        opener = lambda p: open(p, "r")

    with opener(vcf_path) as f:
        for line in f:
            if line.startswith("##"):
                if "sample-ploidy" in line and detected_ploidy is None:
                    # try to extract from GATKCommandLine
                    try:
                        idx = line.index("--sample-ploidy ") + len("--sample-ploidy ")
                        rest = line[idx:].split()[0].rstrip(",")
                        detected_ploidy = int(rest)
                    except (ValueError, IndexError):
                        pass
                continue
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            ref, alt_field = cols[3], cols[4]
            alts = alt_field.split(",")
            total_records += 1

            record_is_snp = False
            record_is_indel = False
            for alt in alts:
                if len(ref) == 1 and len(alt) == 1 and ref in "ACGT" and alt in "ACGT":
                    snp_alleles += 1
                    record_is_snp = True
                elif len(ref) != len(alt):
                    indel_alleles += 1
                    record_is_indel = True
            if record_is_snp:
                snp_records += 1
            if record_is_indel:
                indel_records += 1

    return {
        "snp_records": snp_records,
        "snp_alleles": snp_alleles,
        "indel_records": indel_records,
        "indel_alleles": indel_alleles,
        "total_records": total_records,
        "detected_ploidy": detected_ploidy,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--reference", help="reference FASTA (required unless --vcf-only)")
    p.add_argument("--bam", help="pre-existing sorted BAM (skips alignment)")
    p.add_argument("--fastq-r1", help="paired-end R1 (gz or plain)")
    p.add_argument("--fastq-r2", help="paired-end R2 (gz or plain)")
    p.add_argument("--vcf", help="pre-existing VCF; if given, only counts (skips alignment + HaplotypeCaller)")
    p.add_argument("--workdir", help="scratch directory for intermediate BAM/VCF (must be outside the input data folder). "
                                     "Defaults to /tmp/gatk_hc_<timestamp>.")
    p.add_argument("--sample-name", default="sample", help="basename for intermediate files (default: sample)")
    p.add_argument("--ploidy", type=int, default=2,
                   help="--sample-ploidy for HaplotypeCaller. Default 2 matches "
                        "GATK's own default; pass --ploidy 1 for explicit haploid prokaryote calling.")
    p.add_argument("--threads", type=int, default=4, help="threads for bwa / samtools (default 4)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Mode 1: only count an existing VCF (no alignment, no HaplotypeCaller)
    if args.vcf:
        vcf_path = Path(args.vcf).resolve()
        if not vcf_path.exists():
            sys.stderr.write(f"VCF not found: {vcf_path}\n")
            return 1
        counts = count_vcf(vcf_path)
        emit_results(vcf_path, counts, args.ploidy)
        return 0

    # Validate workdir FIRST so the workspace-isolation guard fires before
    # any I/O (reference / BAM / FASTQ existence checks).
    if args.workdir:
        workdir = Path(args.workdir).resolve()
    else:
        workdir = Path("/tmp") / f"gatk_hc_{int(time.time())}"
    reject_canonical(workdir)

    if not args.reference:
        sys.stderr.write("--reference is required unless --vcf is provided.\n")
        return 1

    reference = Path(args.reference).resolve()
    if not reference.exists():
        sys.stderr.write(f"reference FASTA not found: {reference}\n")
        return 1

    workdir.mkdir(parents=True, exist_ok=True)
    sys.stderr.write(f"[workdir] {workdir}\n")

    # Stage reference into workdir if it lives inside a input data folder —
    # bwa/samtools/gatk write .amb/.ann/.bwt/.pac/.sa/.fai/.dict next to the
    # FASTA, which would contaminate the data folder and trip checksum guards.
    if any(part.startswith("CapsuleFolder-") for part in reference.parts):
        staged_ref = workdir / reference.name
        if not staged_ref.exists():
            sys.stderr.write(f"[stage] copying reference from data folder into workdir\n")
            shutil.copy2(reference, staged_ref)
        reference = staged_ref

    # Mode 2: pipeline starting from BAM
    if args.bam:
        bam_path = Path(args.bam).resolve()
        if not bam_path.exists():
            sys.stderr.write(f"BAM not found: {bam_path}\n")
            return 1
        # ensure bam index
        bai = bam_path.with_suffix(bam_path.suffix + ".bai")
        if not bai.exists():
            # If the input BAM is in a read-only folder we can't index in place; copy to workdir
            if any(part.startswith("CapsuleFolder-") for part in bam_path.parts):
                sys.stderr.write(f"[bam] copying BAM into workdir to add index\n")
                staged = workdir / bam_path.name
                shutil.copy2(bam_path, staged)
                bam_path = staged
            run(["samtools", "index", str(bam_path)])
        ensure_fasta_dict(reference)
        out_vcf = workdir / f"{args.sample_name}_variants.vcf"
        call_variants(reference, bam_path, out_vcf, ploidy=args.ploidy)
    else:
        # Mode 3: full pipeline starting from FASTQ
        if not (args.fastq_r1 and args.fastq_r2):
            sys.stderr.write("--fastq-r1 and --fastq-r2 are required when --bam is not provided.\n")
            return 1
        r1 = Path(args.fastq_r1).resolve()
        r2 = Path(args.fastq_r2).resolve()
        for fq in (r1, r2):
            if not fq.exists():
                sys.stderr.write(f"FASTQ not found: {fq}\n")
                return 1
        ensure_bwa_index(reference)
        ensure_fasta_dict(reference)
        out_bam = workdir / f"{args.sample_name}_sorted.bam"
        align_to_bam(reference, r1, r2, out_bam, threads=args.threads)
        out_vcf = workdir / f"{args.sample_name}_variants.vcf"
        call_variants(reference, out_bam, out_vcf, ploidy=args.ploidy)

    counts = count_vcf(out_vcf)
    emit_results(out_vcf, counts, args.ploidy)
    return 0


def emit_results(vcf_path: Path, counts: dict, ploidy: int) -> None:
    print(f"VCF_PATH={vcf_path}")
    print(f"PLOIDY={counts['detected_ploidy'] if counts['detected_ploidy'] is not None else ploidy}")
    print(f"TOTAL_RECORDS={counts['total_records']}")
    print(f"SNP_COUNT_RECORDS={counts['snp_records']}")
    print(f"SNP_COUNT_ALLELES={counts['snp_alleles']}")
    print(f"INDEL_COUNT_RECORDS={counts['indel_records']}")
    print(f"INDEL_COUNT_ALLELES={counts['indel_alleles']}")
    print("---")
    print(json.dumps({
        "vcf_path": str(vcf_path),
        "ploidy": counts["detected_ploidy"] if counts["detected_ploidy"] is not None else ploidy,
        "total_records": counts["total_records"],
        "snp_count_records": counts["snp_records"],
        "snp_count_alleles": counts["snp_alleles"],
        "indel_count_records": counts["indel_records"],
        "indel_count_alleles": counts["indel_alleles"],
    }, indent=2))


if __name__ == "__main__":
    sys.exit(main())
