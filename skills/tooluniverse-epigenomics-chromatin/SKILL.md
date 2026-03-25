---
name: tooluniverse-epigenomics-chromatin
description: >
  Epigenomics and chromatin accessibility research -- histone modification ChIP-seq data from ENCODE,
  CTCF binding and chromatin architecture, eQTL analysis connecting variants to gene regulation,
  gene expression correlation with chromatin marks, regulatory element identification via SCREEN/UCSC cCREs,
  transcription factor binding motifs via JASPAR/ReMap, and variant regulatory scoring via RegulomeDB.
  Use when users ask about histone marks, chromatin states, CTCF binding, eQTLs, cis-regulatory elements,
  enhancer/promoter annotation, or chromatin accessibility in specific cell types.
triggers:
  - keywords: [histone, ChIP-seq, chromatin, ENCODE, eQTL, CTCF, enhancer, promoter, cCRE, H3K27ac, H3K4me3, H3K4me1, chromatin state, ATAC-seq, regulatory element, RegulomeDB]
  - patterns: ["histone modification", "chromatin accessibility", "chromatin architecture", "gene regulation", "regulatory variant", "expression QTL", "cis-regulatory"]
---

# Epigenomics and Chromatin Accessibility Research

Systematic chromatin and epigenomics analysis: query histone modification ChIP-seq experiments from ENCODE,
identify cis-regulatory elements (cCREs) via SCREEN/UCSC, analyze eQTLs connecting variants to gene expression
via GTEx and EBI eQTL Catalogue, characterize CTCF binding and chromatin architecture, and annotate
regulatory variants with RegulomeDB scoring.

## When to Use

- "What histone modification data is available for GM12878 in ENCODE?"
- "Find H3K27ac ChIP-seq experiments for liver cells"
- "What are the eQTLs for BRCA1 in breast tissue?"
- "Show CTCF binding sites near the MYC locus"
- "What cis-regulatory elements exist in the TP53 promoter region?"
- "Score this variant for regulatory potential using RegulomeDB"
- "What chromatin states are annotated for K562?"
- "Find ATAC-seq experiments for T cells in ENCODE"
- "Which tissues have significant eQTLs for gene X?"
- "What transcription factor binding motifs overlap this region?"

## NOT for (use other skills instead)

- Methylation array data processing (CpG beta values, differential methylation) -> Use `tooluniverse-epigenomics`
- ChIP-seq peak file analysis from user-provided BED files -> Use `tooluniverse-epigenomics`
- RNA-seq differential expression -> Use `tooluniverse-rnaseq-deseq2`
- GWAS variant interpretation -> Use `tooluniverse-gwas-snp-interpretation`
- Variant functional annotation from VCF -> Use `tooluniverse-variant-analysis`

---

## Workflow Overview

```
Input (gene / region / variant / cell type / histone mark)
  |
  v
Phase 0: Disambiguation (resolve gene symbols, genomic coordinates, cell types)
  |
  v
Phase 1: Histone Modification & ChIP-seq (ENCODE experiments, chromatin marks)
  |
  v
Phase 2: Chromatin Accessibility & Architecture (ATAC-seq, chromatin states, CTCF)
  |
  v
Phase 3: Regulatory Element Identification (SCREEN cCREs, UCSC cCREs, ENCODE annotations)
  |
  v
Phase 4: eQTL Analysis (GTEx single/multi-tissue eQTLs, EBI eQTL Catalogue)
  |
  v
Phase 5: Gene Expression Context (GTEx tissue expression, expression-chromatin correlation)
  |
  v
Phase 6: Transcription Factor Binding (JASPAR motifs, ReMap TF ChIP-seq, STRING annotations)
  |
  v
Phase 7: Variant Regulatory Scoring (RegulomeDB scores, tissue-specific regulatory impact)
  |
  v
Phase 8: Integration & Report (combine all evidence layers)
```

---

## Phase 0: Disambiguation

Resolve user input to canonical identifiers.

**MyGene_query_genes**: `query` (string). Returns gene Ensembl IDs, symbols, genomic coordinates.
- Use to convert gene symbols to Ensembl IDs and get chr/start/end coordinates.
- IMPORTANT: Filter results by `symbol == '<GENE>'` (first hit may not match).

**ensembl_lookup_gene**: `gene_id` (string, e.g., "ENSG00000141510"), `species` (string, REQUIRED, use "homo_sapiens"). Returns gene coordinates, biotype, description.

