# Tool Parameters Reference

Complete parameter documentation for all enrichment tools.

---

## gseapy Tools

### gseapy.enrichr() - Over-Representation Analysis

**Function**: `gseapy.enrichr()`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `gene_list` | list[str] | Yes | - | List of gene symbols |
| `gene_sets` | str or list[str] | Yes | - | Enrichr library name(s) |
| `organism` | str | No | 'human' | Organism: 'human', 'mouse', 'fly', 'yeast', 'worm', 'fish', 'rat' |
| `outdir` | str or None | No | None | Output directory (None = no file output) |
| `no_plot` | bool | No | False | Suppress plots (set True for programmatic use) |
| `background` | list[str] or None | No | None | Custom background genes (None = genome-wide) |
| `cutoff` | float | No | 0.05 | Significance cutoff (applied after BH correction) |

**Returns**: Enrichr object with `.results` DataFrame

**Result DataFrame Columns**:
- `Gene_set`: Library name
- `Term`: GO term or pathway name
- `Overlap`: Format "X/Y" (X genes from list, Y total in pathway)
- `P-value`: Raw p-value from Fisher's exact test
- `Adjusted P-value`: Benjamini-Hochberg corrected p-value
- `Old P-value`: Legacy Enrichr p-value
- `Old Adjusted P-value`: Legacy corrected p-value
- `Odds Ratio`: Enrichment magnitude
- `Combined Score`: log(p-value) × z-score(odds ratio)
- `Genes`: Semicolon-separated gene list

**Example**:
```python
result = gseapy.enrichr(
    gene_list=['TP53', 'BRCA1', 'EGFR'],
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
df = result.results
```

---

### gseapy.prerank() - Gene Set Enrichment Analysis

**Function**: `gseapy.prerank()`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `rnk` | pd.Series | Yes | - | Ranked gene list (index=gene, value=score) |
| `gene_sets` | str or list[str] | Yes | - | Enrichr library name(s) or GMT file |
| `outdir` | str or None | No | None | Output directory (None = no file output) |
| `no_plot` | bool | No | False | Suppress plots |
| `seed` | int | No | None | Random seed for reproducibility (HIGHLY RECOMMENDED) |
| `min_size` | int | No | 5 | Minimum gene set size |
| `max_size` | int | No | 500 | Maximum gene set size |
| `permutation_num` | int | No | 1000 | Number of permutations (1000-5000) |

**Returns**: Prerank object with `.res2d` DataFrame

**Result DataFrame Columns**:
- `Name`: Gene set ID
- `Term`: Gene set name
- `ES`: Enrichment Score (raw)
- `NES`: Normalized Enrichment Score (positive = up, negative = down)
- `NOM p-val`: Nominal p-value (unadjusted)
- `FDR q-val`: False Discovery Rate (use cutoff < 0.25)
- `FWER p-val`: Family-Wise Error Rate (Bonferroni-like)
- `Tag %`: Percentage of genes in set before peak
- `Gene %`: Position in ranked list
- `Lead_genes`: Core enrichment genes

**Example**:
```python
import pandas as pd
ranked = pd.Series({'TP53': 3.2, 'BRCA1': 2.8, 'EGFR': -1.5}).sort_values(ascending=False)
result = gseapy.prerank(
    rnk=ranked,
    gene_sets='GO_Biological_Process_2021',
    outdir=None,
    no_plot=True,
    seed=42,
    min_size=5,
    max_size=500,
    permutation_num=1000,
)
df = result.res2d
```

---

## ToolUniverse Enrichment Tools

### PANTHER_enrichment

