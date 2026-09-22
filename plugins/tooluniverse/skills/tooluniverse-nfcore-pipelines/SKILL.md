---

name: tooluniverse-nfcore-pipelines
description: "Run real end-to-end bioinformatics pipelines (nf-core rnaseq, sarek, atacseq) via Nextflow + Docker/Singularity, for raw FASTQ/BAM data — either local files or public GEO/SRA datasets. Use when someone asks to \"run RNA-seq alignment\", \"quantify gene expression from FASTQs\", \"call germline or somatic variants from my WGS/WES data\", \"run an nf-core pipeline\", \"analyze ATAC-seq chromatin accessibility data\", \"reanalyze a GEO/SRA dataset (GSE/GSM/SRR accession)\", \"generate a samplesheet for nf-core\", or \"set up Nextflow to process my sequencing data\". Orchestrates the full pipeline (alignment/quantification, or variant calling, or peak calling) rather than a single step. Honest: shells out to real Nextflow/Docker; checks the environment first and stops with install instructions rather than fabricating pipeline output; always runs the pipeline's small test profile before real data."
---

# nf-core Pipeline Orchestration

Run real nf-core bioinformatics pipelines end-to-end for bench scientists who
need alignment/quantification, variant calling, or chromatin-accessibility
analysis without hand-building a pipeline.

## Honesty contract (read first)

This skill drives **real Nextflow pipelines** on **real compute**. It must
never fabricate a pipeline result.

1. **Preflight before anything.** Run `scripts/check_environment.py`. If
   Docker, Nextflow (>=23.04), or Java (>=11) is missing, print the install
   plan and STOP. Do not describe hypothetical alignment/variant-calling
   output. This skill cannot do useful work in a sandbox with no Docker
   daemon and no ability to install one — say so plainly instead of
   improvising a fake run.
2. **Test profile is mandatory before real data.** Every pipeline ships a
   `-profile test` that downloads a few MB of toy data and runs in minutes.
   It MUST pass before touching the user's real samples — it is the only way
   to know the environment actually works end-to-end (network egress,
   container pulls, resource limits) before a run that can take hours.
3. **Never invent a pipeline version.** nf-core pipelines are versioned and
   pinned with `-r <version>`. If you are not certain of the current stable
   release, tell the user to check `https://nf-co.re/<pipeline>/releases`
   rather than guessing a version number — the version numbers below were
   accurate at the time this skill was written but nf-core ships new releases
   regularly.
4. **Confirm decision points with the user**, do not silently default:
   pipeline choice, reference genome, and pipeline-specific options
   (aligner, variant-calling tools, read length). See Step 2 and Step 5.
5. **If you cannot run, say so.** "Docker is not installed; here is the
   install plan" is the correct answer — never a made-up MultiQC summary or
   invented gene-count table.

## When to use vs. not

**Use this skill when the user wants to:**
- Turn raw FASTQ (or BAM/CRAM) files into gene counts, called variants, or
  accessibility peaks by actually running an nf-core pipeline
- Reanalyze a public GEO/SRA dataset (GSE/GSM/SRR/SRX accession) from raw
  reads through to pipeline output
- Generate or validate an nf-core-format samplesheet
- Get help diagnosing a failed/stuck Nextflow run

**Do NOT use this skill for (route elsewhere):**
- QC-only on FASTQs, adapter trimming decisions -> `tooluniverse-fastq-qc`
- Differential expression on a count matrix that already exists ->
  `tooluniverse-rnaseq-deseq2`
- Interpreting/annotating a VCF that already exists ->
  `tooluniverse-variant-analysis`
- scRNA-seq QC/clustering on an h5ad/10X matrix -> `tooluniverse-single-cell`
- Finding which software/package/tutorial to use for a task, rather than
  running a specific nf-core pipeline -> `tooluniverse-bioinformatics-resource-discovery`

This skill's job ends at "pipeline completed, here are the output files."
Interpreting those outputs is the job of the skills above.

## Requirements (be upfront about these)

- Docker (or Singularity/Apptainer for HPC) — pipelines run in containers,
  not bare-metal, so software versions are pinned and reproducible