### Common Identifiers Needed

| Data Type | Format | Example |
|-----------|--------|---------|
| Gene (GTEx) | Versioned GENCODE | ENSG00000012048.20 |
| Gene (SCREEN/ENCODE) | Gene symbol | BRCA1 |
| Region (UCSC cCREs) | chr:start-end | chr17:7668421-7687490 |
| Variant (RegulomeDB) | rsID | rs4994 |
| Variant (GTEx eQTL) | chr_pos_ref_alt_b38 | chr17_43705621_T_C_b38 |
| Tissue (GTEx) | tissueSiteDetailId | Breast_Mammary_Tissue |
| Cell type (ENCODE) | biosample name | GM12878, K562, HepG2 |

---

## Phase 1: Histone Modification & ChIP-seq Data

### Search histone ChIP-seq experiments

**ENCODE_search_histone_experiments**: `target` (string, e.g., "H3K27ac"), `cell_type` (string, e.g., "GM12878"), `tissue` (alias for `cell_type` -- e.g., "liver"), `biosample_term_name` (canonical ENCODE ontology name, most explicit), `biosample` (alias for `biosample_term_name`), `limit` (int, default 25).
Returns `{status: "success", data: {total, experiments: [{accession, histone_mark, biosample_summary, status, lab, date_released}]}, metadata: {source, assay, histone_mark_filter, organism}}`.

**IMPORTANT -- ENCODE anatomy term mapping**: Common anatomy terms often need ENCODE-specific ontology names. For example:
- "breast" -> use "breast epithelium" or "mammary epithelial cell"
- "brain" -> use "brain" (works) or specific regions like "frontal cortex"
- "liver" -> use "liver" (works directly)
- "kidney" -> use "kidney" (works directly)
- "lung" -> use "lung" (works directly)
If a tissue search returns 0 results, try appending "tissue", "epithelium", or "cell" to the anatomy term.

```python
# Example: Find H3K27ac experiments in GM12878
result = tu.tools.ENCODE_search_histone_experiments(target="H3K27ac", cell_type="GM12878", limit=5)
# result["data"]["experiments"][0]["accession"] -> "ENCSR000AKC"
```

### ENCODE RNA-seq experiments

**ENCODE_search_rnaseq_experiments**: `assay_type` (string, default `"total RNA-seq"`), `biosample` (string/null, e.g. `"liver"`), `limit` (int).
Available `assay_type` values: `"total RNA-seq"`, `"polyA plus RNA-seq"`, `"small RNA-seq"`, `"microRNA-seq"`.

```python
# Search total RNA-seq for liver
result = tu.tools.ENCODE_search_rnaseq_experiments(assay_type="total RNA-seq", biosample="liver", limit=5)
```

**IMPORTANT -- polyA plus RNA-seq fallback**: Some biosamples have few or zero `total RNA-seq` experiments. If a search returns 0 results, retry with `assay_type="polyA plus RNA-seq"`:
```python
result = tu.tools.ENCODE_search_rnaseq_experiments(assay_type="total RNA-seq", biosample="K562", limit=5)
if result["data"]["total"] == 0:
    result = tu.tools.ENCODE_search_rnaseq_experiments(assay_type="polyA plus RNA-seq", biosample="K562", limit=5)
```

### Common histone marks and their meaning

| Mark | Function | Color (ENCODE) |
|------|----------|----------------|
| H3K27ac | Active enhancers/promoters | - |
| H3K4me3 | Active promoters | Red |
| H3K4me1 | Enhancers (poised or active) | - |
| H3K27me3 | Polycomb repression | - |
| H3K36me3 | Transcribed gene bodies | - |
| H3K9me3 | Heterochromatin | - |

### Get GEO ChIP-seq datasets

**GEO_search_chipseq_datasets**: Search GEO for ChIP-seq datasets.
- Complementary to ENCODE for older or non-ENCODE datasets.

### GEO RNA-seq datasets

**GEO_search_rnaseq_datasets**: `query` (string, free-text keyword), `organism` (string, default "Homo sapiens"), `limit` (int, also `max_results` accepted).
Returns GEO Series accessions (GSExxxxxx) with titles, summaries, organism, sample counts, and publication dates.

```json
{"query": "breast cancer", "limit": 5}
```

NOTE: Both `limit` and `max_results` are accepted as parameter names.