**Tool**: `tu.tools.PANTHER_enrichment`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gene_list` | str | Yes | **Comma-separated** gene symbols (NOT array!) |
| `organism` | int | Yes | NCBI Taxonomy ID (9606 for human, 10090 for mouse) |
| `annotation_dataset` | str | Yes | Dataset ID (see table below) |
| `enrichment_test_type` | str | No | 'FISHER' (default) or 'BINOMIAL' |
| `correction` | str | No | 'FDR' (Benjamini-Hochberg, default) or 'BONFERRONI' |

**Annotation Datasets**:
| Dataset ID | Description |
|-----------|-------------|
| `GO:0008150` | GO Biological Process |
| `GO:0003674` | GO Molecular Function |
| `GO:0005575` | GO Cellular Component |
| `ANNOT_TYPE_ID_PANTHER_PATHWAY` | PANTHER Pathways |
| `ANNOT_TYPE_ID_PANTHER_REACTOME_PATHWAY` | Reactome via PANTHER |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_BP` | GO Slim BP |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_MF` | GO Slim MF |
| `ANNOT_TYPE_ID_PANTHER_GO_SLIM_CC` | GO Slim CC |

**Returns**: `{data: {enriched_terms: [...]}}` structure

**enriched_terms fields**:
- `term_id`: Term ID (e.g., "GO:0051726")
- `term_label`: Term name
- `number_in_list`: Count in your gene list
- `number_in_reference`: Count in reference genome
- `expected`: Expected count by chance
- `fold_enrichment`: Observed/Expected
- `pvalue`: Raw p-value
- `fdr`: FDR-corrected p-value
- `direction`: "+" (over-represented) or "-" (under-represented)

**Example**:
```python
result = tu.tools.PANTHER_enrichment(
    gene_list='TP53,BRCA1,EGFR,MYC',  # comma-separated string
    organism=9606,
    annotation_dataset='GO:0008150'
)
terms = result.get('data', {}).get('enriched_terms', [])
```

---

### STRING_functional_enrichment

**Tool**: `tu.tools.STRING_functional_enrichment`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protein_ids` | list[str] | Yes | Gene symbols or STRING IDs |
| `species` | int | Yes | NCBI Taxonomy ID (9606 for human) |
| `category` | str | No | **IGNORED** - always returns all categories |

**Important**: STRING returns ALL categories regardless of `category` parameter. Filter by category after receiving results.

**Categories Returned**:
- `Process`: GO Biological Process
- `Function`: GO Molecular Function
- `Component`: GO Cellular Component
- `KEGG`: KEGG pathways
- `Reactome`: Reactome pathways
- `WikiPathways`: WikiPathways
- `COMPARTMENTS`: Protein localization
- `DISEASES`: Disease associations
- `TISSUES`: Tissue expression
- `Keyword`: UniProt keywords
- `PMID`: PubMed associations

**Returns**: `{status: "success", data: [...]}` structure

**data fields**:
- `category`: Category name (use for filtering)
- `term`: Term ID (e.g., "GO:0051726", "KEGG:04110")
- `description`: Term description
- `number_of_genes`: Count in your gene list
- `number_of_genes_in_background`: Count in STRING database
- `p_value`: Raw p-value
- `fdr`: FDR-corrected p-value
- `inputGenes`: Comma-separated input gene list
- `preferredNames`: Comma-separated preferred names

**Example**:
```python
result = tu.tools.STRING_functional_enrichment(
    protein_ids=['TP53', 'BRCA1', 'EGFR'],
    species=9606
)
data = result.get('data', [])
go_bp = [d for d in data if d.get('category') == 'Process']
kegg = [d for d in data if d.get('category') == 'KEGG']
```

---

### ReactomeAnalysis_pathway_enrichment

**Tool**: `tu.tools.ReactomeAnalysis_pathway_enrichment`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `identifiers` | str | Yes | - | **Space-separated** gene symbols (NOT array!) |
| `page_size` | int | No | 20 | Max pathways to return |
| `include_disease` | bool | No | True | Include disease pathways |
| `projection` | bool | No | False | Project to human (for cross-species) |

**Returns**: `{data: {pathways: [...], identifiers_not_found: [...]}}` structure

**pathways fields**:
- `pathway_id`: Reactome ID (e.g., "R-HSA-212436")
- `name`: Pathway name
- `species`: Species name
- `is_disease`: Boolean (disease pathway or not)
- `is_lowest_level`: Boolean (leaf pathway or parent)
- `entities_found`: Count in your gene list
- `entities_total`: Total entities in pathway
- `entities_ratio`: Found/Total ratio
- `p_value`: Raw p-value
- `fdr`: FDR-corrected p-value
- `reactions_found`: Reactions with your genes
- `reactions_total`: Total reactions