- Nextflow >= 23.04
- Java >= 11 (Nextflow runtime dependency)
- Sufficient disk (container images + reference genome + data; tens of GB is
  common) and, for real (non-test) runs, non-trivial CPU/RAM/time
- Optionally `sra-tools` (`prefetch`, `fasterq-dump`) if downloading from
  SRA by accession rather than via ToolUniverse's direct-URL tools (see
  `references/geo_sra_acquisition.md`)

If any of this is unavailable (e.g. a sandboxed environment with no Docker
daemon and no root), `check_environment.py` will say so — do not attempt to
work around it by simulating a run.

## Workflow Checklist

```
- [ ] Step 0: Acquire data (skip if user already has local FASTQ/BAM files)
- [ ] Step 1: Environment check (MUST pass)
- [ ] Step 2: Select pipeline (confirm with user)
- [ ] Step 3: Run test profile (MUST pass before real data)
- [ ] Step 4: Generate samplesheet
- [ ] Step 5: Configure genome + pipeline options (confirm with user), run
- [ ] Step 6: Verify outputs
```

---

## Step 0: Acquire Data (GEO/SRA only)

Skip this step if the user already has local FASTQ files.

For public datasets, use ToolUniverse's own GEO/SRA tools to resolve the
accession to downloadable files FIRST — do not hand-roll a scraper. Full
tool names, parameters, and the download step (via direct URL or
`sra-tools`) are in `references/geo_sra_acquisition.md`.

Quick summary of the tool chain:
1. `geo_search_datasets` / `SRA_search_experiments` — find a dataset if the
   user only has a topic, not an accession.
2. `geo_get_dataset_info` (GSE) or `SRA_get_experiment` (SRX) — confirm the
   dataset and pull out its runs.
3. `NCBI_SRA_search_runs` / `NCBI_SRA_get_run_info` — resolve to SRR run
   accessions and confirm layout (paired/single), platform, and strategy
   (must be RNA-Seq / WGS / WES / ATAC-Seq matching the intended pipeline).
4. `NCBI_SRA_get_download_urls` or `NCBI_SRA_locate_run_files` — get actual
   FTP/S3/HTTPS URLs for the run's FASTQ/SRA files, OR
   `geo_list_supplementary_files` if the files were deposited directly on
   GEO as FASTQ/BAM supplementary files.
5. Download with `curl`/`wget` (URLs from step 4) or with `prefetch` +
   `fasterq-dump` (from `sra-tools`, if only given an accession).

**DECISION POINT:** confirm with the user which samples/runs to download
(a GSE can have dozens of GSMs) and which pipeline this implies, before
downloading anything.

---

## Step 1: Environment Check

**Run first. The pipeline will fail without a passing environment.**

```bash
python3 scripts/check_environment.py
```

All critical checks (Docker, Nextflow, Java) must pass. `check_environment.py`
prints Linux-appropriate fix instructions for each failure it finds (this
skill assumes a Linux host; see the script for macOS notes). **Do not
proceed past a failing check** — report the failure and the fix instructions
to the user instead of continuing.

---

## Step 2: Select Pipeline

**DECISION POINT: confirm with the user before proceeding.**

| Data Type | nf-core Pipeline | Goal |
|-----------|------------------|------|
| RNA-seq (bulk) | `rnaseq` | Gene expression / gene counts for downstream DE |
| WGS/WES | `sarek` | Germline or somatic variant calling |
| ATAC-seq | `atacseq` | Chromatin accessibility peak calling |

Auto-detect a starting suggestion from a directory of files:

```bash
python3 scripts/detect_data_type.py /path/to/data
```

Treat the suggestion as a starting point, not a final answer — confirm the
assay type with the user (filenames alone cannot distinguish, e.g., WGS from
WES, or RNA-seq from a mislabeled ATAC-seq run).

Pipeline-specific details (version pins, samplesheet columns, key outputs,
common options): `references/pipelines/rnaseq.md`,
`references/pipelines/sarek.md`, `references/pipelines/atacseq.md`.

---

## Step 3: Run Test Profile

**Validates the whole toolchain with toy data. MUST pass before real data.**

```bash
nextflow run nf-core/<pipeline> -r <version> -profile test,docker --outdir test_output
```

Verify completion honestly:

```bash
ls test_output/multiqc/multiqc_report.html
grep "Pipeline completed successfully" .nextflow.log
```

