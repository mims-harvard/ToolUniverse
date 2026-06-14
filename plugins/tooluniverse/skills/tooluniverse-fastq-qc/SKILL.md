---

name: tooluniverse-fastq-qc
description: "FASTQ quality control and adapter/quality-trimming decisions with local NGS tools — run FastQC on raw reads, summarize a project with MultiQC, interpret per-base sequence quality, per-base N content, adapter content, overrepresented sequences, sequence duplication and GC content, and decide whether (and how) to trim with fastp / Cutadapt before downstream analysis. seqkit for read counts/stats/subsampling. Use when someone asks \"run QC on my FASTQs\", \"are my reads good quality?\", \"do I need to trim adapters?\", \"interpret this FastQC report\", \"what does this WARN/FAIL mean\", \"why are overrepresented sequences flagged\", \"should I quality-trim before alignment\", \"make a MultiQC summary\", or \"clean up these reads with fastp\". NOT for differential expression / DEG analysis (use tooluniverse-rnaseq-deseq2), NOT for read alignment, coverage, or variant calling (use tooluniverse-variant-analysis / tooluniverse-sequence-analysis). Honest: shells out to real local binaries; if a tool is missing..."
---

# FASTQ Quality Control & Trimming Decisions

Run quality control on raw sequencing reads, interpret the report, and make
an evidence-based decision about whether to trim — using real local
command-line tools (FastQC, MultiQC, fastp, Cutadapt, seqkit).

## Honesty contract (read first)

This skill drives **real binaries**. It must never fabricate QC numbers.

1. **Preflight before anything.** Check whether the required tools are on
   PATH. If a required tool is missing, emit the install plan and STOP.
   Do not estimate, guess, or describe hypothetical QC results.
2. **Never auto-trim.** Trimming is a *decision*. QC-only is the default.
   Only trim after inspecting adapter content / per-base quality, and only
   when the user has confirmed `--mode trim`.
3. **Never overwrite raw FASTQs.** All outputs go to a separate `--workdir`.
   The input directory is read-only. Trimmed reads are written as NEW files.
4. **If you cannot run, say so.** "FastQC is not installed; here is the
   install plan" is the correct answer — not a made-up PASS/FAIL table.

## When to use vs. not

**Use this skill when the user wants to:**
- Run FastQC / fastp QC on one or more FASTQ (`.fastq`, `.fq`, `.gz`) files
- Interpret a FastQC report (per-base quality, adapter content, etc.)
- Decide whether adapter or quality trimming is needed before downstream work
- Summarize many samples into one MultiQC report
- Count reads, get length/GC stats, or subsample with seqkit
- Trim adapters/low-quality bases with fastp or Cutadapt (explicitly)

**Do NOT use this skill for (route elsewhere):**
- Differential expression / DEG / fold-change analysis -> `tooluniverse-rnaseq-deseq2`
- Read alignment, coverage depth, samtools, BWA -> `tooluniverse-sequence-analysis`
- Variant calling, VCF, VAF, mutation analysis -> `tooluniverse-variant-analysis`
- Single-cell / scRNA QC (per-cell metrics, scanpy) -> `tooluniverse-single-cell`

## Essential inputs to confirm

Before running, confirm with the user (ask if unstated):

1. **FASTQ paths** — exact path(s). One file = single-end; an R1+R2 pair =
   paired-end (e.g. `*_R1.fastq.gz` / `*_R2.fastq.gz`).
2. **QC-only or trim?** Default is QC-only. Only trim on explicit request.
3. **Known adapters / primers?** Standard Illumina adapters are auto-detected
   by fastp; amplicon/primer sequences usually need explicit Cutadapt removal.
4. **Organism** — only needed if a contamination / over-representation screen
   is requested (needs a reference; see Limitations).
5. **Output directory** — a `--workdir` SEPARATE from the input folder.
6. **Read provenance** — are these raw, already-trimmed, or UMI-tagged reads?
   Already-trimmed reads should NOT be trimmed again; UMIs must be handled
   before trimming or you corrupt the UMI.

## Preflight (do this first, every time)

