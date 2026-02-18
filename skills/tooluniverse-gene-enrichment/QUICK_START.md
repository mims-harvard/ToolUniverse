# Gene Enrichment and Pathway Analysis - Quick Start Guide

Perform comprehensive gene enrichment analysis using gseapy, PANTHER, STRING, and Reactome with cross-validation across 225+ Enrichr libraries.

## Prerequisites

```python
# Required packages
import gseapy
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
```

---

## Use Case 1: Standard GO Enrichment (ORA)

**Question**: "What GO Biological Processes are enriched in my DEG list?"

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

# GO Biological Process ORA
go_bp = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)

# View results
df = go_bp.results
sig = df[df['Adjusted P-value'] < 0.05]
print(f"Significant GO BP terms: {len(sig)}")
print(sig[['Term', 'P-value', 'Adjusted P-value', 'Overlap', 'Genes']].head(10).to_string())

# Example output:
# Term                                                              P-value    Adj P-value  Overlap  Genes
# regulation of G1/S transition of mitotic cell cycle (GO:2000045)  3.35e-13   2.36e-10     6/71    RB1;CCND1;CDK4;PTEN;AKT1;EGFR
# regulation of cell cycle (GO:0051726)                             1.67e-11   5.90e-09     7/296   RB1;CCND1;CDK4;MYC;MDM2;BRCA1;TP53
```

---

## Use Case 2: KEGG Pathway Enrichment

**Question**: "What is the most significantly enriched KEGG pathway?"

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

# KEGG enrichment
kegg = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='KEGG_2021_Human',
    organism='human',
    outdir=None,
    no_plot=True,
)

kegg_sig = kegg.results[kegg.results['Adjusted P-value'] < 0.05]
most_enriched = kegg_sig.iloc[0]
print(f"Most enriched KEGG pathway: {most_enriched['Term']}")
print(f"P-value: {most_enriched['P-value']:.2e}")
print(f"Adjusted P-value: {most_enriched['Adjusted P-value']:.2e}")
print(f"Genes: {most_enriched['Genes']}")
```

---

## Use Case 3: Cross-Validated Enrichment (Multiple Sources)

**Question**: "Which GO terms are confirmed by multiple databases?"

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

# Source 1: gseapy
go_result = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None, no_plot=True,
)

# Source 2: PANTHER
panther_result = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_list),
    organism=9606,
    annotation_dataset='GO:0008150'
)
panther_terms = panther_result.get('data', {}).get('enriched_terms', [])

# Source 3: STRING
string_result = tu.tools.STRING_functional_enrichment(
    protein_ids=gene_list,
    species=9606
)
string_data = string_result.get('data', [])
string_bp = [d for d in string_data if d.get('category') == 'Process'] if isinstance(string_data, list) else []

# Cross-validate: find consensus GO terms
import re
gseapy_go_ids = set()
for term in go_result.results[go_result.results['Adjusted P-value'] < 0.05]['Term']:
    m = re.search(r'(GO:\d+)', term)
    if m:
        gseapy_go_ids.add(m.group(1))

panther_go_ids = set(t['term_id'] for t in panther_terms if t.get('fdr', 1) < 0.05)
string_go_ids = set(d['term'].replace('GOBP:', 'GO:') for d in string_bp if d.get('fdr', 1) < 0.05)

# Consensus = present in 2+ sources
consensus = set()
for go_id in gseapy_go_ids | panther_go_ids | string_go_ids:
    count = sum([go_id in gseapy_go_ids, go_id in panther_go_ids, go_id in string_go_ids])
    if count >= 2:
        consensus.add(go_id)

print(f"Consensus GO BP terms (2+ sources): {len(consensus)}")
```

---

## Use Case 4: GSEA with Ranked Gene List

**Question**: "Using GSEA, which pathways are enriched in my ranked gene list?"

```python
import pandas as pd

# Ranked gene list (e.g., by log2 fold-change)
ranked_genes = {
    "MYC": 4.1, "TP53": 3.2, "BRCA1": 2.8, "RB1": 1.6, "MDM2": 0.8,
    "CCND1": 0.5, "CDK4": 0.3, "NOTCH1": 0.1, "GAPDH": -0.1, "ACTB": -0.3,
    "IL6": -0.5, "TNF": -0.8, "EGFR": -1.5, "PTEN": -2.0, "AKT1": -2.5,
    "VEGFA": -1.2, "KRAS": -0.9, "PIK3CA": -1.8, "MTOR": -1.1, "JAK1": -0.7,
}
ranked_series = pd.Series(ranked_genes).sort_values(ascending=False)

# GSEA preranked
gsea_result = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=3,
    max_size=500,
    permutation_num=1000,
)

# Results
gsea_df = gsea_result.res2d
sig = gsea_df[gsea_df['FDR q-val'].astype(float) < 0.25]
print(f"Significant GSEA terms (FDR < 0.25): {len(sig)}")
print(sig[['Term', 'NES', 'NOM p-val', 'FDR q-val', 'Lead_genes']].head(10).to_string())
```

---

## Use Case 5: Reactome Pathway Enrichment

**Question**: "What Reactome pathways are enriched?"

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

# Via gseapy
reactome_gseapy = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='Reactome_Pathways_2024',
    organism='human',
    outdir=None,
    no_plot=True,
)
print("gseapy Reactome top 5:")
print(reactome_gseapy.results.head(5)[['Term', 'P-value', 'Adjusted P-value']].to_string())

# Via Reactome Analysis Service (cross-validation)
reactome_api = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers=' '.join(gene_list),
    page_size=20
)
pathways = reactome_api.get('data', {}).get('pathways', [])
print(f"\nReactome API top 5:")
for p in pathways[:5]:
    print(f"  {p['name']}: p={p['p_value']:.2e}, fdr={p['fdr']:.2e}, entities={p['entities_found']}")
```

