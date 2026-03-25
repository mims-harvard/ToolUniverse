---
name: tooluniverse-regulatory-variant-analysis
description: Regulatory variant interpretation -- GWAS association lookup, eQTL analysis, chromatin state annotation, regulatory element overlap, and trait ontology resolution. Connects GWAS Catalog, GTEx, ENCODE, RegulomeDB, OpenTargets, OLS ontology, and Ensembl regulatory features. Use when users ask about non-coding variants, GWAS hits, eQTLs, regulatory elements, enhancer/promoter variants, or trait-associated SNPs.
---

# Regulatory Variant Analysis Skill

Systematic regulatory variant interpretation: discover trait associations from GWAS, map eQTL effects, annotate chromatin context, assess regulatory element overlap, and produce evidence-graded functional impact predictions for non-coding variants.

## When to Use

- "What GWAS associations exist for rs12913832?"
- "Find eQTLs for the APOE locus in brain tissue"
- "What regulatory elements overlap this variant region?"
- "Which SNPs are associated with type 2 diabetes from GWAS?"
- "Is this intronic variant in an active enhancer?"
- "What is the RegulomeDB score for rs429358?"
- "Find ENCODE histone marks at the BRCA1 promoter region"
- "Map trait ontology terms for 'blood pressure' to EFO IDs"

**NOT for** (use other skills instead):
- Coding variant pathogenicity -> Use `tooluniverse-variant-interpretation`
- Full clinical variant classification (ACMG) -> Use `tooluniverse-variant-interpretation`
- Gene-disease associations (not variant-specific) -> Use `tooluniverse-gene-disease-association`
- Pharmacogenomic variant annotation -> Use `tooluniverse-pharmacogenomics`
- Epigenomics data processing (BED/narrowPeak files) -> Use `tooluniverse-epigenomics`

---

## Workflow Overview

```
Input (rsID, genomic coordinates, trait/disease, gene)
  |
  v
Phase 0: Variant/Trait Resolution
  Resolve rsIDs, map trait names to EFO/MONDO IDs via OLS
  |
  v
Phase 1: GWAS Association Lookup
  GWAS Catalog associations, p-values, effect sizes, study metadata
  |
  v
Phase 2: eQTL Analysis
  GTEx tissue-specific eQTLs, target gene identification
  |
  v
Phase 3: Regulatory Element Annotation
  ENCODE histone marks, RegulomeDB scores, chromatin state
  |
  v
Phase 4: OpenTargets GWAS Integration
  OpenTargets GWAS study aggregation, locus-to-gene mapping
  |
  v
Phase 5: Functional Impact Synthesis
  Integrate all evidence, assign regulatory impact scores
  |
  v
Phase 6: Report
  Evidence-graded regulatory variant report
```

---

## Phase 0: Variant/Trait Resolution

### Resolve Trait Names to Ontology IDs

**ols_search_terms**: `query` (string REQUIRED), `ontology` (string, optional), `exact` (bool), `rows` (int).
- Search OLS (Ontology Lookup Service) for trait/disease terms.
- Returns ontology term IDs (EFO, MONDO, HP, etc.) needed by downstream tools.
- Tip: Use `ontology="efo"` to restrict to Experimental Factor Ontology for GWAS traits.

```python
# Resolve "type 2 diabetes" to EFO ID
ols_result = tu.tools.ols_search_terms(query="type 2 diabetes", ontology="efo")
# Returns: {status, data: [{iri, label, short_form, ontology_name}]}
# Extract EFO ID: e.g., "EFO_0001360" (but for OpenTargets, MONDO_0005148 is preferred)
```

**ols_get_term_info**: `term_id` (string REQUIRED, e.g., "EFO_0001360"), `ontology` (string, optional -- inferred from CURIE prefix).
- Get details for a specific ontology term.
- NOTE: `ontology` param is now optional; OLS infers from CURIE prefix (e.g., "HP:0001234" -> hp).

### Resolve Variant IDs

**EnsemblVEP_annotate_rsid**: `variant_id` (string REQUIRED, e.g., "rs429358").
- Returns VEP annotation with consequence, gene, SIFT/PolyPhen scores.
- NOTE: Param is `variant_id`, NOT `rsid`.
- Response format is variable: can be `[{...}]`, `{data, metadata}`, or `{error}`. Handle all three.