The bundled script preflights for you, but the decision logic is:

```python
import shutil
for tool in ("fastqc", "fastp", "seqkit"):
    print(tool, shutil.which(tool) or "MISSING")
```

`command -v fastqc` / `shutil.which("fastqc")` returning nothing means the
tool is absent. If a **required** tool (FastQC for QC; FastQC+fastp for trim)
is missing, emit:

```
mamba install -c bioconda -c conda-forge fastqc fastp seqkit multiqc
#   or
conda install -c bioconda -c conda-forge fastqc fastp seqkit multiqc
```

and stop. Do not proceed to fabricate output.

## Tool roles

| Tool      | Role                                                            | Install (bioconda) |
|-----------|----------------------------------------------------------------|--------------------|
| FastQC    | Per-file raw read QC; produces the module PASS/WARN/FAIL report | `fastqc`           |
| MultiQC   | Aggregates many FastQC (and fastp) reports into one summary     | `multiqc`          |
| fastp     | All-in-one QC + adapter + quality trimming (fast, auto-detect)  | `fastp`            |
| Cutadapt  | Explicit, precise adapter/primer removal (amplicons, custom)    | `cutadapt`         |
| seqkit    | Read counts, length/GC stats, subsampling                      | `seqkit`           |

Rule of thumb: **FastQC to diagnose, fastp to fix general adapter/quality,
Cutadapt to fix a known primer/adapter precisely, seqkit to count/stat.**

## Bundled orchestration script

`scripts/run_fastq_qc.py` does the preflight + run-if-available + plan-if-missing
flow, with workspace isolation built in.

```bash
# QC only (default) — never modifies reads
python scripts/run_fastq_qc.py \
    --fastq reads/sample_R1.fastq.gz reads/sample_R2.fastq.gz \
    --workdir /tmp/fastq_qc_run

# QC + trim (explicit) — fastp writes NEW trimmed files into --workdir
python scripts/run_fastq_qc.py \
    --fastq reads/sample_R1.fastq.gz reads/sample_R2.fastq.gz \
    --workdir /tmp/fastq_qc_run \
    --mode trim
```

Behavior:
- **Preflights** FastQC (+ fastp in trim mode) and seqkit. If a required
  tool is missing it prints the install plan and exits 0 — no fabricated QC.
- Runs **FastQC** (always) + **seqkit stats** (if present) into `--workdir`.
- In `--mode trim`, runs **fastp** writing `*.trimmed.fastq.gz` into
  `--workdir/trimmed/` — raw inputs are never touched.
- **Refuses** to run if `--workdir` equals an input directory (overwrite guard).

For a project-level summary after FastQC, run MultiQC over the workdir:

```bash
multiqc /tmp/fastq_qc_run -o /tmp/fastq_qc_run/multiqc
```

## INTERPRETATION — FastQC module -> meaning -> action

This table is the core value-add. Map each FastQC module to what PASS/WARN/FAIL
means and what to actually do. (See `references/fastqc_interpretation.md` for the
long form with thresholds and worked cases.)

| FastQC module                | Typical PASS              | WARN / FAIL means                                              | Suggested action |
|------------------------------|---------------------------|----------------------------------------------------------------|------------------|
| Per base sequence quality    | All positions Q>=28       | 3' tail drops below Q20-Q28 (common, esp. R2)                  | **Quality-trim** 3' (fastp `-q`/sliding window). Proceed if only the last few bases dip. |
| Per base N content           | Near 0% N                 | Spike of N at a position = sequencer/base-call problem         | **Investigate**: cycle-specific issue; consider hard-trim that position or re-sequence. |
| Adapter content              | Flat, no adapter ramp     | Rising adapter % toward 3' end = read-through into adapter      | **Trim adapters** (fastp auto-detect, or Cutadapt with the known adapter). |
| Overrepresented sequences    | None / <0.1%              | A sequence is a large fraction: adapter, primer-dimer, rRNA, or low-complexity | **Investigate** the hit (BLAST it). If adapter/primer -> trim. If biology (rRNA/highly-expressed) -> proceed. |
| Sequence Duplication Levels  | Low (diverse library)     | High duplication = PCR over-amplification OR expected (amplicon/RNA-seq) | **Investigate, usually proceed**. Do NOT dedup blindly — expected high in amplicon/targeted/RNA-seq. Mark-duplicates belongs post-alignment, not here. |
| Per sequence GC content      | Single peak at expected GC| Bimodal / shifted peak = contamination or mixed species        | **Investigate** contamination (needs a reference screen; see Limitations). Not fixed by trimming. |
| Per base sequence content    | Flat after first ~10 bp   | Bias in first bases (random-hexamer priming) or adapter        | Random-priming bias: usually **proceed** (expected in RNA-seq). Persistent bias at 3' -> adapter -> trim. |
| Sequence Length Distribution | Single length (raw)       | Multiple lengths AFTER trimming is normal; before trimming may indicate mixed input | Usually **proceed**; only a concern on supposedly-raw uniform-length data. |

