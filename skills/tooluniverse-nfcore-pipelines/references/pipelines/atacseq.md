# nf-core/atacseq

**Goal:** chromatin accessibility analysis from ATAC-seq data (alignment,
peak calling, consensus peaks, differential accessibility inputs).

**Version:** pin with `-r <version>`. Verify the current stable release at
https://nf-co.re/atacseq/releases before running.

## Samplesheet format

```csv
sample,fastq_1,fastq_2,replicate
CONTROL,/abs/path/ctrl_R1.fastq.gz,/abs/path/ctrl_R2.fastq.gz,1
CONTROL,/abs/path/ctrl_rep2_R1.fastq.gz,/abs/path/ctrl_rep2_R2.fastq.gz,2
```

- Same `sample` name across replicate rows, incrementing `replicate`.
- `generate_samplesheet.py` auto-numbers replicates per unique sample name
  in the order files are discovered — verify the replicate order/grouping
  makes biological sense before running; it does not know which files are
  true biological replicates versus technical re-runs.

Generate with:
```bash
python3 scripts/generate_samplesheet.py /path/to/fastqs atacseq -o samplesheet.csv
```

## Key options to confirm with the user

- `--read_length` — REQUIRED, one of `50`, `75`, `100`, `150` (used for
  blacklist/effective genome size lookups). Ask; do not assume from a
  typical value.
- `--genome <iGenomes key>` — REQUIRED, ask; do not default.
- `--narrow_peak` (default) vs broad peak calling, depending on the
  chromatin mark/assay expectations — confirm with the user if unsure.

## Key outputs

- `results/macs2/narrowPeak/*.narrowPeak` — called peaks per sample
- `results/bwa/mergedLibrary/bigwig/*.bigWig` — coverage tracks for
  visualization
- `results/multiqc/multiqc_report.html` — QC summary (FRiP score, etc.)

## Handoff

Peak files and counts -> downstream differential accessibility analysis
(not currently covered by a dedicated ToolUniverse skill; treat similarly to
`tooluniverse-rnaseq-deseq2`-style count-based DE if a consensus peak count
matrix is produced).
