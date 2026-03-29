---
name: tooluniverse-immune-repertoire-analysis
description: Comprehensive immune repertoire analysis for T-cell and B-cell receptor sequencing data. Analyze TCR/BCR repertoires to assess clonality, diversity, V(D)J gene usage, CDR3 characteristics, convergence, and predict epitope specificity. Integrate with single-cell data for clonotype-phenotype associations. Use for adaptive immune response profiling, cancer immunotherapy research, vaccine response assessment, autoimmune disease studies, or repertoire diversity analysis in immunology research.
---

# ToolUniverse Immune Repertoire Analysis

Comprehensive skill for analyzing T-cell receptor (TCR) and B-cell receptor (BCR) repertoire sequencing data to characterize adaptive immune responses, clonal expansion, and antigen specificity.

## Domain Reasoning

Repertoire diversity reflects immune history. High clonality — a few clones dominating — indicates antigen-driven expansion, as seen in active infection, tumor-infiltrating lymphocytes, or chronic stimulation. Low diversity points to immunodeficiency or treatment-induced lymphopenia. Always compare observed metrics against healthy donor reference distributions before drawing conclusions; a Shannon entropy of 7 is unremarkable in a healthy adult but alarming post-chemotherapy.

## LOOK UP DON'T GUESS

- Clonotype frequency thresholds, CDR3 length ranges, and convergence ratios: query IEDB or VDJdb; do not assume values from memory.
- Epitope specificities for expanded clones: search `iedb_search_tcell_assays` and `BVBRC_search_epitopes`; never infer antigen identity from CDR3 alone.
- V gene family usage biases in healthy donors: retrieve published reference data or query ImmPort; do not assume baseline distributions are uniform.
- Sequencing depth adequacy: compute rarefaction curves from the actual data; do not guess whether depth is sufficient.

---

## Overview

Adaptive immune receptor repertoire sequencing (AIRR-seq) enables comprehensive profiling of T-cell and B-cell populations through high-throughput sequencing of TCR and BCR variable regions. This skill provides an 8-phase workflow for:
- Clonotype identification and tracking
- Diversity and clonality assessment
- V(D)J gene usage analysis
- CDR3 sequence characterization
- Clonal expansion and convergence detection
- Epitope specificity prediction
- Integration with single-cell phenotyping
- Longitudinal repertoire tracking

---

## Core Workflow

### Phase 1: Data Import & Clonotype Definition

Load AIRR-seq data from common formats (MiXCR, ImmunoSEQ, AIRR standard, 10x Genomics VDJ). Standardize columns to: `cloneId`, `count`, `frequency`, `cdr3aa`, `cdr3nt`, `v_gene`, `j_gene`, `chain`. Define clonotypes using one of three methods:
- **cdr3aa**: Amino acid CDR3 sequence only
- **cdr3nt**: Nucleotide CDR3 sequence
- **vj_cdr3**: V gene + J gene + CDR3aa (most common, recommended)

Aggregate by clonotype, sort by count, assign ranks.

### Phase 2: Diversity & Clonality Analysis

Calculate diversity metrics for the repertoire:
- **Shannon entropy**: Overall diversity (higher = more diverse)
- **Simpson index**: Probability two random clones are same
- **Inverse Simpson**: Effective number of clonotypes
- **Gini coefficient**: Inequality in clonotype distribution
- **Clonality**: 1 - Pielou's evenness (higher = more clonal)
- **Richness**: Number of unique clonotypes

Generate rarefaction curves to assess whether sequencing depth is sufficient.

### Phase 3: V(D)J Gene Usage Analysis

Analyze V and J gene usage patterns weighted by clonotype count:
- V gene family usage frequencies
- J gene family usage frequencies
- V-J pairing frequencies
- Statistical testing for biased usage (chi-square test vs. uniform expectation)

### Phase 4: CDR3 Sequence Analysis