**Decision summary for "do I need to trim?"**
- Adapter content FAIL/WARN with a 3' adapter ramp -> **yes, adapter-trim**.
- Per-base quality FAIL at the 3' tail -> **yes, quality-trim** that tail.
- Overrepresented = adapter/primer-dimer -> **yes, trim**; overrepresented =
  biology (rRNA, abundant transcript) -> **no, proceed**.
- High duplication / GC anomaly / N-spike -> **investigate**, not a trimming fix.
- Everything PASS -> **proceed without trimming.**

## Workflow

1. **Confirm inputs** (paths, pairing, mode, adapters, provenance).
2. **Preflight** tools. If missing -> install plan, STOP.
3. **Run QC** (`--mode qc`): FastQC + seqkit -> read the report.
4. **Interpret** each flagged module with the table above.
5. **Decide** trim vs investigate vs proceed. State the decision and why.
6. **(If trimming chosen)** run `--mode trim` (fastp) or Cutadapt for precise
   primer removal; re-run FastQC on the trimmed output to confirm the fix.
7. **(Optional)** MultiQC for a multi-sample summary.
8. **Report**: per-module status, the trim decision + rationale, and the exact
   commands run. Never report numbers a tool did not actually produce.

## Limitations (honest)

- **Requires local binaries.** FastQC/fastp/seqkit/Cutadapt/MultiQC must be
  installed (bioconda). This is not a cloud service; with no tools installed
  the skill can only emit an install plan, not QC results.
- **Large files.** Whole-lane FASTQs can be many GB; FastQC/fastp are
  single-pass and memory-light but still I/O-bound. Use seqkit `sample` to
  subsample for a quick look on huge files.
- **Contamination / cross-species screening is NOT included by default.** GC
  anomalies and "is this the right organism" need a reference index
  (e.g. FastQ Screen + bowtie2 indexes, or Kraken2) — extra setup beyond this
  skill's bundled tools.
- **No deduplication of raw reads.** PCR-duplicate removal is an alignment-stage
  decision (Picard/samtools markdup); FastQC duplication is diagnostic only.
- **UMI-aware trimming** needs UMI extraction first (umi_tools); naive trimming
  corrupts UMIs.

## Completeness checklist

- [ ] Inputs confirmed (paths, single/paired, raw vs trimmed, adapters)
- [ ] Tools preflighted; install plan emitted if any required tool missing
- [ ] QC run with outputs in a workdir separate from inputs (raw preserved)
- [ ] Each flagged FastQC module interpreted (meaning + action)
- [ ] Explicit trim/investigate/proceed decision with rationale
- [ ] Trimming (if done) was opt-in, wrote new files, raw FASTQs untouched
- [ ] Post-trim FastQC re-run to confirm the fix (if trimmed)
- [ ] No QC numbers reported that a tool did not actually produce

## References

- `references/fastqc_interpretation.md` — full module-by-module thresholds + cases
- `references/tools_and_install.md` — install commands, tool flags, command recipes
- `references/trimming_decisions.md` — when/how to trim (fastp vs Cutadapt), pitfalls