### GEO ATAC-seq datasets

**GEO_search_atacseq_datasets**: `query` (string), `organism` (string, default "Homo sapiens"), `limit` (int, also `max_results` accepted).
Returns GEO ATAC-seq datasets. Automatically adds "ATAC-seq" to the search term.

```json
{"query": "T cells", "limit": 5}
```

NOTE: Both `limit` and `max_results` are accepted as parameter names.

---

## Phase 2: Chromatin Accessibility & Architecture

### ATAC-seq experiments

**ENCODE_search_chromatin_accessibility**: `cell_type` (string, optional), `limit` (int, default 10).
Returns `{status: "success", data: {total, experiments: [{accession, assay_title, biosample_summary, status, lab}]}}`.

```python
# Find ATAC-seq experiments for GM12878
result = tu.tools.ENCODE_search_chromatin_accessibility(cell_type="GM12878", limit=5)
```

### Chromatin state annotations

**ENCODE_get_chromatin_state**: `cell_type` (string, optional), `limit` (int, default 10).
Returns ChromHMM 15-state model annotations. `{status: "success", data: {total, annotations: [{accession, annotation_type, description, biosample_summary, status}]}}`.

ChromHMM 15-state model states:
1. TssA - Active TSS
2. TssAFlnk - Flanking Active TSS
3. TxFlnk - Transcr. at gene 5' and 3'
4. Tx - Strong transcription
5. TxWk - Weak transcription
6. EnhG - Genic enhancers
7. Enh - Enhancers
8. ZNF/Rpts - ZNF genes & repeats
9. Het - Heterochromatin
10. TssBiv - Bivalent/Poised TSS
11. BivFlnk - Flanking Bivalent TSS/Enh
12. EnhBiv - Bivalent Enhancer
13. ReprPC - Repressed PolyComb
14. ReprPCWk - Weak Repressed PolyComb
15. Quies - Quiescent/Low

### CTCF binding (chromatin architecture)

**ReMap_get_transcription_factor_binding**: `gene_name` (string, e.g., "CTCF"), `cell_type` (string, e.g., "GM12878"), `limit` (int, default 10).
Returns ENCODE TF ChIP-seq experiments for the specified TF. `{status: "success", data: {experiments: [{accession, assay_title, target: {genes, label}, biosample_ontology: {term_name, classification}, description, status}]}}`.

```python
# Find CTCF binding experiments in GM12878
result = tu.tools.ReMap_get_transcription_factor_binding(gene_name="CTCF", cell_type="GM12878", limit=5)
# Returns ENCODE TF ChIP-seq experiments targeting CTCF
```

---

## Phase 3: Regulatory Element Identification

### SCREEN cis-regulatory elements

**SCREEN_get_regulatory_elements**: `gene_name` (string), `element_type` (string), `limit` (int).
Returns ENCODE SCREEN cCRE data. Response is JSON-LD format.

Element types:
- `PLS` - Promoter-like signatures
- `pELS` - Proximal enhancer-like signatures
- `dELS` - Distal enhancer-like signatures
- `CTCF-only` - CTCF-bound only
- `DNase-H3K4me3` - DNase with H3K4me3

### UCSC cCREs (region-based query)

**UCSC_get_encode_cCREs**: `chrom` (string, REQUIRED, e.g., "chr17"), `start` (int, REQUIRED), `end` (int, REQUIRED), `genome` (string, default "hg38").
Returns cCREs in the specified region with Z-scores for DNase, H3K4me3, H3K27ac, CTCF signals.

```python
# Get cCREs near TP53 (chr17:7668421-7687490)
result = tu.tools.UCSC_get_encode_cCREs(chrom="chr17", start=7668421, end=7687490, genome="hg38")
```

### ENCODE annotation search

**ENCODE_search_annotations**: `annotation_type` (string), `biosample_term_name` (string/null), `organism` (string, default "Homo sapiens"), `assembly` (string, default "GRCh38"), `limit` (int).
- annotation_type options: "candidate Cis-Regulatory Elements", "chromatin state"

---

## Phase 4: eQTL Analysis

### GTEx single-tissue eQTLs

**GTEx_get_single_tissue_eqtls**: `gene_symbol` (string). Returns significant eQTLs across tissues.
`{status: "success", data: [{snpId, pos, variantId, geneSymbol, pValue, tissueSiteDetailId, gencodeId, nes}]}`.

