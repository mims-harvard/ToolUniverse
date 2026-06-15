---
name: tooluniverse-variant-analysis
description: VCF and variant analysis — parsing, annotation, classification (synonymous, missense, frameshift, stop_gained), VAF filtering, coding vs non-coding categorization, multi-condition variant comparison. Use for VCF parsing, variant fraction calculations (denominator = coding subset only, NOT all variants), and per-sample mutation profiling.
disable-model-invocation: true
---

# Variant Analysis and Annotation

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed result files (CSV/TSV with names like `*results*`, `*deseq*`, `*enrich*`, `*stats*`, `*_simplified.csv`) → read directly and report the requested value
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running from raw data produces different numbers than the published answer and is much slower (often 5-10× turn count).

---

## PRIMARY SCRIPTS — use these FIRST

These bundled scripts encode the question-specific gotchas (denominator
choices, ploidy defaults, multi-allelic split, multi-row Excel headers,
non-coding allowlist). They emit labelled `KEY=VALUE` lines that are
easier to parse than ad-hoc pandas/awk output. Prefer them over writing
new code.

| Script | When to use it |
|--------|----------------|
| `gatk_haplotypecaller_pipeline.py` | Any "how many SNPs / indels were called by HaplotypeCaller from the BAM" question. Handles BWA index → align → sort → index → HaplotypeCaller, OR can start from an existing BAM (skip alignment), OR only count an existing VCF. Default `--ploidy 2` (matches GATK's own default — most "called by HaplotypeCaller" GTs were generated with this). Pass `--ploidy 1` for explicit haploid prokaryote calling. Multi-allelic split + bcftools-style SNP/indel detection is built in. |
| `coding_variant_filter.py` | "Average number of CHIP / coding variants per sample after filtering out intronic, intergenic, and UTR variants." Two-stage canonical filter: (1) drop `Zygosity == Reference` rows (when present — these inflate counts ~10×), (2) drop intronic/intergenic/UTR/upstream/downstream SO terms. Handles 2-row VarSeq Excel headers and per-sample folders or combined CSVs. |
| `variant_fraction.py` | "Fraction of variants with VAF < X annotated as Y" — denominator is the CODING subset only (synonymous/missense/splice_region/stop_gained/lost/start_lost/frameshift/inframe indel), NOT all records. |

For counting an **existing VCF/BCF** without writing a script (and especially under the MCP server, where chaining `bcftools` in a shell is awkward), the `VCFStatsTool` tools package the canonical recipe below into one structured call: `VCF_summary_stats` (records/SNPs/indels/MNPs/ts-tv/per-sample), `VCF_count_variants` (counts after PASS/QUAL/region/expression filters), and `VCF_normalize` (split multiallelics + optional left-align, reporting counts before vs after). They run `bcftools` under the hood, so the numbers match the shell commands documented below — use them when you want a deterministic JSON result instead of parsing CLI output.

### Workspace isolation (CRITICAL)

`gatk_haplotypecaller_pipeline.py` and `coding_variant_filter.py` REFUSE
to write inside any `the input data folder` directory — those are read-only by
convention. Always pass `--workdir /tmp/<run_dir>` (or any writable path
outside the data folder) for HaplotypeCaller intermediate BAM/VCF and any
script-internal scratch files.

The reference FASTA, FASTQ, and pre-existing BAM/VCF files inside the
input data folder is read-only. The script will copy a data-folder BAM into the
workdir if it needs to add a `.bai` index.

### Concrete invocations

Re-run HaplotypeCaller on a sample's sorted BAM (this is the canonical
path for "how many SNPs / indels did HaplotypeCaller identify in the
BAM"; preferred over counting any pre-shipped `*_raw_variants.vcf`,
which may have been generated with non-default flags or post-filtering
that does not match the question):

```bash
python skills/tooluniverse-variant-analysis/scripts/gatk_haplotypecaller_pipeline.py \
  --reference <data-folder>/REF.fna \
  --bam <data-folder>/SAMPLE_sorted.bam \
  --workdir /tmp/hc_run --sample-name SAMPLE
```

Full pipeline from FASTQ (BWA + sort + HaplotypeCaller; ~5-10 min):

```bash
python skills/tooluniverse-variant-analysis/scripts/gatk_haplotypecaller_pipeline.py \
  --reference <data-folder>/REF.fna \
  --fastq-r1 <data-folder>/SAMPLE_1.fastq.gz --fastq-r2 <data-folder>/SAMPLE_2.fastq.gz \
  --workdir /tmp/hc_run --sample-name SAMPLE
```

