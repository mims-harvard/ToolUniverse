---
name: tooluniverse-gene-enrichment
description: Perform comprehensive gene enrichment and pathway analysis using gseapy (ORA and GSEA), PANTHER, STRING, Reactome, and 40+ ToolUniverse tools. Supports GO enrichment (BP, MF, CC), KEGG, Reactome, WikiPathways, MSigDB Hallmark, and 220+ Enrichr libraries. Handles multiple ID types (gene symbols, Ensembl, Entrez, UniProt), multiple organisms (human, mouse, rat, fly, worm, yeast), customizable backgrounds, and multiple testing correction (BH, Bonferroni). Use when users ask about gene enrichment, pathway analysis, GO term enrichment, KEGG pathway analysis, GSEA, over-representation analysis, functional annotation, or gene set analysis.
---

# Gene Enrichment and Pathway Analysis Pipeline

Perform comprehensive gene enrichment analysis including Gene Ontology (GO), KEGG, Reactome, WikiPathways, and MSigDB enrichment using both Over-Representation Analysis (ORA) and Gene Set Enrichment Analysis (GSEA). Integrates local computation via gseapy with ToolUniverse pathway databases for cross-validated, publication-ready results.

**IMPORTANT**: Always use English terms in tool calls (gene names, pathway names, organism names), even if the user writes in another language. Only try original-language terms as a fallback if English returns no results. Respond in the user's language.

---

## When to Use This Skill

Apply when users:
- Ask about gene enrichment analysis (GO, KEGG, Reactome, etc.)
- Have a gene list from differential expression, clustering, or any experiment
- Want to know which biological processes, molecular functions, or cellular components are enriched
- Need KEGG or Reactome pathway enrichment analysis
- Ask about GSEA (Gene Set Enrichment Analysis) with ranked gene lists
- Want over-representation analysis (ORA) with Fisher's exact test
- Need multiple testing correction (Benjamini-Hochberg, Bonferroni)
- Ask about enrichGO, gseapy, clusterProfiler-style analyses
- Want to compare enrichment across multiple gene lists
- Need to convert between gene ID types before enrichment
- Ask specific BixBench-style questions about enrichment p-values, adjusted p-values, top terms

**NOT for** (use other skills instead):
- Network pharmacology / drug repurposing -> Use `tooluniverse-network-pharmacology`
- Disease characterization -> Use `tooluniverse-multiomic-disease-characterization`
- Single gene function lookup -> Use `tooluniverse-disease-research`
- Spatial omics analysis -> Use `tooluniverse-spatial-omics-analysis`
- Protein-protein interaction analysis only -> Use `tooluniverse-protein-interactions`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **gene_list** | Yes | List of gene symbols, Ensembl IDs, or Entrez IDs | `["TP53", "BRCA1", "EGFR"]` |
| **organism** | No | Organism (default: human). Supported: human, mouse, rat, fly, worm, yeast, zebrafish | `human` |
| **analysis_type** | No | `ORA` (default) or `GSEA` | `ORA` |
| **enrichment_databases** | No | Which databases to query. Default: all applicable | `["GO_BP", "GO_MF", "GO_CC", "KEGG", "Reactome"]` |
| **gene_id_type** | No | Input ID type: `symbol`, `ensembl`, `entrez`, `uniprot` (auto-detected if omitted) | `symbol` |
| **p_value_cutoff** | No | Significance threshold (default: 0.05) | `0.05` |
| **correction_method** | No | Multiple testing: `BH` (Benjamini-Hochberg, default), `bonferroni`, `fdr` | `BH` |
| **background_genes** | No | Custom background gene set (default: genome-wide) | `["GENE1", "GENE2", ...]` |
| **ranked_gene_list** | No | For GSEA: gene-to-score mapping (e.g., log2FC) | `{"TP53": 2.5, "BRCA1": -1.3, ...}` |
| **min_gene_set_size** | No | Minimum genes in a gene set (default: 5) | `5` |
| **max_gene_set_size** | No | Maximum genes in a gene set (default: 500) | `500` |
| **enrichr_libraries** | No | Specific Enrichr/gseapy library names | `["GO_Biological_Process_2021"]` |

---

## Supported Enrichment Databases

### Gene Ontology (GO)
| Category | gseapy Library | PANTHER Dataset | STRING Category |
|----------|---------------|-----------------|-----------------|
| **Biological Process (BP)** | `GO_Biological_Process_2021/2023/2025` | `GO:0008150` | `Process` |
| **Molecular Function (MF)** | `GO_Molecular_Function_2021/2023/2025` | `GO:0003674` | `Function` |
| **Cellular Component (CC)** | `GO_Cellular_Component_2021/2023/2025` | `GO:0005575` | `Component` |

### Pathway Databases
| Database | gseapy Library | ToolUniverse Tool | Notes |
|----------|---------------|-------------------|-------|
| **KEGG** | `KEGG_2021_Human`, `KEGG_2026` | `STRING_functional_enrichment(category='KEGG')` | KEGG pathways |
| **Reactome** | `Reactome_2022`, `Reactome_Pathways_2024` | `ReactomeAnalysis_pathway_enrichment` | Curated pathways |
| **WikiPathways** | `WikiPathways_2024_Human` | `WikiPathways_search` | Community pathways |
| **MSigDB Hallmark** | `MSigDB_Hallmark_2020` | - | Cancer hallmarks |
| **BioPlanet** | `BioPlanet_2019` | - | NCI pathways |
| **BioCarta** | `BioCarta_2016` | - | Signal transduction |
| **PANTHER** | - | `PANTHER_enrichment` | Protein classification |