**MyVariant_query_variants**: `variant_id` (string), `fields` (string).
- Aggregated annotations from ClinVar, dbSNP, gnomAD, CADD.

---

## Phase 1: GWAS Association Lookup

### Search by Trait/Disease

**gwas_search_associations**: Primary GWAS Catalog search tool with flexible filtering.
- `disease_trait` (string) -- free-text disease/trait name
- `efo_id` (string) -- EFO term ID (e.g., "EFO_0001645"); recommended for reliable filtering
- `efo_trait` (string) -- exact EFO trait label
- `rs_id` (string) -- search by specific rsID
- `p_value` or `p_value_threshold` (float) -- maximum p-value filter (e.g., 5e-8)
- `size` (int) -- number of results
- `sort` (string) -- sort field (e.g., "p_value")
- `direction` (string) -- "asc" or "desc"

```python
# Search GWAS associations for type 2 diabetes
gwas = tu.tools.gwas_search_associations(
    disease_trait="type 2 diabetes",
    p_value=5e-8,  # genome-wide significance
    size=20
)
# Returns: {data: [{...association data...}], metadata: {...}}

# Search by specific rsID
gwas_snp = tu.tools.gwas_search_associations(rs_id="rs429358", size=10)
```

### Search Variants by Trait

**gwas_get_variants_for_trait**: Find all SNPs linked to a trait.
- `disease_trait` (string) -- free-text trait name
- `trait` (string) -- alias for disease_trait
- `efo_id` (string) -- EFO term ID (preferred for precision)
- `efo_trait` (string) -- exact EFO label
- `size` or `limit` (int) -- results per page
- `page` (int) -- pagination

```python
# Get all genome-wide significant variants for breast cancer
variants = tu.tools.gwas_get_variants_for_trait(
    disease_trait="breast cancer",
    size=50
)
# Returns: {data: [{rsId, chromosomeName, chromosomePosition, ...}], metadata: {...}}
```

### Search SNPs for a Gene

**gwas_get_snps_for_gene**: `gene_symbol` (string REQUIRED).
- Find GWAS-cataloged SNPs mapped to a specific gene.

**gwas_search_snps**: `rs_id` (string REQUIRED).
- Get detailed SNP information from GWAS Catalog.

### Key GWAS Metrics

| Metric | Interpretation |
|--------|---------------|
| p-value < 5e-8 | Genome-wide significance threshold |
| p-value 5e-8 to 1e-5 | Suggestive association |
| OR (Odds Ratio) > 1 | Risk allele |
| OR < 1 | Protective allele |
| Beta > 0 | Trait-increasing allele (quantitative) |

---

## Phase 2: eQTL Analysis

### GTEx eQTLs

**GTEx_query_eqtl**: `gene_symbol` (string) or `ensembl_gene_id` (string), `page` (int, default 1), `size` (int, default 10).
- Query tissue-specific eQTL associations for a gene.
- Returns SNP-gene associations with effect size and p-value per tissue.
- NOTE: Accepts gene symbols directly (auto-resolves to GENCODE ID).
- IMPORTANT: GTEx API uses v8 data (gtex_v10 returns empty for some endpoints).

```python
# Find eQTLs for APOE
eqtls = tu.tools.GTEx_query_eqtl(gene_symbol="APOE", size=50)
# Returns: {status, data: [{snpId, geneSymbol, tissueSiteDetailId, pValue, nes}]}
```

### GTEx Expression Context

**GTEx_get_median_gene_expression**: `gene_symbol` (string) or `ensembl_gene_id` (string).
- Median gene expression across GTEx tissues.
- Useful for identifying tissues where eQTL effects are most relevant.

**GTEx_get_expression_summary**: `gene_symbol` (string) or `ensembl_gene_id` (string).
- Summary expression statistics.

### eQTL Interpretation

| NES (Normalized Effect Size) | Meaning |
|------------------------------|---------|
| NES > 0 | Alternative allele increases expression |
| NES < 0 | Alternative allele decreases expression |
| abs(NES) > 0.5 | Strong effect on expression |
| Tissue-specific eQTL | Effect in 1-2 tissues -> cell-type-specific regulation |
| Ubiquitous eQTL | Effect across many tissues -> core regulatory element |

---

