# Skill: Population Genetics Analysis

Analyze population-level genetic variation, allele frequencies, GWAS associations, clinical significance, and evolutionary constraints using ToolUniverse tools.

## When to Use

Activate this skill when the user asks about:
- Allele frequencies across populations (gnomAD, 1000 Genomes)
- GWAS associations for diseases/traits
- Clinical variant interpretation (ClinVar, VEP)
- Gene-level constraint metrics (pLI, LOEUF, o/e ratios)
- Variant annotation and functional consequences
- Population-specific variant distributions
- Regulatory variant scoring

## Workflow

### Phase 0: Input Disambiguation

Determine:
- Is the query about a specific variant (rsID, HGVS) or a gene/disease?
- Does the user need population frequencies, clinical significance, or GWAS context?
- Is a specific population or ancestry group relevant?

Key input types:
- **rsID** (e.g., rs7412) -- variant-centric queries
- **Gene symbol** (e.g., APOE) -- gene-centric queries
- **Disease/trait** (e.g., "Alzheimer disease") -- GWAS-centric queries
- **Genomic coordinates** (e.g., chr19:44908822) -- region-centric queries

### Phase 1: Variant Frequency Lookup

#### 1a: gnomAD Population Frequencies

gnomAD requires a two-step lookup: first resolve rsID to gnomAD variant_id, then fetch details.

**Tool: `gnomad_search_variants`** (Step 1: resolve rsID)
```
Parameters:
  query  string  rsID or search term (REQUIRED)
```

Example:
```json
{"query": "rs7412"}
```

Response:
```json
{
  "status": "success",
  "data": {
    "variant_search": [
      {"variant_id": "19-44908822-C-T"}
    ]
  }
}
```

**Tool: `gnomad_get_variant`** (Step 2: get frequencies)
```
Parameters:
  variant_id  string  gnomAD format: "chr-pos-ref-alt" (REQUIRED, e.g., "19-44908822-C-T")
  dataset     string  Dataset ID (default "gnomad_r3"). Options: gnomad_r4, gnomad_r3, gnomad_r2_1
```

Example:
```json
{"variant_id": "19-44908822-C-T", "dataset": "gnomad_r4"}
```

Response:
```json
{
  "status": "success",
  "data": {
    "variant": {
      "variant_id": "19-44908822-C-T",
      "chrom": "19",
      "pos": 44908822,
      "ref": "C",
      "alt": "T",
      "rsid": "rs7412",
      "genome": {"af": 0.0778, "an": 152112, "ac": 11840},
      "exome": {"af": 0.0738, "an": 1388698, "ac": 102550}
    }
  }
}
```

**IMPORTANT**: `variant_id` format is `CHR-POS-REF-ALT` (no "chr" prefix). Use `gnomad_search_variants` first to resolve rsIDs.

#### 1b: MyVariant (Aggregated Annotation)

For a one-stop variant lookup with ClinVar, dbSNP, gnomAD, and CADD annotations.

**Tool: `MyVariant_query_variants`**
```
Parameters:
  query  string  rsID, HGVS, or variant coordinates (REQUIRED)
```

Example:
```json
{"query": "rs7412"}
```

Response (key fields):
```json
{
  "hits": [{
    "_id": "chr19:g.45412079C>T",
    "cadd": {"phred": 26.2, "1000g": {"af": 0.07, "afr": 0.09, "eur": 0.07}},
    "clinvar": {"rcv": [{"clinical_significance": "risk factor"}]},
    "dbsnp": {"rsid": "rs7412", "alleles": [...]},
    "gnomad_genome": {"af": {"af": 0.078}}
  }]
}
```

**NOTE**: MyVariant uses hg19 coordinates by default. CADD `phred` score >= 20 means top 1% most deleterious.

### Phase 2: Variant Functional Annotation (Ensembl VEP)

**Tool: `EnsemblVEP_annotate_rsid`**
```
Parameters:
  variant_id  string  rsID (REQUIRED, e.g., "rs7412"). Param is "variant_id", NOT "rsid".
```

Example:
```json
{"variant_id": "rs7412"}
```

