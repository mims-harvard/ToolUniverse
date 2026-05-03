---
name: tooluniverse-population-genetics-1000genomes
description: >
  Population genetics research using the 1000 Genomes Project (IGSR) -- search populations by
  superpopulation ancestry (AFR, AMR, EAS, EUR, SAS), retrieve samples by population code,
  list available data collections, and integrate with GWAS tools for population stratification
  analysis. Use when users ask about 1000 Genomes populations, sample ancestry, allele frequency
  variation across continental groups, population-specific GWAS interpretation, or IGSR data
  collections like the 30x high-coverage resequencing or HGSVC.
triggers:
  - keywords: [1000 Genomes, IGSR, population, superpopulation, AFR, AMR, EAS, EUR, SAS, YRI, GBR, CHB, population stratification, ancestry, admixture, allele frequency, population genetics]
  - patterns: ["population code", "population stratification", "ancestral population", "1000 Genomes sample", "continental ancestry", "superpopulation filter"]
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Population Genetics with 1000 Genomes (IGSR)

Use IGSR tools to search 1000 Genomes populations and samples, explore data collections, and
combine with GWAS tools for population-stratified analysis.

## When to Use

- "List all African (AFR) populations in the 1000 Genomes Project"
- "Find samples from the YRI (Yoruba) population"
- "What 1000 Genomes data collections are available?"
- "Which GWAS SNPs for type 2 diabetes have population-specific effects?"
- "Find all SNPs mapped to TCF7L2 in GWAS studies"

## NOT for (use other skills instead)

- Allele frequencies from gnomAD -> Use `tooluniverse-population-genetics`
- ClinVar / OMIM variant interpretation -> Use `tooluniverse-variant-interpretation`
- GWAS fine-mapping -> Use `tooluniverse-gwas-finemapping`

---

## Phase 1: Search 1000 Genomes Populations

**IGSR_search_populations**: `superpopulation` (string/null, one of AFR/AMR/EAS/EUR/SAS), `query` (string/null, free-text search by name), `limit` (int).
Returns `{status, data: {total, populations: [{code, name, description, sample_count, superpopulation_code, superpopulation_name, latitude, longitude}]}, metadata: {source, filter_superpopulation, filter_query}}`.

Superpopulation codes:
| Code | Ancestry |
|------|----------|
| AFR | African |
| AMR | Admixed American |
| EAS | East Asian |
| EUR | European |
| SAS | South Asian |

```json
// List all AFR populations
{"superpopulation": "AFR", "limit": 10}

// Search by name (free-text)
{"query": "Yoruba", "limit": 5}

// List all populations
{"limit": 26}
```

Response example:
```json
{
  "status": "success",
  "data": {
    "total": 3,
    "populations": [
      {"code": "YRI", "name": "Yoruba", "description": "Yoruba in Ibadan, Nigeria",
       "sample_count": 188, "superpopulation_code": "AFR", "superpopulation_name": "African Ancestry"}
    ]
  }
}
```

---

## Phase 2: Search Samples by Population

**IGSR_search_samples**: `population` (string/null, population code e.g. "YRI"), `data_collection` (string/null, collection title), `sample_name` (string/null, specific sample e.g. "NA12878"), `limit` (int).
Returns `{status, data: {total, samples: [{name, sex, biosample_id, populations: [{code, name, superpopulation}], data_collections: [...]}]}}`.

```json
// Find all YRI samples
{"population": "YRI", "limit": 10}

// Look up the reference sample NA12878
{"sample_name": "NA12878", "limit": 1}

// Find samples in the 30x high-coverage collection
{"data_collection": "1000 Genomes 30x on GRCh38", "limit": 5}
```

NOTE: `population` takes a population code (e.g. "YRI", "GBR", "CHB"), not a superpopulation code. Use IGSR_search_populations first to get population codes if starting from a superpopulation.

---

## Phase 3: List Data Collections

**IGSR_list_data_collections**: `limit` (int).
Returns `{status, data: {total, collections: [{code, title, short_title, sample_count, population_count, data_types, website}]}}`.

```json
{"limit": 20}
```

Key collections available (18 total):
| Collection | Description | Data Types |
|------------|-------------|------------|
| 1000 Genomes on GRCh38 | 2709 samples, 26 populations | sequence, alignment, variants |
| 1000 Genomes 30x on GRCh38 | High-coverage resequencing | sequence, alignment, variants |
| 1000 Genomes phase 3 release | Original phase 3 | sequence, alignment, variants |
| Human Genome Structural Variation Consortium | HGSVC SV discovery | sequence, alignment |
| MAGE RNA-seq | RNA-seq data | - |
| Geuvadis | Expression + genotype | - |

---

## Phase 4: GWAS Context for Population Stratification

### Search GWAS associations for a trait

**gwas_search_associations**: `trait` (string, free text), `limit` (int).
Returns GWAS associations with rsID, p-value, mapped genes, EFO trait IDs.

```json
{"trait": "type 2 diabetes", "limit": 10}
```

### Get variants for a specific trait (by EFO ID)

**gwas_get_variants_for_trait**: `trait` (string, EFO ID e.g. "EFO_0001645"), `limit` (int).

```json
{"trait": "EFO_0001645", "limit": 10}
```

### Find SNPs in a gene from GWAS catalog

**gwas_get_snps_for_gene**: `gene_symbol` (string), `limit` (int).
Returns SNPs mapped to the gene with rsIDs, genomic positions, functional classes.