```python
# Get all significant eQTLs for BRCA1
result = tu.tools.GTEx_get_single_tissue_eqtls(gene_symbol="BRCA1")
# Each entry has tissue, SNP, p-value, normalized effect size (NES)
```

### GTEx eQTL query (specific tissue)

**GTEx_query_eqtl**: `gene_symbol` (string), `tissue` (string, tissueSiteDetailId alias; also `tissue_id`), `page` (int, default 1), `size` (int, records per page, default 10).
Returns `{status: "success", data: {singleTissueEqtl: [...]}}`.
- NOTE: Parameter is `gene_symbol` (NOT `gene_input`). Also accepts `ensembl_gene_id` or `gene_id` (Ensembl ID).
- May return empty array if no significant eQTLs in that tissue.
- **Page is 1-indexed**: `page=1` returns the first page of results (NOT `page=0`).
- Use `size` to control how many eQTLs per page (max 100).

### GTEx multi-tissue eQTL meta-analysis

**GTEx_get_multi_tissue_eqtls**: `operation` (string, use "get_multi_tissue_eqtls"), `gencode_id` (string, REQUIRED, versioned e.g., "ENSG00000012048.20").
Returns per-variant m-values (posterior probability of eQTL effect) across all tissues. Shows tissue-sharing patterns.

```python
# Multi-tissue eQTL meta-analysis for BRCA1
result = tu.tools.GTEx_get_multi_tissue_eqtls(
    operation="get_multi_tissue_eqtls",
    gencode_id="ENSG00000012048.20"
)
# result["data"][0]["tissues"]["Thyroid"]["mValue"] -> 0.0 (no effect), 1.0 (effect present)
```

### GTEx calculate custom eQTL

**GTEx_calculate_eqtl**: `operation` (string, use "calculate_eqtl"), `gencode_id` (string, REQUIRED), `variant_id` (string, REQUIRED, GTEx format chr_pos_ref_alt_b38), `tissue_site_detail_id` (string, REQUIRED).
Dynamically calculates gene-variant association. Works for both significant and non-significant pairs.

### GTEx eGenes (genes with significant eQTLs)

**GTEx_get_eqtl_genes**: `operation` (string, use "get_eqtl_genes"), `tissue_site_detail_id` (array of strings, optional).
Returns genes with at least one significant cis-eQTL in specified tissues.

### EBI eQTL Catalogue

**eQTL_list_datasets**: `size` (int), `quant_method` (string, "ge"/"exon"/"tx"/"txrev"/"leafcutter"), `tissue_id` (string).
Returns available datasets. Use to find dataset IDs first.

**eQTL_get_associations**: `dataset_id` (string, REQUIRED), `size` (int), `gene_id` (string, Ensembl ID), `variant` (string, chr_pos_ref_alt format).
Returns eQTL associations from the EBI eQTL Catalogue (complementary to GTEx).

---

## Phase 5: Gene Expression Context

### GTEx median gene expression

> **Recommended**: Use `GTEx_get_expression_summary` (accepts `gene_symbol` directly and auto-resolves GENCODE versions). `GTEx_get_median_gene_expression` requires `operation` + exact versioned `gencode_id` (e.g., ENSG00000012048.23) and may fail if the version doesn't match the GTEx release.

**GTEx_get_expression_summary**: `gene_symbol` (string). Returns median TPM across all GTEx tissues. Most reliable for gene-symbol-based queries.

```python
# Get tissue expression profile for BRCA1 (recommended approach)
result = tu.tools.GTEx_get_expression_summary(gene_symbol="BRCA1")
tissues = sorted(result["data"], key=lambda x: x["median"], reverse=True)
```

**GTEx_get_median_gene_expression**: Requires `operation="get_median_gene_expression"` + `gencode_id` (versioned, e.g., "ENSG00000012048.23"). Use only when you need GTEx v2 API features like tissue filtering.
`{status: "success", data: {geneExpression: [...]}}`.

### GTEx tissue sites

**GTEx_get_tissue_sites**: No params required. Returns all available GTEx tissue site detail IDs with names.

### GTEx top expressed genes

**GTEx_get_top_expressed_genes**: Returns top expressed genes per tissue. Useful for tissue-specific analysis.

---

## Phase 6: Transcription Factor Binding

### JASPAR motif search