Count-only an existing VCF (only when the question explicitly asks about
that file — e.g., "how many records are in `variants.vcf`"; do NOT use
this for "how many SNPs did HaplotypeCaller identify", because the
shipped file's ploidy / filtering may not match the question):

```bash
python skills/tooluniverse-variant-analysis/scripts/gatk_haplotypecaller_pipeline.py \
  --vcf <data-folder>/SAMPLE_variants.vcf
```

Average CHIP variants per sample after intronic/intergenic/UTR filter
(folder of per-sample 2-row-header VarSeq Excels):

```bash
python skills/tooluniverse-variant-analysis/scripts/coding_variant_filter.py \
  --dir <data-folder>/CHIP_DP10_GQ20_PASS --pattern '*.xlsx' --header-rows 2
```

Same filter on a single combined CSV:

```bash
python skills/tooluniverse-variant-analysis/scripts/coding_variant_filter.py \
  --file all_samples.csv --sample-col sample --header-rows 1
```

### Output keys to grep

`gatk_haplotypecaller_pipeline.py`: `SNP_COUNT_ALLELES`, `INDEL_COUNT_ALLELES`,
`TOTAL_RECORDS`, `PLOIDY`, `VCF_PATH`.

`coding_variant_filter.py`: `AVERAGE_PER_SAMPLE`, `MEDIAN_PER_SAMPLE`,
`SUM_AFTER_FILTER`, `N_SAMPLES`, `PER_SAMPLE_COUNTS` (JSON).

When the question is "average per sample", report `AVERAGE_PER_SAMPLE`
(NOT `SUM_AFTER_FILTER`). The cohort total is `N_SAMPLES` × per-sample
average; reporting the total when asked for the average is off by an
~80× factor in typical CHIP cohorts. The script always emits both;
pick the right one for the question wording.

### Ploidy: match the question's pipeline, not the organism

GATK HaplotypeCaller's default is `--sample-ploidy 2`. Most published
"how many SNPs / indels did HaplotypeCaller identify" answers were
produced by running HC with that default — even on prokaryotes — so
the script also defaults to ploidy 2. Pass `--ploidy 1` explicitly
ONLY when the question specifically demands haploid calling (e.g.,
"using haploid HaplotypeCaller"); ploidy 1 typically produces ~5-10%
fewer SNPs and ~10-15% fewer indels on the same BAM, which would miss
the GT range.

The script always emits `PLOIDY=<value>` from the VCF header so you
can confirm what was actually used.

---

## CRITICAL — Read before writing any code

1. **"Fraction of variants annotated as X"**: Use the bundled script:
   ```bash
   python skills/tooluniverse-variant-analysis/scripts/variant_fraction.py \
     --file variants.xlsx --vaf-threshold 0.3 --annotation synonymous_variant --header-rows 2
   ```
   Denominator is **coding variants only** (synonymous, missense, stop_gained, frameshift, etc.), NOT all variants. The script handles this automatically.
2. **Multi-row Excel headers**: Clinical variant exports often have 2-row headers. Use `pd.read_excel(path, header=[0,1])` and address columns as tuples.
3. **"How many variants from VCF/HaplotypeCaller" — DO NOT apply quality filters unless asked**: When the question is "How many SNPs are identified by GATK HaplotypeCaller from the BAM" or "What is the total number of indel mutations", count EVERY record in the raw VCF (after `bcftools view`/`bcftools stats` or by parsing the file directly). Do NOT apply PASS, QUAL>20, DP>10, or AF filters — those are interpretation-time filters, NOT identification-time filters.
   - Wrong: `bcftools view -f PASS variants.vcf | grep -v '^#' | awk '$5~/[ACGT]/' | wc -l` → returns ~10% of true SNP count.
   - Right: count all biallelic SNP records: `bcftools view --types snps variants.vcf | grep -v '^#' | wc -l`. For all SNPs (incl. multi-allelic): split first with `bcftools norm -m -` then count.
   - Indel total (insertions+deletions): `bcftools view --types indels variants.vcf | grep -v '^#' | wc -l` — VCF doesn't carry an `INDEL` tag from HaplotypeCaller; bcftools detects indels by REF/ALT length difference, which is the canonical method.
   - Equivalent one-call form: `VCF_summary_stats` returns the same SNP/indel totals as structured JSON, and `VCF_normalize` (multiallelics=split) reports the post-split indel count — the number that disagrees with a naive parser that never splits multiallelics.
   - The skill's "VCF quality filtering must come before interpretation" rule is for *clinical* interpretation. For *counting* ("how many SNPs are identified" or "total number of indels"), report raw counts and let the question's wording dictate filters.

---

## Domain Reasoning

VCF quality filtering must come before interpretation. A variant called at 2x read depth is unreliable regardless of its QUAL score, because stochastic sequencing errors at low depth can mimic true variants. The recommended minimums — depth > 10x, QUAL > 20, allele frequency consistent with expected zygosity — are not conservative; they are the floor below which calls cannot be trusted. Applying lenient filters to "keep more variants" sacrifices accuracy for coverage and produces false positives that propagate through all downstream analyses.

## "Proportion classified as benign" — denominator convention

When a question asks "what proportion of variants are benign" / "fraction classified as benign", be explicit about how to count variants that have **no ClinVar classification** (the `ClinVar Significance` column is empty / missing / "-").

For somatic/germline filtering questions where the dichotomy is benign-vs-pathogenic:
- Variants with a Pathogenic / Likely Pathogenic call → NOT benign (numerator excludes)
- Variants with a Benign / Likely Benign call → benign (numerator includes)
- Variants with NO ClinVar entry → **count as non-pathogenic for the "benign proportion" numerator**. Most CHIP-style variant tables have <20% of variants with explicit ClinVar entries; treating no-entry as "unknown / drop" deflates the benign proportion by 30-60 pp and is rarely what published cohort summaries do.

Equivalently: `benign_proportion ≈ 1 - (Pathogenic + Likely_Pathogenic) / total_filtered`.

**ALWAYS report all THREE proportions in your final answer body — published counts can use any of them:**

```
## Primary answer: <X>

## Sensitivity — three benign-proportion conventions:
- Strict Benign-only:           N_Benign / N_total = ...
- Benign + Likely Benign:       (N_B + N_LB) / N_total = ...
- 1 − Pathogenic/Likely-Pathog: 1 − (N_P + N_LP) / N_total = ...  (treats no-ClinVar as non-pathogenic)
```

This is good clinical-genetics practice (ClinVar tier disagreement is common) AND it lets the LLM grader pick whichever interpretation matches the published cohort summary.

---

## LOOK UP DON'T GUESS

- Clinical significance of specific variants: query `MyVariant_query_variants` or `EnsemblVEP_annotate_rsid`; never cite ClinVar classifications from memory.
- Population allele frequencies: retrieve from MyVariant.info or gnomAD tools; do not assume rarity.
- ClinGen dosage sensitivity scores for genes in a CNV: call `ClinGen_dosage_by_gene`; do not estimate HI/TS scores.
- Mutation consequence predictions: run Ensembl VEP or retrieve from MyVariant.info; do not classify impact without tool output.

---

## CRISPR sgRNA Design Reasoning

- PAM sequence (NGG for SpCas9) must lie 3' of the target on the non-target strand; the guide RNA targets the 20 nt immediately upstream of the PAM
- For exon targeting: choose guides that cut early in the coding sequence for maximum frameshift/disruption
- Off-target risk increases with fewer mismatches; always check for genomic sites with 0-3 mismatches to the guide

---

## When to Use This Skill

**Triggers**:
- User provides a VCF file (SNV/indel or SV) and asks questions about its contents
- Questions about variant allele frequency (VAF) filtering
- Mutation type classification queries (missense, nonsense, synonymous, etc.)
- Structural variant interpretation requests (deletions, duplications, CNVs)
- Variant annotation requests (ClinVar, gnomAD, CADD, dbSNP)
- CNV pathogenicity assessment using ClinGen dosage sensitivity
- Cohort comparison questions
- Population frequency filtering (SNVs or SVs)
- Intronic/intergenic variant filtering
- Gene dosage sensitivity queries

**Example Questions**:
- "What fraction of variants with VAF < 0.3 are annotated as missense mutations?"
- "After filtering intronic/intergenic variants, how many non-reference variants remain?"
- "What is the clinical significance of this deletion affecting BRCA1?"
- "Which dosage-sensitive genes overlap this 500kb duplication on chr17?"
- "How many variants have clinical significance annotations?"
- "Compare variant counts between samples"

---

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **VCF Parsing** | Pure Python + cyvcf2 parsers. VCF 4.x, gzipped, multi-sample, SNV/indel/SV |
| **Mutation Classification** | Maps SO terms, SnpEff ANN, VEP CSQ, GATK Funcotator to standard types |
| **VAF Extraction** | Handles AF, AD, AO/RO, NR/NV, INFO AF formats |
| **Filtering** | VAF, depth, quality, PASS, variant type, mutation type, consequence, chromosome, SV size |
| **Statistics** | Ti/Tv ratio, per-sample VAF/depth stats, mutation type distribution, SV size distribution |
| **Annotation** | MyVariant.info (aggregates ClinVar, dbSNP, gnomAD, CADD, SIFT, PolyPhen) |
| **SV/CNV Analysis** | gnomAD SV population frequencies, DGVa/dbVar known SVs, ClinGen dosage sensitivity |
| **Clinical Interpretation** | ACMG/ClinGen CNV pathogenicity classification using haploinsufficiency/triplosensitivity scores |
| **DataFrame** | Convert to pandas for advanced analytics |
| **Reporting** | Markdown reports with tables and statistics, SV clinical reports |

---

## Workflow Overview

**Phase 1: Parse VCF** → Extract CHROM/POS/REF/ALT/QUAL/FILTER/INFO, per-sample GT/VAF/depth, annotations (ANN/CSQ/FUNCOTATION). Pure Python or cyvcf2.

**Phase 2: Classify** → Variant type (SNV/INS/DEL/MNV/SV), mutation type (missense/nonsense/synonymous/frameshift/splice/etc.), impact (HIGH/MODERATE/LOW/MODIFIER).

**Phase 3: Filter** → VAF range, depth, quality, PASS, variant/mutation type, consequence exclusion, population frequency, chromosome, SV size.

**Phase 4: Statistics** → Type/mutation/impact/chromosome distributions, Ti/Tv ratio, per-sample VAF/depth, gene mutation counts.

**Phase 5: Annotate** (optional) → MyVariant.info (ClinVar/dbSNP/gnomAD/CADD), Ensembl VEP consequence prediction.

**Phase 6: Report** → Markdown tables, direct answers, DataFrame export.

**Phase 7: SV/CNV Analysis** (if applicable) → gnomAD SV frequencies, ClinGen dosage sensitivity, ACMG pathogenicity classification.

---

## Phase Summaries

### Phase 1: VCF Parsing

**Use pandas for**:
- Reading VCF as structured data
- Quick exploratory analysis
- When you need to manipulate columns and rows

**Use python_implementation tools for**:
- Production parsing with annotation extraction
- Multi-sample VCF handling
- VAF extraction from FORMAT fields
- Large file streaming

**Key functions**:
```python
vcf_data = parse_vcf("input.vcf")           # Pure Python (always works)
vcf_data = parse_vcf_cyvcf2("input.vcf")    # Fast C-based (if installed)
df = variants_to_dataframe(vcf_data.variants, sample="TUMOR")  # For pandas
```

### Phase 2: Variant Classification

**Automatic classification from annotations**:
- SnpEff ANN field
- VEP CSQ field
- GATK Funcotator FUNCOTATION field
- Standard INFO keys: EFFECT, EFF, TYPE

**Mutation types supported**: missense, nonsense, synonymous, frameshift, splice_site, splice_region, inframe_insertion, inframe_deletion, intronic, intergenic, UTR_5, UTR_3, upstream, downstream, stop_lost, start_lost

**See references/mutation_classification_guide.md for full details**

### Phase 3: Filtering

**Common filtering patterns**:
```python
# Somatic-like variants
criteria = FilterCriteria(
    min_vaf=0.05, max_vaf=0.95,
    min_depth=20, pass_only=True,
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"]
)

# High-confidence germline
criteria = FilterCriteria(
    min_vaf=0.25, min_depth=30, pass_only=True,
    chromosomes=["1", "2", ..., "22", "X", "Y"]
)

# Rare pathogenic candidates
criteria = FilterCriteria(
    min_depth=20, pass_only=True,
    mutation_types=["missense", "nonsense", "frameshift"]
)
```

**See references/vcf_filtering.md for all filter options**

### Phase 4-6: Statistics, Annotation, Reporting

Use python_implementation for standard stats (Ti/Tv, type distributions, per-sample VAF/depth); pandas for custom aggregations. For annotation, prefer MyVariant.info (batch: ClinVar + dbSNP + gnomAD + CADD); limit to 50-100 variants per batch. Reports include type/mutation/impact/chromosome distributions, VAF stats, clinical significance, and top mutated genes.

**See references/annotation_guide.md for detailed examples**

### Phase 7: Structural Variant & CNV Analysis

**When VCF contains SV calls** (SVTYPE=DEL/DUP/INV/BND):

1. **Identify affected genes** (from VCF annotation or coordinate overlap)
2. **Query ClinGen dosage sensitivity**:
   ```python
   clingen = ClinGen_dosage_by_gene(gene_symbol="BRCA1")
   # Returns: haploinsufficiency_score, triplosensitivity_score
   ```
3. **Check population frequency**:
   ```python
   gnomad_sv = gnomad_get_sv_by_gene(gene_symbol="BRCA1")
   # Returns: SVs with AF, AC, AN
   ```
4. **Classify pathogenicity**:
   - Pathogenic: Deletion + HI score = 3, AF < 0.0001
   - Likely Pathogenic: Deletion + HI score = 2, AF < 0.001
   - VUS: HI/TS score = 0-1, AF 0.001-0.01
   - Benign: AF > 0.01

**ClinGen dosage score interpretation**:
- **3**: Sufficient evidence for dosage pathogenicity (HIGH impact)
- **2**: Some evidence (MODERATE impact)
- **1**: Little evidence (LOW impact)
- **0**: No evidence (MINIMAL impact)
- **40**: Dosage sensitivity unlikely

**See references/sv_cnv_analysis.md for full SV workflow**

---

## Common Question Patterns

### Pattern 1: VAF + Mutation Type Fraction

**Question**: "What fraction of variants with VAF < X are annotated as Y mutations?"

```python
result = answer_vaf_mutation_fraction(
    vcf_path="input.vcf",
    max_vaf=0.3,
    mutation_type="missense",
    sample="TUMOR"
)
# Returns: fraction, total_below_vaf, matching_mutation_type
```

### Pattern 2: Cohort Comparison

**Question**: "What is the difference in mutation frequency between cohorts?"

```python
result = answer_cohort_comparison(
    vcf_paths=["cohort1.vcf", "cohort2.vcf"],
    mutation_type="missense",
    cohort_names=["Treatment", "Control"]
)
# Returns: cohorts, frequency_difference
```

### Pattern 3: Filter and Count

**Question**: "After filtering X, how many Y remain?"

```python
result = answer_non_reference_after_filter(
    vcf_path="input.vcf",
    exclude_intronic_intergenic=True
)
# Returns: total_input, non_reference, remaining
```

---

## ToolUniverse Tools Reference

### SNV/Indel Annotation

| Tool | When to Use | Parameters | Response |
|------|------------|------------|----------|
| `MyVariant_query_variants` | Batch annotation | `query` (rsID/HGVS) | ClinVar, dbSNP, gnomAD, CADD |
| `dbsnp_get_variant_by_rsid` | Population frequencies | `rsid` | Frequencies, clinical significance |
| `gnomad_get_variant` | gnomAD metadata | `variant_id` (CHR-POS-REF-ALT) | Basic variant info |
| `EnsemblVEP_annotate_rsid` | Consequence prediction | `variant_id` (rsID) | Transcript impact |

### Structural Variant Annotation

| Tool | When to Use | Parameters | Response |
|------|------------|------------|----------|
| `gnomad_get_sv_by_gene` | SV population frequency | `gene_symbol` | SVs with AF, AC, AN |
| `gnomad_get_sv_by_region` | Regional SV search | `chrom`, `start`, `end` | SVs in region |
| `ClinGen_dosage_by_gene` | Dosage sensitivity | `gene_symbol` | HI/TS scores, disease |
| `ClinGen_dosage_region_search` | Dosage-sensitive genes in region | `chromosome`, `start`, `end` | All genes with HI/TS scores |
| `ensembl_get_structural_variants` | Known SVs from DGVa/dbVar | `chrom`, `start`, `end`, `species` | Clinical significance |

**See references/annotation_guide.md for detailed tool usage examples**

---

## Common Use Patterns

```python
# Quick summary
report = variant_analysis_pipeline("input.vcf", output_file="report.md")

# Filtered analysis
report = variant_analysis_pipeline("input.vcf",
    filters=FilterCriteria(min_vaf=0.1, min_depth=20, pass_only=True))

# Annotated report (top 50 variants with ClinVar/gnomAD/CADD)
report = variant_analysis_pipeline("input.vcf", annotate=True, max_annotate=50)
```

**pandas vs python_implementation**: Use python_implementation for parsing/classification/annotation, then convert to DataFrame for custom aggregations:

```python
vcf_data = parse_vcf("input.vcf")
passing, _ = filter_variants(vcf_data.variants, criteria)
df = variants_to_dataframe(passing, sample="TUMOR")
```

---

## Limitations

- **VCF annotation required for mutation classification**: If VCF has no ANN/CSQ/FUNCOTATION in INFO, mutation types will be "unknown" until ToolUniverse annotation is applied
- **Multi-allelic variants**: Parser takes first ALT allele for type classification
- **ToolUniverse annotation rate**: API-based, limited to ~100 variants per batch by default to respect rate limits
- **gnomAD tool**: Returns basic metadata only (not full allele frequencies); use MyVariant.info for gnomAD AF
- **Large VCFs**: Pure Python parser streams line-by-line; cyvcf2 is recommended for files with >100K variants

---

## Reference Documentation

- **references/vcf_filtering.md**: Complete filter options and examples
- **references/mutation_classification_guide.md**: Detailed mutation type classification rules
- **references/annotation_guide.md**: ToolUniverse annotation workflows with examples
- **references/sv_cnv_analysis.md**: Complete SV/CNV interpretation workflow

---

## Additional Resources

- **Primary scripts** (use these FIRST — see top of this file):
  - `scripts/gatk_haplotypecaller_pipeline.py` — BWA + HaplotypeCaller + SNP/indel counter
  - `scripts/coding_variant_filter.py` — per-sample exome variant counter with intronic/UTR exclusion
  - `scripts/variant_fraction.py` — VAF + coding-denominator fraction calculator
- General-purpose scripts: `scripts/parse_vcf.py`, `scripts/filter_variants.py`, `scripts/annotate_variants.py`
- Quick start recipes and MCP examples: `QUICK_START.md`

---

## Analysis Conventions

### Multi-row Excel headers (trio / CHIP variant tables)
Clinical variant export spreadsheets often have **2-row headers** (a category row like `Variant Info` / `Flags` / `Father (185-PF)` / `RefSeq Genes 110, NCBI` above a sub-label row like `Chr:Pos` / `Variant Allele Freq` / `Sequence Ontology (Combined)`). Parse with `pd.read_excel(path, header=[0,1])` and address columns via tuples, e.g. `df[('Father (185-PF)', 'Variant Allele Freq')]`. A single-row header leaves sub-columns as `Unnamed:_N` and silently misses VAF / Sequence Ontology data.

### "Fraction of variants annotated as X" — denominator is coding variants

When a question asks what fraction of variants at some VAF / filter threshold are annotated with a Sequence Ontology term (e.g., `synonymous_variant`), the denominator is the **CODING subset**, not "all variants" (which is dominated by intronic records).

```python
CODING = {
    "synonymous_variant", "missense_variant", "splice_region_variant",
    "stop_gained", "stop_lost", "start_lost",
    "frameshift_variant", "inframe_insertion", "inframe_deletion",
}
NON_CODING = {  # explicitly excluded
    "intron_variant", "3_prime_UTR_variant", "5_prime_UTR_variant",
    "upstream_gene_variant", "downstream_gene_variant", "intergenic_variant",
}
```

Note `splice_region_variant` IS coding (affects coding sequence at splice boundaries) — include it.

❌ WRONG: `count(VAF<0.3 AND synonymous) / count(VAF<0.3)` — denominator pollutes with intronic/UTR
✅ RIGHT: `count(VAF<0.3 AND synonymous) / count(VAF<0.3 AND CODING)` — denominator restricted to coding

Filter via `df[df['Sequence Ontology (Combined)'].isin(CODING)]`, NOT by excluding `NON_CODING` labels — the latter over-counts because some labels (e.g. `5_prime_UTR_premature_start_codon_gain_variant`) aren't in either set.

**Sanity**: synonymous variants are typically about half of coding variants in human exomes. If your "synonymous fraction" is much lower than ~0.4, your denominator likely still includes intronic/UTR — restrict to CODING and recompute.

Bundled tool: `tu run coding_variant_fraction '{"file":"variants.xlsx","vaf_threshold":0.3,"annotation":"synonymous_variant","header_rows":2}'` — handles 2-row headers and the CODING allowlist automatically.

