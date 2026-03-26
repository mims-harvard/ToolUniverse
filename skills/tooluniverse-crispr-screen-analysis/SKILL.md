---
name: tooluniverse-crispr-screen-analysis
description: Comprehensive CRISPR screen analysis for functional genomics. Analyze pooled or arrayed CRISPR screens (knockout, activation, interference) to identify essential genes, synthetic lethal interactions, and drug targets. Perform sgRNA count processing, gene-level scoring (MAGeCK, BAGEL), quality control, pathway enrichment, and drug target prioritization. Use for CRISPR screen analysis, gene essentiality studies, synthetic lethality detection, functional genomics, drug target validation, or identifying genetic vulnerabilities.
---

# ToolUniverse CRISPR Screen Analysis

Comprehensive skill for analyzing CRISPR-Cas9 genetic screens to identify essential genes, synthetic lethal interactions, and therapeutic targets through robust statistical analysis and pathway enrichment.

## Overview

CRISPR screens enable genome-wide functional genomics by systematically perturbing genes and measuring fitness effects. This skill provides an 8-phase workflow for:
- Processing sgRNA count matrices
- Quality control and normalization
- Gene-level essentiality scoring (MAGeCK-like and BAGEL-like approaches)
- Synthetic lethality detection
- Pathway enrichment analysis
- Drug target prioritization with DepMap integration
- Integration with expression and mutation data

---

## Core Workflow

### Phase 1: Data Import & sgRNA Count Processing

Load sgRNA count matrix (MAGeCK format or generic TSV). Expected columns: `sgRNA`, `Gene`, plus sample columns. Create experimental design table linking samples to conditions (baseline/treatment) with replicate assignments.

### Phase 2: Quality Control & Filtering

Assess sgRNA distribution quality:
- **Library sizes** per sample (total reads)
- **Zero-count sgRNAs**: Count across samples
- **Low-count filtering**: Remove sgRNAs below threshold (default: <30 reads in >N-2 samples)
- **Gini coefficient**: Assess distribution skewness per sample
- Report filtering recommendations

### Phase 3: Normalization

Normalize sgRNA counts to account for library size differences:
- **Median ratio** (DESeq2-like): Calculate geometric mean reference, compute size factors as median of ratios
- **Total count** (CPM-like): Divide by library size in millions

Calculate log2 fold changes (LFC) between treatment and control conditions with pseudocount.

### Phase 4: Gene-Level Scoring

Two scoring approaches:
- **MAGeCK-like (RRA)**: Rank all sgRNAs by LFC, compute mean rank per gene. Lower mean rank = more essential. Includes sgRNA count and mean LFC per gene.
- **BAGEL-like (Bayes Factor)**: Use reference essential/non-essential gene sets to estimate LFC distributions. Calculate likelihood ratio (Bayes Factor) for each gene. Higher BF = more likely essential.

### Phase 5: Synthetic Lethality Detection

Compare essentiality scores between wildtype and mutant cell lines:
- Merge gene scores, calculate delta LFC and delta rank
- Filter for genes essential in mutant (LFC < threshold) but not wildtype (LFC > -0.5) with large rank change
- Sort by differential essentiality

Query DepMap/literature for known dependencies using PubMed search.

### Phase 6: Pathway Enrichment Analysis

Submit top essential genes to Enrichr for pathway enrichment:
- KEGG pathways
- GO Biological Process
- Retrieve enriched terms with p-values and gene lists

### Phase 7: Drug Target Prioritization

Composite scoring combining:
- **Essentiality** (50% weight): Normalized mean LFC from CRISPR screen
- **Expression** (30% weight): Log2 fold change from RNA-seq (if available)
- **Druggability** (20% weight): Number of drug interactions from DGIdb

Query DGIdb for each candidate gene to find existing drugs, interaction types, and sources.

### Phase 8: Report Generation

Generate markdown report with:
- Summary statistics (total genes, essential genes, non-essential genes)
- Top 20 essential genes table (rank, gene, mean LFC, sgRNAs, score)
- Pathway enrichment results (top 10 terms per database)
- Drug target candidates (rank, gene, essentiality, expression FC, druggability, priority score)
- Methods section

---

## ToolUniverse Tool Integration

**Key Tools Used**:
- `PubMed_search_articles` - Literature search for gene essentiality and drug resistance
- `ReactomeAnalysis_pathway_enrichment` - Pathway enrichment (param: `identifiers` newline-separated, `page_size`)
- `enrichr_gene_enrichment_analysis` - Enrichr enrichment (param: `gene_list` array, `libs` array)
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions (param: `genes` as array)
- `DGIdb_get_gene_druggability` - Druggability categories
- `STRING_get_network` - Protein interaction networks
- `kegg_search_pathway` - Pathway search by keyword
- `kegg_get_pathway_info` - Pathway details by ID

