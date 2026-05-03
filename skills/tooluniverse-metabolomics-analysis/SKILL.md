---
name: tooluniverse-metabolomics-analysis
description: Analyze metabolomics data including metabolite identification, quantification, pathway analysis, and metabolic flux. Processes LC-MS, GC-MS, NMR data from targeted and untargeted experiments. Performs normalization, statistical analysis, pathway enrichment, metabolite-enzyme integration, and biomarker discovery. Use when analyzing metabolomics datasets, identifying differential metabolites, studying metabolic pathways, integrating with transcriptomics/proteomics, discovering metabolic biomarkers, performing flux balance analysis, or characterizing metabolic phenotypes in disease, drug response, or physiological conditions.
---

# Metabolomics Analysis

Comprehensive analysis of metabolomics data from metabolite identification through quantification, statistical analysis, pathway interpretation, and integration with other omics layers.

## Domain Reasoning

Metabolomics quantification depends critically on normalization. Total ion current (TIC) normalization corrects for sample-loading variation and works well for global abundance changes; internal standard normalization is more accurate for targeted analysis where specific metabolite concentrations matter. Missing values in a peak table may reflect signal below the detection limit — not true absence — and should be imputed or handled explicitly rather than treated as zero. Failing to account for batch effects across instrument runs is a frequent source of spurious differential metabolites.

## LOOK UP DON'T GUESS

- Metabolite identities: use `Metabolite_search` and `Metabolite_get_info` to confirm names, CIDs, and HMDB IDs; never assume identity from m/z alone.
- Pathway memberships: query KEGG, MetaCyc, or Reactome tools; do not list pathways from memory.
- Disease associations: retrieve from CTD via `Metabolite_get_diseases`; do not infer clinical relevance without database evidence.
- CV thresholds and QC criteria: apply the values defined in this workflow (CV < 30%, blank ratio > 3x); do not override with guesses.

---

## When to Use This Skill

**Triggers**:
- User has metabolomics data (LC-MS, GC-MS, NMR)
- Questions about metabolite abundance or concentrations
- Differential metabolite analysis requests
- Metabolic pathway analysis
- Multi-omics integration with metabolomics
- Metabolic biomarker discovery
- Flux balance analysis or metabolic modeling
- Metabolite-enzyme correlation

**Example Questions**:
1. "Analyze this LC-MS metabolomics data for differential metabolites"
2. "Which metabolic pathways are dysregulated between conditions?"
3. "Identify metabolite biomarkers for disease classification"
4. "Correlate metabolite levels with enzyme expression"
5. "Perform pathway enrichment for differential metabolites"
6. "Integrate metabolomics with transcriptomics data"

---

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Data Import** | LC-MS, GC-MS, NMR, targeted/untargeted platforms |
| **Metabolite Identification** | Match to HMDB, KEGG, PubChem, spectral libraries |
| **Quality Control** | Peak quality, blank subtraction, internal standard normalization |
| **Normalization** | Probabilistic quotient, total ion current, internal standards |
| **Statistical Analysis** | Univariate and multivariate (PCA, PLS-DA, OPLS-DA) |
| **Differential Analysis** | Identify significant metabolite changes |
| **Pathway Enrichment** | KEGG, Reactome, BioCyc metabolic pathway analysis |
| **Metabolite-Enzyme Integration** | Correlate with expression data |
| **Flux Analysis** | Metabolic flux balance analysis (FBA) |
| **Biomarker Discovery** | Multi-metabolite signatures |

---

## Workflow Overview

