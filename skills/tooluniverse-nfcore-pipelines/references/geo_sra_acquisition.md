# Acquiring GEO/SRA Data with ToolUniverse Tools

Use ToolUniverse's existing GEO/SRA tools to resolve an accession or topic to
actual downloadable files. Do not hand-roll scraping or guess FTP paths —
these tools exist and are verified against `src/tooluniverse/data/geo_tools.json`,
`sra_tools.json`, and `ncbi_sra_tools.json`.

## Tool chain

### 1. Find a dataset (if you only have a topic, not an accession)

- `geo_search_datasets(query, organism=None, study_type=None, platform=None, limit=None)`
  — search GEO by keyword/organism/study type/platform.
- `SRA_search_experiments(query, organism=None, library_strategy=None, platform=None, limit=None)`
  — search SRA directly by keyword/organism/library strategy/platform.

### 2. Confirm the dataset and get its structure

- `geo_get_dataset_info(dataset_id)` — title, summary, metadata for a GEO
  accession (GSE/GDS).
- `geo_get_sample_info(dataset_id)` — per-sample characteristics/conditions
  for a GEO dataset (same `dataset_id` param as above); confirm the
  accession's samples/conditions here before deciding which GSMs to
  download.
- `SRA_get_experiment(accession)` — title, organism, platform, library info,
  study details for an SRX/ERX/DRX/study accession.

**DECISION POINT:** a GSE can contain dozens of GSMs across multiple
conditions/timepoints. Confirm with the user which subset to download before
proceeding — do not download everything by default.

### 3. Resolve to run-level accessions and confirm assay type

- `NCBI_SRA_search_runs(operation, study=None, organism=None, strategy=None, platform=None, source=None, query=None, limit=None, sort=None)`
  — search runs by study accession / organism / strategy (RNA-Seq, WGS,
  ChIP-Seq, etc.) / platform. Check the `operation` parameter's allowed
  values in `ncbi_sra_tools.json` before calling.
- `NCBI_SRA_get_run_info(operation, accessions)` — platform, instrument,
  library strategy, library source, layout (paired/single) for one or more
  SRR accessions.

**Verify `strategy`/`library_source` here matches the pipeline you intend to
run** (e.g. `RNA-Seq` for the `rnaseq` pipeline, `WGS`/`WXS` for `sarek`,
`ATAC-seq` for `atacseq`). A mismatch here is a common source of a wasted
multi-hour pipeline run.

### 4. Get actual download locations

Two tools return file locations; prefer `NCBI_SRA_locate_run_files` when both
are available since it verifies against the current SDL service rather than
constructing a legacy path:

- `NCBI_SRA_locate_run_files(operation, accessions)` — verified cloud
  location(s) plus authoritative file size and md5 checksum via the NCBI SRA
  Data Locator (SDL) service. Preferred.
- `NCBI_SRA_get_download_urls(operation, accessions)` — NCBI FTP URLs (.sra
  file), AWS S3 URLs, and NCBI web URLs. Use as a fallback or for the S3 path
  if faster large-scale access is needed.

If the data was deposited directly as FASTQ/BAM supplementary files on GEO
(rather than only in SRA), use:

- `geo_list_supplementary_files(accession)` — per-file name, byte size,
  type, modification time, and a **direct download URL** for a GSE or GSM.
  When this returns FASTQ/BAM files directly, it is simpler than going
  through SRA at all — check it first for GEO accessions.

### 5. Download

**Path A — direct URL (from `geo_list_supplementary_files` or
`NCBI_SRA_get_download_urls`'s HTTPS/S3 URL):**

```bash
curl -L -o sample1.fastq.gz "<direct-url>"
```

`curl` is available on virtually every system — prefer this path when a
direct FASTQ URL exists, since it avoids needing `sra-tools` at all.

**Path B — SRA accession only, `.sra`/no direct FASTQ URL available:**

Requires `sra-tools` (`prefetch`, `fasterq-dump`) — `check_environment.py`
verifies these are on PATH. If missing, it prints:

```bash
mamba install -c bioconda -c conda-forge sra-tools
```

Then:

```bash
prefetch <SRR_accession> -O ./sra_cache
fasterq-dump ./sra_cache/<SRR_accession> --split-files -O ./fastq_out
gzip ./fastq_out/*.fastq   # nf-core samplesheets expect .fastq.gz
```

`--split-files` is required for paired-end data (writes `_1.fastq` /
`_2.fastq`, which `generate_samplesheet.py` recognizes).

## After download

Feed the output directory (containing `.fastq.gz` files) into
`scripts/generate_samplesheet.py <dir> <pipeline>` (Step 4 of `SKILL.md`).