Response:
```json
{
  "status": "success",
  "data": {
    "input": "rs7412",
    "assembly_name": "GRCh38",
    "seq_region_name": "19",
    "start": 44908822,
    "allele_string": "C/T",
    "most_severe_consequence": "missense_variant",
    "transcript_consequences": [
      {
        "gene_symbol": "APOE",
        "gene_id": "ENSG00000130203",
        "transcript_id": "ENST00000252486",
        "consequence_terms": ["missense_variant"],
        "impact": "MODERATE",
        "amino_acids": "R/C",
        "codons": "Cgc/Tgc",
        "sift_prediction": "deleterious",
        "sift_score": 0,
        "polyphen_prediction": "probably_damaging",
        "polyphen_score": 1
      }
    ]
  }
}
```

**Tool: `EnsemblVEP_variant_recoder`** (convert between variant formats)
```
Parameters:
  variant_id  string  rsID or HGVS notation (REQUIRED)
```

Converts between rsID, HGVS, VCF, SPDI formats.

### Phase 3: GWAS Associations

#### 3a: SNPs Associated with a Gene

**Tool: `gwas_get_snps_for_gene`**
```
Parameters:
  gene_symbol  string  Gene symbol (REQUIRED, e.g., "APOE")
```

Returns all GWAS-catalogued SNPs mapped to the gene locus.

Response:
```json
{
  "status": "success",
  "data": [
    {
      "rsId": "rs769283491",
      "functionalClass": "non_coding_transcript_exon_variant",
      "locations": [{"chromosomeName": "19", "chromosomePosition": 44909978}],
      "genomicContexts": [{"gene": {"geneName": "APOE"}, "isIntergenic": false}]
    }
  ]
}
```

#### 3b: Associations for a Disease/Trait

**Tool: `gwas_search_associations`**
```
Parameters:
  query  string  Disease/trait name (REQUIRED). Must be an EFO/MONDO term, NOT a gene name.
```

Example:
```json
{"query": "Alzheimer disease"}
```

Response:
```json
{
  "status": "success",
  "data": [
    {
      "association_id": 214596830,
      "p_value": 7e-07,
      "or_per_copy_num": 1.81,
      "efo_traits": [{"efo_id": "MONDO_0004975", "efo_trait": "Alzheimer disease"}],
      "mapped_genes": ["ZNRF4"],
      "snp_allele": [{"rs_id": "rs8104246", "effect_allele": "?"}],
      "pubmed_id": "41268768"
    }
  ]
}
```

**IMPORTANT**: `gwas_search_associations` requires a disease/trait name, NOT a gene name. Using a gene name will fail with "Could not resolve trait to EFO ID". For gene-based lookups, use `gwas_get_snps_for_gene`.

**Tool: `gwas_get_variants_for_trait`**
```
Parameters:
  trait  string  Disease/trait name (REQUIRED)
```

Similar to `gwas_search_associations` but variant-focused output.

#### 3c: GWAS SNP Search (BROKEN)

**`gwas_search_snps`** -- Currently returns HTTP 500 errors. Do NOT use this tool. Use `gwas_get_snps_for_gene` or `gwas_search_associations` instead.

### Phase 4: Clinical Significance (ClinVar)

**Tool: `ClinVar_search_variants`**
```
Parameters:
  gene         string  Gene symbol (e.g., "APOE")
  condition    string  Disease/condition name
  significance string  Clinical significance filter (e.g., "pathogenic")
```

At least one of `gene` or `condition` is required.

Example:
```json
{"gene": "APOE"}
```

Response:
```json
{
  "status": "success",
  "data": {
    "total_count": 292,
    "variants": [
      {
        "variant_id": "4812836",
        "title": "NM_000041.4(APOE):c.493C>T (p.Arg165Trp)",
        "genes": ["APOE"],
        "clinical_significance": "Uncertain significance",
        "review_status": "criteria provided, single submitter"
      }
    ]
  }
}
```

**NOTE**: ClinVar response format is variable. Sometimes returns a list, sometimes `{status, data: {esearchresult: {count, idlist}}}`. Always handle both formats.

### Phase 5: Gene-Level Constraint Metrics (gnomAD)

**Tool: `gnomad_get_gene_constraints`**
```
Parameters:
  gene_symbol  string  Gene symbol (REQUIRED, e.g., "APOE")
```

Example:
```json
{"gene_symbol": "APOE"}
```