### Other Libraries (via gseapy)
- **Transcription Factors**: `ChEA_2022`, `ENCODE_TF_ChIP-seq_2015`
- **Diseases**: `DisGeNET`, `OMIM_Disease`, `ClinVar_2025`
- **Drugs**: `DGIdb_Drug_Targets_2024`, `DrugMatrix`
- **Cell Types**: `CellMarker_2024`, `Azimuth_2023`
- **Tissues**: `GTEx_Tissues_V8_2023`, `ARCHS4_Tissues`

Total: 225+ Enrichr libraries available via `gseapy.get_library_name()`.

---

## Organism Support

| Organism | Taxonomy ID | gseapy | PANTHER | STRING | Reactome |
|----------|------------|--------|---------|--------|----------|
| **Human** | 9606 | Yes | Yes | Yes | Yes |
| **Mouse** | 10090 | Yes (`*_Mouse`) | Yes | Yes | Yes (projection) |
| **Rat** | 10116 | Limited | Yes | Yes | Yes (projection) |
| **Fly** (Drosophila) | 7227 | Limited | Yes | Yes | Yes (projection) |
| **Worm** (C. elegans) | 6239 | Limited | Yes | Yes | Yes (projection) |
| **Yeast** (S. cerevisiae) | 4932 | Limited | Yes | Yes | Yes |
| **Zebrafish** | 7955 | Limited | Yes | Yes | Yes (projection) |

---

## KEY PRINCIPLES

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **ID disambiguation FIRST** - Detect and convert gene IDs before ANY enrichment
3. **Multi-source validation** - Run enrichment on at least 2 independent tools, cross-validate
4. **Exact p-values** - Report raw p-values AND adjusted p-values with correction method
5. **Multiple testing correction** - ALWAYS apply Benjamini-Hochberg unless user specifies otherwise
6. **Gene set size filtering** - Filter by min/max gene set size to avoid trivial/overly broad terms
7. **Redundancy reduction** - Group similar GO terms, report parent terms where appropriate
8. **Background specification** - Warn if no background provided; genome-wide is default
9. **Evidence grading** - Grade enrichment sources T1-T4
10. **Negative results documented** - "No significant enrichment" is a valid finding
11. **Source references** - Every enrichment result must cite the tool/database/library used
12. **Completeness checklist** - Mandatory section at end showing analysis coverage

---

## Evidence Grading System

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Curated/experimental enrichment | PANTHER enrichment (curated GO), Reactome (curated pathways) |
| **T2** | [T2] | Computational enrichment, well-validated | gseapy ORA/GSEA, STRING functional enrichment |
| **T3** | [T3] | Text-mining/predicted enrichment | Enrichr non-curated libraries, predicted functions |
| **T4** | [T4] | Single-source annotation | Individual gene GO annotations from QuickGO |

---

## Complete Workflow

### Phase 0: Input Validation and ID Conversion

**Step 0.1**: Create the report file immediately.

```python
report_path = "[analysis_name]_enrichment_report.md"
# Write header and placeholder sections
```

**Step 0.2**: Detect gene ID type and convert if needed.

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# === ID TYPE DETECTION ===
# Ensembl IDs start with "ENSG" (human), "ENSMUSG" (mouse), etc.
# Entrez IDs are numeric strings ("7157", "672")
# UniProt IDs match pattern like "P04637", "Q9Y243"
# Gene symbols are alphabetic (TP53, BRCA1)

gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN"]

# Detect ID type
sample = gene_list[0]
if sample.startswith("ENSG") or sample.startswith("ENSMUS"):
    id_type = "ensembl"
elif sample.replace("-", "").isdigit():
    id_type = "entrez"
elif len(sample) == 6 and sample[0].isalpha() and sample[1:].replace("_","").isalnum():
    id_type = "uniprot"  # rough heuristic
else:
    id_type = "symbol"

# === ID CONVERSION (if needed) ===
# Convert Ensembl -> Symbol using MyGene
if id_type == "ensembl":
    batch_result = tu.tools.MyGene_batch_query(
        gene_ids=gene_list,
        fields="symbol,entrezgene,ensembl.gene"
    )
    # Returns: {results: [{query, _id, symbol, entrezgene, ensembl: {gene}}]}
    symbol_map = {}
    for hit in batch_result.get('results', batch_result.get('data', {}).get('results', [])):
        symbol_map[hit['query']] = hit.get('symbol', hit['query'])
    gene_symbols = [symbol_map.get(g, g) for g in gene_list]
elif id_type == "entrez":
    batch_result = tu.tools.MyGene_batch_query(
        gene_ids=gene_list,
        fields="symbol,entrezgene,ensembl.gene"
    )
    symbol_map = {}
    for hit in batch_result.get('results', batch_result.get('data', {}).get('results', [])):
        symbol_map[hit['query']] = hit.get('symbol', hit['query'])
    gene_symbols = [symbol_map.get(g, g) for g in gene_list]
