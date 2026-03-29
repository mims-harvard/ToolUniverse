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

## NOT for (use other skills instead)

- Methylation array data processing (CpG beta values, differential methylation) -> Use `tooluniverse-epigenomics`
- RNA-seq differential expression -> Use `tooluniverse-rnaseq-deseq2`
- GWAS variant interpretation -> Use `tooluniverse-gwas-snp-interpretation`
- Variant functional annotation from VCF -> Use `tooluniverse-variant-analysis`

---

## Reasoning: Classify the Question First

Before calling any tool, identify which question type you're answering. Each maps to a different tool set.

**(a) Which regulatory elements exist at a locus?**
Use UCSC_get_encode_cCREs (region-based) or SCREEN_get_regulatory_elements (gene-based). Then check ENCODE_get_chromatin_state for ChromHMM annotation and ENCODE_search_chromatin_accessibility for ATAC-seq evidence.

**(b) Which TFs bind there?**
Use ReMap_get_transcription_factor_binding for ChIP-seq experiments. Use jaspar_search_matrices to retrieve binding motifs and check whether the sequence disrupts a known motif.

**(c) How does a variant affect regulation?**
Use RegulomeDB_query_variant for a scored summary. Then build multi-layer evidence: UCSC_get_encode_cCREs (is the variant in a cCRE?), GTEx_get_single_tissue_eqtls (is it an eQTL?), jaspar_search_matrices (does it disrupt a TF motif?). No single layer is sufficient — see the variant reasoning section below.

**(d) What genes are regulated by an element?**
Use GTEx_get_single_tissue_eqtls or GTEx_query_eqtl to find genes whose expression is associated with variants in the element. Use SCREEN_get_regulatory_elements with element_type="PLS"/"pELS"/"dELS" to classify element-to-promoter relationships.

---

## Reasoning: Histone Marks

Use histone mark identity to guide tool queries and interpret results before fetching data.

- **H3K4me3** = active promoter. If present without H3K27ac, promoter may be active but not hyperacetylated.
- **H3K27ac** = active enhancer or promoter. Strong signal = regulatory element is on.
- **H3K4me1** = poised or active enhancer. Needs H3K27ac to confirm activity; H3K4me1 alone = poised.
- **H3K27me3** = Polycomb repression. Gene is silenced by PRC2.
- **H3K9me3** = constitutive heterochromatin. Region is structurally silenced.
- **H3K36me3** = transcribed gene body. Confirms active elongation.

**Bivalent promoter logic**: If you observe H3K4me3 + H3K27me3 together at the same locus, the promoter is bivalent — poised but not active. This is common in stem cells and developmentally regulated genes. Do not report such genes as "actively transcribed." Use GTEx_get_expression_summary to check if the gene is actually expressed in the tissue of interest.

**Inference rule**: If a user asks about a mark you haven't queried yet, ask: does the mark you *have* found already answer the question? H3K4me3 in a region predicts active transcription; you may not need to also query H3K36me3 unless confirming elongation specifically.

---

## Reasoning: eQTL Interpretation

An eQTL means variant X is statistically associated with expression of gene Y in tissue T. Before reporting eQTL results, apply this chain of reasoning:

1. **Association ≠ causation.** The variant may be in LD with the causal variant. Report effect size (NES) and p-value, not causality.
2. **Check tissue specificity.** Use GTEx_get_multi_tissue_eqtls to see whether the effect is shared across tissues (m-value near 1.0 in many tissues) or tissue-specific (m-value near 1.0 in only one tissue). Tissue-specific eQTLs are stronger candidates for cell-type-specific regulation.
3. **Cross-reference with chromatin.** Is the eQTL variant inside a cCRE? Use UCSC_get_encode_cCREs on the variant's coordinates. If yes, the variant likely acts through a regulatory element.
4. **Check TF motif disruption.** Use jaspar_search_matrices to find motifs overlapping the eQTL locus. If the variant alleles differ in motif score, it is a candidate causal variant.
5. **Effect direction matters.** Positive NES = reference allele increases expression. Negative NES = alternative allele decreases expression.

---

## Reasoning: Variant Regulatory Impact

To assess a non-coding variant's regulatory impact, build evidence from multiple independent layers. No single layer is sufficient.

**Layer 1 — RegulomeDB score**: High probability (score 1a–2b) means convergent evidence from eQTL + TF binding + DNase. Score 4–7 means weak support. Use as a triage filter.

**Layer 2 — Regulatory element overlap**: Query UCSC_get_encode_cCREs at the variant's coordinates. If the variant falls in a cCRE (especially PLS or pELS), it is in a functional context.

