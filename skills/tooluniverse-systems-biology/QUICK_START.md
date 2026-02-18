## Quick Start: Systems Biology & Pathway Analysis

This skill performs comprehensive pathway analysis using multiple databases (Reactome, KEGG, WikiPathways, Pathway Commons, BioModels).

---

## Choose Your Implementation

### Python SDK

#### Option 1: Complete Pipeline (Recommended)

Use the ready-made pipeline function for comprehensive analysis:

```python
from skills.tooluniverse_systems_biology.python_implementation import systems_biology_pipeline

# Example 1: Gene list enrichment
gene_list = ["TP53", "BRCA1", "EGFR", "MYC", "KRAS", "AKT1", "PTEN"]
systems_biology_pipeline(
    gene_list=gene_list,
    output_file="genelist_analysis.md"
)

# Example 2: Protein-specific pathways
systems_biology_pipeline(
    protein_id="P53350",  # TP53 protein
    output_file="tp53_pathways.md"
)

# Example 3: Keyword search
systems_biology_pipeline(
    pathway_keyword="apoptosis",
    organism="Homo sapiens",
    output_file="apoptosis_pathways.md"
)

# Example 4: Combined analysis
systems_biology_pipeline(
    gene_list=["TP53", "MDM2", "BCL2"],
    protein_id="P04637",
    pathway_keyword="cell death",
    output_file="comprehensive_analysis.md"
)
```

#### Option 2: Individual Tools

Use specific tools for targeted queries:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# 1. Pathway enrichment
enrichment = tu.tools.enrichr_gene_enrichment_analysis(
    gene_list=["TP53", "BRCA1", "EGFR"],
    library="KEGG_2021_Human"
)

# 2. Map protein to pathways
pathways = tu.tools.Reactome_map_uniprot_to_pathways(
    id="P53350"  # Note: parameter is 'id' not 'uniprot_id'
)

# 3. Get pathway details
reactions = tu.tools.Reactome_get_pathway_reactions(
    stId="R-HSA-73817"  # Reactome pathway ID
)

# 4. Search KEGG pathways
kegg_results = tu.tools.kegg_search_pathway(
    keyword="diabetes"
)

# 5. Search WikiPathways
wiki_results = tu.tools.WikiPathways_search(
    query="apoptosis",
    organism="Homo sapiens"
)

# 6. Search Pathway Commons
pc_results = tu.tools.pc_search_pathways(
    action="search_pathways",
    keyword="apoptosis",
    limit=10
)

# 7. Search BioModels
models = tu.tools.biomodels_search(
    query="glycolysis",
    limit=5
)

# 8. List top-level pathways
top_pathways = tu.tools.Reactome_list_top_pathways(
    species="Homo sapiens"
)
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Natural Language)

Ask Claude to perform analysis directly:

```
"Analyze pathways enriched in this gene list: TP53, BRCA1, EGFR, MYC, KRAS, AKT1, PTEN"

"What pathways is the protein P53350 involved in?"

"Find pathways related to apoptosis in humans"

"Search for computational models of glycolysis"

"What are the top-level biological pathways in humans?"

"Perform comprehensive pathway analysis for genes TP53, MDM2, BCL2 and also search for cell death pathways"
```

#### Option 2: Direct Tool Calls

Use specific tools via JSON (for programmatic MCP usage):

**1. Pathway Enrichment**:
```json
{
  "tool": "enrichr_gene_enrichment_analysis",
  "parameters": {
    "gene_list": ["TP53", "BRCA1", "EGFR"],
    "library": "KEGG_2021_Human"
  }
}
```

**2. Protein to Pathways**:
```json
{
  "tool": "Reactome_map_uniprot_to_pathways",
  "parameters": {
    "id": "P53350"
  }
}
```

**3. Pathway Reactions**:
```json
{
  "tool": "Reactome_get_pathway_reactions",
  "parameters": {
    "stId": "R-HSA-73817"
  }
}
```

**4. KEGG Search**:
```json
{
  "tool": "kegg_search_pathway",
  "parameters": {
    "keyword": "diabetes"
  }
}
```

**5. WikiPathways Search**:
```json
{
  "tool": "WikiPathways_search",
  "parameters": {
    "query": "apoptosis",
    "organism": "Homo sapiens"
  }
}
```

**6. Pathway Commons Search**:
```json
{
  "tool": "pc_search_pathways",
  "parameters": {
    "action": "search_pathways",
    "keyword": "apoptosis",
    "limit": 10
  }
}
```

**7. BioModels Search**:
```json
{
  "tool": "biomodels_search",
  "parameters": {
    "query": "glycolysis",
    "limit": 5
  }
}
```

**8. Top-Level Pathways**:
```json
{
  "tool": "Reactome_list_top_pathways",
  "parameters": {
    "species": "Homo sapiens"
  }
}
```

---

## Tool Parameters (All Implementations)

**Note**: Whether using Python SDK or MCP, the parameter names are the same.

### Pathway Enrichment
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `gene_list` | array | Yes | Array of gene symbols |
| `library` | string | Yes | Pathway library (e.g., "KEGG_2021_Human") |

### Protein-Pathway Mapping
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | UniProt accession (⚠️ NOT `uniprot_id`) |

### Pathway Reactions
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `stId` | string | Yes | Reactome stable ID (e.g., "R-HSA-73817") |

### KEGG Search
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | Yes | Search keyword |

### WikiPathways Search
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `organism` | string | No | Organism filter (e.g., "Homo sapiens") |

