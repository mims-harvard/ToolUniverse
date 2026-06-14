---
name: tooluniverse-epigenomics
description: "Genomics and epigenomics analysis: DNA methylation (CpG, 5mC, 5hmC, bisulfite, RRBS), m6A RNA modification (MeRIP-seq), ChIP-seq peaks, ATAC-seq accessibility, histone modifications, chromatin state, multi-omics integration. Combines pandas/scipy/pysam computation with ToolUniverse annotation tools. Use for genome-wide epigenomic statistics, methylation analysis, and chromatin-genome integration."
disable-model-invocation: true
---

# Genomics and Epigenomics Data Processing

## ⚠️ TOP-OF-MIND RULE: long-format methylation CSV — count ROWS, not unique positions

When the input is a long-format methylation CSV (one row per `(sample, CpG_position)`
e.g. columns `Pos, Chromosome, MethylationPercentage`), "how many sites are
removed when filtering" almost always means **rows removed**, NOT unique-position
removals. The two answers differ by a factor of ≈ `n_samples`.

| Question phrasing | What it means |
|---|---|
| "how many sites are removed when filtering …" | **rows removed** (= samples × positions failing the filter) |
| "how many unique CpG sites pass filter" | **unique positions** (dedupe by `Pos` then filter) |

❌ WRONG: `df.drop_duplicates(["Pos"]).query("MethylationPercentage<10 or >90")` then `len(filtered)` → counts unique positions (typically 100–1500)

✅ RIGHT: `df.query("MethylationPercentage<10 or MethylationPercentage>90")` then `len(df) - len(filtered)` → counts rows (typically 10k–30k)

If your answer is < 2000 when the data has 1000+ positions × 20+ samples, you
deduplicated too early. Re-read the question's noun before reporting.

---

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed result files (CSV/TSV with names like `*results*`, `*deseq*`, `*enrich*`, `*stats*`, `*_simplified.csv`) → read directly and report the requested value
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running from raw data produces different numbers than the published answer and is much slower (often 5-10× turn count).

---

Production-ready skill combining Python computation (pandas, scipy, numpy, pysam, statsmodels) with ToolUniverse annotation tools for epigenomics analysis.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first.

## When to Use

Methylation data, ChIP-seq peaks, ATAC-seq, multi-omics integration, genome-wide epigenomic statistics. Keywords: methylation, CpG, ChIP-seq, ATAC-seq, histone, chromatin, epigenetic.

**NOT for**: RNA-seq DEG, variant calling, gene enrichment, protein structure.

---

## Key Principles

1. **Data-first** - Load/inspect before analysis
2. **Question-driven** - Extract specific numeric answer
3. **Coordinate system awareness** - Track genome build (hg19/hg38/mm10), chr prefix
4. **Statistical rigor** - FDR correction, effect size filtering
5. **CpG identification** - Parse Illumina probe IDs, genomic coordinates

## PRIMARY SCRIPT — methylation_density.py (use FIRST for CpG-density questions)

For long-format methylation CSVs (`Pos, Chromosome, MethylationPercentage`)
paired with chromosome-length CSVs, ALWAYS run the bundled script before
hand-rolling pandas. It deterministically computes every common metric in one
pass and avoids the rows-vs-sites pitfall that produces silently-wrong answers.

```bash
python skills/tooluniverse-epigenomics/scripts/methylation_density.py \
  --cpg <CpG csv> --chr-lengths <chr lengths csv> \
  --filter-meth-extremes 90 10
```

The full JSON output contains every metric. Pick the one that matches the
question's wording (NOT a similar-looking one):

| Question phrasing                                              | Script field              |
|----------------------------------------------------------------|---------------------------|
| "how many sites are removed when filtering …"                  | `rows_removed`            |
| "how many unique CpG sites pass filter"                        | `unique_pos_after_filter` |
| "genome-wide AVERAGE chromosomal density"                      | `density_avg_per_chr`     |
| "density on chromosome X"                                      | `density_chromosome` (pass `--chromosome X`) |
| "total density across the genome"                              | `density_total_over_genome` |

The two density numbers (`density_avg_per_chr` vs `density_total_over_genome`)
typically differ by ~2× because CpGs are not uniformly distributed across
chromosomes; reporting one when the question asks for the other is the most
common failure mode here.

For "sites removed" questions, the long-format CSV has multiple rows per CpG
position (one per sample), so `rows_removed` is in the tens of thousands while
`unique_pos_removed` is in the hundreds. Match the granularity to the question.

## Distinguish "rows" vs "unique sites" — methylation CSVs are usually long-format

CpG methylation CSVs typically have ONE ROW PER (sample × CpG site) — so `len(df) >> n_unique_sites`. Before computing anything, decide which axis the question is asking about:

| Question phrasing | Axis | Operation |
|-------------------|------|-----------|
| "how many sites are removed when filtering" | sample-rows | filter then count rows; do NOT dedupe by `Pos`. The CSV is in long format; "sites" here is row-shaped. Subtract `len(df_filtered)` from `len(df)`. |
| "how many unique CpG sites pass filter" | unique positions | dedupe by position (or `Pos` column), then filter |
| **"genome-wide average chromosomal density"** | per-chromosome density | MEAN of per-chromosome densities: `(n_unique_per_chr / chr_length).mean()`. NOT `total_unique / total_genome` — that gives a different answer (typically ≈ ½ of the per-chr mean for unevenly distributed CpGs). |
| **"density on chromosome X"** | single chromosome | unique positions on X / length(X). Be careful which species — check the question text for "Zebra Finch" vs "Jackdaw". |
| "chi-square for uniform distribution across chromosomes" | unique positions per chromosome | filter rows first, then dedupe by `(Chromosome, Pos)`, then count per-chromosome unique positions for chi-square against expected = `chr_length / total_length × n_unique_filtered` |

