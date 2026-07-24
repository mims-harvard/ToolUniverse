# Over-Representation Analysis (ORA) Workflow

Complete guide to performing ORA enrichment analysis with gseapy and ToolUniverse tools.

---

## When to Use ORA

Use ORA when:
- You have an **unranked gene list** (e.g., DEGs from differential expression)
- No fold-change or score information available
- Statistical test: Fisher's exact test / hypergeometric test
- Question: "Are genes from my list over-represented in this pathway?"

---

## Step-by-Step ORA Workflow

### Step 1: GO Biological Process Enrichment

```python
import gseapy
import pandas as pd

# GO Biological Process ORA
go_bp_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Biological_Process_2021',  # or 2023, 2025
    organism='human',  # 'human', 'mouse', 'fly', 'yeast', 'worm', 'fish', 'rat'
    outdir=None,        # None = no file output
    no_plot=True,       # suppress plots for programmatic use
    background=None,    # None = Enrichr default background
)

# Result is Enrichr object with .results DataFrame
# Columns: Gene_set, Term, Overlap, P-value, Adjusted P-value,
#          Old P-value, Old Adjusted P-value, Odds Ratio, Combined Score, Genes
go_bp_df = go_bp_result.results

# Filter by significance
go_bp_sig = go_bp_df[go_bp_df['Adjusted P-value'] < 0.05].copy()

# Extract key info
for _, row in go_bp_sig.head(10).iterrows():
    term = row['Term']
    pval = row['P-value']
    adj_pval = row['Adjusted P-value']
    overlap = row['Overlap']
    genes = row['Genes']
    odds_ratio = row['Odds Ratio']
    combined_score = row['Combined Score']
    print(f"{term}: adj_p={adj_pval:.2e}, overlap={overlap}, genes={genes}")
```

### Step 2: GO Molecular Function and Cellular Component

```python
# GO Molecular Function
go_mf_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Molecular_Function_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
go_mf_df = go_mf_result.results

# GO Cellular Component
go_cc_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Cellular_Component_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
go_cc_df = go_cc_result.results
```

### Step 3: KEGG Pathway Enrichment

```python
# KEGG via gseapy
kegg_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='KEGG_2021_Human',  # or KEGG_2026
    organism='human',
    outdir=None,
    no_plot=True,
)
kegg_df = kegg_result.results
kegg_sig = kegg_df[kegg_df['Adjusted P-value'] < 0.05]
```

### Step 4: Reactome Pathway Enrichment

```python
# Reactome via gseapy
reactome_gseapy = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='Reactome_Pathways_2024',  # or Reactome_2022
    organism='human',
    outdir=None,
    no_plot=True,
)
reactome_df = reactome_gseapy.results
```

### Step 5: MSigDB Hallmark and Other Libraries

```python
# MSigDB Hallmark
hallmark_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='MSigDB_Hallmark_2020',
    organism='human',
    outdir=None,
    no_plot=True,
)
hallmark_df = hallmark_result.results

# WikiPathways
wp_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='WikiPathways_2024_Human',
    organism='human',
    outdir=None,
    no_plot=True,
)
wp_df = wp_result.results

# Multiple libraries at once
multi_result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets=['GO_Biological_Process_2021', 'KEGG_2021_Human', 'Reactome_2022'],
    organism='human',
    outdir=None,
    no_plot=True,
)
# Results combined in single DataFrame with Gene_set column distinguishing libraries
```

### Step 6: Custom Background Gene Set

```python
# With custom background (e.g., all expressed genes)
background_genes = ["GENE1", "GENE2", ...]  # user-provided

# gseapy enrichr with background
result_with_bg = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
    background=background_genes,  # custom background
)
# Note: background changes p-value calculation significantly
```

---

## Understanding ORA Results

### Result DataFrame Columns

| Column | Description | Interpretation |
|--------|-------------|----------------|
| **Term** | GO term or pathway name | What biological process/pathway |
| **P-value** | Raw p-value from Fisher's exact test | Uncorrected significance |
| **Adjusted P-value** | BH-corrected p-value | Multiple testing corrected significance |
| **Overlap** | Format: "X/Y" | X genes from your list in pathway of size Y |
| **Odds Ratio** | Enrichment magnitude | >1 = over-represented, <1 = under-represented |
| **Combined Score** | log(p) × z-score(OR) | Enrichr's ranking metric |
| **Genes** | Semicolon-separated | Which genes from your list are in this pathway |

### Significance Thresholds

| Threshold | Stringency | Use When |
|-----------|-----------|----------|
| **Adjusted P < 0.05** | Standard | Default for most analyses |
| **Adjusted P < 0.01** | Stringent | High-confidence results only |
| **Adjusted P < 0.1** | Relaxed | Exploratory analysis |
| **P < 0.001 (raw)** | Alternative | When Bonferroni too stringent |

---

## Cross-Validation with ToolUniverse

Always validate gseapy results with at least one independent tool:

### PANTHER Enrichment (T1 - Curated)

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# PANTHER ORA - GO Biological Process
panther_bp = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_symbols),  # comma-separated string
    organism=9606,                      # NCBI taxonomy ID
    annotation_dataset='GO:0008150'     # biological_process
)
# Returns: {data: {gene_list, organism, annotation_dataset, result_count, enriched_terms: [
#   {term_id, term_label, number_in_list, number_in_reference, expected, fold_enrichment, pvalue, fdr, direction}
# ]}}
panther_terms = panther_bp.get('data', {}).get('enriched_terms', [])

# PANTHER - GO Molecular Function
panther_mf = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_symbols),
    organism=9606,
    annotation_dataset='GO:0003674'  # molecular_function
)

# PANTHER - GO Cellular Component
panther_cc = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_symbols),
    organism=9606,
    annotation_dataset='GO:0005575'  # cellular_component
)