**Layer 3 — eQTL evidence**: Query GTEx_get_single_tissue_eqtls for nearby genes. If the variant is a significant eQTL, the association supports regulatory function.

**Layer 4 — TFBS disruption**: Query jaspar_search_matrices for TFs with motifs at the locus. If the variant changes a high-information-content position in a motif, it is a strong functional candidate.

**Synthesis rule**: Report each layer separately. Convergence across 3+ layers = high-confidence regulatory variant. A single layer (e.g., eQTL alone) warrants caution.

---

## Phase 0: Disambiguation

**MyGene_query_genes**: `query` (string). Converts gene symbols to Ensembl IDs and coordinates. Filter results by `symbol == '<GENE>'` — first hit may not match.

**ensembl_lookup_gene**: `gene_id` (Ensembl ID), `species` (REQUIRED, "homo_sapiens"). Returns chr/start/end.

Key format notes:
- GTEx requires versioned GENCODE IDs: `ENSG00000012048.20`
- RegulomeDB takes rsIDs: `rs4994`
- GTEx variant IDs: `chr17_43705621_T_C_b38`
- UCSC cCRE regions: `chrom="chr17", start=7668421, end=7687490`

---

## Phase 1: Histone Modification & ChIP-seq

**ENCODE_search_histone_experiments**: `target` (histone mark), `cell_type` (or `tissue` alias), `biosample_term_name` (most explicit ENCODE ontology name), `limit`.

ENCODE anatomy term notes: "breast" → try "breast epithelium" or "mammary epithelial cell"; "brain" → "brain" works; if 0 results, append "tissue", "epithelium", or "cell".

```python
result = tu.tools.ENCODE_search_histone_experiments(target="H3K27ac", cell_type="GM12878", limit=5)
# result["data"]["experiments"][0]["accession"] -> "ENCSR000AKC"
```

**GEO_search_chipseq_datasets**: Fallback for older or non-ENCODE ChIP-seq datasets.

---

## Phase 2: Chromatin Accessibility & Architecture

**ENCODE_search_chromatin_accessibility**: `cell_type`, `limit`. Returns ATAC-seq experiments.

**ENCODE_get_chromatin_state**: `cell_type`, `limit`. Returns ChromHMM 15-state annotations (TssA, Enh, TssBiv, ReprPC, etc.). Use to confirm bivalent promoter state or enhancer classification.

**ENCODE_search_rnaseq_experiments**: `assay_type` (default `"total RNA-seq"`), `biosample`, `limit`. If 0 results, retry with `assay_type="polyA plus RNA-seq"`.

**GEO_search_rnaseq_datasets** / **GEO_search_atacseq_datasets**: `query`, `organism`, `limit` (also `max_results`). GEO adds "ATAC-seq" automatically for the ATAC tool.

**ReMap_get_transcription_factor_binding** (CTCF): `gene_name="CTCF"`, `cell_type`, `limit`. Returns ENCODE TF ChIP-seq experiments.

---

## Phase 3: Regulatory Element Identification

**SCREEN_get_regulatory_elements**: `gene_name`, `element_type` (PLS/pELS/dELS/CTCF-only/DNase-H3K4me3), `limit`.

**UCSC_get_encode_cCREs**: `chrom` (REQUIRED), `start` (REQUIRED), `end` (REQUIRED), `genome` (default "hg38"). Returns cCREs with Z-scores for DNase, H3K4me3, H3K27ac, CTCF signals.

```python
# cCREs near TP53
result = tu.tools.UCSC_get_encode_cCREs(chrom="chr17", start=7668421, end=7687490, genome="hg38")
```

**ENCODE_search_annotations**: `annotation_type` ("candidate Cis-Regulatory Elements" or "chromatin state"), `biosample_term_name`, `organism`, `assembly`, `limit`.

---

## Phase 4: eQTL Analysis

**GTEx_get_single_tissue_eqtls**: `gene_symbol`. Returns all significant eQTLs across tissues with snpId, pValue, tissueSiteDetailId, nes (normalized effect size).

```python
result = tu.tools.GTEx_get_single_tissue_eqtls(gene_symbol="BRCA1")
from collections import Counter
tissue_counts = Counter(e["tissueSiteDetailId"] for e in result["data"])
```

**GTEx_query_eqtl**: `gene_symbol`, `tissue` (tissueSiteDetailId), `page` (1-indexed), `size`. Use for a specific tissue.

**GTEx_get_multi_tissue_eqtls**: `operation="get_multi_tissue_eqtls"`, `gencode_id` (versioned, REQUIRED). Returns per-variant m-values showing tissue-sharing. m-value near 1.0 = effect present; near 0.0 = absent.