else:
    gene_symbols = gene_list  # Already symbols

# === VALIDATE GENE SYMBOLS ===
# Verify genes map correctly with STRING
string_mapped = tu.tools.STRING_map_identifiers(
    protein_ids=gene_symbols[:20],  # sample for validation
    species=9606
)
# Returns: {status, data: [{queryItem, preferredName, stringId, ...}]}
# Use preferredName for canonical symbol
```

**Step 0.3**: Determine organism and taxonomy ID.

```python
# Map organism name to taxonomy ID
ORGANISM_MAP = {
    'human': 9606, 'homo_sapiens': 9606,
    'mouse': 10090, 'mus_musculus': 10090,
    'rat': 10116, 'rattus_norvegicus': 10116,
    'fly': 7227, 'drosophila_melanogaster': 7227,
    'worm': 6239, 'caenorhabditis_elegans': 6239,
    'yeast': 4932, 'saccharomyces_cerevisiae': 4932,
    'zebrafish': 7955, 'danio_rerio': 7955,
}
taxon_id = ORGANISM_MAP.get(organism.lower(), 9606)
```

---

### Phase 1: Over-Representation Analysis (ORA) with gseapy

**This is the PRIMARY enrichment method.** Uses Fisher's exact test with Benjamini-Hochberg correction.

**Step 1.1**: GO Biological Process enrichment.

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

**Step 1.2**: GO Molecular Function and Cellular Component.

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

**Step 1.3**: KEGG pathway enrichment.

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

**Step 1.4**: Reactome pathway enrichment.

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

**Step 1.5**: MSigDB Hallmark and other libraries.

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

**Step 1.6**: Custom background gene set.

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

### Phase 2: Gene Set Enrichment Analysis (GSEA)

**Use when you have a RANKED gene list** (e.g., by log2 fold-change, p-value, or signal-to-noise ratio).

**Step 2.1**: Prepare ranked gene list.

```python
import pandas as pd
import numpy as np

# Input: dict of gene -> score (e.g., log2FC from DESeq2)
ranked_dict = {"TP53": 3.2, "BRCA1": 2.8, "EGFR": -1.5, "MYC": 4.1, ...}

# Convert to Series, sorted by score (descending)
ranked_series = pd.Series(ranked_dict).sort_values(ascending=False)
# OR from a DataFrame:
# ranked_series = df.set_index('gene_symbol')['log2FoldChange'].sort_values(ascending=False)
```

**Step 2.2**: Run GSEA preranked.

```python
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

# Filter significant
gsea_sig = gsea_bp_df[gsea_bp_df['FDR q-val'].astype(float) < 0.25]  # GSEA uses 0.25 FDR cutoff

# Key metrics:
# NES (Normalized Enrichment Score): positive = enriched in top of list, negative = enriched in bottom
# NOM p-val: nominal p-value (unadjusted)
# FDR q-val: false discovery rate (adjusted)
# FWER p-val: family-wise error rate (Bonferroni-like)
# Lead_genes: core genes driving enrichment
```

**Step 2.3**: GSEA with KEGG and Reactome.

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
```

**Step 2.4**: Multiple gene set libraries.

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

### Phase 3: Cross-Validation with ToolUniverse Enrichment Tools

Run enrichment on at least one additional independent source and cross-validate results.

**Step 3.1**: PANTHER enrichment (curated GO enrichment).

```python
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

**Step 3.2**: STRING functional enrichment.

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

**Step 3.3**: Reactome Analysis Service enrichment.

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

**Step 3.4**: Cross-validate results.

```python
# Compare top terms across tools
# 1. Collect top GO BP terms from each source
gseapy_top_bp = set(go_bp_sig.head(20)['Term'].str.extract(r'\(GO:\d+\)')[0].dropna())
panther_top_bp = set(t['term_id'] for t in panther_terms[:20] if t.get('fdr', 1) < 0.05)
string_top_bp = set(d['term'] for d in string_go_bp[:20] if d.get('fdr', 1) < 0.05)

# Find consensus terms (present in 2+ sources)
all_go_terms = gseapy_top_bp | panther_top_bp | string_top_bp
consensus_terms = []
for term in all_go_terms:
    sources = []
    if term in gseapy_top_bp: sources.append('gseapy')
    if term in panther_top_bp: sources.append('PANTHER')
    if term in string_top_bp: sources.append('STRING')
    if len(sources) >= 2:
        consensus_terms.append((term, sources))

# 2. Compare KEGG results
# gseapy KEGG vs STRING KEGG vs Reactome
# Cross-reference pathway IDs and names
```

---

### Phase 4: Additional Multiple Testing Correction

Apply user-specified or additional correction methods.

**Step 4.1**: Apply Benjamini-Hochberg (default).

```python
from scipy import stats
import statsmodels.stats.multitest as mt
import numpy as np

# gseapy already applies BH correction (Adjusted P-value column)
# For custom correction on raw p-values:

raw_pvals = go_bp_df['P-value'].values

# Benjamini-Hochberg (FDR)
reject_bh, pvals_bh, _, _ = mt.multipletests(raw_pvals, alpha=0.05, method='fdr_bh')

# Bonferroni
reject_bonf, pvals_bonf, _, _ = mt.multipletests(raw_pvals, alpha=0.05, method='bonferroni')

