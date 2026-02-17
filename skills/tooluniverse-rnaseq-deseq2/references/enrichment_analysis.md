# Enrichment Analysis with gseapy

Complete guide to pathway and GO enrichment analysis.

## Basic Over-Representation Analysis (ORA)

```python
import gseapy as gp

# Prepare gene list (from DESeq2 results)
sig_genes = results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)]
gene_list = sig_genes.index.tolist()

# Run enrichment
enr = gp.enrich(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2023',
    background=None,  # or provide background gene list
    outdir=None,  # Don't save files
    cutoff=0.05,
    no_plot=True,
    verbose=False
)

# Access results
results_df = enr.results
print(results_df.head(10))
```

## Gene Set Library Selection

### Gene Ontology (GO)

```python
# Human/Mouse GO Biological Process (most recent)
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Biological_Process_2023')

# GO Molecular Function
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Molecular_Function_2021')

# GO Cellular Component
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Cellular_Component_2021')
```

### KEGG Pathways

```python
# Human KEGG
enr = gp.enrich(gene_list=gene_list, gene_sets='KEGG_2021_Human')

# Mouse KEGG
enr = gp.enrich(gene_list=gene_list, gene_sets='KEGG_2019_Mouse')
```

### Reactome

```python
enr = gp.enrich(gene_list=gene_list, gene_sets='Reactome_2022')
```

### WikiPathways

```python
# Human
enr = gp.enrich(gene_list=gene_list, gene_sets='WikiPathways_2019_Human')

# Mouse
enr = gp.enrich(gene_list=gene_list, gene_sets='WikiPathways_2019_Mouse')
```

### Other Libraries

```python
# MSigDB Hallmark gene sets
enr = gp.enrich(gene_list=gene_list, gene_sets='MSigDB_Hallmark_2020')

# GWAS Catalog
enr = gp.enrich(gene_list=gene_list, gene_sets='GWAS_Catalog_2019')

# BioCarta
enr = gp.enrich(gene_list=gene_list, gene_sets='BioCarta_2016')
```

## Using Background Gene Sets

```python
# Background = all genes tested in DESeq2
background = results.dropna(subset=['padj']).index.tolist()

enr = gp.enrich(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2023',
    background=background,  # Provide background
    outdir=None,
    cutoff=0.05
)
```

## Extract Specific Results

```python
def extract_enrichment_answer(enr_results, term_query=None, metric='Adjusted P-value'):
    """Extract specific enrichment result.

    Args:
        enr_results: gseapy enrichment results DataFrame
        term_query: String to search in Term column (case-insensitive)
        metric: Column to return ('Adjusted P-value', 'Odds Ratio', 'P-value', etc.)

    Returns:
        Value or DataFrame of matches
    """
    if term_query:
        # Case-insensitive search
        mask = enr_results['Term'].str.lower().str.contains(term_query.lower())
        matches = enr_results[mask]
        if len(matches) == 1:
            return matches.iloc[0][metric]
        elif len(matches) > 1:
            return matches[['Term', metric]]
        else:
            return None

    # Return top result
    return enr_results.sort_values(metric).head(1)

# Usage
enr = gp.enrich(gene_list=gene_list, gene_sets='KEGG_2021_Human')
pval = extract_enrichment_answer(enr.results, term_query='ABC transporters', metric='Adjusted P-value')
print(f"ABC transporters adjusted p-value: {pval}")
```

## Extract Gene Count in Pathway

```python
# Enrichment results have 'Overlap' column (e.g., "11/42")
# Also 'Genes' column with semicolon-separated gene list

pathway_row = enr.results[enr.results['Term'].str.contains('ABC transporters')].iloc[0]

# Number of DEGs in pathway
overlap_str = pathway_row['Overlap']  # e.g., "11/42"
n_overlap = int(overlap_str.split('/')[0])  # 11

# Pathway size
n_pathway = int(overlap_str.split('/')[1])  # 42

# Gene list
genes_in_pathway = pathway_row['Genes'].split(';')
print(f"{n_overlap} genes contribute to this pathway:")
print(genes_in_pathway)
```

## Multi-Library Enrichment

```python
# Run enrichment on multiple libraries
libraries = [
    'GO_Biological_Process_2023',
    'KEGG_2021_Human',
    'Reactome_2022'
]

all_results = {}
for lib in libraries:
    enr = gp.enrich(
        gene_list=gene_list,
        gene_sets=lib,
        outdir=None,
        cutoff=0.05,
        no_plot=True,
        verbose=False
    )
    all_results[lib] = enr.results

# Combine top results
combined = []
for lib, res in all_results.items():
    top5 = res.head(5).copy()
    top5['Library'] = lib
    combined.append(top5)
combined_df = pd.concat(combined, ignore_index=True)
```

## GO Term Simplification

