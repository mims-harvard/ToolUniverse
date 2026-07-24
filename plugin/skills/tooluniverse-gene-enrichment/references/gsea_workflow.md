# Gene Set Enrichment Analysis (GSEA) Workflow

Complete guide to performing GSEA with gseapy for ranked gene lists.

---

## When to Use GSEA

Use GSEA when:
- You have a **ranked gene list** with scores (e.g., log2FC, t-statistic, signal-to-noise ratio)
- You want to detect **weak but consistent** signals across a gene set
- Statistical test: Running enrichment score with permutation
- Question: "Are genes in this pathway consistently up/down-regulated?"

**Key advantage over ORA**: Detects coordinated changes even when individual genes don't pass significance thresholds.

---

## Step-by-Step GSEA Workflow

### Step 1: Prepare Ranked Gene List

```python
import pandas as pd
import numpy as np

# Option 1: From dictionary
ranked_dict = {"TP53": 3.2, "BRCA1": 2.8, "EGFR": -1.5, "MYC": 4.1, ...}
ranked_series = pd.Series(ranked_dict).sort_values(ascending=False)

# Option 2: From DataFrame (e.g., DESeq2 results)
# df has columns: gene_symbol, log2FoldChange, pvalue, padj
ranked_series = df.set_index('gene_symbol')['log2FoldChange'].sort_values(ascending=False)

# Option 3: Signal-to-noise ratio
# snr = (mean_class1 - mean_class2) / (std_class1 + std_class2)
ranked_series = pd.Series(snr_dict).sort_values(ascending=False)

# Option 4: -log10(p) * sign(FC)
df['rank_metric'] = -np.log10(df['pvalue']) * np.sign(df['log2FoldChange'])
ranked_series = df.set_index('gene_symbol')['rank_metric'].sort_values(ascending=False)
```

**Important**:
- Series must be sorted in descending order (highest scores first)
- Remove NaN values and duplicates
- Use consistent gene symbols

### Step 2: Run GSEA Preranked

```python
import gseapy

# GSEA with GO Biological Process
gsea_bp = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,         # minimum gene set size
    max_size=500,       # maximum gene set size
    permutation_num=1000,  # number of permutations (1000 is standard)
)

# Result columns: Name, Term, ES, NES, NOM p-val, FDR q-val, FWER p-val, Tag %, Gene %, Lead_genes
gsea_bp_df = gsea_bp.res2d

# Filter significant (GSEA uses FDR < 0.25 as standard)
gsea_sig = gsea_bp_df[gsea_bp_df['FDR q-val'].astype(float) < 0.25]

# Key metrics:
# NES (Normalized Enrichment Score): positive = enriched in top of list, negative = enriched in bottom
# NOM p-val: nominal p-value (unadjusted)
# FDR q-val: false discovery rate (adjusted)
# FWER p-val: family-wise error rate (Bonferroni-like)
# Lead_genes: core genes driving enrichment
```

### Step 3: GSEA with Multiple Databases

```python
# KEGG GSEA
gsea_kegg = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='KEGG_2021_Human',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,
    max_size=500,
    permutation_num=1000,
)

# Reactome GSEA
gsea_reactome = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='Reactome_Pathways_2024',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,
    max_size=500,
    permutation_num=1000,
)

# MSigDB Hallmark (cancer hallmarks)
gsea_hallmark = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='MSigDB_Hallmark_2020',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,
    max_size=500,
    permutation_num=1000,
)
```

### Step 4: Multiple Gene Set Libraries

```python
# Run GSEA across multiple libraries
gsea_multi = gseapy.prerank(
    rnk=ranked_series,
    gene_sets=['GO_Biological_Process_2021', 'KEGG_2021_Human', 'MSigDB_Hallmark_2020'],
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,
    max_size=500,
    permutation_num=1000,
)
```

---

## Understanding GSEA Results

### Result DataFrame Columns

| Column | Description | Interpretation |
|--------|-------------|----------------|
| **Name** | Gene set ID | Internal identifier |
| **Term** | Gene set name | Pathway/GO term name |
| **ES** | Enrichment Score | Raw enrichment score (-1 to 1) |
| **NES** | Normalized Enrichment Score | ES normalized to gene set size |
| **NOM p-val** | Nominal p-value | Unadjusted significance |
| **FDR q-val** | False Discovery Rate | Multiple testing corrected |
| **FWER p-val** | Family-Wise Error Rate | Bonferroni-like correction |
| **Tag %** | Percentage of genes before peak | How many genes in set before peak enrichment |
| **Gene %** | Percentage of ranked list before peak | Position in ranked list |
| **Lead_genes** | Core enrichment genes | Genes driving the enrichment signal |

### Interpreting NES (Normalized Enrichment Score)

