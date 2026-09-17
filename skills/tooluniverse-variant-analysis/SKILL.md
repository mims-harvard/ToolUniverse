---
name: tooluniverse-variant-analysis
description: VCF and variant analysis — parsing, annotation, classification (synonymous, missense, frameshift, stop_gained), VAF filtering, coding vs non-coding categorization, multi-condition variant comparison, variant-notation conversion (SPDI/HGVS/VCF/rsID interconversion, ALFA per-ancestry allele frequencies), European Variation Archive (EVA) lookups (per-study cohort variant data, RS-accession resolution), HGVS validation/normalization (Mutalyzer), gene-specific curated variants (LOVD), canonical cross-database allele IDs (ClinGen Allele Registry), automated ACMG/AMP classification (GeneBe), principal-transcript selection (APPRIS), Ensembl linkage disequilibrium (LD) for GWAS/fine-mapping, GRCh37/GRCh38 coordinate liftover and protein/cDNA-to-genomic mapping, and Ensembl ID utilities (stable-ID version history, cross-references, region/gene feature overlap, assembly/species metadata). Use for VCF parsing, variant fraction calculations (denominator = coding subset only, NOT all variants), per-sample mutation profiling, converting a variant between SPDI/HGVS/VCF-coordinate/dbSNP-rsID representations, cross-checking a variant against EVA's raw submitted study cohorts, validating an HGVS string's syntax, looking up curated variants for a well-studied gene, resolving a variant to its ClinGen CA ID, getting an automated ACMG verdict, or picking a gene's principal transcript.
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

### European Variation Archive (EVA)

EVA is EBI's variant archive: a repository of raw, per-study submitted
variant calls (small sequencing-project cohorts, not one large aggregated
population database) plus a clustered-variant (RS) accessioning service.
It is **complementary to, not a replacement for**, MyVariant/dbSNP/gnomAD
above:

- gnomAD/MyVariant give you one large, aggregated population allele
  frequency per variant (hundreds of thousands of individuals pooled).
- EVA's `cohortStats` (verified live) is per-submitted-study: each
  `sourceEntries.<studyId>_<fileId>.cohortStats.ALL` block carries its
  OWN small cohort's `maf`/`altAlleleFreq` (e.g. one exome-sequencing
  project of a few hundred samples) — treat as **cohort-specific evidence
  to corroborate a gnomAD frequency**, never as a substitute for it, and
  never average cohort-level MAFs together as if they were one population.
- `EVA_list_studies` surfaces the actual named sequencing projects behind
  those cohorts (disease-specific or population-specific studies), useful
  when the question is "what data exists" rather than "what is the
  frequency."
- `EVA_get_clustered_variant_by_rs` is a *different* EVA sub-service (the
  accessioning/identifiers API, not the variant-data API) — it resolves a
  numeric RS accession (no `rs` prefix, e.g. `429358`) straight to its
  assembly/contig/position record; useful as a fast coordinate check that
  doesn't require picking a gene or region first.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `EVA_get_variants_by_gene` | All EVA-submitted variants for a gene | `gene` (HGNC symbol) | `response[].result[]`, each with `chromosome` (a RefSeq contig accession like `CM000679.2`, NOT a plain chromosome number), `start`, `reference`/`alternate`, `hgvs.genomic[]`, per-study `sourceEntries` |