**jaspar_search_matrices**: `search` (string, free text), `name` (string, TF name), `collection` (string, e.g., "CORE"), `tax_group` (string, e.g., "vertebrates"), `species` (string, NCBI taxid e.g., "9606"), `page` (int), `page_size` (int).
Returns `{count, next, previous, results: [{matrix_id, name, collection, tax_group, species, ...}]}`.

```python
# Find CTCF binding motif profiles
result = tu.tools.jaspar_search_matrices(name="CTCF", collection="CORE", page_size=5)
```

### JASPAR matrix details

**jaspar_get_matrix**: Get detailed position frequency matrix for a JASPAR matrix ID.

### ReMap TF binding experiments

**ReMap_get_transcription_factor_binding**: `gene_name` (string, TF name), `cell_type` (string), `limit` (int).
Returns ENCODE TF ChIP-seq experiments. Use for CTCF, FOXA1, TP53, etc.

### STRING functional annotations

**STRING_get_functional_annotations**: `identifiers` (string, gene name or STRING ID), `species` (int, default 9606), `category` (string, e.g., "Process", "Function", "Component", "KEGG").
Returns comprehensive annotations from GO, KEGG, Reactome, InterPro, Pfam, HPO.

---

## Phase 7: Variant Regulatory Scoring

### RegulomeDB variant scoring

**RegulomeDB_query_variant**: `rsid` (string, e.g., "rs4994").
Returns `{status: "success", data: {rsid, assembly, query_coordinates, regulome_score: {probability, ranking, tissue_specific_scores}}}`.

```python
# Score variant for regulatory potential
result = tu.tools.RegulomeDB_query_variant(rsid="rs4994")
score = result["data"]["regulome_score"]
# ranking: "1a" (most regulatory) to "7" (least)
# probability: higher = more likely functional
# tissue_specific_scores: per-tissue regulatory probability
```

### RegulomeDB Score Interpretation

| Score | Meaning |
|-------|---------|
| 1a | eQTL + TF binding + TF motif + DNase + DNase footprint |
| 1b | eQTL + TF binding + any motif |
| 1c | eQTL + TF binding |
| 1d | eQTL + any motif |
| 1e | eQTL + DNase |
| 1f | eQTL only |
| 2a | TF binding + matched TF motif + DNase + DNase footprint |
| 2b | TF binding + any motif + DNase + DNase footprint |
| 2c | TF binding + matched TF motif + DNase |
| 3a | TF binding + any motif + DNase |
| 3b | TF binding + matched TF motif |
| 4-7 | Decreasing evidence |

---

## Phase 8: Integration & Report

Combine evidence across all phases to build a comprehensive chromatin/regulatory picture.

### Evidence Grading

- **T1 (Direct experimental)**: ENCODE ChIP-seq experiments, GTEx eQTL with p < 5e-8
- **T2 (Strong computational)**: RegulomeDB score <= 2, SCREEN cCRE classification, ChromHMM state
- **T3 (Moderate)**: eQTL p < 0.05, JASPAR motif match, multi-tissue m-value > 0.5
- **T4 (Annotation-based)**: STRING annotations, GO terms, literature references

### Report Template

```
## Epigenomics & Chromatin Report: [Gene/Region/Variant]

### 1. Histone Modifications
- Available ChIP-seq experiments: [list from ENCODE]
- Key marks: [H3K27ac, H3K4me3, etc.]

### 2. Chromatin Accessibility
- ATAC-seq data: [available experiments]
- Chromatin states: [ChromHMM annotations]
- CTCF binding: [experiments in region]

### 3. Regulatory Elements
- cCREs in region: [PLS, pELS, dELS counts]
- Key regulatory elements: [accessions, types]

### 4. eQTL Evidence
- Significant eQTLs: [count, top variants]
- Tissue specificity: [which tissues, m-values]
- Effect sizes: [NES values]

### 5. Expression Context
- Highest expression: [top 5 tissues with TPM]
- Expression-chromatin correlation: [if applicable]

### 6. TF Binding
- Key TFs: [from JASPAR, ReMap]
- Binding motifs: [matrix IDs]

### 7. Variant Regulatory Scores
- RegulomeDB: [score, probability]
- Tissue-specific regulation: [top tissues]

### Evidence Summary
| Evidence Layer | Source | Confidence |
|---|---|---|
| ... | ... | T1/T2/T3/T4 |
```

---

## Common Use Patterns