# Benjamini-Yekutieli (more conservative FDR)
reject_by, pvals_by, _, _ = mt.multipletests(raw_pvals, alpha=0.05, method='fdr_by')

# Holm-Sidak
reject_hs, pvals_hs, _, _ = mt.multipletests(raw_pvals, alpha=0.05, method='holm-sidak')

# Add to DataFrame
go_bp_df['BH_adjusted'] = pvals_bh
go_bp_df['Bonferroni_adjusted'] = pvals_bonf
```

**Step 4.2**: Compare correction methods.

```python
# Count significant terms by method
n_bh = sum(reject_bh)
n_bonf = sum(reject_bonf)
n_by = sum(reject_by)

print(f"Significant terms:")
print(f"  BH (FDR): {n_bh}")
print(f"  Bonferroni: {n_bonf}")
print(f"  BY: {n_by}")
```

---

### Phase 5: Pathway Context from ToolUniverse

Enrich top findings with additional biological context from ToolUniverse pathway databases.

**Step 5.1**: Get pathway details from Reactome.

```python
# For top enriched Reactome pathways, get details
for pathway in reactome_sig[:5]:
    pathway_id = pathway['pathway_id']  # e.g., "R-HSA-212436"

    # Get full pathway info
    pathway_detail = tu.tools.Reactome_get_pathway(pathway_id=pathway_id)

    # Get pathway hierarchy
    pathway_hier = tu.tools.Reactome_get_pathway_hierarchy(pathway_id=pathway_id)

    # Get pathway reactions
    pathway_rxns = tu.tools.Reactome_get_pathway_reactions(pathway_id=pathway_id)
```

**Step 5.2**: Get KEGG pathway details.

```python
# For top KEGG pathways
for _, row in kegg_sig.head(5).iterrows():
    term = row['Term']  # e.g., "Cell cycle"
    # Search KEGG for pathway details
    kegg_info = tu.tools.kegg_search_pathway(query=term)
    # Get specific pathway info if ID known
    # kegg_detail = tu.tools.kegg_get_pathway_info(pathway_id="hsa04110")
```

**Step 5.3**: WikiPathways context.

```python
# For top WikiPathways results
for _, row in wp_df[wp_df['Adjusted P-value'] < 0.05].head(5).iterrows():
    term = row['Term']
    # Search WikiPathways
    wp_detail = tu.tools.WikiPathways_search(query=term, organism='Homo sapiens')
    # Get specific pathway
    # wp_full = tu.tools.WikiPathways_get_pathway(pathway_id="WP179")
```

**Step 5.4**: GO term details for top enriched terms.

```python
# Get details for top enriched GO terms
for _, row in go_bp_sig.head(5).iterrows():
    term_str = row['Term']
    # Extract GO ID from term string: "regulation of cell cycle (GO:0051726)"
    import re
    go_match = re.search(r'(GO:\d+)', term_str)
    if go_match:
        go_id = go_match.group(1)
        # Get GO term details
        go_detail = tu.tools.GO_get_term_by_id(go_id=go_id)
        # Get GO term hierarchy
        go_children = tu.tools.QuickGO_get_term_children(go_id=go_id)
```

**Step 5.5**: Gene-level GO annotations for key genes.

```python
# For genes driving top enrichment, get individual annotations
for gene in gene_symbols[:10]:
    # Get GO annotations from GO API
    go_annot = tu.tools.GO_get_annotations_for_gene(gene_id=gene)

    # For detailed annotations with evidence codes, use QuickGO with UniProt ID
    # First get UniProt ID
    mygene_result = tu.tools.MyGene_query_genes(query=gene)
    if mygene_result.get('hits'):
        hit = mygene_result['hits'][0]
        uniprot_id = hit.get('uniprot', {}).get('Swiss-Prot', '')
        if uniprot_id:
            quickgo = tu.tools.QuickGO_annotations_by_gene(
                gene_product_id=f"UniProtKB:{uniprot_id}",
                limit=50
            )
```

---

### Phase 6: Network Context and PPI Enrichment

Connect enrichment results to protein interaction networks.

**Step 6.1**: STRING PPI enrichment test.

```python
# Test if gene list has more interactions than expected
ppi_enrichment = tu.tools.STRING_ppi_enrichment(
    protein_ids=gene_symbols,
    species=9606
)
# Returns: PPI enrichment p-value (significant = more connected than random)
```

**Step 6.2**: Build interaction network for enriched gene sets.

```python
# Get interactions for genes in top enriched pathway
top_pathway_genes = go_bp_sig.iloc[0]['Genes'].split(';')

string_network = tu.tools.STRING_get_interaction_partners(
    protein_ids=top_pathway_genes,
    species=9606,
    limit=50
)
# Returns: {status: "success", data: [{stringId_A, stringId_B, preferredName_A, preferredName_B, score}]}
```

---

### Phase 7: Comparative Enrichment (Multiple Gene Lists)

When users have multiple gene lists (e.g., up-regulated vs down-regulated, cluster 1 vs cluster 2).

**Step 7.1**: Run enrichment on each list.

```python
# Example: up-regulated and down-regulated genes
up_genes = ["TP53", "BRCA1", "MYC", ...]
down_genes = ["EGFR", "AKT1", "PTEN", ...]