---

## Use Case 6: Multiple Testing Correction

**Question**: "Compare BH vs Bonferroni correction results."

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

go_result = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None, no_plot=True,
)

df = go_result.results
raw_pvals = df['P-value'].values

# Apply different corrections
from statsmodels.stats.multitest import multipletests

_, bh_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='fdr_bh')
_, bonf_pvals, _, _ = multipletests(raw_pvals, alpha=0.05, method='bonferroni')

df['BH_adjusted'] = bh_pvals
df['Bonferroni_adjusted'] = bonf_pvals

n_bh = sum(bh_pvals < 0.05)
n_bonf = sum(bonf_pvals < 0.05)
print(f"Significant by BH: {n_bh}")
print(f"Significant by Bonferroni: {n_bonf}")
```

---

## Use Case 7: Answering Specific Enrichment Questions

**Question**: "What is the adjusted p-value for 'neutrophil activation' from GO enrichment?"

```python
gene_list = [...]  # your gene list

# Run enrichment
result = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None, no_plot=True,
)

# Search for specific term
df = result.results
neutrophil = df[df['Term'].str.contains('neutrophil activation', case=False)]
if not neutrophil.empty:
    row = neutrophil.iloc[0]
    print(f"Term: {row['Term']}")
    print(f"P-value: {row['P-value']:.6e}")
    print(f"Adjusted P-value: {row['Adjusted P-value']:.6e}")
    print(f"Overlap: {row['Overlap']}")
    print(f"Genes: {row['Genes']}")
else:
    print("neutrophil activation not found in results")
```

---

## Use Case 8: Multi-Library Enrichment

**Question**: "Run enrichment across GO, KEGG, Reactome, and MSigDB Hallmark."

```python
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN", "RB1", "MDM2", "CDK4", "CCND1"]

# Multiple libraries in one call
multi = gseapy.enrichr(
    gene_list=gene_list,
    gene_sets=[
        'GO_Biological_Process_2021',
        'GO_Molecular_Function_2021',
        'GO_Cellular_Component_2021',
        'KEGG_2021_Human',
        'Reactome_Pathways_2024',
        'MSigDB_Hallmark_2020',
        'WikiPathways_2024_Human',
    ],
    organism='human',
    outdir=None,
    no_plot=True,
)

# Results grouped by Gene_set column
df = multi.results
for lib in df['Gene_set'].unique():
    lib_df = df[df['Gene_set'] == lib]
    sig = lib_df[lib_df['Adjusted P-value'] < 0.05]
    print(f"{lib}: {len(sig)} significant terms (top: {sig.iloc[0]['Term'] if len(sig) > 0 else 'none'})")
```

---

## Use Case 9: Non-Human Organism Enrichment

**Question**: "Enrich mouse DEGs."

```python
mouse_genes = ["Trp53", "Brca1", "Egfr", "Myc", "Akt1", "Pten", "Rb1", "Mdm2", "Cdk4", "Ccnd1"]

# gseapy with mouse
mouse_result = gseapy.enrichr(
    gene_list=mouse_genes,
    gene_sets='KEGG_2019_Mouse',
    organism='mouse',
    outdir=None,
    no_plot=True,
)

# PANTHER with mouse
panther_mouse = tu.tools.PANTHER_enrichment(
    gene_list=','.join(mouse_genes),
    organism=10090,  # mouse taxonomy ID
    annotation_dataset='GO:0008150'
)

# STRING with mouse
string_mouse = tu.tools.STRING_functional_enrichment(
    protein_ids=mouse_genes,
    species=10090
)
```

---

## Use Case 10: ID Conversion Before Enrichment

**Question**: "My genes are Ensembl IDs, how do I run enrichment?"

```python
ensembl_ids = ["ENSG00000141510", "ENSG00000012048", "ENSG00000146648",
               "ENSG00000136997", "ENSG00000142208"]

# Convert to symbols using MyGene
batch = tu.tools.MyGene_batch_query(
    gene_ids=ensembl_ids,
    fields="symbol,entrezgene,ensembl.gene"
)

results = batch.get('results', batch.get('data', {}).get('results', []))
gene_symbols = [hit.get('symbol', hit['query']) for hit in results if 'symbol' in hit]
print(f"Converted: {gene_symbols}")
# Output: ['TP53', 'BRCA1', 'EGFR', 'MYC', 'AKT1']

# Now run enrichment with symbols
go_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None, no_plot=True,
)
```

---

## Quick Reference: Key Libraries

| Category | Library Name | Year |
|----------|-------------|------|
| GO BP | `GO_Biological_Process_2021` / `2023` / `2025` | 2021-2025 |
| GO MF | `GO_Molecular_Function_2021` / `2023` / `2025` | 2021-2025 |
| GO CC | `GO_Cellular_Component_2021` / `2023` / `2025` | 2021-2025 |
| KEGG | `KEGG_2021_Human` / `KEGG_2026` | 2021/2026 |
| Reactome | `Reactome_2022` / `Reactome_Pathways_2024` | 2022/2024 |
| WikiPathways | `WikiPathways_2024_Human` | 2024 |
| MSigDB Hallmark | `MSigDB_Hallmark_2020` | 2020 |
| BioPlanet | `BioPlanet_2019` | 2019 |
| Disease | `DisGeNET` / `OMIM_Disease` / `ClinVar_2025` | Various |
| Drugs | `DGIdb_Drug_Targets_2024` | 2024 |
| Cells | `CellMarker_2024` / `Azimuth_2023` | 2023/2024 |
| Tissues | `GTEx_Tissues_V8_2023` | 2023 |
| TF | `ChEA_2022` | 2022 |