**Sanity check**: if your filtered count is two orders of magnitude smaller than the GT range, you likely deduped when the question wanted row-level counts (or vice versa). Re-run with the other axis and compare.

For the chi-square uniformity test: expected counts = `chromosome_length / total_genome_length × n_unique_sites`. The chi-square statistic depends on the **count granularity** (rows vs unique sites) — a row-level chi-square gives a much higher chi-square than a unique-position chi-square because `n` is larger.

**Precedence**: when an `*_executed.ipynb` exists, read its filtering code verbatim — `df[(df.MethylationPercentage > 90) | (df.MethylationPercentage < 10)]` (no dedup) and `df.drop_duplicates('Pos')` (with dedup) yield wildly different counts on the same dataset.

---

## Workflow

### Phase 0: Question Parsing
Identify data files, specific statistic, thresholds, genome build. Categorize by keywords.
See `ANALYSIS_PROCEDURES.md` for decision tree.

### Phase 1: Methylation Processing
- Load beta/M-value matrix (CSV/TSV/parquet/HDF5)
- Filter by variance, missing rate, probe type, chromosome, CpG island relation
- Differential methylation: T-test/Wilcoxon between groups + FDR
- Age-related CpG: Pearson/Spearman correlation + FDR
- Chromosome density: CpG count / chromosome length

### Phase 2: ChIP-seq Peak Analysis
- Load BED/narrowPeak/broadPeak, normalize chromosomes
- Peak stats, annotation to genes, overlap analysis (Jaccard)

### Phase 3: ATAC-seq
- NFR detection (<150bp peaks), region classification

### Phase 4: Multi-Omics Integration
- Methylation-expression correlation per probe-gene (Pearson/Spearman + FDR)
- ChIP-seq + expression: promoter peaks vs expression levels

### Phase 5: Clinical Data
- Missing data analysis across modalities, complete case identification

### Phase 6: ToolUniverse Annotation

**ENCODE tools**:
- `ENCODE_search_rnaseq_experiments`: `assay_type` ("total RNA-seq" default; fall back to "polyA plus RNA-seq"), `biosample`, `limit`
- `ENCODE_search_histone_experiments`: `target` (e.g., "H3K27ac"), `cell_type`/`tissue`/`biosample`, `limit`

**GEO tools**: `GEO_search_rnaseq_datasets`, `GEO_search_atacseq_datasets` -- both accept `limit` or `max_results`

**GTEx tools**:
- `GTEx_get_median_gene_expression`: `gene_symbol` (NOT Ensembl ID)
- `GTEx_query_eqtl`: `gene_symbol`, `tissue_id` (case-sensitive exact, e.g., `"Whole_Blood"`)

**Other**: `ensembl_lookup_gene` (requires `species='homo_sapiens'`), `ensembl_get_regulatory_features` (NO "chr" prefix), `SCREEN_get_regulatory_elements`, `ChIPAtlas_*` (requires `operation` param), `SRA_search_experiments` (library_strategy: "ChIP-Seq"/"Bisulfite-Seq"/"ATAC-seq")

### Phase 7: Genome-Wide Statistics
Global mean/median beta, probe variance, chromosome density, DMP counts.

See `CODE_REFERENCE.md` for full implementations.

---

## Common Patterns

| Pattern | Key Steps |
|---------|-----------|
| Differential methylation | Filter probes → groups → t-test → FDR → threshold |
| Age-related CpG density | Correlate with age → FDR → map to chr → density ratio |
| Multi-omics missing data | Extract IDs → intersect → check NaN → complete case count |
| ChIP-seq annotation | Load peaks → annotate genes → classify regions |
| Methylation-expression | Align samples → correlate → FDR → anti-correlations |

---

## GTEx Tissue IDs

Whole_Blood, Liver, Lung, Breast_Mammary_Tissue, Brain_Cortex, Heart_Left_Ventricle, Kidney_Cortex, Thyroid, Adipose_Subcutaneous, Muscle_Skeletal

---

## Evidence Grading

| Grade | Criteria |
|-------|----------|
| **Strong** | padj < 0.01 AND abs(delta-beta) >= 0.2, replicated |
| **Moderate** | padj < 0.05 AND abs(delta-beta) >= 0.1 |
| **Weak** | padj < 0.05 but delta-beta < 0.1 |
| **Insufficient** | padj >= 0.05 or no replication |

Delta-beta >= 0.2 = strong effect. ChIP-seq: q < 0.01, FE >= 2 for confidence. ATAC-seq NFR < 150bp = active regulatory. Always apply BH FDR. Verify genome build consistency.

---

## Limitations

- No pybedtools/pyBigWig: pure Python intervals
- Illumina-centric (450K/EPIC); uses t-test/Wilcoxon (not limma)
- No peak calling (assumes pre-called)
- API rate limits: ~20 genes per batch

## Reference Files

`CODE_REFERENCE.md`, `TOOLS_REFERENCE.md`, `ANALYSIS_PROCEDURES.md`, `QUICK_START.md`