up_result = gseapy.enrichr(
    gene_list=up_genes,
    gene_sets='GO_Biological_Process_2021',
    organism='human', outdir=None, no_plot=True,
)

down_result = gseapy.enrichr(
    gene_list=down_genes,
    gene_sets='GO_Biological_Process_2021',
    organism='human', outdir=None, no_plot=True,
)
```

**Step 7.2**: Compare enrichment results.

```python
# Find unique and shared enriched terms
up_terms = set(up_result.results[up_result.results['Adjusted P-value'] < 0.05]['Term'])
down_terms = set(down_result.results[down_result.results['Adjusted P-value'] < 0.05]['Term'])

shared = up_terms & down_terms
up_unique = up_terms - down_terms
down_unique = down_terms - up_terms

print(f"Up-regulated specific: {len(up_unique)} terms")
print(f"Down-regulated specific: {len(down_unique)} terms")
print(f"Shared: {len(shared)} terms")
```

---

### Phase 8: Report Generation

**Step 8.1**: Compile comprehensive enrichment report.

```markdown
# Gene Enrichment Analysis Report

## Executive Summary
[2-3 sentence summary: number of input genes, organism, top findings across databases]

## Input Summary
- **Gene list**: N genes
- **Organism**: [organism]
- **Gene ID type**: [symbol/ensembl/entrez]
- **Analysis type**: [ORA/GSEA]
- **Background**: [genome-wide/custom (N genes)]
- **Significance threshold**: p < [cutoff]
- **Correction method**: [BH/Bonferroni]
- **Genes not mapped**: [list or count]

## 1. GO Biological Process Enrichment

### Top Enriched Terms (gseapy ORA)
| Rank | GO Term | Description | P-value | Adj. P-value | Overlap | Genes |
|------|---------|-------------|---------|-------------|---------|-------|
| 1 | GO:XXXXXXX | [description] | X.XXe-XX | X.XXe-XX | X/Y | [genes] |

### Cross-Validation
| GO Term | gseapy FDR | PANTHER FDR | STRING FDR | Consensus |
|---------|-----------|-------------|-----------|-----------|
| [term] | [fdr] | [fdr] | [fdr] | [2/3 or 3/3] |

## 2. GO Molecular Function Enrichment
[Same format as BP]

## 3. GO Cellular Component Enrichment
[Same format as BP]

## 4. KEGG Pathway Enrichment
| Rank | Pathway | P-value | Adj. P-value | Overlap | Genes |
|------|---------|---------|-------------|---------|-------|
| 1 | [pathway] | X.XXe-XX | X.XXe-XX | X/Y | [genes] |

## 5. Reactome Pathway Enrichment
| Rank | Pathway ID | Name | P-value | FDR | Entities Found | Entities Total |
|------|-----------|------|---------|-----|---------------|----------------|
| 1 | R-HSA-XXXXX | [name] | X.XXe-XX | X.XXe-XX | X | Y |

## 6. Additional Enrichment Libraries
### MSigDB Hallmark
[If applicable]

### WikiPathways
[If applicable]

## 7. GSEA Results (if applicable)
| Term | NES | NOM p-val | FDR q-val | Lead Genes |
|------|-----|-----------|-----------|------------|

## 8. Multiple Testing Correction Comparison
| Method | Significant Terms (BP) | Significant Terms (KEGG) |
|--------|----------------------|------------------------|
| BH (FDR) | N | N |
| Bonferroni | N | N |
| BY | N | N |

## 9. Network Context
- **PPI enrichment p-value**: [value]
- **Network interpretation**: [connected/random]

## 10. Consensus Findings
[List of findings confirmed by 2+ independent sources]

## Evidence Summary Table
| Finding | Source | Evidence Grade | P-value | FDR |
|---------|--------|---------------|---------|-----|
| [finding] | gseapy/PANTHER/STRING/Reactome | [T1-T4] | [pval] | [fdr] |

## Completeness Checklist
| Phase | Status | Tools Used | Key Findings |
|-------|--------|------------|--------------|
| ID Conversion | Done/Partial/Failed | MyGene, STRING_map | [summary] |
| GO BP | Done/Partial/Failed | gseapy, PANTHER, STRING | [N significant terms] |
| GO MF | Done/Partial/Failed | gseapy, PANTHER, STRING | [N significant terms] |
| GO CC | Done/Partial/Failed | gseapy, PANTHER, STRING | [N significant terms] |
| KEGG | Done/Partial/Failed | gseapy, STRING | [N significant terms] |
| Reactome | Done/Partial/Failed | gseapy, Reactome API | [N significant terms] |
| WikiPathways | Done/Partial/Failed | gseapy | [N significant terms] |
| MSigDB Hallmark | Done/Partial/Failed | gseapy | [N significant terms] |
| GSEA | Done/Skipped/Failed | gseapy prerank | [N significant terms] |
| Cross-validation | Done/Partial/Failed | comparison | [N consensus terms] |
| Network Context | Done/Partial/Failed | STRING PPI | [summary] |
| Report | Done | - | Complete |
```

---

## Tool Parameter Reference (Verified)

### Primary Enrichment Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `gseapy.enrichr()` | `gene_list: list[str]`, `gene_sets: str/list`, `organism: str`, `outdir: None`, `no_plot: True`, `background: list/None` | `.results` DataFrame: `Gene_set, Term, Overlap, P-value, Adjusted P-value, Odds Ratio, Combined Score, Genes` |
| `gseapy.prerank()` | `rnk: pd.Series`, `gene_sets: str/list`, `outdir: None`, `no_plot: True`, `seed: int`, `min_size: int`, `max_size: int`, `permutation_num: int` | `.res2d` DataFrame: `Name, Term, ES, NES, NOM p-val, FDR q-val, FWER p-val, Tag %, Gene %, Lead_genes` |
| `PANTHER_enrichment` | `gene_list: str` (comma-separated), `organism: int` (9606), `annotation_dataset: str` | `{data: {enriched_terms: [{term_id, term_label, fold_enrichment, pvalue, fdr, direction}]}}` |
| `STRING_functional_enrichment` | `protein_ids: list[str]`, `species: int` (9606), `category: str` | `{status, data: [{category, term, p_value, fdr, description, inputGenes}]}` |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers: str` (space-separated), `page_size: int`, `include_disease: bool`, `projection: bool` | `{data: {pathways: [{pathway_id, name, p_value, fdr, entities_found, entities_total}]}}` |