| NES Value | Interpretation | Meaning |
|-----------|---------------|---------|
| **NES > 0** | Positive enrichment | Gene set enriched in **top** of ranked list (up-regulated) |
| **NES < 0** | Negative enrichment | Gene set enriched in **bottom** of ranked list (down-regulated) |
| **|NES| > 1.5** | Strong enrichment | Moderate to strong signal |
| **|NES| > 2.0** | Very strong enrichment | Strong coordinated change |

### Significance Thresholds

| Threshold | Stringency | Use When |
|-----------|-----------|----------|
| **FDR q-val < 0.25** | Standard | Default for GSEA (more relaxed than ORA) |
| **FDR q-val < 0.05** | Stringent | High-confidence results |
| **FWER p-val < 0.05** | Very stringent | When Bonferroni correction needed |
| **NOM p-val < 0.01** | Alternative | Exploratory without multiple testing |

**Note**: GSEA uses FDR < 0.25 as standard (not 0.05 like ORA) because GSEA is more conservative.

---

## Visualizing GSEA Results

### Top Up-Regulated Pathways

```python
# Positive NES (enriched in up-regulated genes)
gsea_up = gsea_sig[gsea_sig['NES'] > 0].sort_values('NES', ascending=False)
print("Top Up-Regulated Pathways:")
for _, row in gsea_up.head(10).iterrows():
    print(f"  {row['Term']}: NES={row['NES']:.2f}, FDR={row['FDR q-val']:.3e}")
    print(f"    Lead genes: {row['Lead_genes'][:100]}...")
```

### Top Down-Regulated Pathways

```python
# Negative NES (enriched in down-regulated genes)
gsea_down = gsea_sig[gsea_sig['NES'] < 0].sort_values('NES')
print("Top Down-Regulated Pathways:")
for _, row in gsea_down.head(10).iterrows():
    print(f"  {row['Term']}: NES={row['NES']:.2f}, FDR={row['FDR q-val']:.3e}")
    print(f"    Lead genes: {row['Lead_genes'][:100]}...")
```

---

## GSEA vs ORA Comparison

| Aspect | ORA | GSEA |
|--------|-----|------|
| **Input** | Unranked gene list | Ranked gene list with scores |
| **Statistics** | Fisher's exact test | Running enrichment score + permutation |
| **Threshold** | Requires gene selection (e.g., padj < 0.05) | Uses entire ranked list |
| **Sensitivity** | Misses weak but consistent signals | Detects coordinated changes |
| **Specificity** | High (if proper cutoff used) | Moderate (more false positives) |
| **FDR cutoff** | 0.05 (standard) | 0.25 (standard) |
| **Use case** | Distinct gene lists (clusters, DEGs) | Differential expression with fold-changes |

**Rule of thumb**:
- Use **ORA** when you have clear gene lists (e.g., cluster markers, significant DEGs)
- Use **GSEA** when you have ranked data (e.g., all genes with log2FC from DESeq2)

---

## GSEA Result Format Examples

### gseapy.prerank Output

```
Term: regulation of cell cycle (GO:0051726)
ES: 0.623
NES: 2.14
NOM p-val: 0.001
FDR q-val: 0.023
FWER p-val: 0.045
Tag %: 26.7
Gene %: 12.3
Lead_genes: TP53,BRCA1,EGFR,MYC,AKT1,CCND1,CDK4,CDK6,RB1,E2F1
```

**Interpretation**:
- This pathway is **strongly enriched** (NES = 2.14) in the **up-regulated** genes
- FDR = 0.023 means 2.3% chance this is a false positive
- Lead genes (TP53, BRCA1, etc.) are the core genes driving enrichment
- Tag % = 26.7% means 26.7% of genes in this pathway appear before the peak enrichment point

---

## Advanced GSEA Techniques

### Custom Gene Sets

```python
# Define custom gene set dictionary
custom_genesets = {
    'MyCustomPathway1': ['TP53', 'BRCA1', 'EGFR', 'MYC'],
    'MyCustomPathway2': ['AKT1', 'PTEN', 'PIK3CA', 'MTOR'],
    'MyCustomPathway3': ['KRAS', 'NRAS', 'HRAS', 'BRAF'],
}

# Run GSEA with custom gene sets
gsea_custom = gseapy.prerank(
    rnk=ranked_series,
    gene_sets=custom_genesets,
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=3,  # allow smaller sets for custom gene sets
    max_size=500,
    permutation_num=1000,
)
```

### Gene Set Size Filtering