### Pattern 1: Histone landscape for a cell type

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

cell_type = "GM12878"
marks = ["H3K27ac", "H3K4me3", "H3K4me1", "H3K27me3", "H3K36me3", "H3K9me3"]
for mark in marks:
    result = tu.tools.ENCODE_search_histone_experiments(target=mark, cell_type=cell_type, limit=3)
    count = result["data"]["total"]
    print(f"{mark}: {count} experiments")

# Also get ATAC-seq and chromatin states
atac = tu.tools.ENCODE_search_chromatin_accessibility(cell_type=cell_type, limit=3)
chrom_state = tu.tools.ENCODE_get_chromatin_state(cell_type=cell_type, limit=3)
```

### Pattern 2: eQTL tissue specificity for a gene

```python
# Get all significant eQTLs
eqtls = tu.tools.GTEx_get_single_tissue_eqtls(gene_symbol="BRCA1")

# Count eQTLs per tissue
from collections import Counter
tissue_counts = Counter(e["tissueSiteDetailId"] for e in eqtls["data"])
print("Tissues with eQTLs:", dict(tissue_counts.most_common(10)))

# Get multi-tissue meta-analysis
multi = tu.tools.GTEx_get_multi_tissue_eqtls(
    operation="get_multi_tissue_eqtls",
    gencode_id="ENSG00000012048.20"
)
```

### Pattern 3: Regulatory elements in a genomic region

```python
# Get cCREs in TP53 region
ccres = tu.tools.UCSC_get_encode_cCREs(chrom="chr17", start=7668421, end=7687490, genome="hg38")

# Also search ENCODE annotations
annotations = tu.tools.ENCODE_search_annotations(
    annotation_type="candidate Cis-Regulatory Elements",
    organism="Homo sapiens",
    limit=10
)

# Get CTCF binding in the region
ctcf = tu.tools.ReMap_get_transcription_factor_binding(gene_name="CTCF", cell_type="K562", limit=5)
```

### Pattern 4: Variant regulatory assessment

```python
# Score variant
reg = tu.tools.RegulomeDB_query_variant(rsid="rs4994")
score = reg["data"]["regulome_score"]
print(f"RegulomeDB ranking: {score['ranking']}, probability: {score['probability']}")
print(f"Top tissue scores: {sorted(score['tissue_specific_scores'].items(), key=lambda x: float(x[1]), reverse=True)[:5]}")

# Check if variant is an eQTL
eqtls = tu.tools.GTEx_get_single_tissue_eqtls(gene_symbol="ADRB3")  # gene near rs4994
# Cross-reference variant with eQTL results
```

### Pattern 5: CTCF and chromatin architecture

```python
# Find CTCF binding experiments
ctcf_exps = tu.tools.ReMap_get_transcription_factor_binding(gene_name="CTCF", cell_type="GM12878", limit=10)

# Get CTCF motif from JASPAR
ctcf_motif = tu.tools.jaspar_search_matrices(name="CTCF", collection="CORE", page_size=3)

