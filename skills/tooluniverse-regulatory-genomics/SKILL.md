---
name: tooluniverse-regulatory-genomics
description: >
  Investigate transcription factor binding, cis-regulatory elements, chromatin
  accessibility, and regulatory variant annotation. Use when asked about TF binding
  sites, enhancers, promoters, ChIP-seq data, ATAC-seq signals, candidate cis-regulatory
  elements (cCREs), or the regulatory impact of genomic variants.
---

# Regulatory Genomics Research Skill

Systematic investigation of gene regulation through transcription factor binding, chromatin state, and regulatory element annotation. Integrates JASPAR (TF motifs), ENCODE (functional genomics experiments), RegulomeDB (regulatory variant scoring), and UCSC cCREs.

## Domain Reasoning

Regulatory element identification requires converging lines of evidence: sequence conservation alone is insufficient (many conserved sequences are not regulatory), chromatin accessibility is necessary but not sufficient (open chromatin can be structural), TF binding peaks require motif validation, and eQTL evidence ties the element to a transcriptional outcome. No single data type is sufficient. A high-confidence regulatory element requires at least two independent evidence types, and ideally all four.

## LOOK UP DON'T GUESS

- TF binding motifs: retrieve from `jaspar_search_matrices` and `jaspar_get_matrix`; do not describe motifs from memory.
- Experimental ChIP-seq data: search `ENCODE_search_experiments`; do not assume a TF has been profiled in a given cell type.
- cCRE annotations for a genomic region: call `UCSC_get_encode_cCREs` with exact coordinates; do not guess element types.
- Regulatory impact of a variant: query `RegulomeDB_query_variant`; never estimate regulatory importance from position alone.

---

**KEY PRINCIPLES**:
1. **English-first queries** - Use English gene/TF names in all tool calls; respond in user's language
2. **Evidence layering** - Combine motif (JASPAR) + experimental (ENCODE ChIP-seq) + variant (RegulomeDB) evidence
3. **Coordinate precision** - Genome coordinates must specify assembly (GRCh38 preferred)
4. **Negative results documented** - Report when a TF has no ChIP-seq data in ENCODE

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

- "What transcription factors bind near gene X?"
- "Does this SNP affect a regulatory element?"
- "Find CTCF binding sites in liver tissue"
- "What are the enhancers active in this cell type?"
- "Show me ChIP-seq experiments for H3K27ac in T cells"
- "Is rs1234567 in a regulatory region?"
- "What TF motifs overlap this genomic region?"
- "Find ENCODE experiments for ATAC-seq in cancer cell lines"

---

## Key Tools

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `jaspar_search_matrices` | Find TF binding motifs by TF name or organism | `name`, `species`, `collection`, `tax_id` |
| `jaspar_get_matrix` | Get full PWM/PFM for a specific JASPAR matrix | `matrix_id` (e.g., "MA0139.1") |
| `JASPAR_get_transcription_factors` | List all TF matrices (paginated) | `page`, `page_size` |
| `ENCODE_search_experiments` | Search ENCODE ChIP-seq/ATAC-seq/WGBS experiments | `assay_title`, `target`, `biosample_term_name`, `limit` |
| `ENCODE_search_histone_experiments` | Search histone mark ChIP-seq specifically | `histone_mark`, `biosample_term_name`, `limit` |
| `ENCODE_search_chromatin_accessibility` | Search ATAC-seq/DNase-seq experiments | `biosample_term_name`, `limit` |
| `ENCODE_get_experiment` | Get full metadata for a specific ENCODE experiment | `accession` (e.g., "ENCSR000EGM") |
| `ENCODE_search_annotations` | Search ENCODE cCRE and chromatin state annotations | `annotation_type`, `biosample_term_name`, `limit` |
| `ENCODE_get_chromatin_state` | Search ChromHMM segmentation data | `biosample_term_name`, `limit` |
| `UCSC_get_encode_cCREs` | Get cCREs overlapping a genomic region | `chrom`, `start`, `end` |
| `RegulomeDB_query_variant` | Score regulatory impact of a variant | `rsid` (e.g., "rs4994") |
| `ENCODE_search_biosamples` | Find available cell lines/tissues in ENCODE | `term_name`, `biosample_type`, `limit` |

---

## Workflow

### Phase 1: TF Motif Discovery (JASPAR)

When asked about TF binding motifs or what TFs might regulate a gene:

```
1. jaspar_search_matrices(name="TF_NAME", species="Homo sapiens")
   -> Returns list of matrices with matrix_id, collection, version

2. jaspar_get_matrix(matrix_id="MA0139.1")
   -> Returns full PFM/PWM matrix, sequence logo URL, binding sites URL

3. For broad TF family search:
   jaspar_search_matrices(species="Homo sapiens", collection="CORE")
   -> Filter by TF family name in results
```