```python
def simplify_go_terms(enr_results, similarity_threshold=0.7):
    """Simplify GO terms by removing highly similar terms.

    Approximation of R clusterProfiler::simplify().
    Uses Jaccard similarity on gene sets.
    """
    if len(enr_results) == 0:
        return enr_results

    # Parse gene sets from Genes column
    terms = enr_results.sort_values('Adjusted P-value').copy()
    gene_sets = {}
    for _, row in terms.iterrows():
        genes = set(row['Genes'].split(';'))
        gene_sets[row['Term']] = genes

    # Compute Jaccard similarity between terms
    keep = []
    removed = set()

    for i, (term_i, genes_i) in enumerate(gene_sets.items()):
        if term_i in removed:
            continue
        keep.append(term_i)

        for term_j, genes_j in list(gene_sets.items())[i+1:]:
            if term_j in removed:
                continue
            # Jaccard similarity
            intersection = len(genes_i & genes_j)
            union = len(genes_i | genes_j)
            if union > 0:
                similarity = intersection / union
                if similarity > similarity_threshold:
                    removed.add(term_j)  # Remove the less significant term

    return terms[terms['Term'].isin(keep)]

# Usage
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Biological_Process_2023')
simplified = simplify_go_terms(enr.results, similarity_threshold=0.7)
print(f"Original: {len(enr.results)} terms")
print(f"Simplified: {len(simplified)} terms")
```

## Gene Set Enrichment Analysis (GSEA)

```python
# GSEA requires ranked gene list (not just significant genes)
# Rank by -log10(pvalue) * sign(log2FC)

results_ranked = results.dropna(subset=['pvalue', 'log2FoldChange'])
results_ranked['rank'] = -np.log10(results_ranked['pvalue']) * np.sign(results_ranked['log2FoldChange'])
results_ranked = results_ranked.sort_values('rank', ascending=False)

# Create rank dictionary
rank_dict = dict(zip(results_ranked.index, results_ranked['rank']))

# Run GSEA
gsea_res = gp.prerank(
    rnk=rank_dict,
    gene_sets='KEGG_2021_Human',
    outdir=None,
    permutation_num=1000,
    no_plot=True,
    verbose=False
)

# Access results
gsea_df = gsea_res.res2d
print(gsea_df[gsea_df['FDR q-val'] < 0.05])
```

## Organism-Specific Libraries

### Human

```python
libraries_human = [
    'GO_Biological_Process_2023',
    'GO_Molecular_Function_2021',
    'GO_Cellular_Component_2021',
    'KEGG_2021_Human',
    'Reactome_2022',
    'WikiPathways_2019_Human',
    'MSigDB_Hallmark_2020',
    'BioCarta_2016'
]
```

### Mouse

```python
libraries_mouse = [
    'GO_Biological_Process_2023',
    'GO_Molecular_Function_2021',
    'GO_Cellular_Component_2021',
    'KEGG_2019_Mouse',
    'WikiPathways_2019_Mouse'
]
```

### Other Organisms

For other organisms, use custom gene sets:

```python
# Load custom GMT file
enr = gp.enrich(
    gene_list=gene_list,
    gene_sets='/path/to/custom.gmt',
    background=background
)
```

## Complete Example: DEG to Enrichment

```python
import pandas as pd
import gseapy as gp
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Run DESeq2 (from pydeseq2_workflow.md)
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
results = stat_res.results_df

# Filter DEGs
sig_genes = results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)]
gene_list = sig_genes.index.tolist()

# Run GO enrichment
enr_go = gp.enrich(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2023',
    background=results.dropna(subset=['padj']).index.tolist(),
    outdir=None,
    cutoff=0.05,
    no_plot=True,
    verbose=False
)

# Run KEGG enrichment
enr_kegg = gp.enrich(
    gene_list=gene_list,
    gene_sets='KEGG_2021_Human',
    background=results.dropna(subset=['padj']).index.tolist(),
    outdir=None,
    cutoff=0.05,
    no_plot=True,
    verbose=False
)

# Display top results
print("\nTop 5 GO terms:")
print(enr_go.results[['Term', 'Adjusted P-value', 'Overlap']].head(5))

print("\nTop 5 KEGG pathways:")
print(enr_kegg.results[['Term', 'Adjusted P-value', 'Overlap']].head(5))

# Answer specific question
if 'immune response' in question.lower():
    immune_result = enr_go.results[enr_go.results['Term'].str.contains('immune', case=False)]
    if len(immune_result) > 0:
        answer = immune_result.iloc[0]['Adjusted P-value']
        print(f"\nImmune response adjusted p-value: {answer}")
```

## Common BixBench Enrichment Patterns

### Pattern 1: Extract adjusted p-value for specific pathway

```python
enr = gp.enrich(gene_list=gene_list, gene_sets='KEGG_2021_Human')
pathway = enr.results[enr.results['Term'].str.contains('ABC transporters')]
answer = round(pathway.iloc[0]['Adjusted P-value'], 4)
```

### Pattern 2: Count significant pathways

```python
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Biological_Process_2023', cutoff=0.05)
answer = len(enr.results[enr.results['Adjusted P-value'] < 0.05])
```

### Pattern 3: Gene count in pathway

```python
pathway = enr.results[enr.results['Term'].str.contains('ribosome')]
overlap = pathway.iloc[0]['Overlap']  # e.g., "25/150"
answer = int(overlap.split('/')[0])  # 25
```

### Pattern 4: Simplify GO terms

```python
enr = gp.enrich(gene_list=gene_list, gene_sets='GO_Biological_Process_2023')
simplified = simplify_go_terms(enr.results, similarity_threshold=0.7)
answer = len(simplified)
```
