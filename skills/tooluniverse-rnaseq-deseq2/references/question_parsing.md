# Question Parsing Guide

Extract parameters from user questions before analysis.

## Parameter Extraction Table

| Parameter | Default | Example Question Text |
|-----------|---------|----------------------|
| **padj threshold** | 0.05 | "padj < 0.05", "adjusted p-value < 0.01" |
| **log2FC threshold** | 0 (no filter) | "|log2FC| > 0.5", "absolute log2 fold change > 1.5" |
| **baseMean threshold** | 0 (no filter) | "baseMean > 10", "removing those with <10 expression counts" |
| **LFC shrinkage** | No | "with lfc shrinkage", "type=apeglm" |
| **Design formula** | ~condition | "Account for Replicate, Strain, and Media" |
| **Contrast** | Infer from context | "condition_A vs condition_B", "mutant vs wildtype", "case vs control" |
| **Enrichment** | None | "enrichGO", "KEGG", "gseapy", "Reactome" |
| **Specific gene** | None | "What is the padj for gene X?" |
| **Direction filter** | Both | "upregulated", "downregulated" |
| **Multiple testing** | BH (default) | "Bonferroni correction", "Benjamini-Yekutieli" |

## File Discovery

Look in the working directory for:

```python
import os
import glob

# List all data files
data_dir = "."  # or specified path
all_files = glob.glob(os.path.join(data_dir, "**/*"), recursive=True)
data_files = [f for f in all_files if f.endswith(('.csv', '.tsv', '.txt', '.h5ad', '.rds', '.h5'))]

# Common patterns
count_files = [f for f in data_files if any(x in f.lower() for x in ['count', 'expression', 'matrix'])]
meta_files = [f for f in data_files if any(x in f.lower() for x in ['metadata', 'coldata', 'sample', 'design', 'pheno'])]
```

## Decision Tree

```
Q: Is there a count matrix file?
  YES -> Load and proceed to validation
  NO  -> Q: Is there an h5ad/AnnData file?
           YES -> Load with anndata, extract counts
           NO  -> Q: Is there processed DE results already?
                    YES -> Skip to filtering/enrichment
                    NO  -> ERROR: No suitable input data found
```

## Multi-Factor Design Examples

**Question**: "Account for Replicate, Strain, and Media"
```python
design = "~Replicate + Strain + Media"
```

**Question**: "Control for batch effects"
```python
design = "~batch + condition"
```

**Question**: "Include interaction between strain and treatment"
```python
design = "~strain + treatment + strain:treatment"
```

## Contrast Parsing

**Question**: "mutant vs wildtype"
```python
contrast = ['condition', 'mutant', 'wildtype']
```

**Question**: "Compare treatment to control"
```python
contrast = ['condition', 'treatment', 'control']
```

**Question**: "Effect of strain B relative to strain A"
```python
contrast = ['strain', 'B', 'A']
```

## Subset Identification

**Question**: "Analyze control mice only"
```python
subset = metadata[metadata['treatment'] == 'control']
```

**Question**: "Excluding the third replicates"
```python
subset = metadata[metadata['replicate'] != 3]
```

**Question**: "CD4 and CD8 cells only"
```python
subset = metadata[metadata['cell_type'].isin(['CD4', 'CD8'])]
```

## Enrichment Library Selection

| Question Text | gseapy Library |
|--------------|----------------|
| "enrichGO" + human | `GO_Biological_Process_2023` |
| "enrichGO" + mouse | `GO_Biological_Process_2023` |
| "KEGG" + human | `KEGG_2021_Human` |
| "KEGG" + mouse | `KEGG_2019_Mouse` |
| "Reactome" | `Reactome_2022` |
| "WikiPathways" + mouse | `WikiPathways_2019_Mouse` |
| "GO Process" | `GO_Biological_Process_2023` |
| "GO Function" | `GO_Molecular_Function_2021` |
| "GO Component" | `GO_Cellular_Component_2021` |

## Organism Detection

```python
def detect_organism(metadata, gene_names):
    """Detect organism from gene naming patterns."""
    # Check gene names
    if any(g.startswith('ENSG') for g in gene_names[:100]):
        return 'homo_sapiens'
    elif any(g.startswith('ENSMUSG') for g in gene_names[:100]):
        return 'mus_musculus'

    # Check metadata columns
    if 'organism' in metadata.columns:
        org = metadata['organism'].iloc[0].lower()
        if 'human' in org or 'sapiens' in org:
            return 'homo_sapiens'
        elif 'mouse' in org or 'musculus' in org:
            return 'mus_musculus'

    return 'unknown'
```