### ID Conversion Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `MyGene_batch_query` | `gene_ids: list[str]`, `fields: str` | `{results: [{query, _id, symbol, entrezgene, ensembl: {gene}}]}` |
| `MyGene_query_genes` | `query: str` | `{hits: [{_id, symbol, entrezgene, ensembl: {gene}}]}` |
| `STRING_map_identifiers` | `protein_ids: list[str]`, `species: int` | `[{queryItem, preferredName, stringId}]` |
| `UniProtIDMap_convert_ids` | `from_db: str`, `to_db: str`, `ids: str` (comma-separated) | ID mapping results |

### GO Term Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `GO_get_term_by_id` | `go_id: str` | GO term details |
| `GO_get_term_details` | `go_id: str` | Detailed GO term info |
| `GO_search_terms` | `query: str` | Search results |
| `GO_get_annotations_for_gene` | `gene_id: str` | List of GO annotations |
| `GO_get_genes_for_term` | `go_id: str` | List of genes for GO term |
| `QuickGO_annotations_by_gene` | `gene_product_id: str` (format: "UniProtKB:P04637") | Detailed annotations with evidence |
| `QuickGO_get_term_detail` | `go_id: str` | GO term detail |
| `QuickGO_get_term_children` | `go_id: str` | Child terms |

### Pathway Context Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `Reactome_get_pathway` | `pathway_id: str` | Pathway details |
| `Reactome_get_pathway_hierarchy` | `pathway_id: str` | Hierarchy |
| `Reactome_get_pathway_reactions` | `pathway_id: str` | Reactions list |
| `Reactome_map_uniprot_to_pathways` | `id: str` (UniProt) | Plain list of pathways |
| `WikiPathways_search` | `query: str`, `organism: str` | `{status, data: {result: [{id, name, species}]}}` |
| `WikiPathways_get_pathway` | `pathway_id: str` | Pathway detail |
| `kegg_search_pathway` | `query: str` | KEGG pathway matches |
| `kegg_get_pathway_info` | `pathway_id: str` | Pathway detail |
| `kegg_get_gene_info` | `gene_id: str` | Gene in KEGG |

### Network Context Tools
| Tool | Key Parameters | Response Structure |
|------|---------------|-------------------|
| `STRING_ppi_enrichment` | `protein_ids: list[str]`, `species: int` | PPI enrichment statistics |
| `STRING_get_interaction_partners` | `protein_ids: list[str]`, `species: int`, `limit: int` | `{status, data: [{preferredName_A, preferredName_B, score}]}` |
| `STRING_get_network` | `protein_ids: list[str]`, `species: int` | Network data |

---

## Response Format Notes

**gseapy enrichr results**: DataFrame with columns `Gene_set, Term, Overlap, P-value, Adjusted P-value, Old P-value, Old Adjusted P-value, Odds Ratio, Combined Score, Genes`. Access via `.results`.

**gseapy prerank results**: DataFrame with columns `Name, Term, ES, NES, NOM p-val, FDR q-val, FWER p-val, Tag %, Gene %, Lead_genes`. Access via `.res2d`.

**PANTHER enrichment**: Returns `{data: {enriched_terms: [...]}}`. Each term has `term_id, term_label, pvalue, fdr, fold_enrichment, direction`.

**STRING functional enrichment**: Returns ALL categories in one call regardless of `category` parameter. Filter by `d['category']` after receiving results. Categories: Process, Function, Component, KEGG, Reactome, WikiPathways, COMPARTMENTS, DISEASES, Keyword, PMID, HPO, TISSUES, NetworkNeighborAL, RCTM.

**ReactomeAnalysis_pathway_enrichment**: Takes space-separated `identifiers` string, NOT array. Returns `{data: {pathways: [...]}}`.

**enrichr_gene_enrichment_analysis (ToolUniverse)**: Returns connected_paths JSON string (NOT standard enrichment). DO NOT USE for standard enrichment analysis -- use gseapy.enrichr() directly instead.

**MyGene_batch_query**: Parameter is `gene_ids` (NOT `ids`). Returns `{results: [...]}` or `{data: {results: [...]}}`.