**JASPAR Collections**:
- `CORE`: High-quality, non-redundant matrices (best for most use cases)
- `CNE`: Conserved non-coding elements
- `POLII`: RNA Pol II binding sites

**Key Response Fields**:
- `matrix_id`: Versioned ID (e.g., "MA0139.1") — use for jaspar_get_matrix
- `name`: TF gene symbol
- `sequence_logo`: URL to binding site logo PNG/SVG
- `collection`: Which JASPAR collection

### Phase 2: ENCODE Experiment Search

When looking for ChIP-seq, ATAC-seq, or other functional genomics data:

**For TF ChIP-seq**:
```
ENCODE_search_experiments(
    assay_title="TF ChIP-seq",
    target="CTCF",              # TF gene name
    biosample_term_name="HepG2", # Cell line or tissue
    limit=10
)
```

**For histone marks**:
```
ENCODE_search_histone_experiments(
    histone_mark="H3K27ac",         # or H3K4me3, H3K27me3, H3K36me3
    biosample_term_name="liver",
    limit=10
)
```

**For chromatin accessibility**:
```
ENCODE_search_chromatin_accessibility(
    biosample_term_name="T cell",
    limit=10
)
```

**For regulatory annotations (cCREs, ChromHMM)**:
```
ENCODE_search_annotations(
    annotation_type="candidate Cis-Regulatory Elements",
    biosample_term_name="K562",
    limit=10
)
```

**Common assay_title values**:
- `"TF ChIP-seq"` - Transcription factor binding
- `"Histone ChIP-seq"` - Histone modification
- `"ATAC-seq"` - Chromatin accessibility
- `"DNase-seq"` - Open chromatin (older method)
- `"WGBS"` - DNA methylation

**Note**: `ENCODE_search_experiments` returns experiment metadata only (accession, biosample, status). Use `ENCODE_get_experiment(accession)` to get file download links and detailed metadata.

### Phase 3: cCRE Annotation (UCSC + ENCODE)

When annotating a specific genomic region:

```
UCSC_get_encode_cCREs(
    chrom="chr8",       # Chromosome (GRCh38)
    start=37966000,     # Start coordinate
    end=37967000        # End coordinate
)
# Returns cCREs with type: pELS (proximal enhancer), dELS (distal enhancer),
# PLS (promoter-like), CTCF-only, DNase-H3K4me3
```

**cCRE Types**:
- **PLS** (Promoter-like): High DNase + H3K4me3 + H3K27ac signal near TSS
- **pELS** (Proximal Enhancer): High DNase + H3K27ac, within 2kb of TSS
- **dELS** (Distal Enhancer): High DNase + H3K27ac, >2kb from TSS
- **CTCF-only**: CTCF binding without enhancer marks
- **DNase-H3K4me3**: Unclassified accessible region

### Phase 4: Regulatory Variant Scoring (RegulomeDB)

When assessing regulatory impact of a variant:

```
RegulomeDB_query_variant(rsid="rs4994")
# Returns:
#   regulome_score.ranking: "1a"-"7" (1a = highest regulatory evidence)
#   regulome_score.probability: 0-1 continuous score
#   tissue_specific_scores: dict of tissue -> score
#   overlapping features: eQTLs, TF binding, DNase peaks, motifs
```

**RegulomeDB Score Interpretation**:
| Rank | Meaning |
|------|---------|
| 1a | eQTL + TF binding + matched TF motif + DNase peak |
| 1b | eQTL + TF binding + DNase peak |
| 1c | eQTL + TF binding or DNase peak |
| 1d | eQTL + motif or protein binding |
| 1e | eQTL + motif hit |
| 1f | eQTL only |
| 2a | TF binding + motif match + DNase |
| 2b | TF binding + matched motif |
| 2c | TF binding with/without motif |
| 3a | DNase peak + motif |
| 3b | DNase peak only |
| 4 | Motif hit only |
| 5 | Proximity to Footprint |
| 6 | Proximity to Footprint + TF |
| 7 | No evidence |

Variants with rank 1a-2b are most likely to affect gene regulation.

---

## Tool Parameter Reference

