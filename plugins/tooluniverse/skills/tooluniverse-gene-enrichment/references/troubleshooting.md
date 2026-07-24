# Troubleshooting Guide

Complete troubleshooting guide for gene enrichment analysis issues.

---

## Common Issues Index

1. [No Significant Enrichment Found](#no-significant-enrichment-found)
2. [Gene Not Found Errors](#gene-not-found-errors)
3. [gseapy Library Not Found](#gseapy-library-not-found)
4. [PANTHER Returns Empty Results](#panther-returns-empty-results)
5. [STRING Returns All Categories](#string-returns-all-categories)
6. [Reactome Identifiers Not Found](#reactome-identifiers-not-found)
7. [enrichr_gene_enrichment_analysis Returns Wrong Format](#enrichr_gene_enrichment_analysis-returns-wrong-format)
8. [Results Don't Match Between Tools](#results-dont-match-between-tools)
9. [GSEA Gives Unstable Results](#gsea-gives-unstable-results)
10. [Memory Errors with Large Gene Lists](#memory-errors-with-large-gene-lists)

---

## No Significant Enrichment Found

### Symptoms
```python
go_bp_result = gseapy.enrichr(gene_list=genes, gene_sets='GO_Biological_Process_2021', ...)
go_bp_sig = go_bp_result.results[go_bp_result.results['Adjusted P-value'] < 0.05]
print(len(go_bp_sig))  # Output: 0
```

### Possible Causes & Solutions

#### 1. Gene Symbols Are Invalid

**Diagnosis**:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Check if genes are recognized
mapped = tu.tools.STRING_map_identifiers(
    protein_ids=genes,
    species=9606
)
print(f"Mapped: {len(mapped['data'])}/{len(genes)}")
```

**Solution**:
- Convert IDs using MyGene: `tu.tools.MyGene_batch_query(gene_ids=genes, fields='symbol')`
- Use official HGNC symbols
- Remove version suffixes from Ensembl IDs

#### 2. Library Version Too Old/New

**Solution**:
```python
# Try different library versions
for lib_version in ['GO_Biological_Process_2021', 'GO_Biological_Process_2023', 'GO_Biological_Process_2025']:
    result = gseapy.enrichr(gene_list=genes, gene_sets=lib_version, ...)
    sig = result.results[result.results['Adjusted P-value'] < 0.05]
    print(f"{lib_version}: {len(sig)} significant terms")
```

#### 3. Significance Threshold Too Stringent

**Solution**:
```python
# Try relaxing threshold
for cutoff in [0.05, 0.1, 0.15, 0.2]:
    sig = go_bp_result.results[go_bp_result.results['Adjusted P-value'] < cutoff]
    print(f"Cutoff {cutoff}: {len(sig)} significant terms")
```

#### 4. Wrong Statistical Method

**Solution**:
```python
# If ORA fails, try GSEA
import pandas as pd

# Create ranked list (even if you don't have fold-changes)
# Use presence/absence scoring: 1 for genes in list, 0 for others
ranked_dict = {gene: 1 for gene in genes}
ranked_series = pd.Series(ranked_dict).sort_values(ascending=False)

gsea_result = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    ...
)
```

#### 5. Organism Mismatch

**Solution**:
```python
# Verify organism parameter
result = gseapy.enrichr(
    gene_list=genes,
    gene_sets='GO_Biological_Process_2021',
    organism='human',  # NOT 'homo_sapiens' or 9606
    ...
)
```

#### 6. Gene List Too Small or Too Large

**Diagnosis**:
```python
print(f"Gene list size: {len(genes)}")
# Small (<5): insufficient power
# Large (>500): too non-specific
```

**Solution**:
- Small lists (<5 genes): Use PANTHER/STRING (better for small lists) or switch to gene-level annotation
- Large lists (>500 genes): Use custom background or stricter DEG cutoff

#### 7. No True Enrichment

**Valid Result**: Sometimes there genuinely is no enrichment. Document this:
```markdown
## Results
No significant enrichment was found at FDR < 0.05.
- Gene list size: 45 genes
- Libraries tested: GO BP, GO MF, GO CC, KEGG, Reactome
- Alternative cutoff (FDR < 0.1): 3 weak hits (exploratory only)
```

---

## Gene Not Found Errors

### Symptoms
```
Error: Gene 'TP-53' not found
Warning: 15 out of 50 genes not mapped
```

### Solutions

#### 1. Check ID Type

```python
# Detect ID type
sample = genes[0]
if sample.startswith('ENSG'):
    id_type = 'ensembl'
elif sample.isdigit():
    id_type = 'entrez'
elif len(sample) == 6 and sample[0].isalpha():
    id_type = 'uniprot'
else:
    id_type = 'symbol'

print(f"Detected ID type: {id_type}")
```

#### 2. Convert IDs

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Convert Ensembl -> Symbol
if id_type == 'ensembl':
    result = tu.tools.MyGene_batch_query(
        gene_ids=genes,
        fields='symbol,entrezgene,ensembl.gene'
    )
    symbol_map = {hit['query']: hit.get('symbol', hit['query'])
                  for hit in result.get('results', [])}
    gene_symbols = [symbol_map.get(g, g) for g in genes]
```

#### 3. Remove Version Suffixes

```python
# ENSG00000141510.16 -> ENSG00000141510
genes_clean = [g.split('.')[0] for g in genes]
```

#### 4. Fix Common Typos

```python
# Common issues
fixes = {
    'TP-53': 'TP53',
    'BRCA 1': 'BRCA1',
    'p53': 'TP53',
    'egfr': 'EGFR',  # case-sensitive
}

genes_fixed = [fixes.get(g, g) for g in genes]
```

#### 5. Try Aliases

```python
# Use MyGene to find aliases
for gene in unmapped_genes:
    result = tu.tools.MyGene_query_genes(query=gene)
    if result.get('hits'):
        official_symbol = result['hits'][0].get('symbol')
        print(f"{gene} -> {official_symbol}")
```

---

## gseapy Library Not Found

### Symptoms
```
ValueError: gene_set 'GO_Biological_Process' not found
```

### Solutions

#### 1. List Available Libraries

```python
import gseapy as gp

all_libs = gp.get_library_name(organism='human')
print(f"Total libraries: {len(all_libs)}")

# Search for library
matching = [lib for lib in all_libs if 'GO_Biological' in lib]
print("Available GO BP libraries:", matching)
```

#### 2. Use Exact Library Name

```python
# Wrong (will fail)
gene_sets='GO_Biological_Process'

# Correct
gene_sets='GO_Biological_Process_2021'  # or 2023, 2025
```

#### 3. Check Case Sensitivity

```python
# Library names are case-sensitive
gene_sets='KEGG_2021_Human'  # NOT 'kegg_2021_human'
```

#### 4. Organism-Specific Libraries

```python
# Wrong for mouse
gene_sets='KEGG_2021_Human'  # Will fail for mouse genes

# Correct for mouse
gene_sets='KEGG_2019_Mouse'
```

---

## PANTHER Returns Empty Results

### Symptoms
```python
panther_result = tu.tools.PANTHER_enrichment(gene_list=genes, organism=9606, ...)
print(panther_result.get('data', {}).get('enriched_terms', []))  # Output: []
```

### Solutions

#### 1. Check Input Format

```python
# Wrong (array)
gene_list=["TP53", "BRCA1", "EGFR"]

# Correct (comma-separated string)
gene_list="TP53,BRCA1,EGFR"
```

#### 2. Check Organism ID

```python
# Wrong
organism='human'  # PANTHER uses taxonomy IDs

# Correct
organism=9606  # NCBI Taxonomy ID for human
```

#### 3. Check Annotation Dataset

```python
# Valid datasets
annotation_datasets = [
    'GO:0008150',  # Biological Process
    'GO:0003674',  # Molecular Function
    'GO:0005575',  # Cellular Component
    'ANNOT_TYPE_ID_PANTHER_PATHWAY',
    'ANNOT_TYPE_ID_PANTHER_REACTOME_PATHWAY',
]

# Wrong
annotation_dataset='biological_process'

# Correct
annotation_dataset='GO:0008150'
```

#### 4. Gene Symbols Not Recognized

```python
# PANTHER uses official gene symbols
# Convert using STRING first
mapped = tu.tools.STRING_map_identifiers(
    protein_ids=genes,
    species=9606
)
official_symbols = [item['preferredName'] for item in mapped.get('data', [])]
gene_list = ','.join(official_symbols)
```

---

## STRING Returns All Categories

### Symptoms
```python
string_result = tu.tools.STRING_functional_enrichment(
    protein_ids=genes,
    species=9606,
    category='Process'  # Only want GO BP
)
# But result includes Process, Function, Component, KEGG, Reactome, etc.
```

### Solution

**This is expected behavior**. STRING always returns all categories. Filter after receiving results:

```python
string_data = string_result.get('data', [])

# Filter by category
string_go_bp = [d for d in string_data if d.get('category') == 'Process']
string_go_mf = [d for d in string_data if d.get('category') == 'Function']
string_go_cc = [d for d in string_data if d.get('category') == 'Component']
string_kegg = [d for d in string_data if d.get('category') == 'KEGG']
string_reactome = [d for d in string_data if d.get('category') == 'Reactome']
string_wp = [d for d in string_data if d.get('category') == 'WikiPathways']

print(f"GO BP terms: {len(string_go_bp)}")
print(f"KEGG pathways: {len(string_kegg)}")
```

---

## Reactome Identifiers Not Found

### Symptoms
```python
reactome_result = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers=genes, ...)
identifiers_not_found = reactome_result.get('data', {}).get('identifiers_not_found', [])
print(f"Not found: {len(identifiers_not_found)}")  # High number
```

### Solutions

#### 1. Use Space-Separated String

```python
# Wrong (array)
identifiers=["TP53", "BRCA1", "EGFR"]

# Correct (space-separated string)
identifiers="TP53 BRCA1 EGFR"
# or
identifiers=' '.join(genes)
```

#### 2. Use Official Gene Symbols

```python
# Use STRING to get official names
mapped = tu.tools.STRING_map_identifiers(
    protein_ids=genes,
    species=9606
)
official_symbols = [item['preferredName'] for item in mapped.get('data', [])]
identifiers = ' '.join(official_symbols)
```

#### 3. Try UniProt IDs

```python
# Convert to UniProt IDs
mygene_result = tu.tools.MyGene_batch_query(
    gene_ids=genes,
    fields='uniprot.Swiss-Prot'
)
uniprot_ids = [hit['uniprot']['Swiss-Prot']
               for hit in mygene_result.get('results', [])
               if 'uniprot' in hit]
identifiers = ' '.join(uniprot_ids)
```

---

## enrichr_gene_enrichment_analysis Returns Wrong Format

### Symptoms
```python
result = tu.tools.enrichr_gene_enrichment_analysis(genes=genes, ...)
# Returns: connected_paths JSON string, NOT standard enrichment results
```

### Solution

**DO NOT USE `enrichr_gene_enrichment_analysis`** for standard enrichment analysis.

This ToolUniverse tool returns path analysis, not standard ORA enrichment.

**Use `gseapy.enrichr()` directly instead**:

```python
import gseapy

# Correct approach
result = gseapy.enrichr(
    gene_list=genes,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
# Returns standard enrichment DataFrame
```

---

## Results Don't Match Between Tools

### Symptoms
```python
# gseapy finds 50 significant terms
# PANTHER finds 30 significant terms
# Only 10 overlap
```

### Explanation & Solutions

#### This is Normal

Different tools use:
- Different gene set annotations (versions, curation)
- Different backgrounds (genome-wide vs database-specific)
- Different statistical methods (Fisher's exact vs hypergeometric)
- Different multiple testing corrections

#### Focus on Consensus

```python
# Extract GO IDs from each source
import re

gseapy_terms = set()
for term in go_bp_sig['Term']:
    match = re.search(r'(GO:\d+)', term)
    if match:
        gseapy_terms.add(match.group(1))

panther_terms = set(t['term_id'] for t in panther_bp_terms if t.get('fdr', 1) < 0.05)

string_terms = set(d['term'] for d in string_go_bp if d.get('fdr', 1) < 0.05)

# Consensus terms (in 2+ sources)
all_terms = gseapy_terms | panther_terms | string_terms
consensus = []
for term in all_terms:
    sources = []
    if term in gseapy_terms: sources.append('gseapy')
    if term in panther_terms: sources.append('PANTHER')
    if term in string_terms: sources.append('STRING')
    if len(sources) >= 2:
        consensus.append((term, sources))

print(f"Consensus terms: {len(consensus)}")
```

#### Report Both

```markdown
| GO Term | gseapy FDR | PANTHER FDR | STRING FDR | Consensus |
|---------|-----------|-------------|-----------|-----------|
| GO:0051726 | 3.4e-06 | 4.5e-05 | 3.2e-05 | 3/3 ✓ |
| GO:0006281 | 1.2e-05 | 2.1e-04 | - | 2/3 |
| GO:0007049 | 5.6e-06 | - | 8.9e-06 | 2/3 |
```

---

## GSEA Gives Unstable Results

### Symptoms
```python
# Run 1: 50 significant terms
# Run 2: 45 significant terms (different terms!)
```

### Solutions

#### 1. Set Random Seed

```python
gsea_result = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    seed=42,  # CRITICAL for reproducibility
    permutation_num=1000,
    ...
)
```

#### 2. Increase Permutation Number

```python
# More permutations = more stable p-values
gsea_result = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    seed=42,
    permutation_num=5000,  # instead of 1000
    ...
)
```

#### 3. Check for Ties

```python
# Check for many genes with same score
print(ranked_series.value_counts().head())
# If many ties, add small noise
import numpy as np
np.random.seed(42)
ranked_series = ranked_series + np.random.normal(0, 0.001, len(ranked_series))
```

---

## Memory Errors with Large Gene Lists

### Symptoms
```
MemoryError: Unable to allocate array
```

### Solutions

#### 1. Run Libraries Sequentially

```python
# Wrong (runs all at once)
result = gseapy.enrichr(
    gene_list=genes,
    gene_sets=['GO_Biological_Process_2021', 'GO_Molecular_Function_2021', ...],  # 10+ libraries
    ...
)

# Correct (one at a time)
results = {}
for lib in ['GO_Biological_Process_2021', 'GO_Molecular_Function_2021', 'KEGG_2021_Human']:
    results[lib] = gseapy.enrichr(gene_list=genes, gene_sets=lib, ...)
```

#### 2. Filter Gene Sets by Size

```python
gsea_result = gseapy.prerank(
    rnk=ranked_series,
    gene_sets='GO_Biological_Process_2021',
    min_size=10,    # instead of 5
    max_size=200,   # instead of 500
    ...
)
```

#### 3. Use Smaller Libraries

```python
# Instead of GO_Biological_Process_2021 (17,000 terms)
# Use GO Slim (high-level terms only)
gene_sets='ANNOT_TYPE_ID_PANTHER_GO_SLIM_BP'  # via PANTHER
```

---

## Getting Help

If you encounter an issue not covered here:

1. **Check gseapy documentation**: https://gseapy.readthedocs.io/
2. **Check tool parameter documentation**: `references/tool_parameters.md`
3. **Test with known good example**:
   ```python
   # Known working example
   genes = ["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN"]
   result = gseapy.enrichr(
       gene_list=genes,
       gene_sets='GO_Biological_Process_2021',
       organism='human',
       outdir=None,
       no_plot=True,
   )
   ```

---

See also:
- ora_workflow.md - Complete ORA examples
- gsea_workflow.md - Complete GSEA examples
- tool_parameters.md - Complete parameter reference
