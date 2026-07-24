# Tools, install, and command recipes

All tools install from **bioconda**. Preflight with `command -v <tool>` (shell)
or `shutil.which("<tool>")` (Python) before using them. If missing, emit the
install plan and stop — do not fabricate QC output.

## Install (one line)

```bash
mamba install -c bioconda -c conda-forge fastqc multiqc fastp cutadapt seqkit
#   or, if you only have conda:
conda install -c bioconda -c conda-forge fastqc multiqc fastp cutadapt seqkit
```

Minimum for QC-only: `fastqc`. For trimming: add `fastp` (and/or `cutadapt`).
`seqkit` and `multiqc` are recommended but optional.

## FastQC — per-file raw QC

```bash
fastqc -o <workdir>/fastqc --extract reads/sample_R1.fastq.gz reads/sample_R2.fastq.gz
```
- `-o`   output dir (create it; never the input dir).
- `--extract` unzip the report so the per-module text (`fastqc_data.txt`,
  `summary.txt`) can be read programmatically.
- Reads `.fastq`, `.fq`, and gzipped `.gz` directly. Never writes to inputs.

Parse `summary.txt` lines: `PASS\tPer base sequence quality\tsample_R1.fastq.gz`.

## MultiQC — project summary

```bash
multiqc <workdir> -o <workdir>/multiqc
```
Scans a directory tree for FastQC (and fastp/Cutadapt) outputs and builds one
HTML + a `multiqc_data/` folder with parseable tables. Run AFTER FastQC/fastp.

## fastp — all-in-one QC + trim (auto-detect adapters)

Single-end:
```bash
fastp -i in.fastq.gz -o <workdir>/trimmed/in.trimmed.fastq.gz \
      --json <workdir>/trimmed/fastp.json --html <workdir>/trimmed/fastp.html
```
Paired-end (auto-detects adapter from read overlap):
```bash
fastp -i R1.fastq.gz -I R2.fastq.gz \
      -o <workdir>/trimmed/R1.trimmed.fastq.gz \
      -O <workdir>/trimmed/R2.trimmed.fastq.gz \
      --detect_adapter_for_pe \
      --json <workdir>/trimmed/fastp.json --html <workdir>/trimmed/fastp.html
```
Useful flags:
- `-q 20`            min per-base quality for the sliding-window filter.
- `-l 30`            discard reads shorter than 30 bp after trimming.
- `--trim_poly_g`    remove NovaSeq/NextSeq poly-G dark-cycle tails (auto for those).
- `--adapter_sequence <SEQ>`  force a specific adapter instead of auto-detect.
Always writes NEW files to `<workdir>/trimmed/`; inputs untouched.

## Cutadapt — explicit primer/adapter removal

Use when you KNOW the exact 3' adapter or primer (amplicons, custom kits) and
want precise control fastp's auto-detect won't give.
```bash
cutadapt -a AGATCGGAAGAGC -o <workdir>/trimmed/out.fastq.gz in.fastq.gz
# paired-end, 3' adapter on both mates:
cutadapt -a ADAPTER_FWD -A ADAPTER_REV \
         -o <workdir>/trimmed/R1.trimmed.fastq.gz \
         -p <workdir>/trimmed/R2.trimmed.fastq.gz \
         R1.fastq.gz R2.fastq.gz
```
`-a` = 3' adapter (most common), `-g` = 5' adapter/primer, `-A`/`-G` = the same
for R2 in paired mode.

## seqkit — counts, stats, subsample

```bash
seqkit stats -a -T reads/*.fastq.gz > <workdir>/seqkit_stats.tsv   # counts, len, GC, N50
seqkit sample -p 0.01 in.fastq.gz -o <workdir>/in.subsample.fastq.gz  # 1% for a quick look
```
`-a` all stats, `-T` tab-separated (machine-readable). Read-only on inputs.

## Workspace isolation rule

Every command above directs output to a `<workdir>` that is **separate from the
input FASTQ directory**. Never pass the input folder as the output folder. The
bundled `scripts/run_fastq_qc.py` enforces this and refuses to run otherwise.