```json
{"gene_symbol": "TCF7L2", "limit": 10}
```

---

## Workflow: Population Stratification in GWAS

Step 1 -- Find populations of interest:
```json
// Get all EUR populations
{"superpopulation": "EUR", "limit": 10}
// -> Returns codes like GBR, FIN, CEU, TSI, IBS
```

Step 2 -- Get samples from target population:
```json
// Get YRI samples (AFR)
{"population": "YRI", "limit": 100}
```

Step 3 -- Get GWAS SNPs for the gene or trait:
```json
// GWAS hits for TCF7L2 (T2D gene)
{"gene_symbol": "TCF7L2", "limit": 20}
```

Step 4 -- Cross-reference with population data for stratification analysis.

---

## Common Population Codes

| Code | Population | Superpopulation |
|------|-----------|-----------------|
| YRI | Yoruba in Ibadan, Nigeria | AFR |
| LWK | Luhya in Webuye, Kenya | AFR |
| GWD | Gambian Mandinka | AFR |
| CEU | Utah residents (CEPH) | EUR |
| GBR | British in England/Scotland | EUR |
| FIN | Finnish in Finland | EUR |
| TSI | Toscani in Italia | EUR |
| CHB | Han Chinese in Beijing | EAS |
| JPT | Japanese in Tokyo | EAS |
| CHS | Southern Han Chinese | EAS |
| MXL | Mexican Ancestry in LA | AMR |
| PUR | Puerto Rican in Puerto Rico | AMR |
| GIH | Gujarati Indian in Houston | SAS |
| PJL | Punjabi from Lahore | SAS |

---

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Strong** | AF difference > 0.2 across superpopulations, GWAS p < 5e-8, replicated in multiple cohorts | rs7903146 (TCF7L2) with AF = 0.30 EUR vs 0.05 EAS, GWAS p = 1e-40 |
| **Moderate** | AF difference 0.05-0.2, GWAS p < 5e-8 in one ancestry, nominal in others | Variant with AF = 0.15 AFR vs 0.08 EUR, GWAS p < 5e-8 in EUR only |
| **Weak** | AF difference < 0.05, GWAS p < 5e-8 but single study, no cross-ancestry replication | Common variant with similar AF across populations, significant in one cohort |
| **Population-specific** | Variant common (AF > 0.01) in one superpopulation, rare (AF < 0.01) in others | Sickle cell variant (rs334) AF ~0.10 in AFR, < 0.001 elsewhere |

### Interpretation Guidance

- **Allele frequency interpretation by ancestry**: Allele frequencies vary across superpopulations (AFR, AMR, EAS, EUR, SAS) due to genetic drift, selection, and demographic history. AFR populations have the highest genetic diversity and longest haplotypes broken by recombination. Disease-risk alleles may be common in one ancestry and rare in another, leading to differential genetic risk across populations.
- **Fst significance thresholds**: Fst measures population differentiation (0 = no differentiation, 1 = complete fixation of different alleles). Global Fst for human populations averages ~0.12. Locus-specific Fst > 0.3 suggests strong differentiation (possible selection). Fst > 0.5 is extreme and rare in humans outside known selection targets (e.g., SLC24A5 for skin pigmentation). Compare locus Fst against genome-wide distribution to identify outliers.
- **LD interpretation**: Linkage disequilibrium (LD) patterns differ by ancestry. AFR populations have shorter LD blocks due to older demographic history, requiring denser genotyping for fine-mapping. EUR and EAS populations have longer LD blocks. When a GWAS hit is in LD with multiple variants, the causal variant is more likely to be resolved in AFR-ancestry data. Report r-squared values: r2 > 0.8 = strong LD, 0.2-0.8 = moderate, < 0.2 = weak.
- **Population stratification**: Uncontrolled population structure in GWAS inflates false positives. The 1000 Genomes superpopulation labels provide a framework for stratified analysis. Mixed-ancestry samples (e.g., AMR) require local ancestry deconvolution for accurate interpretation.
- **Sample size context**: 1000 Genomes has ~2500 samples across 26 populations. Population-specific allele frequencies have limited precision for smaller populations (N < 100). For rare variants (AF < 0.01), larger resources like gnomAD provide more reliable estimates.

### Synthesis Questions

1. Does the allele frequency of the variant of interest differ meaningfully (> 5%) across superpopulations, and could this explain differential disease prevalence or GWAS effect sizes?
2. Is the GWAS association replicated across ancestries, or is it population-specific, potentially due to LD structure differences or population-specific selection?
3. For fine-mapping, does the LD pattern in AFR populations narrow the association signal compared to EUR, helping identify the likely causal variant?
4. Are the population labels and sample sizes in the 1000 Genomes dataset adequate for the analysis, or is the target population underrepresented?
5. Could population stratification (uncontrolled ancestry differences between cases and controls) explain the observed association, rather than a true genetic effect?

---

## Tool Parameter Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| IGSR_search_populations | superpopulation, query, limit | superpopulation: AFR/AMR/EAS/EUR/SAS |
| IGSR_search_samples | population, data_collection, sample_name, limit | population = population code (e.g. YRI) |
| IGSR_list_data_collections | limit | 18 collections total |
| gwas_search_associations | trait, limit | free-text trait search |
| gwas_get_variants_for_trait | trait, limit | trait = EFO ID |
| gwas_get_snps_for_gene | gene_symbol, limit | returns mapped SNPs |