**Cancer Context** (essential for drug resistance screens):
- `civic_search_evidence_items` - Clinical evidence for drug resistance/sensitivity
- `COSMIC_get_mutations_by_gene` - Somatic mutation landscape
- `cBioPortal_get_mutations` - Mutations in specific cancer cohorts
- `ChEMBL_search_targets` - Structural druggability assessment

**Expression & Variant Integration**:
- `GEO_search_rnaseq_datasets` / `geo_search_datasets` - Expression datasets
- `ClinVar_search_variants` - Known pathogenic variants
- `gnomad_get_gene_constraints` - Gene constraint metrics (pLI, oe_lof)
- `UniProt_get_function_by_accession` - Protein function for hit validation

---

## Quick Start

```python
import pandas as pd
from tooluniverse import ToolUniverse

# 1. Load data
counts, meta = load_sgrna_counts("sgrna_counts.txt")
design = create_design_matrix(['T0_1', 'T0_2', 'T14_1', 'T14_2'],
                               ['baseline', 'baseline', 'treatment', 'treatment'])

# 2. Process
filtered_counts, filtered_mapping = filter_low_count_sgrnas(counts, meta['sgrna_to_gene'])
norm_counts, _ = normalize_counts(filtered_counts)
lfc, _, _ = calculate_lfc(norm_counts, design)

# 3. Score genes
gene_scores = mageck_gene_scoring(lfc, filtered_mapping)

# 4. Enrich pathways
enrichment = enrich_essential_genes(gene_scores, top_n=100)

# 5. Find drug targets
drug_targets = prioritize_drug_targets(gene_scores)

# 6. Generate report
report = generate_crispr_report(gene_scores, enrichment, drug_targets)
```

---

## Interpretation Framework

| Evidence Grade | Criteria | Validation Priority |
|----------------|----------|---------------------|
| **A -- Strong hit** | MAGeCK RRA p < 0.001, BAGEL BF > 5, >=3 sgRNAs with concordant LFC | Immediate validation (individual KO, growth assay) |
| **B -- Moderate hit** | MAGeCK RRA p < 0.01, BAGEL BF 2-5, >=2 concordant sgRNAs | Secondary validation pool |
| **C -- Weak/ambiguous** | p > 0.01, BF < 2, or discordant sgRNA effects | Deprioritize; check for copy-number bias or seed effects |

**Interpreting screen results:**
- A gene with mean LFC < -1.0 across replicates and >=3 concordant sgRNAs is a robust essentiality hit; single-sgRNA effects are more likely off-target and should be flagged.
- Essential gene thresholds are context-dependent: core fitness genes (e.g., ribosomal, spliceosomal) should deplete in any screen and serve as positive controls -- their absence from the hit list indicates a QC problem.
- Synthetic lethal hits (depleted in mutant but not wildtype) require delta-LFC > 1.5 and confirmation in an independent cell line before therapeutic target nomination.

**Synthesis questions to address in the report:**
1. Do the top hits cluster in known pathways (Reactome/KEGG), or are they scattered -- suggesting technical noise?
2. Are known essential genes (Hart et al. reference set) correctly identified, confirming screen quality?
3. For drug target candidates: does DGIdb show existing compounds, and does DepMap confirm the dependency across multiple cell lines?

---

## References

- Li W, et al. (2014) MAGeCK enables robust identification of essential genes from genome-scale CRISPR/Cas9 knockout screens. Genome Biology
- Hart T, et al. (2015) High-Resolution CRISPR Screens Reveal Fitness Genes and Genotype-Specific Cancer Liabilities. Cell
- Meyers RM, et al. (2017) Computational correction of copy number effect improves specificity of CRISPR-Cas9 essentiality screens. Nature Genetics
- Tsherniak A, et al. (2017) Defining a Cancer Dependency Map. Cell (DepMap)

---

## See Also

- `ANALYSIS_DETAILS.md` - Detailed code snippets for all 8 phases
- `USE_CASES.md` - Complete use cases (essentiality screen, synthetic lethality, drug target discovery, expression integration) and best practices
- `EXAMPLES.md` - Example usage and quick reference
- `QUICK_START.md` - Quick start guide
- `FALLBACK_PATCH.md` - Fallback patterns for API issues
