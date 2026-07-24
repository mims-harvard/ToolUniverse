# FastQC module interpretation (long form)

FastQC assigns each module PASS (green), WARN (amber), or FAIL (red). These
flags are heuristics tuned for whole-genome shotgun DNA; many "FAIL"s are
**expected and fine** for RNA-seq, amplicon, and bisulfite libraries. Always
interpret in the context of the library type. Never report a flag as a problem
without saying what it means for *this* library.

## Per base sequence quality
- **What**: box-and-whisker of Phred quality at each read position.
- **PASS**: lower quartile stays high (>~Q28) across all positions.
- **WARN/FAIL**: quality drops at the 3' end (very common, worse on R2 of
  paired-end), or a mid-read dip (lane/bubble problem).
- **Action**: 3' tail decay -> **quality-trim** (fastp default sliding window,
  or `-q 20`). A few low bases at the very end -> often safe to **proceed**;
  aligners soft-clip. A mid-read dip -> **investigate** the run, not a trim fix.

## Per tile sequence quality (Illumina patterned flowcells)
- **What**: quality deviation per flowcell tile.
- **WARN/FAIL**: a tile/region underperformed (bubble, smudge, over-clustering).
- **Action**: usually **proceed**; localized and small. Large losses -> check
  the run / consider re-sequencing.

## Per sequence quality scores
- **What**: distribution of mean read quality.
- **WARN/FAIL**: a subset of reads has low overall quality.
- **Action**: fastp/Cutadapt length+quality filtering drops these reads.

## Per base sequence content
- **What**: %A/C/G/T at each position.
- **PASS**: roughly flat after the first few bases.
- **WARN/FAIL**: bias in the first ~10-12 bases (random-hexamer priming in
  RNA-seq — **expected, proceed**), or a 3' shift toward adapter composition.
- **Action**: random-priming bias -> **proceed**. 3' adapter composition ->
  **trim adapters**.

## Per base N content
- **What**: % of bases called N at each position.
- **PASS**: near 0.
- **WARN/FAIL**: an N spike at a position = the base caller could not decide
  there (cycle/optics problem).
- **Action**: **investigate**. Hard-trim that cycle if isolated, or re-sequence
  if widespread. Not a generic adapter-trim fix.

## Sequence Length Distribution
- **What**: spread of read lengths.
- **PASS (raw)**: single length.
- **WARN after trimming**: multiple lengths — **normal and expected** post-trim.
- **Action**: only a concern if supposedly-raw uniform-length data shows a
  spread (mixed input). Otherwise **proceed**.

## Sequence Duplication Levels
- **What**: fraction of reads that are exact duplicates.
- **WARN/FAIL**: high duplication. Causes: PCR over-amplification (true
  artifact) OR expected biology (amplicon/targeted panels, deep RNA-seq of
  abundant transcripts, small genomes at high coverage).
- **Action**: **investigate, usually proceed**. Do NOT dedup raw reads. PCR
  duplicate removal is an **alignment-stage** decision (Picard/samtools markdup
  using mapping coordinates), not a FASTQ-stage one.

## Overrepresented sequences
- **What**: individual sequences making up >0.1% of reads, with a guessed source.
- **WARN/FAIL**: a sequence is highly abundant. Common sources: adapter,
  primer-dimer, rRNA, poly-A/poly-G (NovaSeq two-color dark cycles), or a
  genuinely abundant transcript.
- **Action**: identify the hit (FastQC's "Possible Source" column, or BLAST it).
  - adapter / primer-dimer -> **trim** (Cutadapt for a known primer; fastp).
  - poly-G tail (NovaSeq/NextSeq) -> fastp `--trim_poly_g` (auto on for those).
  - rRNA / abundant transcript -> **biology, proceed** (optionally rRNA-deplete
    upstream next time).

## Adapter content
- **What**: cumulative % of reads containing known adapter sequences by position.
- **PASS**: flat near 0.
- **WARN/FAIL**: a rising curve toward the 3' end = reads are shorter than the
  insert and read through into the adapter.
- **Action**: **trim adapters**. fastp auto-detects standard Illumina adapters;
  use Cutadapt with the explicit sequence for non-standard/custom adapters.

## Per sequence GC content
- **What**: distribution of per-read GC vs a theoretical normal.
- **WARN/FAIL**: shifted or bimodal peak.
- **Action**: **investigate contamination / mixed species** — NOT fixed by
  trimming. Needs a reference screen (FastQ Screen + bowtie2 indexes, or
  Kraken2). Some shift is normal for biased genomes (AT-rich, GC-rich organisms).

## Kmer content (older FastQC)
- **What**: positionally-enriched k-mers.
- **Action**: usually redundant with adapter/overrepresented modules; investigate
  only if those are clean but Kmer flags.

---

## Quick decision recap

| Symptom                                   | Decision        |
|-------------------------------------------|-----------------|
| 3' quality decay                          | quality-trim    |
| Adapter content ramp at 3'                | adapter-trim    |
| Overrepresented = adapter/primer-dimer    | trim            |
| Overrepresented = rRNA / abundant txpt    | proceed         |
| poly-G tails (two-color chemistry)        | fastp --trim_poly_g |
| High duplication (amplicon/RNA-seq)       | proceed (dedup post-align if at all) |
| GC bimodal / shifted                      | investigate contamination |
| Per-base N spike                          | investigate / hard-trim cycle |
| First-bases composition bias (RNA-seq)    | proceed (random priming) |
| All PASS                                  | proceed, no trim |