Characterize CDR3 sequences:
- **Length distribution**: Typical TCR CDR3 = 12-18 aa; BCR CDR3 = 10-20 aa
- **Amino acid composition**: Weighted by clonotype frequency
- Flag unusual length distributions (may indicate PCR bias)

### Phase 5: Clonal Expansion Detection

Identify expanded clonotypes above a frequency threshold (default: 95th percentile). Track clonotypes longitudinally across multiple timepoints to measure persistence, mean/max frequency, and fold changes.

### Phase 6: Convergence & Public Clonotypes

- **Convergent recombination**: Same CDR3 amino acid from different nucleotide sequences (evidence of antigen-driven selection)
- **Public clonotypes**: Shared across multiple samples/individuals (may indicate common antigen responses)

### Phase 7: Epitope Prediction & Specificity

Query epitope databases for known TCR-epitope associations:
- **IEDB** (`iedb_search_tcell_assays`): Search T-cell assay records by sequence or MHC class; use `iedb_search_epitopes` with `sequence_contains` for motif search
- **BVBRC** (`BVBRC_search_epitopes`): Best for organism-based epitope discovery (e.g., `taxon_id="2697049"` for SARS-CoV-2); returns epitope sequences with T-cell/B-cell assay counts
- **VDJdb** (manual): https://vdjdb.cdr3.net/search
- **PubMed literature** (`PubMed_search_articles`): Search for CDR3 + epitope/antigen/specificity
- **IEDB detail tools**: `iedb_get_epitope_antigens` (link epitope→antigen), `iedb_get_epitope_mhc` (MHC restriction)

### Phase 8: Integration with Single-Cell Data

Link TCR/BCR clonotypes to cell phenotypes from paired single-cell RNA-seq:
- Map clonotypes to cell barcodes
- Identify expanded clonotype phenotypes on UMAP
- Analyze clonotype-cluster associations (cross-tabulation)
- Find cluster-specific clonotypes (>80% cells in one cluster)
- Differential gene expression: expanded vs. non-expanded cells

---

## ToolUniverse Tool Integration

**Key Tools Used**:
- `iedb_search_tcell_assays` - T-cell assay records (sequence, MHC class filters)
- `iedb_search_bcell` - B-cell assay records
- `iedb_search_epitopes` - Epitope motif search via `sequence_contains`
- `BVBRC_search_epitopes` - Organism-based epitope discovery (best for pathogen-specific queries)
- `NCBI_SRA_search_runs` - Find public TCR/BCR-seq datasets (use strategy="AMPLICON")
- `ImmPort_search_studies` - NIAID immunology studies (vaccine trials, flow cytometry)
- `PubMed_search_articles` - Literature on TCR/BCR specificity
- `UniProt_get_entry_by_accession` - Antigen protein information

**Integration with Other Skills**:
- `tooluniverse-single-cell` - Single-cell transcriptomics
- `tooluniverse-rnaseq-deseq2` - Bulk RNA-seq analysis
- `tooluniverse-variant-analysis` - Somatic hypermutation analysis (BCR)

---

## Quick Start

```python
from tooluniverse import ToolUniverse

# 1. Load data
tcr_data = load_airr_data("clonotypes.txt", format='mixcr')

# 2. Define clonotypes
clonotypes = define_clonotypes(tcr_data, method='vj_cdr3')

# 3. Calculate diversity
diversity = calculate_diversity(clonotypes['count'])
print(f"Shannon entropy: {diversity['shannon_entropy']:.2f}")

# 4. Detect expanded clones
expansion = detect_expanded_clones(clonotypes)
print(f"Expanded clonotypes: {expansion['n_expanded']}")

# 5. Analyze V(D)J usage
vdj_usage = analyze_vdj_usage(tcr_data)

# 6. Query epitope databases
top_clones = expansion['expanded_clonotypes']['clonotype'].head(10)
epitopes = query_epitope_database(top_clones)
```