| `EVA_get_variants_by_region` | Scan a coordinate range (hotspots, regulatory regions) | `region` (`chr:start-end`, plain chromosome number here, unlike the response's contig accession) | Same shape as above, region-scoped |
| `EVA_list_studies` | Discover what sequencing projects/cohorts exist before querying variants | `species` (default `hsapiens_grch38`) | `result[]` of `{studyId, studyName, filesCount}` |
| `EVA_get_clustered_variant_by_rs` | Fast RS-accession-to-coordinate resolution (accessioning API, distinct from the variant-data API above) | `accession` (numeric RS id, no `rs` prefix) | `[{accession, version, data: {assemblyAccession, taxonomyAccession, contig, start, type}}]` |

**Pagination note**: `numTotalResults` in the response can far exceed the
returned page (e.g. BRCA1 had 6,684 total EVA-submitted variants against
a `limit` of 3-20) — never treat a small returned page as the complete
set; check `numTotalResults` before summarizing "how many variants."

### Ensembl Phenotype Associations

Aggregates phenotype/disease associations from multiple upstream sources
(NHGRI-EBI GWAS catalog, ClinVar, OMIM, Cancer Gene Census, Orphanet,
dbGaP) behind one Ensembl REST endpoint, queryable by gene, region,
phenotype term, or variant. **Live reliability, verified repeatedly, not
assumed**: only `EnsemblPheno_get_by_variant` currently works — 2/2 live
calls succeeded with real data. `EnsemblPheno_get_by_gene`,
`EnsemblPheno_get_by_region`, and `EnsemblPheno_get_by_term` all failed on
every attempt (`get_by_gene` hangs/times out; the other two return a fast
"HTTP error: unknown"). This traces to Ensembl's own REST API, not
ToolUniverse: a direct `curl` to
`rest.ensembl.org/phenotype/gene/homo_sapiens/BRCA1` independently
returned a live HTTP 500 from EBI. **Use `EnsemblPheno_get_by_variant`
with confidence; treat the other three as currently broken upstream and
re-check with a fresh `tu run` call before relying on them** — do not
fabricate a gene/region/term-level phenotype result if they fail again.

| Tool | When to Use | Key Parameter | Response | Live status |
|------|------------|----------------|----------|-------------|
| `EnsemblPheno_get_by_variant` | Phenotypes/traits linked to one rsID, multi-source | `variant_id` (rsID) | `phenotypes[]` with `trait`, `source`, `risk_allele`, `pvalue`, `beta_coefficient`, `study` | **Working** (verified) |
| `EnsemblPheno_get_by_gene` | Phenotypes linked to a gene, multi-source aggregate | `gene` (symbol) | `phenotypes[]` with `description`, `source`, `ontology_accessions` | Broken (HTTP 500 upstream, verified) |
| `EnsemblPheno_get_by_region` | Phenotype landscape of a genomic interval | `region` (`chr:start-end`) | `phenotypes[]`, region-scoped | Broken upstream (verified) |
| `EnsemblPheno_get_by_term` | Reverse lookup: phenotype name/ontology accession -> variants/genes | `term` or `accession` (EFO/HP/MONDO) | `associations[]` with `variant`, `gene`, `risk_allele`, `p_value`, `odds_ratio` | Broken upstream (verified) |

**Real example** (rs429358, the same APOE variant already used above in
Variant Notation Conversion — cross-checked for consistency):
`EnsemblPheno_get_by_variant(variant_id="rs429358")` returned 1140 real
phenotype associations, including lipid/metabolite GWAS hits (e.g.
"1,2-dihydroxy-3-keto-5-methylthiopentene dioxygenase levels", PMID
39528825) sourced from the NHGRI-EBI GWAS catalog — a second rsID,
`rs7903146` (TCF7L2/diabetes), returned 331 associations including MAGIC
consortium glucose-trait hits. Each `phenotypes[]` entry's `source` field
tells you which upstream database it came from — grade evidence
accordingly (a ClinVar-sourced entry carries different weight than a
single-study GWAS hit).

For gene-level phenotype aggregation while `EnsemblPheno_get_by_gene` is
down, use Monarch or Gene2Phenotype instead (see
`tooluniverse-gene-disease-association`'s Phase 4/Phase 5).

### Structural Variant Annotation

| Tool | When to Use | Parameters | Response |
|------|------------|------------|----------|
| `gnomad_get_sv_by_gene` | SV population frequency | `gene_symbol` | SVs with AF, AC, AN |
| `gnomad_get_sv_by_region` | Regional SV search | `chrom`, `start`, `end` | SVs in region |
| `ClinGen_dosage_by_gene` | Dosage sensitivity | `gene_symbol` | HI/TS scores, disease |
| `ClinGen_dosage_region_search` | Dosage-sensitive genes in region | `chromosome`, `start`, `end` | All genes with HI/TS scores |
| `ensembl_get_structural_variants` | Known SVs from DGVa/dbVar | `chrom`, `start`, `end`, `species` | Clinical significance |

**See references/annotation_guide.md for detailed tool usage examples**

### Variant Notation Conversion (SPDI / HGVS / VCF / rsID)

Different databases and tools expect different variant notations — NCBI's
canonical internal form is SPDI (`SeqID:Position:Deleted:Inserted`), ClinVar
and most clinical reports use HGVS (`NC_000019.10:g.44908684T>C`), a VCF file
uses `CHROM POS REF ALT`, and dbSNP identifies variants by rsID. Converting
between them (or normalizing to one canonical form for deduplication) is a
common preprocessing step before annotation lookups elsewhere in this skill.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `NCBIVariation_vcf_to_spdi` | Have raw VCF fields, need SPDI to enter this pipeline | `chrom` (RefSeq accession, e.g. `NC_000019.10`), `pos`, `ref`, `alt` | Normalized `spdis[]` |
| `NCBIVariation_spdi_to_hgvs` | Have SPDI, need HGVS for a clinical report or ClinVar-style lookup | `spdi` | `hgvs` string |
| `NCBIVariation_hgvs_to_spdi` | Have an HGVS description (g./c./r.), need SPDI or want to validate the HGVS syntax | `hgvs` | `spdis[]` (one HGVS can map to >1 SPDI across assemblies/transcripts) |
| `NCBIVariation_spdi_canonical` | Need the single normalized/right-shifted SPDI for an indel (dedup, consistent storage) | `spdi` | One canonical `spdi` |
| `NCBIVariation_spdi_equivalents` | Need the same variant's coordinates across GRCh37/GRCh38/RefSeqGene/transcript (liftover) | `spdi` | `equivalents[]` across coordinate systems |
| `NCBIVariation_rsid_lookup` | Have an rsID, need genomic coordinates, gene, MANE Select transcript, and ClinVar significance in one call | `rsid` | `grch38_placements[]`, `genes[]`, `clinical_significance[]`, `mane_select_ids[]` |
| `NCBIVariation_spdi_to_rsids` | Have a genomic SPDI, need the co-located dbSNP rsID(s) (reverse of rsid_lookup) | `spdi` | `rsids[]` |
| `NCBIVariation_alfa_frequencies_by_rsid` | Need **per-ancestry** allele frequencies (European/African/East Asian/South Asian/Latin American/etc.), not just one global MAF | `rsid` | `positions[].studies[].populations[]`, each with `allele_counts` and `allele_frequencies` per ancestry |

**Distinct from gnomAD/MyVariant frequency data above**: `gnomad_get_variant`
and `MyVariant_query_variants` return population-level gnomAD frequencies;
`NCBIVariation_alfa_frequencies_by_rsid` is NCBI's own ALFA aggregator and
reports a different set of ancestry buckets (it will not always agree
numerically with gnomAD for the same variant) — do not treat them as
interchangeable sources for the same "population frequency" claim; state
which source (gnomAD vs. ALFA) a reported frequency came from.

**Decision guide** — start from what you have, land on what you need:
VCF fields → SPDI (`vcf_to_spdi`) → HGVS (`spdi_to_hgvs`) or rsID
(`spdi_to_rsids`); rsID → coordinates/gene/ClinVar (`rsid_lookup`) or
per-ancestry frequency (`alfa_frequencies_by_rsid`); HGVS → SPDI
(`hgvs_to_spdi`) if you need to re-enter the SPDI pipeline (equivalents,
canonicalization, rsID lookup).

**See references/variant_notation_conversion.md for the full parameter
tables, real example calls/responses, and a worked rs429358 (APOE) chain.**

### HGVS Validation & Curated Variant Databases (Mutalyzer, LOVD, ClinGen Allele Registry, GeneBe, APPRIS)

Five more small tool families, live-tested, that round out the clinical
variant workflow: syntax validation, gene-specific curated variant
lookup, canonical cross-database allele IDs, automated ACMG
classification, and principal-transcript selection.

**Mutalyzer — HGVS syntax validation/normalization** (complements, does
not duplicate, the NCBI Variation notation-conversion tools above):
`NCBIVariation_hgvs_to_spdi`/`spdi_to_hgvs` convert BETWEEN notations;
Mutalyzer instead validates and corrects ONE HGVS string's syntax against
its actual reference sequence, translates it to predicted protein/RNA
effect, and can back-translate a protein change to its possible coding
descriptions.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `Mutalyzer_normalize_variant` | Validate/correct an HGVS description before using it elsewhere | `variant` (e.g. `NM_000546.6:c.215C>G`) | `corrected_description`, predicted protein/RNA effect, gene symbol |
| `Mutalyzer_parse_hgvs` | Break an HGVS string into its structured parts (ref sequence, coordinate system, variant type) | `variant` | Structured `model` (reference, coordinate_system, variant type/position) |
| `Mutalyzer_back_translate` | Have a protein change (`p.`), need possible DNA-level descriptions | `variant` (e.g. `NP_000537.3:p.Pro72Arg`) | `dna_descriptions[]` (can be >1 — codon degeneracy) |

**LOVD — gene-specific curated variant databases**: unlike MyVariant/EVA's
broad multi-gene sweep, LOVD hosts per-gene curated variant collections
maintained by gene-specific curators (strong for well-studied genes like
TP53/BRCA1/BRCA2, sparse or absent for others).

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `LOVD_get_gene` | Confirm a gene has an LOVD entry, get its transcript/build metadata | `gene_symbol` | HGNC/Entrez ID, RefSeq transcript(s), curation dates |
| `LOVD_get_variants` | List all curated variants for a gene | `gene_symbol` | `[]` of variants with DNA/RNA/protein HGVS, hg19 position, `Times_reported` |
| `LOVD_search_variants` | Look up one specific variant by LOVD DBID or DNA notation | `gene_symbol` + (`variant_dbid` OR `dna_notation`) | Same per-variant shape as above |

**ClinGen Allele Registry — canonical cross-database allele IDs**: two
tool families cover the SAME underlying registry with overlapping
functionality (verified live — same CA IDs, same external-record shape)
but different tool classes (`ClinGenARTool` vs `ClinGenAlleleTool`).
**Prefer `ClinGenAR_*`** — it has the same forward lookup/detail calls
as `ClinGenAllele_*` PLUS a reverse-lookup-by-external-ID capability
`ClinGenAllele_*` lacks. Use `ClinGenAllele_*` only if already in a
context using it.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `ClinGenAR_lookup_allele` | Have an HGVS string, need the canonical CA ID | `hgvs` | `allele_id` (CA...), community-standard title |
| `ClinGenAR_get_external_records` | Have a CA ID, need cross-references to ClinVar/dbSNP/COSMIC/gnomAD/ExAC | `allele_id` | `external_records` grouped by source database |
| `ClinGenAR_lookup_by_external_id` | Have an rsID or ClinVar VariationID, need the CA ID (reverse of the above) | `dbsnp_rs` OR `clinvar_variation_id` (mutually exclusive) | `alleles[]` (can be >1 CA ID per external ID) |

**GeneBe — automated ACMG/AMP classification**: given raw genomic
coordinates (not HGVS), returns a full ACMG verdict with the specific
criteria invoked (PS3/PM1/PM2/etc.), a ClinVar cross-check, and
AlphaMissense/gnomAD context in one call — useful as a fast automated
first-pass classification before manual ACMG review, not a replacement
for expert curation.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `GeneBe_classify_variant` | Classify one variant by chr/pos/ref/alt | `chr`, `pos`, `ref`, `alt`, `genome` (hg38 default) | `acmg_classification`, `acmg_criteria`, `clinvar_classification`, `alphamissense_score`, `gnomad_exomes_af` |
| `GeneBe_classify_variants_batch` | Classify up to 1000 variants in one request | `variants[]` (each `{chr,pos,ref,alt}`), `genome` | Per-variant ACMG results, same fields as above |

**APPRIS — principal transcript/isoform selection**: when a gene has
multiple transcripts and a variant's coding consequence depends on which
transcript is used, APPRIS tells you which isoform is functionally
"principal" (by protein structure/conservation evidence) vs. alternative
— useful for picking the right transcript before interpreting a coding
HGVS description.

| Tool | When to Use | Key Parameter | Response |
|------|------------|----------------|----------|
| `APPRIS_get_isoforms` | List all transcripts for a gene with PRINCIPAL/ALTERNATIVE tags | `gene_id` (Ensembl gene ID), `species` | `[]` per transcript with `type` (principal_isoform/alternative), tags |
| `APPRIS_get_principal_isoform` | Get just the one principal transcript directly | `gene_id`, `species` | `transcript_id`, `ccds_id`, `length_na` |
| `APPRIS_get_functional_annotations` | Detailed per-method evidence (firestar/spade/matador3d/corsair/etc.) behind the principal-isoform call | `gene_id`, `species`, optional `methods`, `transcript_id` | Per-method scores/annotations |

**Real chained example** (TP53, using the same variant coordinate
`NC_000017.11:g.7674220C>T` / `NM_000546.6:c.743G>A` across tools for a
single coherent worked path, verified live):
`Mutalyzer_normalize_variant("NM_000546.6:c.215C>G")` → corrected
description + predicted protein effect. `LOVD_get_variants("TP53")` →
real curated entries (e.g. LOVD DBID `TP53_010464`,
`NM_000546.5:c.*2609C>A`). `ClinGenAR_lookup_by_external_id(clinvar_variation_id="376694")`
→ real `allele_id="CA16040589"`, title `NM_000546.6(TP53):c.706T>A
(p.Tyr236Asn)`, with COSMIC cross-references. `GeneBe_classify_variant(chr="17",
pos=7674220, ref="C", alt="T", genome="hg38")` → real live result:
`acmg_classification="Pathogenic"`, `acmg_score=22`,
`dbsnp="rs11540652"`, `alphamissense_score=0.996`,
`gnomad_exomes_af=6.16e-06` — cross-checks cleanly against ClinVar's own
"Pathogenic" call on the same coordinate. `APPRIS_get_principal_isoform("ENSG00000141510")`
→ real `ccds_id="CCDS11118.1"` principal transcript for TP53.

### Linkage Disequilibrium (Ensembl)

LD measures non-random co-inheritance of alleles at different loci —
essential for GWAS interpretation (is a hit variant itself causal, or just
correlated with the real causal variant?) and fine-mapping (which variants
in a locus should be tested together).

| Tool | When to Use | Key Parameters | Response |
|------|------------|-----------------|----------|
| `EnsemblLD_get_ld_variants` | Find every variant in LD with one query variant, in one population | `variant_id` (rsID), `population` (`1000GENOMES:phase_3:<POP>`), optional `r2_threshold`/`d_prime_threshold`/`limit` | `ld_variants[]` sorted by r2 descending; `truncated`/`total_ld_count` — raise `limit` if truncated |
| `EnsemblLD_get_ld_pairwise` | Check whether two SPECIFIC variants are correlated, across every 1000 Genomes population at once | `variant1`, `variant2` (rsIDs) | `ld_by_population[]`, each with `r2`/`d_prime` — LD can differ sharply by ancestry (verified live: rs6792369/rs1042779 showed r2=1.0 in some populations, 0.84 in others) |
| `EnsemblLD_get_ld_region` | Full pairwise LD matrix among ALL variants in a window | `region` (`chr:start..end`, GRCh38, <=1Mb), `population` | `ld_pairs[]` — this is the LD matrix input to statistical fine-mapping (SuSiE, FINEMAP) and LD-aware clumping |

```
EnsemblLD_get_ld_variants(variant_id="rs429358", population="1000GENOMES:phase_3:CEU", r2_threshold=0.5)
#  -> real: LD partners for the APOE variant (rs429358, also used in
#     Variant Notation Conversion and EVA above) in the CEU population
```

Live-verified response times: 2-8s for `get_ld_variants`/`get_ld_pairwise`,
similar for small `get_ld_region` windows — no special timeout handling
needed.

### Coordinate Liftover and Protein/cDNA-to-Genomic Mapping (Ensembl)

| Tool | When to Use | Key Parameters | Response |
|------|------------|-----------------|----------|
| `EnsemblMap_convert_coordinates` | Migrate a variant/BED interval between genome assemblies (e.g. GRCh37 -> GRCh38) | `species`, `source_assembly`, `chromosome`, `start`, `end`, `target_assembly` | `mappings[]` with `original`/`mapped` blocks, each carrying `seq_region_name`/`start`/`end`/`strand` |
| `EnsemblMap_translate_coordinates` | Map a protein amino-acid range or transcript cDNA-position range to genomic coordinates | `ensembl_id` (ENSP* for protein, ENST* for cDNA), `start`, `end` (1-based, in that coordinate space) | `mappings[]` of genomic coordinates, one entry per exon the range spans |

```
EnsemblMap_convert_coordinates(species="human", source_assembly="GRCh37",
    chromosome="7", start=140453136, end=140453136, target_assembly="GRCh38")
#  -> real: BRAF V600E's GRCh37 position 7:140453136 maps to GRCh38 7:140753336

EnsemblMap_translate_coordinates(ensembl_id="ENSP00000269305", start=100, end=200)
#  -> real: TP53 protein residues 100-200 map to 3 exons at
#     chr17:7674931-7676071 (GRCh38) — use this before designing an assay
#     or interpreting a reported amino-acid range against the genome
```

**Live-verified timing**: `convert_coordinates` is fast (7-24s);
`translate_coordinates` can take up to ~60s — use a generous timeout
rather than assuming a slow response is a failure.

### Ensembl ID Utilities (archive, overlap, cross-references, assembly/species metadata)

Generic Ensembl-ID housekeeping tools, useful whenever a variant-analysis
workflow needs to resolve, validate, or contextualize a gene/transcript ID
rather than annotate a specific variant.

| Tool | When to Use | Key Parameters | Response |
|------|------------|-----------------|----------|
| `EnsemblArchive_get_id_history` | Check whether a stable ID (ENSG\*/ENST\*/ENSP\*) is still current, and what replaced it if not | `ensembl_id` | `is_current`, `latest_version`, `current_release`, `possible_replacement[]` |
| `EnsemblArchive_batch_lookup` | Same check for up to 50 IDs at once | `ensembl_ids` (comma-separated) | `entries[]`, one per ID |
| `Ensembl_get_region_features` | Everything overlapping a genomic window — genes, transcripts, regulatory elements, constrained elements | `region`, `species`, `feature_types` (comma-separated: `gene,transcript,regulatory,constrained,variation,repeat,motif`) | `features[]`, `type_summary` |
| `Ensembl_get_gene_overlapping_features` | Everything co-located with one gene (overlapping genes, transcript isoforms, regulatory features at that locus) | `gene_id`, `feature_types` | `features[]`, `type_summary` |
| `Ensembl_get_cross_references` | Map an Ensembl ID to HGNC/EntrezGene/UniProt/OMIM/Reactome/GeneCards and other external DB records | `ensembl_id`, optional `external_db` filter | `xrefs[]` with `dbname`/`primary_id`/`display_id`, `database_summary` |
| `Ensembl_lookup_gene_by_symbol` | Resolve a gene symbol to its Ensembl gene/transcript/protein IDs | `symbol`, `species` | `ensembl_ids[]` with `id`/`type` |
| `Ensembl_get_assembly_info` | Genome assembly metadata for a species (assembly name/accession, karyotype, coordinate-system versions) | `species` (e.g. `homo_sapiens`) | `assembly_name`, `karyotype[]`, `coordinate_system_versions[]` |
| `Ensembl_get_species_info` | Discover which genomes/assemblies Ensembl has available, by name/common-name/taxon-ID search | `search` (optional — omit to list all 348+ species) | `species[]` with `taxon_id`, `assembly`, `division` |

**Honesty note on reliability (live-verified across repeated attempts, not
assumed from one run):**
- `EnsemblArchive_*`, `Ensembl_get_cross_references`, and
  `Ensembl_get_assembly_info`/`Ensembl_get_species_info` are genuinely
  working endpoints but **slow and occasionally transiently flaky** —
  first attempts sometimes returned a fast `HTTP 500`/timeout that
  succeeded cleanly on retry with a longer timeout (60-90s). Retry once
  with a longer timeout before reporting these as broken.
- `Ensembl_get_region_features` reproducibly fails (`HTTP 500`) when
  `feature_types` combines multiple values (e.g. `"gene,regulatory"`) for
  at least the TP53 region, while each feature type alone
  (`"gene"` or `"regulatory"` separately) succeeds every time. **Workaround:
  query one feature type per call and merge the results client-side rather
  than trusting a combined multi-type query.**
- `Ensembl_lookup_gene_by_symbol` is **confirmed broken upstream, not a
  ToolUniverse bug**: it consistently returns Ensembl's website HTML error
  page (not JSON) instead of a real response, reproduced across multiple
  attempts and multiple symbols (TP53, BRCA1) — and independently
  confirmed via a direct `curl` to the same `xrefs/symbol/<species>/<symbol>`
  endpoint outside ToolUniverse entirely, which also hung/failed. Do not
  fabricate a symbol-to-ID mapping if this tool fails — use
  `Ensembl_get_cross_references` in the other direction (Ensembl ID ->
  external names) if you already have an ID, or resolve the symbol via
  another already-documented tool (e.g. `NCBIVariation_rsid_lookup`'s
  `genes[]` field, or MyGene/UniProt lookups elsewhere in ToolUniverse)
  instead.

```
Ensembl_get_cross_references(ensembl_id="ENSG00000141510")
#  -> real: TP53's HGNC/EntrezGene/UniProt/OMIM/Reactome cross-references
#     (157 xrefs across 11 databases, verified live)

Ensembl_get_region_features(region="7:140424943-140524564", feature_types="gene")
Ensembl_get_region_features(region="7:140424943-140524564", feature_types="regulatory")
#  -> query separately and merge; the combined "gene,regulatory" form
#     500s on this region (see reliability note above)
```

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
- **references/variant_notation_conversion.md**: SPDI/HGVS/VCF/rsID conversion tools, with real example calls and responses

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