## Phase 3: Regulatory Element Annotation

### RegulomeDB

**RegulomeDB_query_variant**: `rsid` (string REQUIRED, e.g., "rs4994").
- Returns regulatory annotations: TF binding, chromatin accessibility, eQTL overlap.
- Uses GRCh38 genome build (not hg19).
- NOTE: Test with real rsIDs (rs4994, rs429358); rs123456 does not exist.

```python
regulome = tu.tools.RegulomeDB_query_variant(rsid="rs429358")
# Returns: {status, data: {score, features: [...]}, url}
```

**RegulomeDB Scoring**:

| Score | Category | Evidence |
|-------|----------|----------|
| 1a | Likely regulatory | eQTL + TF binding + matched TF motif + DNase |
| 1b | Likely regulatory | eQTL + TF binding + any motif + DNase |
| 1c-1f | Likely regulatory | eQTL + varying chromatin evidence |
| 2a-2c | Likely regulatory | TF binding + motif/DNase (no eQTL) |
| 3a-3b | Less likely | TF binding or motif only |
| 4-6 | Minimal evidence | DNase only or no data |

### ENCODE Histone ChIP-seq

**ENCODE_search_histone_experiments**: Search for histone modification data.
- `histone_mark` or `target` (string) -- e.g., "H3K4me3", "H3K27ac", "H3K27me3"
- `biosample_term_name` or `biosample` (string) -- tissue/cell line name (NOT disease name)
- `organism` (string, default "Homo sapiens")
- `limit` (int, default 25)

```python
# Find H3K27ac (active enhancer) experiments in liver
encode = tu.tools.ENCODE_search_histone_experiments(
    histone_mark="H3K27ac",
    biosample_term_name="liver",
    limit=10
)
# Returns: experiment accessions, files, biosample details
```

**Key Histone Marks for Regulatory Interpretation**:

| Mark | Indicates |
|------|-----------|
| H3K4me3 | Active promoter |
| H3K4me1 | Enhancer (active or poised) |
| H3K27ac | Active enhancer / active promoter |
| H3K27me3 | Polycomb-repressed region |
| H3K36me3 | Transcribed gene body |
| H3K9me3 | Heterochromatin / silenced region |

### ENCODE TF ChIP-seq

**ENCODE_search_experiments**: `assay_title` (string), `target` (string), `organism` (string), `status` (string), `limit` (int).
- For TF binding data, use `assay_title="TF ChIP-seq"` (NOT just "ChIP-seq").
- `target` should be TF name (e.g., "CTCF", "TP53").

---

## Phase 4: OpenTargets GWAS Integration

### GWAS Studies by Disease

**OpenTargets_search_gwas_studies_by_disease**: `diseaseIds` (array of strings REQUIRED), `enableIndirect` (bool, default true), `size` (int, default 10), `index` (int, default 0).
- Search GWAS studies from OpenTargets for specific disease ontology IDs.
- Uses MONDO IDs (e.g., "MONDO_0005148" for type 2 diabetes).
- NOTE: MONDO_0005148 for T2D (NOT EFO_0001360, which returns None in OpenTargets).

```python
# Find GWAS studies for type 2 diabetes
ot_gwas = tu.tools.OpenTargets_search_gwas_studies_by_disease(
    diseaseIds=["MONDO_0005148"],
    size=20
)
# Returns: GWAS study metadata, locus-to-gene mappings
```

### ID Resolution for OpenTargets

Use `ols_search_terms` or `OpenTargets_get_disease_id_description_by_name` to find MONDO/EFO IDs:

```python
# Search OpenTargets for disease ID
ot_search = tu.tools.OpenTargets_multi_entity_search(queryString="type 2 diabetes")
# Returns entity IDs (MONDO, EFO format)
```

---

## Phase 5: Functional Impact Synthesis

Integrate all evidence to assess regulatory variant impact.

### Scoring Framework

| Evidence Type | Weight | Source |
|---------------|--------|--------|
| GWAS significance (p < 5e-8) | High | gwas_search_associations |
| eQTL with strong NES | High | GTEx_query_eqtl |
| RegulomeDB score 1a-2a | High | RegulomeDB_query_variant |
| Active enhancer overlap (H3K27ac) | Medium | ENCODE_search_histone_experiments |
| TF binding site disruption | Medium | ENCODE TF ChIP-seq / RegulomeDB |
| Promoter mark (H3K4me3) | Medium | ENCODE |
| OpenTargets GWAS study support | Medium | OpenTargets_search_gwas_studies_by_disease |
| Literature evidence | Low-High | PubMed/EuropePMC |

