# Trimming decisions: when, how, and pitfalls

Trimming is a **decision**, not a default. Over-trimming destroys data and
biases downstream analysis as surely as under-trimming. Decide from the FastQC
evidence, then act minimally.

## Decision tree

1. **All FastQC modules PASS?** -> Do not trim. Proceed.
2. **Adapter content WARN/FAIL** (rising 3' curve)?
   -> Adapter-trim. fastp auto-detect for standard Illumina; Cutadapt with the
      explicit sequence for custom/amplicon adapters.
3. **Per base sequence quality FAIL at 3' tail**?
   -> Quality-trim the 3' end (fastp sliding window / `-q 20`). Keep it gentle;
      aligners soft-clip a few bad bases anyway.
4. **Overrepresented sequence**?
   -> Identify it. Adapter/primer-dimer -> trim. rRNA / abundant transcript ->
      proceed (it's biology). poly-G -> `--trim_poly_g`.
5. **High duplication / GC anomaly / N spike**?
   -> NOT a trimming problem. Investigate (dedup is post-alignment; GC =
      contamination screen; N = base-call/cycle issue).

## fastp vs Cutadapt

- **fastp**: first choice for general Illumina QC+trim. Auto-detects adapters
  (especially well for paired-end via read overlap), trims low-quality 3' bases,
  length-filters, removes poly-G, and emits a JSON/HTML QC report in one pass.
- **Cutadapt**: when you must remove a *specific known* adapter or primer with
  precision (amplicon panels, custom library prep, 5' primers, linked adapters).
  More explicit, less automatic.

## Pitfalls (do not do these)

- **Do NOT auto-trim by default.** QC-only first; trim only after inspection.
- **Do NOT overwrite raw FASTQs.** Always write trimmed reads as new files in a
  separate workdir. Raw data must remain reproducible.
- **Do NOT dedup raw reads.** PCR-duplicate removal uses mapping coordinates and
  belongs after alignment (Picard/samtools markdup). FASTQ-stage duplication is
  diagnostic only.
- **Do NOT trim already-trimmed reads.** Confirm provenance; double-trimming
  erodes read length and can strip real bases.
- **Do NOT trim before UMI extraction.** Extract UMIs first (umi_tools); naive
  adapter/quality trimming corrupts the UMI and breaks deduplication later.
- **Do NOT over-quality-trim.** Aggressive `-q`/length cutoffs shorten reads,
  hurt mappability, and can bias coverage. Trim the minimum the evidence warrants.
- **Mind paired-end synchronization.** When trimming paired reads, keep R1/R2 in
  sync (fastp/Cutadapt paired mode handle this; trimming each file independently
  desynchronizes mates).

## After trimming

Re-run FastQC on the trimmed output and confirm the flagged module(s) now PASS.
Report the before/after status and the exact command used. Length distribution
becoming non-uniform after trimming is expected and not a problem.