# Find CTCF-only cCREs in a region
ccres = tu.tools.UCSC_get_encode_cCREs(chrom="chr17", start=7668421, end=7687490, genome="hg38")
# Filter for CTCF-bound elements from the results
```

---

## Tool Parameter Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| ENCODE_search_histone_experiments | target, cell_type (or tissue alias), limit | target = histone mark name; tissue terms may need ENCODE ontology names |
| ENCODE_search_rnaseq_experiments | assay_type, biosample, limit | assay_type: "total RNA-seq" or "polyA plus RNA-seq"; fall back to polyA if 0 results |
| GEO_search_rnaseq_datasets | query, organism, limit (or max_results) | limit and max_results both accepted |
| GEO_search_atacseq_datasets | query, organism, limit (or max_results) | limit and max_results both accepted; "ATAC-seq" auto-appended to query |
| ENCODE_search_chromatin_accessibility | cell_type, limit | Returns ATAC-seq experiments |
| ENCODE_get_chromatin_state | cell_type, limit | ChromHMM 15-state annotations |
| ENCODE_search_annotations | annotation_type, biosample_term_name, organism, assembly, limit | General annotation search |
| SCREEN_get_regulatory_elements | gene_name, element_type, limit | PLS/pELS/dELS/CTCF-only |
| UCSC_get_encode_cCREs | chrom, start, end, genome | Region-based cCRE query |
| GTEx_query_eqtl | gene_symbol, tissue (alias tissue_id), page, size | gene_symbol or ensembl_gene_id; page is 1-indexed; size controls page length |
| GTEx_get_single_tissue_eqtls | gene_symbol | All significant eQTLs across tissues |
| GTEx_get_multi_tissue_eqtls | operation, gencode_id | Requires versioned GENCODE ID |
| GTEx_calculate_eqtl | operation, gencode_id, variant_id, tissue_site_detail_id | Custom eQTL calculation |
| GTEx_get_eqtl_genes | operation, tissue_site_detail_id | eGenes per tissue |
| GTEx_get_median_gene_expression | gene_symbol | Median TPM across tissues |
| GTEx_get_expression_summary | gene_symbol | Clustered median expression |
| eQTL_list_datasets | size, quant_method, tissue_id | EBI eQTL Catalogue datasets |
| eQTL_get_associations | dataset_id, size, gene_id, variant | EBI eQTL associations |
| jaspar_search_matrices | search, name, collection, tax_group, species, page, page_size | TF motif search |
| jaspar_get_matrix | (matrix_id) | Position frequency matrix |
| ReMap_get_transcription_factor_binding | gene_name, cell_type, limit | TF ChIP-seq from ENCODE |
| RegulomeDB_query_variant | rsid | Regulatory variant scoring |
| STRING_get_functional_annotations | identifiers, species, category | GO/KEGG/Reactome/HPO |
| MyGene_query_genes | query | Gene symbol to Ensembl ID |
| ensembl_lookup_gene | gene_id, species | Gene details (REQUIRES species="homo_sapiens") |

---

## GTEx Tissue Site Detail IDs (common)

| Tissue | tissueSiteDetailId |
|--------|-------------------|
| Whole Blood | Whole_Blood |
| Breast | Breast_Mammary_Tissue |
| Brain Cortex | Brain_Cortex |
| Brain Cerebellum | Brain_Cerebellum |
| Liver | Liver |
| Lung | Lung |
| Heart Left Ventricle | Heart_Left_Ventricle |
| Kidney Cortex | Kidney_Cortex |
| Thyroid | Thyroid |
| Skin (sun exposed) | Skin_Sun_Exposed_Lower_leg |
| Adipose Subcutaneous | Adipose_Subcutaneous |
| Muscle Skeletal | Muscle_Skeletal |
| Testis | Testis |
| Ovary | Ovary |
| Prostate | Prostate |

---

## Fallback Strategies

| Phase | Primary Tool | Fallback |
|-------|-------------|----------|
| Histone ChIP-seq | ENCODE_search_histone_experiments | GEO_search_chipseq_datasets |
| RNA-seq experiments | ENCODE_search_rnaseq_experiments (total RNA-seq) | ENCODE_search_rnaseq_experiments (polyA plus RNA-seq) |
| RNA-seq datasets (GEO) | GEO_search_rnaseq_datasets | EuropePMC_search_articles (query + "RNA-seq") |
| ATAC-seq datasets (GEO) | GEO_search_atacseq_datasets | ENCODE_search_chromatin_accessibility |
| Chromatin accessibility | ENCODE_search_chromatin_accessibility | ENCODE_search_experiments (filter ATAC-seq) |
| cCREs | UCSC_get_encode_cCREs | SCREEN_get_regulatory_elements |
| eQTLs | GTEx_get_single_tissue_eqtls | eQTL_get_associations (EBI Catalogue) |
| Expression | GTEx_get_median_gene_expression | GTEx_get_expression_summary |
| TF motifs | jaspar_search_matrices | ReMap_get_transcription_factor_binding |
| Variant scoring | RegulomeDB_query_variant | (combine eQTL + TF binding evidence manually) |

---

## Completeness Checklist

Before delivering a report, verify:
- [ ] Gene/region/variant identifiers resolved to canonical forms
- [ ] Histone modification data queried for relevant marks
- [ ] Chromatin accessibility checked (ATAC-seq if available)
- [ ] Regulatory elements identified (cCREs in region)
- [ ] eQTL evidence collected (GTEx and/or EBI)
- [ ] Expression context provided (tissue profile)
- [ ] TF binding evidence gathered (if region-based query)
- [ ] Variant regulatory score obtained (if variant query)
- [ ] Evidence graded by tier (T1-T4)
- [ ] All tool results cross-referenced for consistency
