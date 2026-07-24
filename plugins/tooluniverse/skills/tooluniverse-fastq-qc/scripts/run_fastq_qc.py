#!/usr/bin/env python3
"""run_fastq_qc.py — Honest FASTQ QC orchestrator.

PREFLIGHT FIRST, then run-if-available, plan-if-missing.

This script NEVER fabricates QC results. It shells out to real local
binaries (FastQC, fastp, seqkit). If a required binary is absent from
PATH, it prints a copy-paste conda/mamba install plan and exits 0
(a clean "cannot run yet" signal, not an error).

Workspace isolation
-------------------
All outputs are written ONLY under ``--workdir``. The input FASTQ files
are read-only: this script never writes to, renames, or overwrites a
file in the directory the inputs came from. Raw FASTQs are preserved.

Modes
-----
qc    (default) : FastQC per input + seqkit stats. No reads are modified.
trim            : everything in qc, PLUS fastp adapter/quality trimming
                  writing NEW trimmed files into --workdir. Trimming is a
                  decision, so it is opt-in and never the default.

Pure stdlib only (subprocess to the binaries). No third-party imports.
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

# Binaries this script can drive, and what each is for.
TOOL_ROLES = {
    "fastqc": "per-file raw read QC (per-base quality, adapter content, overrepresented seqs)",
    "fastp": "all-in-one QC + adapter/quality trimming (only used in --mode trim)",
    "seqkit": "fast read counts / length & GC stats",
}

# Tools that must be present for a given mode. seqkit is optional (nice-to-have).
REQUIRED_BY_MODE = {
    "qc": ["fastqc"],
    "trim": ["fastqc", "fastp"],
}


def which(tool):
    """Return absolute path to ``tool`` on PATH, or None."""
    return shutil.which(tool)


def preflight(mode):
    """Check tool availability. Return (available: dict, missing_required: list)."""
    available = {t: which(t) for t in TOOL_ROLES}
    missing_required = [t for t in REQUIRED_BY_MODE[mode] if not available[t]]
    return available, missing_required


def print_install_plan(missing, available):
    """Emit a copy-paste conda/mamba install plan for the missing binaries."""
    print("=" * 70)
    print("PREFLIGHT: required QC tools are NOT installed — cannot run yet.")
    print("=" * 70)
    print()
    print("Detected on PATH:")
    for tool, path in available.items():
        status = path if path else "MISSING"
        print(f"  - {tool:8s} {status}   ({TOOL_ROLES[tool]})")
    print()
    print(f"Missing required for this run: {', '.join(missing)}")
    print()
    print("INSTALL PLAN (bioconda — pick mamba if you have it, else conda):")
    print()
    pkgs = " ".join(sorted(set(missing)))
    print(f"  mamba install -c bioconda -c conda-forge {pkgs}")
    print("  # or")
    print(f"  conda install -c bioconda -c conda-forge {pkgs}")
    print()
    print("  # MultiQC (project-level summary across many FastQC reports):")
    print("  mamba install -c bioconda -c conda-forge multiqc")
    print()
    print("After installing, re-run this exact command. No QC numbers were")
    print("produced — nothing was fabricated, and your raw FASTQs are untouched.")
    print("=" * 70)


def validate_inputs(fastqs):
    """Ensure every input exists and looks like a FASTQ. Returns list of abspaths."""
    resolved = []
    for f in fastqs:
        ap = os.path.abspath(f)
        if not os.path.isfile(ap):
            sys.stderr.write(f"ERROR: input not found: {f}\n")
            sys.exit(2)
        low = ap.lower()
        if not (low.endswith(".fastq") or low.endswith(".fq")
                or low.endswith(".fastq.gz") or low.endswith(".fq.gz")):
            sys.stderr.write(
                f"WARNING: {f} does not have a .fastq/.fq[.gz] extension; "
                f"continuing but verify it is FASTQ.\n")
        resolved.append(ap)
    return resolved


def assert_workdir_isolated(workdir, inputs):
    """Refuse to write outputs into a directory that holds an input file."""
    wd = os.path.abspath(workdir)
    input_dirs = {os.path.dirname(p) for p in inputs}
    if wd in input_dirs:
        sys.stderr.write(
            "ERROR: --workdir is the same directory as an input FASTQ. "
            "Refusing to risk overwriting raw data. Choose a separate "
            "--workdir (e.g. /tmp/fastq_qc_run).\n")
        sys.exit(2)
    os.makedirs(wd, exist_ok=True)
    return wd


def run_cmd(cmd, log_path):
    """Run a command, tee combined output to a log file, return returncode."""
    print(f"  $ {' '.join(cmd)}")
    with open(log_path, "w") as log:
        log.write(f"# {' '.join(cmd)}\n")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        log.write(proc.stdout or "")
    if proc.returncode != 0:
        sys.stderr.write(f"  WARNING: command exited {proc.returncode}; "
                        f"see {log_path}\n")
    return proc.returncode


def run_fastqc(inputs, workdir, fastqc_bin):
    """Run FastQC on all inputs, writing reports into workdir/fastqc."""
    out = os.path.join(workdir, "fastqc")
    os.makedirs(out, exist_ok=True)
    print(f"[FastQC] -> {out}")
    cmd = [fastqc_bin, "-o", out, "--extract"] + inputs
    run_cmd(cmd, os.path.join(workdir, "fastqc.log"))
    return out


def run_seqkit_stats(inputs, workdir, seqkit_bin):
    """Run seqkit stats (read counts / length / GC) into workdir."""
    print("[seqkit stats]")
    stats_path = os.path.join(workdir, "seqkit_stats.tsv")
    cmd = [seqkit_bin, "stats", "-a", "-T"] + inputs
    with open(stats_path, "w") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        sys.stderr.write(f"  WARNING: seqkit stats exited {proc.returncode}: "
                        f"{proc.stderr}\n")
    else:
        print(f"  wrote {stats_path}")
    return stats_path


def run_fastp(inputs, workdir, fastp_bin, adapters):
    """Run fastp trimming. Writes NEW trimmed files into workdir/trimmed.

    Handles single-end (1 input) and paired-end (2 inputs). For >2 inputs,
    each is trimmed independently as single-end.
    """
    out = os.path.join(workdir, "trimmed")
    os.makedirs(out, exist_ok=True)
    print(f"[fastp trim] -> {out}  (raw inputs untouched)")

    def trimmed_name(path):
        base = os.path.basename(path)
        for ext in (".fastq.gz", ".fq.gz", ".fastq", ".fq"):
            if base.lower().endswith(ext):
                base = base[: -len(ext)]
                break
        return os.path.join(out, base + ".trimmed.fastq.gz")

    if len(inputs) == 2:
        i1, i2 = inputs
        o1, o2 = trimmed_name(i1), trimmed_name(i2)
        cmd = [fastp_bin,
               "-i", i1, "-I", i2,
               "-o", o1, "-O", o2,
               "--json", os.path.join(out, "fastp.json"),
               "--html", os.path.join(out, "fastp.html"),
               "--detect_adapter_for_pe"]
        if adapters:
            cmd += ["--adapter_sequence", adapters]
        run_cmd(cmd, os.path.join(workdir, "fastp.log"))
    else:
        for idx, inp in enumerate(inputs):
            o1 = trimmed_name(inp)
            cmd = [fastp_bin, "-i", inp, "-o", o1,
                   "--json", os.path.join(out, f"fastp_{idx}.json"),
                   "--html", os.path.join(out, f"fastp_{idx}.html")]
            if adapters:
                cmd += ["--adapter_sequence", adapters]
            run_cmd(cmd, os.path.join(workdir, f"fastp_{idx}.log"))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Honest FASTQ QC orchestrator (preflight + run-if-available).")
    p.add_argument("--fastq", nargs="+", required=True,
                   help="One or more FASTQ files. Two inputs are treated as "
                        "a paired-end R1/R2 pair in --mode trim.")
    p.add_argument("--workdir", required=True,
                   help="Output directory. MUST differ from the input "
                        "directory. All outputs go here; inputs are read-only.")
    p.add_argument("--mode", choices=["qc", "trim"], default="qc",
                   help="qc (default): QC only, no reads modified. "
                        "trim: also run fastp adapter/quality trimming.")
    p.add_argument("--adapters", default=None,
                   help="Optional explicit adapter sequence for fastp "
                        "(otherwise fastp auto-detects).")
    args = p.parse_args(argv)

    print(f"# run_fastq_qc  mode={args.mode}  "
          f"{datetime.now(timezone.utc).isoformat()}")

    # 1) PREFLIGHT — before touching anything.
    available, missing = preflight(args.mode)
    if missing:
        print_install_plan(missing, available)
        return 0  # clean "cannot run yet" — not an error, nothing fabricated.

    # 2) Validate inputs + isolate workspace.
    inputs = validate_inputs(args.fastq)
    workdir = assert_workdir_isolated(args.workdir, inputs)
    print(f"# inputs ({len(inputs)}): {', '.join(inputs)}")
    print(f"# workdir: {workdir}")

    # 3) QC always runs.
    run_fastqc(inputs, workdir, available["fastqc"])
    if available["seqkit"]:
        run_seqkit_stats(inputs, workdir, available["seqkit"])
    else:
        print("[seqkit] not on PATH — skipping read-count/stats (optional).")

    # 4) Trimming only when explicitly requested.
    if args.mode == "trim":
        run_fastp(inputs, workdir, available["fastp"], args.adapters)
    else:
        print("[trim] mode=qc — NOT trimming. Review FastQC adapter content / "
              "per-base quality, then re-run with --mode trim if warranted.")

    print(f"# done. Outputs under {workdir}. Raw FASTQs untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
