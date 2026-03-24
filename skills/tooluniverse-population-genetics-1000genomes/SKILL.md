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

## Tool Parameter Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| IGSR_search_populations | superpopulation, query, limit | superpopulation: AFR/AMR/EAS/EUR/SAS |
| IGSR_search_samples | population, data_collection, sample_name, limit | population = population code (e.g. YRI) |
| IGSR_list_data_collections | limit | 18 collections total |
| gwas_search_associations | trait, limit | free-text trait search |
| gwas_get_variants_for_trait | trait, limit | trait = EFO ID |
| gwas_get_snps_for_gene | gene_symbol, limit | returns mapped SNPs |