---

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Strong** | Clonal expansion > 1% frequency, convergent recombination confirmed, epitope match in IEDB/VDJdb | CDR3 at 5% frequency with 3 nucleotide variants encoding same amino acid, IEDB hit |
| **Moderate** | Expanded clone (0.1-1%), V(D)J bias significant (chi-sq p < 0.01), partial epitope match | Clone at 0.5% with TRBV20-1 bias, similar CDR3 motif in VDJdb |
| **Weak** | Low-frequency expansion (0.01-0.1%), single timepoint only, no epitope database match | Moderately expanded clone without convergence or known specificity |
| **Insufficient** | Below detection threshold, sequencing depth < 10,000 clonotypes, no replication | Singleton clonotypes that may be PCR/sequencing artifacts |

### Interpretation Guidance

- **Clonality metrics**: Shannon diversity measures overall repertoire complexity (higher = more diverse, typical range 5-12 for healthy blood). Gini coefficient ranges from 0 (perfectly even) to 1 (single dominant clone); values > 0.3 suggest clonal expansion. Clonality (1 - Pielou's evenness) > 0.2 indicates moderate clonal dominance; > 0.5 suggests strong oligoclonal expansion (common in active infection or tumor-infiltrating lymphocytes).
- **V(D)J usage significance**: Biased V or J gene usage (chi-square p < 0.01 vs expected uniform distribution) may indicate antigen-driven selection. However, baseline V gene usage is not uniform even in healthy repertoires due to genomic proximity and recombination efficiency. Compare against healthy donor reference distributions rather than uniform expectation when possible.
- **CDR3 convergence meaning**: Convergent recombination (same CDR3 amino acid from different nucleotide sequences) is strong evidence of antigen-driven selection because independent recombination events converged on the same receptor. Public clonotypes (shared across individuals) further strengthen this inference. A convergence ratio > 2 (nucleotide variants per amino acid sequence) for expanded clones is noteworthy.
- **Sequencing depth**: Rarefaction curves that plateau indicate sufficient depth. If the curve is still rising, richness and diversity estimates are underestimates. Minimum recommended depth: 50,000-100,000 total reads for bulk TCR-seq.
- **Longitudinal tracking**: Persistent clones across timepoints with stable or increasing frequency indicate antigen-driven maintenance. Transient expansions that disappear may reflect acute responses.

### Synthesis Questions

1. Does the observed clonal expansion pattern (Gini coefficient, top-clone frequency) match the expected immune context (e.g., post-vaccination expansion, tumor-infiltrating lymphocyte oligoclonality)?
2. Are convergent CDR3 sequences found across multiple individuals in the cohort, suggesting a public response to a shared antigen?
3. Do expanded clonotypes show biased V gene usage consistent with known antigen-specific repertoire features (e.g., TRBV20-1 enrichment in CMV-specific responses)?
4. Is the sequencing depth sufficient (rarefaction plateau reached) to reliably estimate diversity metrics and detect low-frequency expanded clones?
5. For longitudinal data, do clonal dynamics (expansion, contraction, persistence) correlate with clinical outcomes or treatment response?

---

## References

- Dash P, et al. (2017) Quantifiable predictive features define epitope-specific T cell receptor repertoires. Nature
- Glanville J, et al. (2017) Identifying specificity groups in the T cell receptor repertoire. Nature
- Stubbington MJT, et al. (2016) T cell fate and clonality inference from single-cell transcriptomes. Nature Methods
- Vander Heiden JA, et al. (2014) pRESTO: a toolkit for processing high-throughput sequencing raw reads of lymphocyte receptor repertoires. Bioinformatics

---

## See Also

- `ANALYSIS_DETAILS.md` - Detailed code snippets for all 8 phases
- `USE_CASES.md` - Complete use cases (immunotherapy, vaccine, autoimmune, single-cell integration) and best practices