### Pathway Commons Search
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be "search_pathways" |
| `keyword` | string | Yes | Search keyword |
| `limit` | integer | No | Max results (default: 10) |

### BioModels Search
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `limit` | integer | No | Max results (default: 10) |

### Top-Level Pathways
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `species` | string | Yes | Organism (e.g., "Homo sapiens") |

---

## Common Recipes

### Recipe 1: Differential Expression Pathway Enrichment

**Python SDK**:
```python
# After identifying differentially expressed genes
de_genes = ["TP53", "EGFR", "MYC", "KRAS", "AKT1", "PTEN", "RB1", "BRCA1"]

systems_biology_pipeline(
    gene_list=de_genes,
    output_file="deseq_pathway_enrichment.md"
)
```

**MCP**:
```
"Perform pathway enrichment analysis for these differentially expressed genes:
TP53, EGFR, MYC, KRAS, AKT1, PTEN, RB1, BRCA1"
```

### Recipe 2: Protein Function Discovery

**Python SDK**:
```python
# Investigate unknown protein
systems_biology_pipeline(
    protein_id="Q9Y6K9",  # Example protein
    pathway_keyword="signaling",  # Related keyword
    output_file="protein_function_analysis.md"
)
```

**MCP**:
```
"What pathways is protein Q9Y6K9 involved in?
Also search for signaling pathways that might be relevant."
```

### Recipe 3: Disease Pathway Exploration

**Python SDK**:
```python
# Explore diabetes pathways
systems_biology_pipeline(
    pathway_keyword="diabetes",
    organism="Homo sapiens",
    output_file="diabetes_pathways.md"
)
```

**MCP**:
```
"Find all pathways related to diabetes in humans from multiple databases"
```

### Recipe 4: Multi-Database Comparison

**Python SDK**:
```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

keyword = "apoptosis"

# Search all databases
kegg = tu.tools.kegg_search_pathway(keyword=keyword)
wiki = tu.tools.WikiPathways_search(query=keyword, organism="Homo sapiens")
pc = tu.tools.pc_search_pathways(action="search_pathways", keyword=keyword, limit=20)
models = tu.tools.biomodels_search(query=keyword, limit=10)

# Compare coverage
print(f"KEGG: {len(kegg.get('data', []))} pathways")
print(f"WikiPathways: {len(wiki.get('data', {}).get('result', []))} pathways")
print(f"Pathway Commons: {pc.get('total_hits', 0)} pathways")
print(f"BioModels: {models.get('data', {}).get('matches', 0)} models")
```

**MCP**:
```
"Search for apoptosis pathways across KEGG, WikiPathways, Pathway Commons,
and BioModels. Compare the coverage across databases."
```

---

## Expected Output

### Report Structure

The skill generates a markdown report with these sections:

1. **Header**: Analysis parameters
2. **Pathway Enrichment** (if gene list provided)
   - Table of enriched pathways with p-values
   - Genes from input list in each pathway
3. **Protein Pathways** (if protein ID provided)
   - Reactome pathways containing the protein
   - Detailed reactions for top pathway
4. **Keyword Search Results** (if keyword provided)
   - KEGG pathways matching keyword
   - WikiPathways matches
   - Pathway Commons results with source attribution
   - BioModels computational models
5. **Top-Level Pathways** (always included)
   - Hierarchical view of major biological pathways

### Example Output Snippet

```markdown
# Systems Biology & Pathway Analysis Report

**Generated**: 2026-02-09 14:30:00
**Gene List**: TP53, BRCA1, EGFR, MYC, KRAS...
**Organism**: Homo sapiens

---

## 1. Pathway Enrichment Analysis

### KEGG Pathway Enrichment (15 pathways)

| Pathway | P-value | Adjusted P-value | Genes |
|---------|---------|------------------|-------|
| Cell cycle | 2.3e-05 | 0.0012 | TP53, RB1, MYC |
| p53 signaling pathway | 5.1e-04 | 0.0089 | TP53, MDM2 |
| ...

## 2. Pathways for Protein P53350

### Reactome Pathways (25 pathways)

| Pathway Name | Pathway ID | Species |
|--------------|------------|---------|
| Transcriptional Regulation by TP53 | R-HSA-3700989 | Homo sapiens |
| DNA Damage Response | R-HSA-5693532 | Homo sapiens |
| ...
```

---

## Troubleshooting

### Issue: Empty enrichment results
**Solution**: Check that gene symbols are correct (case-sensitive). Try alternative pathway library.

### Issue: Protein not found in Reactome
**Solution**: Verify UniProt ID is correct. Try searching by gene name using keyword search.

### Issue: Keyword returns no results
**Solution**: Try broader keyword or synonyms. Check spelling. Some specialized processes may have limited pathway annotations.

### Issue: Different result counts across databases
**Expected**: Different databases have different coverage. Cross-reference to validate findings.

---

## Next Steps

After running this skill:

1. **Follow-up Pathways**: Use pathway IDs to get detailed information
2. **Visualization**: Use database URLs to view pathway diagrams
3. **Literature Search**: Use pathway names in literature searches
4. **Validation**: Cross-reference enriched pathways across databases
5. **Functional Experiments**: Design experiments based on pathway predictions

---

## Additional Resources

- **Reactome**: https://reactome.org
- **KEGG**: https://www.genome.jp/kegg/
- **WikiPathways**: https://www.wikipathways.org
- **Pathway Commons**: https://www.pathwaycommons.org
- **BioModels**: https://www.ebi.ac.uk/biomodels/
- **Enrichr**: https://maayanlab.cloud/Enrichr/