```python
# Filter gene sets by size before GSEA
# (gseapy does this automatically with min_size/max_size, but you can pre-filter)

from gseapy import get_library_name, parser

# Load gene set library
gene_sets = parser.read_gmt('path/to/geneset.gmt')  # or use Enrichr library

# Filter by size
filtered_genesets = {
    name: genes
    for name, genes in gene_sets.items()
    if 10 <= len(genes) <= 200  # custom size range
}

# Run GSEA
gsea_filtered = gseapy.prerank(
    rnk=ranked_series,
    gene_sets=filtered_genesets,
    outdir=None,
    no_plot=True,
    seed=42,
    permutation_num=1000,
)
```

### Parameter Sensitivity Analysis

```python
# Test different permutation numbers
for n_perm in [100, 500, 1000, 5000]:
    gsea_result = gseapy.prerank(
        rnk=ranked_series,
        gene_sets='GO_Biological_Process_2021',
        outdir=None,
        no_plot=True,
        seed=42,
        permutation_num=n_perm,
    )
    sig_count = (gsea_result.res2d['FDR q-val'].astype(float) < 0.25).sum()
    print(f"Permutations: {n_perm}, Significant terms: {sig_count}")
```

---

## Common Issues and Solutions

### Issue 1: No Significant Results

**Problem**: No terms pass FDR < 0.25

**Solutions**:
- Check ranked list quality: Are there extreme outliers?
- Try relaxing to FDR < 0.5 (exploratory)
- Check gene symbol mapping: Are genes recognized?
- Increase permutation_num to 5000 for more stable p-values
- Try ORA instead (different statistical framework)

### Issue 2: Too Many Significant Results

**Problem**: Hundreds of significant terms

**Solutions**:
- Use stricter cutoff (FDR < 0.05 or FWER < 0.05)
- Filter by |NES| > 1.5 (only strong enrichments)
- Report top 20-50 terms by |NES|
- Use more specific gene set libraries (GO BP level 5-7 instead of all levels)

### Issue 3: Unstable Results

**Problem**: Results change between runs

**Solutions**:
- Always set `seed=42` for reproducibility
- Increase `permutation_num` from 1000 to 5000
- Check for ties in ranked list (same scores for many genes)

### Issue 4: Warning: "No gene sets pass filtering"

**Problem**: Gene sets don't match gene names in ranked list

**Solutions**:
- Check gene symbol format (uppercase? with spaces?)
- Try different gene set library versions
- Convert gene symbols to common format (HGNC)
- Check min_size/max_size parameters (may be filtering all sets)

---

## Best Practices

1. **Always set random seed** (`seed=42`) for reproducibility
2. **Use entire ranked list** (don't pre-filter by significance)
3. **Sort in descending order** (highest scores first)
4. **Remove duplicates** (average or max if gene appears multiple times)
5. **Use appropriate ranking metric**:
   - log2FC: simple, interpretable
   - -log10(p) × sign(FC): weights by significance
   - Signal-to-noise ratio: classic GSEA metric
6. **Use standard FDR < 0.25** (not 0.05 like ORA)
7. **Report NES with FDR** (not just NES alone)
8. **Interpret lead genes** (core enrichment, not all genes in set)
9. **Compare up vs down** (positive vs negative NES)
10. **Cross-validate with ORA** (run ORA on top/bottom genes as sanity check)

---

## GSEA Report Template

```markdown
## GSEA Results

### Ranking Metric
- **Metric**: log2 Fold Change
- **Total genes ranked**: 15,234
- **Score range**: -8.5 to 12.3

### Top Up-Regulated Pathways (NES > 0)
| Rank | Pathway | NES | FDR q-val | Lead Genes |
|------|---------|-----|-----------|------------|
| 1 | Cell cycle (GO:0007049) | 2.34 | 0.001 | TP53, BRCA1, EGFR, MYC, CDK4 |
| 2 | DNA repair (GO:0006281) | 2.12 | 0.003 | BRCA1, RAD51, XRCC4, LIG4 |

### Top Down-Regulated Pathways (NES < 0)
| Rank | Pathway | NES | FDR q-val | Lead Genes |
|------|---------|-----|-----------|------------|
| 1 | Immune response (GO:0006955) | -2.01 | 0.012 | IL6, TNF, IFNG, CXCL10 |
| 2 | Inflammatory response (GO:0006954) | -1.89 | 0.018 | IL1B, TNF, IL6, CCL2 |

### Summary Statistics
- **Total gene sets tested**: 8,456
- **Significant at FDR < 0.25**: 234 (2.8%)
- **Positive NES**: 142 (up-regulated pathways)
- **Negative NES**: 92 (down-regulated pathways)
- **Permutations**: 1,000
- **Gene set size range**: 5-500 genes
```

---

See also:
- ora_workflow.md - For unranked gene lists
- enrichr_guide.md - All available libraries
- cross_validation.md - Multi-source validation strategies