Response:
```json
{
  "status": "success",
  "data": {
    "gene": {
      "symbol": "APOE",
      "gnomad_constraint": {
        "exp_lof": 14.73,
        "obs_lof": 12,
        "oe_lof": 0.815,
        "pLI": 0.000257,
        "exp_mis": 408.34,
        "obs_mis": 471,
        "oe_mis": 1.153
      }
    }
  }
}
```

Interpretation:
- **pLI** (probability of LoF intolerance): > 0.9 = highly constrained (haploinsufficient)
- **o/e LoF** (observed/expected LoF): < 0.35 = strongly constrained
- **o/e missense**: < 0.8 = missense constrained
- APOE has pLI=0.0003, meaning LoF variants are tolerated (consistent with APOE biology)

**NOTE**: gnomAD constraint queries can intermittently return "Service overloaded". Retry once if this happens.

### Phase 6: Regulatory Variant Assessment

**Tool: `RegulomeDB_query_variant`**
```
Parameters:
  rsid  string  dbSNP rsID (REQUIRED, e.g., "rs7412")
```

Response:
```json
{
  "status": "success",
  "data": {
    "rsid": "rs7412",
    "regulome_score": {
      "probability": "0.99522",
      "ranking": "1b",
      "tissue_specific_scores": {
        "liver": "0.42297",
        "brain": "0.32056",
        "blood": "0.44695"
      }
    }
  }
}
```

RegulomeDB ranking:
- **1a/1b**: Likely affects binding + linked to expression (strongest evidence)
- **2a-2c**: Likely affects binding
- **3a-3b**: Less likely to affect binding
- **4-7**: Minimal evidence of regulatory function

### Phase 7: Literature Context

**Tool: `EuropePMC_search_articles`**
```
Parameters:
  query  string  Search query (REQUIRED)
  limit  integer Max results (default 10)
```

**Tool: `PubMed_search_articles`**
```
Parameters:
  query  string  Search query (REQUIRED)
  limit  integer Max results (default 10)
```

---

## Quick Reference: All Tools and Parameters

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `gnomad_search_variants` | `query` (REQUIRED) | Resolve rsID to gnomAD variant_id |
| `gnomad_get_variant` | `variant_id` (REQUIRED), `dataset` | Population frequencies. variant_id format: "19-44908822-C-T" |
| `gnomad_get_gene_constraints` | `gene_symbol` (REQUIRED) | pLI, o/e ratios. May timeout |
| `MyVariant_query_variants` | `query` (REQUIRED) | Aggregated: ClinVar + dbSNP + gnomAD + CADD |
| `EnsemblVEP_annotate_rsid` | `variant_id` (REQUIRED) | Functional consequence, SIFT, PolyPhen. Param is "variant_id" NOT "rsid" |
| `EnsemblVEP_variant_recoder` | `variant_id` (REQUIRED) | Convert between rsID/HGVS/VCF/SPDI |
| `gwas_get_snps_for_gene` | `gene_symbol` (REQUIRED) | All GWAS SNPs for a gene |
| `gwas_search_associations` | `query` (REQUIRED) | GWAS associations for a disease/trait (NOT gene) |
| `gwas_get_variants_for_trait` | `trait` (REQUIRED) | Variants associated with a trait |
| `ClinVar_search_variants` | `gene`, `condition`, `significance` | At least one filter required |
| `RegulomeDB_query_variant` | `rsid` (REQUIRED) | Regulatory variant scoring (1a-7) |
| `EuropePMC_search_articles` | `query`, `limit` | Full-text literature search |
| `PubMed_search_articles` | `query`, `limit` | PubMed indexed articles |
| `NCBI_search_nucleotide` | `query`, `limit` | Sequence database search |

## Common Mistakes

1. **gnomAD variant_id format**: Must be `"CHR-POS-REF-ALT"` (e.g., `"19-44908822-C-T"`), NOT an rsID. Always call `gnomad_search_variants` first to resolve rsIDs.

2. **gnomAD dataset**: Default is `gnomad_r3`. Use `gnomad_r4` for latest data. Older data: `gnomad_r2_1`.

3. **EnsemblVEP parameter name**: The param is `variant_id`, NOT `rsid`. Pass the rsID as the value of `variant_id`.