### Regulatory Impact Classification

| Level | Criteria |
|-------|----------|
| **High Impact** | GWAS significant + eQTL + RegulomeDB <= 2 + active chromatin |
| **Moderate Impact** | 2-3 lines of regulatory evidence |
| **Low Impact** | Single evidence line or RegulomeDB > 3 |
| **No Evidence** | No regulatory annotations found |

---

## Tool Parameter Quick Reference

| Tool | Key Params | Notes |
|------|-----------|-------|
| `gwas_search_associations` | `disease_trait`, `efo_id`, `rs_id`, `p_value`, `size` | Primary GWAS search |
| `gwas_get_variants_for_trait` | `disease_trait` or `efo_id`, `size` | All variants for a trait |
| `gwas_get_snps_for_gene` | `gene_symbol` | SNPs mapped to gene |
| `gwas_search_snps` | `rs_id` | Detailed SNP info |
| `GTEx_query_eqtl` | `gene_symbol` or `ensembl_gene_id`, `size` | Tissue-specific eQTLs |
| `GTEx_get_median_gene_expression` | `gene_symbol` or `ensembl_gene_id` | Expression across tissues |
| `GTEx_get_expression_summary` | `gene_symbol` or `ensembl_gene_id` | Expression statistics |
| `RegulomeDB_query_variant` | `rsid` | Regulatory annotation score |
| `ENCODE_search_histone_experiments` | `histone_mark`, `biosample_term_name`, `limit` | Histone ChIP-seq data |
| `ENCODE_search_experiments` | `assay_title`, `target`, `organism`, `limit` | General ENCODE search |
| `OpenTargets_search_gwas_studies_by_disease` | `diseaseIds` (array), `size` | GWAS studies from OT |
| `OpenTargets_get_disease_id_description_by_name` | `queryString` | Disease/gene ID resolution |
| `ols_search_terms` | `query`, `ontology`, `exact`, `rows` | Ontology term search |
| `ols_get_term_info` | `term_id` | Ontology term details (ontology inferred from CURIE) |
| `EnsemblVEP_annotate_rsid` | `variant_id` (NOT rsid) | VEP annotation for rsID |
| `MyVariant_query_variants` | `variant_id`, `fields` | Aggregated variant annotations |

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Using EFO_0001360 for T2D in OpenTargets | Use MONDO_0005148 (EFO returns None) |
| Passing disease name to ENCODE biosample | ENCODE biosamples are tissues/cell lines, NOT diseases |
| Using `assay_title="ChIP-seq"` for TF binding | Must be `"TF ChIP-seq"` specifically |
| Using RegulomeDB with hg19 assembly | RegulomeDB uses GRCh38 (genome=GRCh38) |
| Using `rsid` param for EnsemblVEP | Param is `variant_id`, not `rsid` |
| Passing `queryString` as `query` to OpenTargets | Param is `queryString` (NOT `query`) |
| Using `gwas_get_associations_for_trait` | BROKEN tool; use `gwas_search_associations` instead |
| Not specifying `ontology` in ols_search_terms | Without it, results span all ontologies; use "efo" for GWAS traits |

---

## Fallback Strategies

- **GWAS Catalog returns empty** -> Try broader trait term, or use efo_id instead of free-text disease_trait
- **GTEx eQTL empty for gene** -> Check gene symbol is correct; try Ensembl ID; increase page size
- **RegulomeDB returns no data** -> Variant may not have regulatory annotations; check ENCODE directly
- **OpenTargets GWAS returns None** -> Verify MONDO/EFO ID format; try OpenTargets_multi_entity_search first
- **OLS search returns wrong ontology** -> Restrict with `ontology="efo"` or `ontology="mondo"`
- **ENCODE tissue not found** -> ENCODE uses specific biosample names; check ENCODE portal for valid names
- **Need chromatin context without ENCODE** -> Use RegulomeDB (aggregates ENCODE + Roadmap + other data)

---

## Example Workflows

### Workflow 1: GWAS Variant Functional Annotation (rs429358 / APOE)

