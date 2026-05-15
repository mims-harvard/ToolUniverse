# Proteomics Analysis - Phase Details

## Phase 1: Data Import & QC

**Supported input formats**:
- **MaxQuant**: `proteinGroups.txt`, `evidence.txt`, `Phospho (STY)Sites.txt`
- **Spectronaut**: `*_Report.tsv`
- **DIA-NN**: `report.tsv`, `report.pr_matrix.tsv`
- **Proteome Discoverer**: `*_Proteins.txt`, `*_PSMs.txt`

**QC checks**:
1. Missing value assessment per protein and per sample
2. Log10 intensity distribution boxplots (expect similar median/spread)
3. Sample-sample Pearson correlation (high within replicates)
4. PCA for sample clustering (expect separation by condition)

## Phase 2: Preprocessing & Normalization

1. **Filter**: Keep proteins with 2+ unique peptides and detected in min 3 samples. Remove contaminants (CON__) and reverse (REV__) sequences.
2. **Impute**: MinProb for MNAR assumption (random low values), KNN for MAR assumption.
3. **Normalize**: Median normalization (divide by sample median, multiply by global median), or quantile normalization.

## Phase 3: Differential Expression

1. For each protein, calculate log2 fold change between conditions
2. Welch's t-test (unequal variance) per protein
3. BH multiple testing correction
4. Classify significant: adj_p < 0.05 AND |log2FC| > 1.0
5. Generate volcano plot

## Phase 4: PTM Analysis

1. Load modification-specific peptides (e.g., Phospho (STY)Sites.txt)
2. Filter by localization probability > 0.75
3. Construct site identifiers: `GENE_AminoAcidPosition` (e.g., AKT1_S473)
4. Differential analysis same as Phase 3
5. Predict upstream kinases using kinase-substrate databases

## Phase 5: Functional Enrichment

Run enrichment for significant proteins using ToolUniverse:
- `enrichr_enrich` with libraries: `KEGG_2021_Human`, `Reactome_2022`, `GO_Biological_Process_2021`
- Protein complex enrichment against CORUM database
- Tissue-specific enrichment if relevant

## Phase 6: Protein-Protein Interactions

1. Query STRING for interaction networks (confidence > 0.7)
2. Build network graph (nodes = proteins, edges = interactions)
3. Detect modules/communities using greedy modularity
4. Identify hub proteins (high degree/betweenness centrality)
5. Annotate modules with enriched functions

## Phase 7: Multi-Omics Integration

1. Match protein and RNA data by gene name across common samples
2. Spearman correlation per gene (expected r ~ 0.4-0.6)
3. Classify regulation: transcriptional (r > 0.6), translational (high protein + low RNA, r < 0.2), degradation (low protein + high RNA)
4. Enrichment analysis on post-transcriptionally regulated genes

## Phase 8: Report Generation

### Report Structure

1. **Dataset Summary**: Platform, samples, conditions, proteins quantified
2. **QC Results**: Missing value heatmap, intensity distributions, PCA plot, replicate correlations
3. **Differential Expression**: Volcano plot, significant protein table (gene, log2FC, adj_p), MA plot
4. **PTM Analysis** (if applicable): Modified sites table, kinase activity predictions
5. **Pathway Enrichment**: Top enriched GO terms, KEGG/Reactome pathways with bar/dot plots
6. **PPI Networks**: STRING network visualization, hub proteins, module annotations
7. **Multi-Omics** (if applicable): Protein-RNA correlation scatter, translation-regulated genes
8. **Conclusions**: Key findings, limitations, suggested follow-up experiments