```
Input: Metabolomics Data (Peak Table or Spectra)
    |
    v
Phase 1: Data Import & Metabolite Identification
    |-- Load peak table or process raw spectra
    |-- Match features to HMDB, KEGG (accurate mass +/- 5 ppm)
    |-- Confidence scoring (Level 1-4)
    |
    v
Phase 2: Quality Control & Filtering
    |-- CV in QC samples (<30%)
    |-- Blank subtraction (sample/blank > 3)
    |-- Remove features with >50% missing
    |
    v
Phase 3: Normalization
    |-- Sample-wise: TIC, PQN, or internal standards
    |-- Transformation: log2, Pareto, or auto-scaling
    |-- Batch effect correction (if multi-batch)
    |
    v
Phase 4: Exploratory Analysis
    |-- PCA for sample clustering
    |-- PLS-DA for supervised separation
    |-- Outlier detection
    |
    v
Phase 5: Differential Analysis
    |-- t-test / ANOVA / Wilcoxon
    |-- Fold change + FDR correction
    |-- Volcano plots, heatmaps
    |
    v
Phase 6: Pathway Analysis
    |-- Metabolite set enrichment (MSEA)
    |-- KEGG/Reactome pathway mapping
    |-- Pathway topology (hub/bottleneck metabolites)
    |
    v
Phase 7: Multi-Omics Integration
    |-- Metabolite-enzyme Spearman correlation
    |-- Pathway-level concordance scoring
    |-- Metabolic flux inference
    |
    v
Phase 8: Generate Report
    |-- Summary statistics, differential metabolites
    |-- Pathway diagrams, biomarker panel
```

---

## Phase Summaries

### Phase 1: Data Import & Identification
Load peak tables (CSV/TSV) or process raw spectra (mzML). Match features to HMDB by accurate mass (+/- 5 ppm). Assign confidence levels: L1 (standard match), L2 (MS/MS), L3 (mass only), L4 (unknown).

### Phase 2: Quality Control
Assess CV in QC samples (reject >30%), compute blank ratios (keep >3x blank), filter features with >50% missing values. Check internal standard recovery (95-105% acceptable).

### Phase 3: Normalization
Three methods available: TIC (simple, assumes similar total abundance), PQN (robust to large changes, recommended), Internal Standard (most accurate with spiked standards). Follow with log2 transform or Pareto scaling.

### Phase 4: Exploratory Analysis
PCA reveals sample grouping and batch effects. PLS-DA provides supervised separation (report R2 and Q2 for model quality). Flag and investigate outliers.

### Phase 5: Differential Analysis
Welch's t-test (two groups) or ANOVA (multiple groups) with Benjamini-Hochberg FDR correction. Significance thresholds: adj. p < 0.05 and |log2FC| > 1.0.

### Phase 6: Pathway Analysis
Map differential metabolites to KEGG compound IDs. Perform MSEA for pathway enrichment. Consider topology: metabolites at pathway hubs (high degree/betweenness centrality) have greater impact.

### Phase 7: Multi-Omics Integration
Correlate metabolite levels with enzyme expression (Spearman). Expected: substrate-enzyme negative correlation (consumption), product-enzyme positive correlation (production). Score pathway dysregulation using combined metabolite + gene evidence.

### Phase 8: Report
See [report_template.md](report_template.md) for full example output.

---

## Integration with ToolUniverse

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-gene-enrichment` | Pathway enrichment | Phase 6 |
| `tooluniverse-rnaseq-deseq2` | Enzyme expression for integration | Phase 7 |
| `tooluniverse-proteomics-analysis` | Protein levels for integration | Phase 7 |
| `tooluniverse-multi-omics-integration` | Comprehensive integration | Phase 7 |

---

## Quantified Minimums

| Component | Requirement |
|-----------|-------------|
| Metabolites | At least 50 identified metabolites |
| Replicates | At least 3 per condition |
| QC | CV < 30% in QC samples, blank subtraction |
| Statistical test | t-test or Wilcoxon with FDR correction |
| Pathway analysis | MSEA with KEGG or Reactome |
| Report | QC, differential metabolites, pathways, visualizations |

---

## Limitations

- **Identification**: Many features remain unidentified (Level 4)
- **Coverage**: Cannot detect all metabolites (depends on method)
- **Quantification**: Relative abundance (not absolute without standards)
- **Isomers**: Difficult to distinguish structural isomers
- **Ion suppression**: Matrix effects can affect quantification
- **Dynamic range**: Limited compared to targeted methods

---

## References

**Methods**:
- MetaboAnalyst: https://doi.org/10.1093/nar/gkab382
- XCMS: https://doi.org/10.1021/ac051437y
- MSEA: https://doi.org/10.1186/1471-2105-11-395

**Databases**:
- HMDB: https://hmdb.ca
- KEGG Compound: https://www.genome.jp/kegg/compound/
- Reactome: https://reactome.org

---

## Reference Files

- [code_examples.md](code_examples.md) - Python code for all phases (data loading, QC, normalization, statistics, pathway analysis)
- [report_template.md](report_template.md) - Full example report (LC-MS disease vs control)