```python
result = tu.tools.GTEx_get_multi_tissue_eqtls(
    operation="get_multi_tissue_eqtls",
    gencode_id="ENSG00000012048.20"
)
```

**GTEx_calculate_eqtl**: `operation="calculate_eqtl"`, `gencode_id`, `variant_id` (chr_pos_ref_alt_b38), `tissue_site_detail_id`. Works for non-significant pairs.

**eQTL_list_datasets** / **eQTL_get_associations**: EBI eQTL Catalogue. Use `dataset_id` (from list call), `gene_id` (Ensembl), `variant`. Complementary to GTEx.

---

## Phase 5: Gene Expression Context

**GTEx_get_expression_summary**: `gene_symbol`. Recommended — auto-resolves GENCODE versions. Returns median TPM per tissue.

```python
result = tu.tools.GTEx_get_expression_summary(gene_symbol="BRCA1")
top_tissues = sorted(result["data"], key=lambda x: x["median"], reverse=True)[:5]
```

**GTEx_get_median_gene_expression**: Requires `operation="get_median_gene_expression"` + exact versioned `gencode_id`. Use only when version precision is needed.

**GTEx_get_tissue_sites**: No params. Returns all tissueSiteDetailId values.

---

## Phase 6: Transcription Factor Binding

**jaspar_search_matrices**: `name` (TF name), `collection` ("CORE"), `tax_group` ("vertebrates"), `species` ("9606"), `page_size`.

```python
result = tu.tools.jaspar_search_matrices(name="CTCF", collection="CORE", page_size=5)
```

**jaspar_get_matrix**: Returns position frequency matrix for a JASPAR matrix ID. Use to check if a variant allele disrupts a high-information-content position.

**ReMap_get_transcription_factor_binding**: `gene_name` (TF), `cell_type`, `limit`. Same tool used for CTCF in Phase 2 — applies to any TF.

**STRING_get_functional_annotations**: `identifiers` (gene name), `species` (9606), `category` ("Process"/"Function"/"KEGG"). Returns GO/KEGG/Reactome annotations for regulatory context.

---

## Phase 7: Variant Regulatory Scoring

**RegulomeDB_query_variant**: `rsid` (e.g., "rs4994"). Returns probability, ranking (1a = strongest, 7 = weakest), and tissue-specific scores.

```python
result = tu.tools.RegulomeDB_query_variant(rsid="rs4994")
score = result["data"]["regulome_score"]
# score["ranking"]: "1a" (eQTL + TF + motif + DNase) ... "7" (no evidence)
# score["probability"]: 0.0–1.0
top_tissues = sorted(score["tissue_specific_scores"].items(), key=lambda x: float(x[1]), reverse=True)[:5]
```

Rankings 1a–1f all have eQTL evidence. Rankings 2a–3b have TF binding without eQTL. Rankings 4–7 have decreasing evidence. Use ranking <= 2b as a threshold for "strong regulatory support."

---

## Phase 8: Integration

Combine evidence tiers before reporting:

- **T1 (Direct experimental)**: ENCODE ChIP-seq experiments, GTEx eQTL p < 5e-8
- **T2 (Strong computational)**: RegulomeDB score <= 2, SCREEN cCRE classification, ChromHMM state
- **T3 (Moderate)**: eQTL p < 0.05, JASPAR motif match, multi-tissue m-value > 0.5
- **T4 (Annotation-based)**: STRING GO terms, literature references

Convergence of T1+T2 evidence from independent sources (e.g., ENCODE ChIP-seq overlapping a RegulomeDB 1a variant with GTEx eQTL) constitutes strong evidence for regulatory function. Contradictions between layers (e.g., high RegulomeDB score but no eQTL) should be explicitly noted.

---

## Fallback Strategies

| Phase | Primary Tool | Fallback |
|-------|-------------|----------|
| Histone ChIP-seq | ENCODE_search_histone_experiments | GEO_search_chipseq_datasets |
| RNA-seq | ENCODE_search_rnaseq_experiments (total RNA-seq) | retry with polyA plus RNA-seq |
| ATAC-seq | ENCODE_search_chromatin_accessibility | GEO_search_atacseq_datasets |
| cCREs | UCSC_get_encode_cCREs | SCREEN_get_regulatory_elements |
| eQTLs | GTEx_get_single_tissue_eqtls | eQTL_get_associations (EBI) |
| Expression | GTEx_get_expression_summary | GTEx_get_median_gene_expression |
| TF motifs | jaspar_search_matrices | ReMap_get_transcription_factor_binding |
| Variant scoring | RegulomeDB_query_variant | combine eQTL + TF binding manually |