---

## Fallback Strategies

| Phase | Primary Tool | Fallback 1 | Fallback 2 |
|-------|-------------|-----------|-----------|
| GO BP enrichment | gseapy enrichr | PANTHER enrichment | STRING functional enrichment |
| GO MF enrichment | gseapy enrichr | PANTHER enrichment | STRING functional enrichment |
| GO CC enrichment | gseapy enrichr | PANTHER enrichment | STRING functional enrichment |
| KEGG enrichment | gseapy enrichr | STRING functional enrichment | kegg_search_pathway (manual) |
| Reactome enrichment | gseapy enrichr | ReactomeAnalysis_pathway_enrichment | Reactome_map_uniprot_to_pathways |
| WikiPathways | gseapy enrichr | WikiPathways_search | - |
| GSEA | gseapy prerank | - | ORA as approximation |
| ID conversion | MyGene_batch_query | STRING_map_identifiers | UniProtIDMap_convert_ids |
| GO term details | GO_get_term_by_id | QuickGO_get_term_detail | GO_search_terms |
| PPI context | STRING_ppi_enrichment | STRING_get_interaction_partners | - |
| Pathway details | Reactome_get_pathway | kegg_get_pathway_info | WikiPathways_get_pathway |

---

## Common Use Patterns

### Pattern 1: Standard ORA from DEG List
```
Input: List of differentially expressed gene symbols
Organism: human

Flow:
1. Validate gene symbols (STRING_map_identifiers)
2. Run gseapy.enrichr with GO_BP, GO_MF, GO_CC, KEGG, Reactome
3. Cross-validate with PANTHER and STRING
4. Apply BH correction
5. Report top enriched terms per category
```

### Pattern 2: GSEA from Ranked List
```
Input: Gene-to-log2FC mapping from DESeq2/edgeR
Organism: human

Flow:
1. Convert to ranked Series (sort by log2FC descending)
2. Run gseapy.prerank with GO_BP, KEGG, MSigDB_Hallmark
3. Filter by FDR q-val < 0.25
4. Report NES, lead genes for top terms
5. Compare positive vs negative NES (up- vs down-regulated pathways)
```

### Pattern 3: BixBench Enrichment Question
```
Input: Specific question about enrichment (e.g., "What is the adjusted p-val for neutrophil activation?")
Context: Gene list and specific library/method

Flow:
1. Parse question for: gene list, library name, GO term of interest
2. Run gseapy.enrichr with exact library specified
3. Find the specific term in results
4. Report exact p-value and adjusted p-value
5. If enrichGO mentioned, use gseapy ORA (closest equivalent)
```

### Pattern 4: Multi-Organism Enrichment
```
Input: Gene list from mouse experiment
Organism: mouse

Flow:
1. Use gseapy with organism='mouse' and mouse-specific libraries
2. Use PANTHER with organism=10090
3. Use STRING with species=10090
4. Use Reactome with projection=True for human pathway mapping
```

### Pattern 5: Custom Background Enrichment
```
Input: DEGs from RNA-seq (detected genes as background)
Background: All expressed genes (e.g., 12000 genes)

Flow:
1. Run gseapy.enrichr with background=expressed_genes
2. Compare with genome-wide background
3. Report both results; custom background is more conservative
4. Note: PANTHER also supports custom background via reference list
```

---

## Available gseapy Enrichr Libraries (225 total)

### GO Libraries
- `GO_Biological_Process_2021`, `GO_Biological_Process_2023`, `GO_Biological_Process_2025`
- `GO_Molecular_Function_2021`, `GO_Molecular_Function_2023`, `GO_Molecular_Function_2025`
- `GO_Cellular_Component_2021`, `GO_Cellular_Component_2023`, `GO_Cellular_Component_2025`

### Pathway Libraries
- `KEGG_2021_Human`, `KEGG_2019_Mouse`, `KEGG_2026`
- `Reactome_2022`, `Reactome_Pathways_2024`
- `WikiPathways_2024_Human`, `WikiPathways_2024_Mouse`
- `BioCarta_2016`, `BioPlanet_2019`
- `MSigDB_Hallmark_2020`, `MSigDB_Computational`, `MSigDB_Oncogenic_Signatures`
- `Elsevier_Pathway_Collection`

### Disease/Phenotype Libraries
- `DisGeNET`, `OMIM_Disease`, `OMIM_Expanded`
- `ClinVar_2025`
- `Rare_Diseases_GeneRIF_Gene_Lists`

### Drug/Target Libraries
- `DGIdb_Drug_Targets_2024`
- `DrugMatrix`
- `Drug_Perturbations_from_GEO_down`, `Drug_Perturbations_from_GEO_up`

### Cell/Tissue Libraries
- `CellMarker_2024`, `Azimuth_2023`
- `GTEx_Tissues_V8_2023`
- `ARCHS4_Tissues`
- `Descartes_Cell_Types_and_Tissue_2021`
- `Allen_Brain_Atlas_10x_scRNA_2021`

### Transcription Factor Libraries
- `ChEA_2022`
- `ENCODE_TF_ChIP-seq_2015`
- `ENCODE_and_ChEA_Consensus_TFs_from_ChIP-X`