If either check fails, stop and consult `references/troubleshooting.md` —
do not proceed to a real run on a broken environment.

---

## Step 4: Generate Samplesheet

```bash
python3 scripts/generate_samplesheet.py /path/to/fastq_dir <pipeline> -o samplesheet.csv
```

The script discovers FASTQ files, pairs R1/R2 by filename pattern, and
writes the pipeline-specific CSV format (columns differ by pipeline — see
`references/pipelines/*.md`). For `sarek`, it will ask about tumor/normal
status per sample if it cannot infer it from filenames.

Validate an existing (user-supplied) samplesheet instead of generating one:

```bash
python3 scripts/generate_samplesheet.py --validate samplesheet.csv <pipeline>
```

---

## Step 5: Configure & Run

**DECISION POINT: confirm with the user before launching a real run:**

1. **Reference genome** — which build (e.g. GRCh38, GRCh37, GRCm39). Do not
   assume human/GRCh38 by default; ask.
2. **Pipeline-specific options** (see `references/pipelines/*.md` for the
   full list):
   - `rnaseq`: aligner (`star_salmon` is the common default; `hisat2` for
     lower-memory hosts)
   - `sarek`: variant-calling tool(s) (`haplotypecaller` for germline,
     `mutect2` for somatic tumor/normal)
   - `atacseq`: `--read_length`

Run:

```bash
nextflow run nf-core/<pipeline> \
    -r <version> \
    -profile docker \
    --input samplesheet.csv \
    --outdir results \
    --genome <genome> \
    -resume
```

`-resume` lets a re-run pick up from the last successful step instead of
restarting from scratch — always include it, even on a first run, so any
later fix-and-retry is cheap. For HPC environments use `-profile
singularity` (or a site-specific profile) instead of `docker` — see
`references/troubleshooting.md`.

---

## Step 6: Verify Outputs

```bash
ls results/multiqc/multiqc_report.html
grep "Pipeline completed successfully" .nextflow.log
```

Report only files that actually exist. Key outputs per pipeline are listed
in `references/pipelines/*.md` (e.g. `salmon.merged.gene_counts.tsv` for
rnaseq, per-sample VCFs under `variant_calling/` for sarek, narrowPeak files
for atacseq).

Hand off downstream interpretation to the matching skill:
DE analysis on the resulting count matrix -> `tooluniverse-rnaseq-deseq2`;
VCF interpretation -> `tooluniverse-variant-analysis`.

### Optional: benchmark a sarek run against Genome in a Bottle (GIAB)

If the sarek run used one of NIST's GIAB reference samples (HG001-HG007) rather
than a real patient sample, you can validate the pipeline's own accuracy by
comparing its output VCF against the matching GIAB high-confidence truth set —
useful when standing up a new pipeline/config and you need to know its
precision/recall before trusting it on real data.

```
GIAB_list_directory(path="")                                            # top-level trios/samples
GIAB_list_directory(path="AshkenazimTrio/HG002_NA24385_son/NISTv4.2.1/GRCh38")
```

This tool only browses NIST's file tree and returns download URLs for the
benchmark VCF/BED files (there is no comparison logic here) — actually
diffing your pipeline's VCF against the truth set requires an external tool
such as `hap.py` or `vcfeval`, run outside ToolUniverse. Verified live:
`path=""` lists the trio/sample directories (e.g. `AshkenazimTrio`), and a
full release path (e.g. the HG002 example above) lists that release's actual
VCF/BED files with direct URLs.

---

## References

- `references/geo_sra_acquisition.md` — GEO/SRA lookup and download using
  ToolUniverse's own tools plus `sra-tools`/`curl`
- `references/pipelines/rnaseq.md`, `sarek.md`, `atacseq.md` — per-pipeline
  version, samplesheet format, options, key outputs
- `references/troubleshooting.md` — common Nextflow/Docker failure modes

## Disclaimer

nf-core pipelines are community-maintained (MIT License); Nextflow is
Apache-2.0. This skill orchestrates them but does not vendor or modify
pipeline code. Always pin `-r <version>` and verify current releases at
https://nf-co.re before a real run — the versions referenced in this skill's
reference files may lag behind the latest nf-core release.
