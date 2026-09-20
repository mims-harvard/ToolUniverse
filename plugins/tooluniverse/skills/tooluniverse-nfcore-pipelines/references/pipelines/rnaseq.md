# nf-core/rnaseq

**Goal:** bulk RNA-seq gene expression / gene-level and transcript-level
quantification for downstream differential expression.

**Version:** pin with `-r <version>`. Verify the current stable release at
https://nf-co.re/rnaseq/releases before running — do not assume a version
number is still current.

## Samplesheet format

```csv
sample,fastq_1,fastq_2,strandedness
SAMPLE1,/abs/path/R1.fastq.gz,/abs/path/R2.fastq.gz,auto
SAMPLE2,/abs/path/R1.fastq.gz,,auto
```

- Absolute paths required.
- `fastq_2` empty for single-end.
- `strandedness`: `auto` lets the pipeline infer it from a subsample
  (recommended default — do not guess strandedness manually unless the
  library prep protocol is known with certainty).

Generate with:
```bash
python3 scripts/generate_samplesheet.py /path/to/fastqs rnaseq -o samplesheet.csv
```

## Key options to confirm with the user

- `--aligner star_salmon` (default, recommended for most cases) vs
  `--aligner star_rsem` vs `--aligner hisat2` (lower memory, use on
  memory-constrained hosts).
- `--genome <iGenomes key>` (e.g. `GRCh38`, `GRCm39`) — REQUIRED, do not
  default silently; ask which reference/build the user needs.
- `--pseudo_aligner salmon` if only pseudo-alignment (faster, no BAMs) is
  needed instead of full alignment.

## Key outputs

- `results/star_salmon/salmon.merged.gene_counts.tsv` — gene-level counts
  (feed into `tooluniverse-rnaseq-deseq2` for differential expression)
- `results/star_salmon/salmon.merged.gene_tpm.tsv` — TPM values
- `results/multiqc/multiqc_report.html` — QC summary across all samples
- `results/star_salmon/<sample>/*.bam` — aligned BAM files (if needed for
  downstream visualization or variant calling)

## Handoff

Gene counts -> `tooluniverse-rnaseq-deseq2` for differential expression.