| Tool | Required Params | Optional Params | Notes |
|------|----------------|-----------------|-------|
| `jaspar_search_matrices` | (none — returns all if empty) | `name`, `species`, `collection`, `tax_id`, `page`, `page_size` | Use `name` for TF name search |
| `jaspar_get_matrix` | `matrix_id` | — | Full version required: "MA0139.1" not "MA0139" |
| `JASPAR_get_transcription_factors` | (none) | `page`, `page_size` | Paginated; default page_size=10 |
| `jaspar_get_matrix_versions` | `base_id` | — | base_id is unversioned (e.g., "MA0139") |
| `ENCODE_search_experiments` | (none — returns all if empty) | `assay_title`, `target`, `biosample_term_name`, `limit` | assay_title must match ENCODE vocabulary exactly |
| `ENCODE_search_histone_experiments` | (none) | `histone_mark`, `biosample_term_name`, `limit` | histone_mark: "H3K27ac", "H3K4me3", etc. |
| `ENCODE_search_chromatin_accessibility` | (none) | `biosample_term_name`, `limit` | Returns ATAC-seq and DNase-seq |
| `ENCODE_get_experiment` | `accession` | — | accession: "ENCSR..." format |
| `ENCODE_search_annotations` | (none) | `annotation_type`, `biosample_term_name`, `limit` | annotation_type: "candidate Cis-Regulatory Elements" |
| `ENCODE_get_chromatin_state` | (none) | `biosample_term_name`, `limit` | Returns ChromHMM segmentation |
| `ENCODE_search_biosamples` | (none) | `term_name`, `biosample_type`, `limit` | biosample_type: "cell line", "tissue", "primary cell" |
| `UCSC_get_encode_cCREs` | `chrom`, `start`, `end` | — | Coordinates in GRCh38; chrom format: "chr1" |
| `RegulomeDB_query_variant` | `rsid` | — | rsid format: "rs4994" (with rs prefix) |

---

## Common Patterns

### Pattern 1: TF Binding Site Investigation
```
Goal: Find where TF X binds and what motif it recognizes
Flow:
  1. jaspar_search_matrices(name="CTCF") -> get matrix_id
  2. jaspar_get_matrix(matrix_id) -> get full PWM, logo URL
  3. ENCODE_search_experiments(assay_title="TF ChIP-seq", target="CTCF") -> experimental binding data
  4. For specific tissue: add biosample_term_name="HepG2"
Output: Motif logo + experimental binding evidence
```

### Pattern 2: Regulatory Variant Interpretation
```
Goal: Assess if variant rs1234567 affects gene regulation
Flow:
  1. RegulomeDB_query_variant(rsid="rs1234567") -> score + overlapping features
  2. If score <= 2b: ENCODE_search_experiments(target=overlapping_TF) -> experimental evidence
  3. UCSC_get_encode_cCREs(chrom, start, end) -> check if variant in known cCRE
Output: Regulatory score + supporting evidence + cCRE context
```

### Pattern 3: Cell-Type Regulatory Landscape
```
Goal: Characterize active enhancers in a cell type
Flow:
  1. ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name="K562") -> active enhancers
  2. ENCODE_search_chromatin_accessibility(biosample_term_name="K562") -> open chromatin
  3. ENCODE_search_annotations(annotation_type="candidate Cis-Regulatory Elements", biosample_term_name="K562")
  4. ENCODE_get_chromatin_state(biosample_term_name="K562") -> ChromHMM states
Output: Active regulatory elements specific to the cell type
```

### Pattern 4: Gene Regulatory Region Mapping
```
Goal: Find all regulatory elements near a gene
Flow:
  1. Get gene coordinates from MyGene_query_genes or ensembl_lookup_gene
  2. UCSC_get_encode_cCREs(chrom, start-50000, end+50000) -> nearby cCREs
  3. ENCODE_search_experiments(target=TF_OF_INTEREST) -> TF binding data
  4. jaspar_search_matrices(name=TF_NAME) -> motif for TF
Output: Map of regulatory elements around gene with evidence types
```

---

## Fallback Strategies

| Primary Tool | Fallback | When |
|-------------|----------|------|
| `ENCODE_search_experiments` with specific biosample | Remove `biosample_term_name` filter | No results for specific tissue |
| `jaspar_search_matrices(name=TF)` | `jaspar_search_matrices(name=TF_family)` | TF not found by exact name |
| `UCSC_get_encode_cCREs` | `ENCODE_search_annotations` without coordinates | If coordinates unknown |
| `RegulomeDB_query_variant(rsid)` | Use `ENCODE_search_experiments` + `JASPAR` to manually assess overlap | rsid not in RegulomeDB |

---

## Limitations

- **ENCODE TF ChIP-seq**: `assay_title="TF ChIP-seq"` uses ENCODE's exact controlled vocabulary — avoid "ChIP-seq" (too general)
- **UCSC cCREs**: Coordinates must be in GRCh38 (hg38); liftOver required for hg19 variants
- **RegulomeDB**: Only scores variants with known rsIDs; novel variants not supported
- **JASPAR**: Provides motif databases only — not genomic binding locations; combine with ENCODE for experimental evidence
- **ENCODE experiment results**: The `@graph` field may be empty if query filters are too restrictive; relax filters and retry