**Example**:
```python
result = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers='TP53 BRCA1 EGFR MYC',  # space-separated string
    page_size=50,
    include_disease=True,
    projection=False
)
pathways = result.get('data', {}).get('pathways', [])
not_found = result.get('data', {}).get('identifiers_not_found', [])
```

---

## ID Conversion Tools

### MyGene_batch_query

**Tool**: `tu.tools.MyGene_batch_query`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gene_ids` | list[str] | Yes | Gene IDs (symbols, Ensembl, Entrez, UniProt) |
| `fields` | str | No | Comma-separated fields to return |
| `species` | str | No | 'human', 'mouse', etc. (auto-detected if omitted) |

**Common Fields**:
- `symbol`: Official gene symbol
- `entrezgene`: Entrez Gene ID
- `ensembl.gene`: Ensembl gene ID
- `uniprot.Swiss-Prot`: UniProt ID
- `name`: Gene name
- `alias`: Gene aliases

**Returns**: `{results: [{query, _id, symbol, ...}]}`

**Example**:
```python
result = tu.tools.MyGene_batch_query(
    gene_ids=['ENSG00000141510', 'ENSG00000012048'],
    fields='symbol,entrezgene,ensembl.gene'
)
for hit in result.get('results', []):
    print(f"{hit['query']} -> {hit.get('symbol')}")
```

---

### STRING_map_identifiers

**Tool**: `tu.tools.STRING_map_identifiers`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protein_ids` | list[str] | Yes | Gene symbols or other identifiers |
| `species` | int | Yes | NCBI Taxonomy ID |

**Returns**: `{status: "success", data: [{...}]}`

**data fields**:
- `queryItem`: Your input ID
- `preferredName`: Official gene symbol (USE THIS)
- `stringId`: STRING database ID
- `annotation`: Additional info

**Example**:
```python
result = tu.tools.STRING_map_identifiers(
    protein_ids=['TP53', 'BRCA1', 'EGFR'],
    species=9606
)
for item in result.get('data', []):
    print(f"{item['queryItem']} -> {item['preferredName']} ({item['stringId']})")
```

---

## Organism Taxonomy IDs

| Organism | Common Name | Taxonomy ID |
|----------|------------|-------------|
| Human | Homo sapiens | 9606 |
| Mouse | Mus musculus | 10090 |
| Rat | Rattus norvegicus | 10116 |
| Fly | Drosophila melanogaster | 7227 |
| Worm | Caenorhabditis elegans | 6239 |
| Yeast | Saccharomyces cerevisiae | 4932 |
| Zebrafish | Danio rerio | 7955 |

---

## Common Parameter Mistakes

### 1. Array vs String

**WRONG**:
```python
# PANTHER expects string, not array
tu.tools.PANTHER_enrichment(gene_list=['TP53', 'BRCA1'], ...)
```

**CORRECT**:
```python
tu.tools.PANTHER_enrichment(gene_list='TP53,BRCA1', ...)
```

### 2. Comma vs Space Separation

**PANTHER**: Comma-separated
```python
gene_list='TP53,BRCA1,EGFR'
```

**Reactome**: Space-separated
```python
identifiers='TP53 BRCA1 EGFR'
```

### 3. Organism Format

**gseapy**: String name
```python
organism='human'  # NOT 9606
```

**PANTHER/STRING**: Taxonomy ID
```python
organism=9606  # NOT 'human'
species=9606
```

### 4. Library Names

**WRONG**:
```python
gene_sets='GO_Biological_Process'  # Missing year
```

**CORRECT**:
```python
gene_sets='GO_Biological_Process_2021'  # Include year
```

### 5. Result Access

**gseapy.enrichr**: `.results` attribute
```python
df = result.results  # NOT result.data
```

**gseapy.prerank**: `.res2d` attribute
```python
df = result.res2d  # NOT result.results
```

---

See also:
- ora_workflow.md - ORA usage examples
- gsea_workflow.md - GSEA usage examples
- troubleshooting.md - Common issues