### Epigenomics Libraries
- `ENCODE_Histone_Modifications_2015`
- `Epigenomics_Roadmap_HM_ChIP-seq`

### Other
- `SynGO_2022`, `SynGO_2024` (synaptic GO)
- `CORUM` (protein complexes)
- `COMPARTMENTS_Curated_2025`, `COMPARTMENTS_Experimental_2025`
- `DepMap_CRISPR_GeneDependency_CellLines_2023`

Full list: Run `gseapy.get_library_name()` for all 225 libraries.

---

## PANTHER Annotation Datasets

| Dataset ID | Description |
|-----------|-------------|
| `GO:0008150` | GO Biological Process |
| `GO:0003674` | GO Molecular Function |
| `GO:0005575` | GO Cellular Component |
| `ANNOT_TYPE_ID_PANTHER_PATHWAY` | PANTHER Pathway |
| `ANNOT_TYPE_ID_PANTHER_REACTOME_PATHWAY` | Reactome Pathways (via PANTHER) |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_MF` | GO Slim Molecular Function |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_BP` | GO Slim Biological Process |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_CC` | GO Slim Cellular Component |
| `ANNOT_TYPE_ID_PANTHER_PC` | PANTHER Protein Class |

---

## Edge Cases

### Small Gene Lists (<5 genes)
- ORA may have insufficient power. Warn user.
- Use PANTHER and STRING which handle small lists better.
- Consider gene-level annotation (GO_get_annotations_for_gene) instead of enrichment.
- Lower min_size for GSEA to 3.

### Very Large Gene Lists (>500 genes)
- Enrichment becomes less specific. Consider stricter cutoff.
- Recommend custom background (e.g., expressed genes only).
- Focus on most specific (lowest-level) GO terms.
- Use GO Slim for high-level overview.

### Non-Human Organisms
- gseapy supports: human, mouse, fly, yeast, worm, fish, rat.
- PANTHER supports many organisms via taxonomy ID.
- STRING supports most model organisms.
- Reactome can project non-human genes to human pathways (projection=True).
- For unsupported organisms, use ortholog mapping first.

### Mixed ID Types
- Detect most common ID type in the list.
- Convert all to gene symbols using MyGene_batch_query.
- Report any unmapped genes in the output.
- Remove duplicates after conversion.

### No Significant Results
- Report as valid finding ("no significant enrichment").
- Try relaxing cutoff (e.g., p < 0.1).
- Try different library version (2021 vs 2023 vs 2025).
- Consider GSEA as alternative (may detect weak but consistent signals).
- Check if gene names are correctly formatted.

### Duplicate/Obsolete GO Terms
- gseapy uses curated Enrichr libraries (already filtered).
- PANTHER uses official GO (current).
- STRING uses current GO.
- Note any discrepancies between library versions.

---

## Troubleshooting

**"No significant enrichment found"**:
- Check gene symbols are valid (try STRING_map_identifiers)
- Try different library versions (2021 vs 2023 vs 2025)
- Try relaxing significance cutoff
- Try GSEA if ORA fails (different statistical framework)
- Verify organism is correctly specified

**"Gene not found" errors**:
- Check ID type (Ensembl vs Entrez vs Symbol)
- Convert IDs using MyGene_batch_query
- Some aliases may not map; try official HGNC symbols
- Remove version suffixes from Ensembl IDs (ENSG00000141510.16 -> ENSG00000141510)

**"gseapy library not found"**:
- Run `gseapy.get_library_name()` to see available libraries
- Library names are case-sensitive
- Some libraries are organism-specific (e.g., `KEGG_2021_Human` vs `KEGG_2019_Mouse`)

**"PANTHER returns empty results"**:
- Check gene_list format: comma-separated string, NOT array
- Check organism taxonomy ID (9606 for human)
- Check annotation_dataset is valid

**"STRING returns all categories"**:
- This is expected behavior; STRING always returns all categories
- Filter by category field after receiving results
- Use `d['category'] == 'Process'` for GO BP, etc.

**"Reactome identifiers_not_found > 0"**:
- Some gene symbols may not map to Reactome entities
- Use official gene symbols (not aliases)
- Try UniProt IDs or Ensembl IDs as alternatives

**"enrichr_gene_enrichment_analysis returns connected_paths"**:
- This is the ToolUniverse enrichr tool, which returns path analysis, NOT standard enrichment
- Use `gseapy.enrichr()` directly for standard ORA enrichment
- The ToolUniverse enrichr tool is NOT suitable for standard enrichment questions

---

## Resources

For network-level analysis: [tooluniverse-network-pharmacology](../tooluniverse-network-pharmacology/SKILL.md)
For disease characterization: [tooluniverse-multiomic-disease-characterization](../tooluniverse-multiomic-disease-characterization/SKILL.md)
For spatial omics: [tooluniverse-spatial-omics-analysis](../tooluniverse-spatial-omics-analysis/SKILL.md)
For protein interactions: [tooluniverse-protein-interactions](../tooluniverse-protein-interactions/SKILL.md)

gseapy documentation: https://gseapy.readthedocs.io/
PANTHER API: http://pantherdb.org/services/oai/pantherdb/
STRING API: https://string-db.org/cgi/help?sessionId=&subpage=api
Reactome Analysis: https://reactome.org/AnalysisService/