4. **VEP response format is variable**: Can return a list, `{data, metadata}`, or `{error}`. Always handle all three.

5. **gwas_search_associations takes disease names, NOT gene names**: Querying with "APOE" will fail. Use `gwas_get_snps_for_gene` for gene-based lookups.

6. **gwas_search_snps is BROKEN**: Returns HTTP 500. Use `gwas_get_snps_for_gene` instead.

7. **ClinVar response format is variable**: Sometimes returns a list, sometimes `{status, data: {esearchresult}}`. Handle both.

8. **gnomAD constraint service overload**: `gnomad_get_gene_constraints` occasionally returns "Service overloaded". Retry once.

9. **MyVariant uses hg19 coordinates**: The `_id` field is in hg19 (e.g., `chr19:g.45412079C>T`), not GRCh38. Be careful when comparing coordinates.

10. **Population frequency interpretation**: gnomAD `af` is allele frequency (0-1). Common variants: af > 0.01. Rare: af < 0.01. Ultra-rare: af < 0.0001.

## Common Use Patterns

### Pattern 1: "What is the population frequency of rs######?"
1. `gnomad_search_variants` -- Resolve rsID to variant_id
2. `gnomad_get_variant` with `dataset: "gnomad_r4"` -- Get genome/exome frequencies
3. `MyVariant_query_variants` -- Get 1000G population-specific frequencies (AFR, EUR, AMR, ASN)
4. `EnsemblVEP_annotate_rsid` -- Functional consequence

### Pattern 2: "What are the GWAS hits for disease X?"
1. `gwas_search_associations` with disease name -- Get associated loci, p-values, odds ratios
2. `gwas_get_variants_for_trait` -- Additional variant details
3. For top hits: `gnomad_get_variant` -- Population frequencies
4. `EuropePMC_search_articles` -- Key publications

### Pattern 3: "Characterize gene X from a population genetics perspective"
1. `gnomad_get_gene_constraints` -- Constraint metrics (pLI, o/e)
2. `gwas_get_snps_for_gene` -- All GWAS associations at locus
3. `ClinVar_search_variants` -- Clinically significant variants
4. `PubMed_search_articles` -- Literature context

### Pattern 4: "Is variant rs###### pathogenic?"
1. `EnsemblVEP_annotate_rsid` -- Consequence, SIFT, PolyPhen
2. `MyVariant_query_variants` -- ClinVar classification, CADD score
3. `gnomad_get_variant` -- Population frequency (rare = more likely pathogenic)
4. `RegulomeDB_query_variant` -- Regulatory impact (for non-coding variants)
5. `ClinVar_search_variants` -- Detailed clinical significance

### Pattern 5: "Compare variant frequencies across populations"
1. `gnomad_search_variants` -- Resolve to variant_id
2. `gnomad_get_variant` with `gnomad_r4` -- Overall genome/exome AF
3. `MyVariant_query_variants` -- 1000 Genomes population breakdowns (AFR, EUR, AMR, EAS, SAS)
4. `EuropePMC_search_articles` -- Population genetics studies

## Evidence Grading

- **T1 (Clinical/Regulatory)**: ClinVar pathogenic/likely pathogenic, FDA pharmacogenomics
- **T2 (Experimental)**: gnomAD population frequencies, GTEx eQTLs, GWAS genome-wide significant (p < 5e-8)
- **T3 (Computational)**: CADD/SIFT/PolyPhen predictions, RegulomeDB scores, constraint metrics
- **T4 (Annotation)**: VEP consequence terms, dbSNP annotations, literature mentions

## Key Concepts

- **Minor Allele Frequency (MAF)**: Frequency of the less common allele. Variants with MAF > 5% are "common".
- **pLI score**: Probability of being Loss-of-function Intolerant. High pLI (>0.9) = haploinsufficiency likely.
- **LOEUF**: Loss-of-function Observed/Expected Upper Fraction. Lower = more constrained. < 0.35 = highly constrained.
- **CADD PHRED score**: >= 10 = top 10%, >= 20 = top 1%, >= 30 = top 0.1% most deleterious.
- **Genome-wide significance**: GWAS p-value < 5e-8 (Bonferroni-corrected threshold).
- **Effect size**: Odds ratio > 1 = risk allele, < 1 = protective. Beta > 0 = increases trait value.