```
Step 1: gwas_search_associations(rs_id="rs429358", size=20)
  -> Find all trait associations: Alzheimer's disease, LDL cholesterol, etc.

Step 2: GTEx_query_eqtl(gene_symbol="APOE", size=50)
  -> Check if rs429358 is an eQTL for APOE in brain tissues

Step 3: RegulomeDB_query_variant(rsid="rs429358")
  -> Get regulatory score and annotations

Step 4: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name="brain")
  -> Check active enhancer marks near variant

Step 5: Synthesize: GWAS significance + eQTL effect + regulatory score -> impact classification
```

### Workflow 2: Trait-to-Variant Discovery (Type 2 Diabetes)

```
Step 1: ols_search_terms(query="type 2 diabetes", ontology="efo")
  -> Get EFO ID (and MONDO_0005148 for OpenTargets)

Step 2: gwas_get_variants_for_trait(disease_trait="type 2 diabetes", size=50)
  -> Get top associated variants with p-values

Step 3: OpenTargets_search_gwas_studies_by_disease(diseaseIds=["MONDO_0005148"], size=20)
  -> Cross-reference with OpenTargets locus-to-gene mapping

Step 4: For top variants:
  RegulomeDB_query_variant(rsid=variant_rsid) -> regulatory score
  GTEx_query_eqtl(gene_symbol=nearest_gene) -> eQTL evidence

Step 5: Rank variants by regulatory evidence + GWAS significance
```

### Workflow 3: Gene Regulatory Landscape (BRCA1 Locus)

```
Step 1: gwas_get_snps_for_gene(gene_symbol="BRCA1")
  -> Find all GWAS SNPs mapped to BRCA1

Step 2: GTEx_query_eqtl(gene_symbol="BRCA1", size=100)
  -> All eQTLs regulating BRCA1 expression

Step 3: ENCODE_search_histone_experiments(histone_mark="H3K4me3", biosample_term_name="breast epithelium")
  -> Promoter marks at BRCA1 locus

Step 4: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name="breast epithelium")
  -> Active enhancer marks

Step 5: For each GWAS SNP:
  RegulomeDB_query_variant(rsid=snp_rsid) -> regulatory annotation

Step 6: Map: SNP positions vs enhancer/promoter marks vs eQTL targets
```

### Workflow 4: Non-Coding Variant Assessment (Intronic/UTR Variant)

```
Step 1: EnsemblVEP_annotate_rsid(variant_id="rs12345678")
  -> Confirm non-coding consequence, identify nearest gene

Step 2: RegulomeDB_query_variant(rsid="rs12345678")
  -> Regulatory score (1a = strong evidence)

Step 3: gwas_search_associations(rs_id="rs12345678")
  -> Any GWAS associations?

Step 4: GTEx_query_eqtl(gene_symbol=nearest_gene)
  -> Is this variant an eQTL?

Step 5: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name=relevant_tissue)
  -> Active chromatin context?

Step 6: Classify: RegulomeDB <= 2 + eQTL + chromatin = "High Impact Regulatory Variant"
```

---

## Evidence Grading

| Tier | Criteria | Sources |
|------|----------|---------|
| **T1** | GWAS genome-wide significant (p < 5e-8) + eQTL + regulatory annotation | GWAS Catalog + GTEx + RegulomeDB |
| **T2** | GWAS suggestive + eQTL or regulatory annotation | GWAS Catalog + GTEx/RegulomeDB |
| **T3** | Single line of regulatory evidence | RegulomeDB or ENCODE or GTEx alone |
| **T4** | Computational prediction only | VEP consequence, no functional data |

---

## Limitations

- GWAS Catalog covers published GWAS only; unpublished studies not included.
- GTEx eQTL data is from v8 (gtex_v10 endpoints may return empty).
- RegulomeDB annotations depend on available ENCODE/Roadmap data for the cell type.
- ENCODE histone experiments may not cover all tissues; check available biosamples.
- OpenTargets GWAS uses MONDO/EFO IDs; some traits may not have MONDO mappings.
- eQTL analysis identifies correlation, not causation; fine-mapping needed for causal variants.
- RegulomeDB scores are heuristic; score 1a does not guarantee functional impact.
- GWAS associations are population-level; individual variant effects depend on genetic background.