# PANTHER - PANTHER Pathways
panther_pw = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_symbols),
    organism=9606,
    annotation_dataset='ANNOT_TYPE_ID_PANTHER_PATHWAY'
)

# PANTHER - Reactome Pathways
panther_reactome = tu.tools.PANTHER_enrichment(
    gene_list=','.join(gene_symbols),
    organism=9606,
    annotation_dataset='ANNOT_TYPE_ID_PANTHER_REACTOME_PATHWAY'
)
```

### STRING Functional Enrichment (T2 - Validated)

```python
# STRING enrichment - returns ALL categories at once
# Categories: Process, Function, Component, KEGG, Reactome, COMPARTMENTS, DISEASES, etc.
string_enrichment = tu.tools.STRING_functional_enrichment(
    protein_ids=gene_symbols,
    species=9606
)
# Returns: {status: "success", data: [
#   {category, term, number_of_genes, number_of_genes_in_background, inputGenes, preferredNames, p_value, fdr, description}
# ]}

# NOTE: STRING returns ALL categories regardless of 'category' parameter
# Filter by category:
string_data = string_enrichment.get('data', [])
if isinstance(string_data, list):
    string_go_bp = [d for d in string_data if d.get('category') == 'Process']
    string_go_mf = [d for d in string_data if d.get('category') == 'Function']
    string_go_cc = [d for d in string_data if d.get('category') == 'Component']
    string_kegg = [d for d in string_data if d.get('category') == 'KEGG']
    string_reactome = [d for d in string_data if d.get('category') == 'Reactome']
    string_wp = [d for d in string_data if d.get('category') == 'WikiPathways']
```

### Reactome Analysis Service (T1 - Curated)

```python
# Reactome pathway overrepresentation analysis
reactome_result = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers=' '.join(gene_symbols),  # space-separated, NOT array
    page_size=50,                         # max pathways to return
    include_disease=True,                 # include disease pathways
    projection=True                       # project to human (for cross-species)
)
# Returns: {data: {token, analysis_type, identifiers_not_found, pathways_found, pathways: [
#   {pathway_id, name, species, is_disease, is_lowest_level, entities_found, entities_total,
#    entities_ratio, p_value, fdr, reactions_found, reactions_total}
# ]}}

reactome_pathways = reactome_result.get('data', {}).get('pathways', [])
# Filter significant
reactome_sig = [p for p in reactome_pathways if p.get('fdr', 1) < 0.05]
```

---

## ORA Result Format Examples

### gseapy.enrichr Output

```
Gene_set: GO_Biological_Process_2021
Term: regulation of cell cycle (GO:0051726)
Overlap: 12/45
P-value: 1.234e-08
Adjusted P-value: 3.456e-06
Odds Ratio: 8.7
Combined Score: 245.3
Genes: TP53;BRCA1;EGFR;MYC;AKT1;...
```

### PANTHER Output

```json
{
  "term_id": "GO:0051726",
  "term_label": "regulation of cell cycle",
  "number_in_list": 12,
  "number_in_reference": 450,
  "expected": 2.3,
  "fold_enrichment": 5.2,
  "pvalue": 2.1e-07,
  "fdr": 4.5e-05,
  "direction": "+"
}
```

### STRING Output

```json
{
  "category": "Process",
  "term": "GO:0051726",
  "description": "regulation of cell cycle",
  "number_of_genes": 12,
  "number_of_genes_in_background": 450,
  "p_value": 1.8e-07,
  "fdr": 3.2e-05,
  "inputGenes": "TP53,BRCA1,EGFR,MYC,AKT1,...",
  "preferredNames": "TP53,BRCA1,EGFR,MYC,AKT1,..."
}
```

---

## Common Issues and Solutions

### Issue 1: Small Gene Lists (<5 genes)

**Problem**: ORA has insufficient statistical power with very small lists

**Solutions**:
- Use PANTHER and STRING (handle small lists better)
- Consider gene-level annotation (GO_get_annotations_for_gene) instead
- Report as exploratory analysis only

### Issue 2: Very Large Gene Lists (>500 genes)

**Problem**: Enrichment becomes less specific

**Solutions**:
- Use stricter significance cutoff (padj < 0.01)
- Recommend custom background (expressed genes only)
- Focus on most specific (lowest-level) GO terms
- Use GO Slim for high-level overview

### Issue 3: No Significant Results

**Problem**: No terms pass significance threshold

**Solutions**:
- Verify gene symbols are valid (STRING_map_identifiers)
- Try different library versions (2021 vs 2023 vs 2025)
- Try relaxing cutoff (padj < 0.1)
- Consider GSEA as alternative
- Report as valid finding: "No significant enrichment"

### Issue 4: Too Many Significant Results

**Problem**: Hundreds of significant terms

**Solutions**:
- Use stricter cutoff
- Filter by gene set size (remove very broad terms)
- Report top 20-50 terms only
- Use redundancy reduction (group similar GO terms)

---

## Best Practices

1. **Always apply multiple testing correction** (default: Benjamini-Hochberg)
2. **Cross-validate with at least 2 tools** (gseapy + PANTHER + STRING)
3. **Report exact p-values and adjusted p-values**
4. **Document background gene set** (genome-wide or custom)
5. **Filter by gene set size** (5-500 genes recommended)
6. **Report genes driving enrichment** (not just term names)
7. **Grade evidence** (T1-T4 tiers)
8. **Include negative results** ("no significant enrichment" is informative)
9. **Provide completeness checklist** (show what was tested)
10. **Reference tools and databases used**

---

See also:
- gsea_workflow.md - For ranked gene lists
- enrichr_guide.md - All available libraries
- cross_validation.md - Multi-source validation strategies
