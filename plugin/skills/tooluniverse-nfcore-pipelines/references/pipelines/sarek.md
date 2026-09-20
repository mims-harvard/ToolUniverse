# nf-core/sarek

**Goal:** germline or somatic variant calling from WGS/WES data (alignment,
preprocessing, variant calling, optional annotation).

**Version:** pin with `-r <version>`. Verify the current stable release at
https://nf-co.re/sarek/releases before running.

## Samplesheet format

```csv
patient,sample,lane,fastq_1,fastq_2,status
patient1,tumor,L001,/abs/path/tumor_R1.fastq.gz,/abs/path/tumor_R2.fastq.gz,1
patient1,normal,L001,/abs/path/normal_R1.fastq.gz,/abs/path/normal_R2.fastq.gz,0
```

- `status`: `1` = tumor, `0` = normal. For germline-only analysis, every
  sample is `status=0`.
- `generate_samplesheet.py` only infers status from filenames containing
  "tumor"/"tumour"/"normal" — anything else is left for the user to fill in
  manually (it will warn loudly rather than guess).

Generate with:
```bash
python3 scripts/generate_samplesheet.py /path/to/fastqs sarek -o samplesheet.csv
```

## Key options to confirm with the user

- `--tools haplotypecaller` — germline variant calling.
- `--tools mutect2` — somatic variant calling (requires tumor/normal pairs
  with correct `status` values).
- `--genome <iGenomes key>` (e.g. `GRCh38`) — REQUIRED, ask; do not default.
- `--wes` flag if this is exome (not whole-genome) data — changes coverage
  expectations and some QC defaults. Ask the user; do not infer WGS vs WES
  from file size alone.

## Key outputs

- `results/variant_calling/<tool>/<sample>/*.vcf.gz` — called variants
- `results/preprocessing/recalibrated/<sample>/*.bam` — analysis-ready BAMs
- `results/multiqc/multiqc_report.html` — QC summary

## Handoff

VCFs -> `tooluniverse-variant-analysis` for interpretation/annotation.
