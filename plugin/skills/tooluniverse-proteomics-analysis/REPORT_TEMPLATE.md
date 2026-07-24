# Report Template: Proteomics Analysis

```markdown
# Proteomics Analysis Report

## Dataset Summary
- **Samples**: X (Y disease, Z control)
- **Proteins Identified**: N
- **Proteins Quantified**: N (at least 3 samples)
- **Platform**: [instrument], [software version]

## Quality Control
- **Missing Values**: X% average per protein
- **Sample Correlation**: X-X within groups
- **PCA**: [separation description] (PC1: X% variance)

## Differential Expression
- **Significant Proteins**: N (adj. p < 0.05, |log2FC| > 1)
  - Upregulated: N proteins
  - Downregulated: N proteins
- **Top upregulated**: [gene] (log2FC=X), [gene] (log2FC=X)
- **Top downregulated**: [gene] (log2FC=X), [gene] (log2FC=X)

## Phosphoproteomics
- **Phosphosites Quantified**: N
- **Differentially Phosphorylated**: N sites (p < 0.05)
- **Top Predicted Kinases**: [kinase1], [kinase2], [kinase3]

## Pathway Enrichment
### Top Pathways (Upregulated)
1. **[Pathway]** (p=X) - N proteins
2. **[Pathway]** (p=X) - N proteins

### Top Pathways (Downregulated)
1. **[Pathway]** (p=X) - N proteins
2. **[Pathway]** (p=X) - N proteins

## Protein Network Analysis
- **Network**: N nodes, N edges (STRING confidence > 0.7)
- **Modules Detected**: N functional modules
  - Module 1: [function] (N proteins)
  - Module 2: [function] (N proteins)

## Protein-RNA Correlation
- **Overall Correlation**: r = X (moderate, expected)
- **High Correlation**: N genes (r > 0.6) - transcriptional regulation
- **Low Correlation**: N genes (r < 0.2) - post-transcriptional regulation
- **Translation-Regulated**: N proteins (high protein, low RNA)

## Biological Interpretation
[Summary of key biological findings]

## Potential Biomarkers
Top proteins for classification (AUC=X):
1. [protein] (type)
2. [protein] (type)
```

## Example Use Cases

### Use Case 1: Cancer Proteomics
**Question**: "Analyze proteomics data from breast cancer vs normal tissue"
**Workflow**: Load MaxQuant -> QC/filter -> Impute/normalize -> DE (432 sig) -> Pathway enrichment -> STRING network -> Integrate with RNA-seq -> Report with biomarkers

### Use Case 2: Phosphoproteomics Signaling
**Question**: "What kinase signaling is activated in response to drug treatment?"
**Workflow**: Load Phospho Sites -> Filter by localization -> Differential phosphorylation -> Kinase prediction -> MAPK/PI3K pathway enrichment -> Report

### Use Case 3: Protein-RNA Integration
**Question**: "Which proteins are regulated post-transcriptionally?"
**Workflow**: Load proteomics + RNA-seq -> Match samples -> Correlate per gene -> Classify low-correlation genes -> Enrichment for post-transcriptional regulators -> Report
