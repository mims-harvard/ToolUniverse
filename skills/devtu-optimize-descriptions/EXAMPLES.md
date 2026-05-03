# Tool Description Optimization - Detailed Examples

This file contains comprehensive examples of description improvements organized by issue type.

## Example Set 1: Clarifying Required Inputs

### ChIP-Atlas Enrichment Analysis

**Original (Unclear):**
```json
{
  "description": "Perform enrichment analysis with ChIP-Atlas to find transcription factors and histone modifications bound to genomic regions, sequence motifs, or gene lists.",
  "parameter": {
    "properties": {
      "bed_data": {"description": "BED format genomic regions"},
      "motif": {"description": "DNA sequence motif"},
      "gene_list": {"description": "Gene symbols"}
    }
  }
}
```

**Problem**: Users don't know if they should provide all three or just one.

**Improved:**
```json
{
  "description": "Perform enrichment analysis to identify transcription factors and histone modifications enriched in your data. **Required: Provide ONE input type** - (1) BED genomic regions, (2) DNA sequence motif (IUPAC notation), or (3) gene symbol list. Compares your input against 433,000+ ChIP-seq/ATAC-seq/Bisulfite-seq experiments to identify significant enrichment. Returns ranked list of proteins bound to your regions/motif or regulating your genes.",
  "parameter": {
    "properties": {
      "bed_data": {
        "description": "**Option 1**: BED format genomic regions (tab-separated: chr, start, end). For finding proteins bound to specific genomic regions. Example: 'chr1\\t1000\\t2000\\nchr2\\t3000\\t4000'."
      },
      "motif": {
        "description": "**Option 2**: DNA sequence motif in IUPAC notation. Use: A/T/G/C (bases), W=A|T, S=G|C, M=A|C, K=G|T, R=A|G, Y=C|T. Example: 'CANNTG' (E-box motif)."
      },
      "gene_list": {
        "description": "**Option 3**: Gene symbols (HGNC for human, MGI for mouse). Provide as array or single gene. Example: ['TP53', 'MDM2', 'CDKN1A']."
      }
    }
  }
}
```

**Key Changes**:
- Added "**Required: Provide ONE input type**" in bold
- Numbered options (1), (2), (3)
- Used "**Option X**" labels in parameters
- Added format details and examples to each option

---

## Example Set 2: Adding Prerequisites

### CELLxGENE Census Tools

**Original (Missing Prerequisites):**
```json
{
  "name": "CELLxGENE_get_census_versions",
  "description": "Get list of available CELLxGENE Census versions with release dates and descriptions. The Census contains single-cell RNA-seq data from 50M+ cells."
}
```

**Improved:**
```json
{
  "name": "CELLxGENE_get_census_versions",
  "description": "Get list of available CELLxGENE Census versions with release dates and descriptions. The Census contains single-cell RNA-seq data from 50M+ cells (human, mouse, non-human primates). Prerequisites: Requires 'cellxgene-census' package (install: pip install tooluniverse[singlecell]). Use for: checking available data versions, selecting stable vs latest builds."
}
```

### 4DN Data Portal Tools

**Original:**
```json
{
  "name": "FourDN_get_download_url",
  "description": "Get download URL and DRS API endpoint for 4DN files. All downloads require authentication."
}
```

**Improved:**
```json
{
  "name": "FourDN_get_download_url",
  "description": "Get download URL and DRS (Data Repository Service) API endpoint for 4DN files. Prerequisites: Requires free 4DN account - create at data.4dnucleome.org, then generate access key in your profile settings. Returns download URL and instructions for command-line access with curl."
}
```

---

## Example Set 3: Expanding Abbreviations

### Various Tools

**Original Examples:**
```json
"Download H5AD files from datasets"
"BigWig contains coverage scores in RPM"
"Distance from TSS for gene analysis"
"Access TAD boundaries and loop calls"
"Supports GA4GH DRS standard"
```

**Improved Examples:**
```json
"Download H5AD (HDF5-based AnnData) files from datasets"
"BigWig contains coverage scores in RPM (Reads Per Million)"
"Distance from Transcription Start Site (TSS) for gene analysis"
"Access TAD (Topologically Associating Domain) boundaries and loop calls"
"Supports GA4GH DRS (Data Repository Service) standard"
```

**Pattern**: "Abbreviation (Full Name)" on first use

---

## Example Set 4: Enhanced Filter Descriptions

### CELLxGENE Filters

**Original (Minimal):**
```json
{
  "obs_value_filter": {
    "description": "SOMA value filter string (e.g., 'tissue == \"lung\" and cell_type == \"T cell\"')"
  }
}
```

**Improved (Comprehensive):**
```json
{
  "obs_value_filter": {
    "description": "Filter cells using SQL-like syntax. Format: 'field == \"value\"'. Operators: ==, !=, in, <, >, <=, >=. Combine with 'and'/'or'. Common fields: tissue, cell_type, disease, assay, sex, ethnicity, donor_id, suspension_type, development_stage. Examples: 'tissue == \"lung\"', 'disease == \"COVID-19\" and tissue == \"lung\"', 'cell_type in [\"T cell\", \"B cell\"]'."
  }
}
```

**Key Additions**:
- Syntax description ("SQL-like")
- Format pattern
- List of operators
- 8-10 common field names
- 3 diverse examples

### Gene Filters

**Original:**
```json
{
  "var_value_filter": {
    "description": "SOMA value filter string (e.g., 'feature_name == \"CD4\"')"
  }
}
```

**Improved:**
```json
{
  "var_value_filter": {
    "description": "Filter genes using SQL-like syntax. Format: 'field == \"value\"'. Common fields: feature_name (gene symbol), feature_id (Ensembl ID), feature_biotype. Examples: 'feature_name == \"TP53\"', 'feature_name in [\"CD4\", \"CD8A\"]', 'feature_biotype == \"protein_coding\"'."
  }
}
```

---

## Example Set 5: Parameter Guidance with Trade-offs

### Threshold Parameters

**Original (Unclear):**
```json
{
  "threshold": {
    "description": "MACS2 Q-value threshold (05=1e-5, 10=1e-10, 20=1e-20)",
    "enum": ["05", "10", "20"],
    "default": "05"
  }
}
```

**Improved (Actionable):**
```json
{
  "threshold": {
    "description": "Peak calling stringency (MACS2 Q-value). Options: '05'=1e-5 (permissive, more peaks, broader features), '10'=1e-10 (moderate, balanced), '20'=1e-20 (strict, high confidence only, narrow peaks). Default '05' suitable for most analyses. Higher values = fewer but more confident peaks.",
    "enum": ["05", "10", "20"],
    "default": "05"
  }
}
```

**Elements Added**:
- What each value means (permissive, moderate, strict)
- Practical outcome (more/fewer peaks)
- When to use each (broad vs narrow features)
- Clear recommendation (default suitable for most)
- General principle (higher = fewer but confident)

### Version Selection

**Original:**
```json
{
  "census_version": {
    "description": "Census version ('stable', 'latest', or 'YYYY-MM-DD')",
    "default": "stable"
  }
}
```

**Improved:**
```json
{
  "census_version": {
    "description": "Census version to query. 'stable' (recommended, Long-Term Support release), 'latest' (newest data, may change), or specific date 'YYYY-MM-DD' (for reproducibility). Default 'stable' is best for production analyses.",
    "default": "stable"
  }
}
```

### Distance/Range Parameters

**Original:**
```json
{
  "distance": {
    "description": "Distance from TSS for gene list analysis (bp)",
    "default": "5000"
  }
}
```

**Improved:**
```json
{
  "distance": {
    "description": "Distance from Transcription Start Site (TSS) in base pairs for gene-TF association. Defines promoter region. Default 5000 (±5kb, captures typical promoters). Use 1000-2000 for narrow promoters, 10000+ for enhancer regions.",
    "default": "5000"
  }
}
```

---

## Example Set 6: File Type Explanations

### 4DN File Types

**Original (Cryptic):**
```json
{
  "file_type": {
    "description": "Filter by file type (e.g., 'contact list', 'pairs', 'cooler')"
  }
}
```

**Improved (Explanatory):**
```json
{
  "file_type": {
    "description": "Filter by file type. Common types: 'contact list' (processed contact matrices), 'pairs' (aligned read pairs), 'cooler' (multi-resolution contact matrices), 'mcool' (multi-resolution cooler), 'hic' (Juicer format)."
  }
}
```

**Pattern**: "type_name (what it contains/represents)"

---

## Example Set 7: Complete Tool Description Makeover

### Before: Minimal Description

```json
{
  "name": "API_query_data",
  "type": "APITool",
  "description": "Query data from API. Returns results.",
  "parameter": {
    "properties": {
      "query": {"description": "Query string"},
      "limit": {"description": "Result limit"},
      "version": {"description": "API version"}
    }
  }
}
```

### After: Comprehensive Description

```json
{
  "name": "API_query_cell_data",
  "type": "SingleCellAPITool",
  "description": "Query single-cell RNA-seq data from Census database containing 50M+ cells (human, mouse, non-human primate). Prerequisites: Requires 'census-api' package (install: pip install tooluniverse[singlecell]). Filter by tissue, cell type, disease, or metadata fields. Returns cell metadata and gene expression summaries. Note: Large queries require 8GB+ RAM. Use for: finding cells matching criteria, exploring cell type distributions, quality filtering, cohort selection for analysis.",
  "parameter": {
    "properties": {
      "query": {
        "description": "Filter cells using SQL-like syntax. Format: 'field == \"value\"'. Operators: ==, !=, in, <, >, <=, >=. Common fields: tissue, cell_type, disease, assay, sex. Examples: 'tissue == \"lung\"', 'disease == \"COVID-19\" and tissue == \"lung\"'."
      },
      "limit": {
        "description": "Maximum cells to return. Default 1000. Use 100-1000 for exploration, 10000+ for analysis. Note: Higher limits require more memory.",
        "default": 1000
      },
      "version": {
        "description": "Census version. 'stable' (recommended, Long-Term Support), 'latest' (newest data, may change), or date 'YYYY-MM-DD' (reproducibility). Default 'stable' best for production.",
        "default": "stable"
      }
    }
  }
}
```

**Improvements Made**:
1. ✅ Specific tool name (not generic "API")
2. ✅ Data scale mentioned (50M+ cells)
3. ✅ Prerequisites stated upfront
4. ✅ Filter syntax explained
5. ✅ Common fields listed
6. ✅ Multiple examples provided
7. ✅ Memory requirements noted
8. ✅ "Use for:" with 4 specific cases
9. ✅ Parameter guidance with trade-offs
10. ✅ Recommendations for each parameter
11. ✅ Practical ranges explained

---

## Common Description Anti-Patterns

### Anti-Pattern 1: Vague Purpose

**Bad:**
```
"Process data from database"
```

**Good:**
```
"Query single-cell RNA-seq metadata from Census containing 50M+ cells. Filter by tissue, cell type, disease. Returns cell annotations and QC metrics."
```

### Anti-Pattern 2: Missing Context

**Bad:**
```
"threshold": "Threshold value (05, 10, 20)"
```

**Good:**
```
"threshold": "Peak stringency. '05'=permissive (more peaks), '10'=moderate, '20'=strict (high confidence). Default '05' for most analyses."
```

### Anti-Pattern 3: Assuming Knowledge

**Bad:**
```
"Filter using SOMA syntax"
```

**Good:**
```
"Filter using SQL-like syntax. Format: 'field == \"value\"'. Operators: ==, !=, in. Examples: 'tissue == \"lung\"', 'cell_type in [\"T cell\", \"B cell\"]'."
```

### Anti-Pattern 4: No Examples

**Bad:**
```
"gene_list": "List of gene symbols"
```

**Good:**
```
"gene_list": "Gene symbols as array. Example: ['TP53', 'MDM2', 'CDKN1A']. Use HGNC symbols for human, MGI for mouse."
```

### Anti-Pattern 5: Hidden Prerequisites

**Bad:**
```
"Download H5AD files..."
```

**Good:**
```
"Download H5AD files... Prerequisites: Requires 'package-name' (install: pip install tooluniverse[extra]). Files can be large (GBs)."
```

---

## Description Length Guidelines

### Too Short (Unhelpful)
```json
"description": "Query data. Returns results."
```
**Length**: 6 words  
**Problem**: No context, no guidance

### Optimal (Clear and Concise)
```json
"description": "Query single-cell data from 50M+ cell Census. Prerequisites: Requires 'census-api' package. Filter by tissue, cell type, disease. Returns cell metadata. Use for: finding cells, cohort selection, quality filtering."
```
**Length**: 35 words  
**Sweet spot**: 30-60 words for main description

### Too Long (Verbose)
```json
"description": "This tool provides functionality to query single-cell RNA sequencing data from the comprehensive Census database which contains over 50 million cells from various organisms including humans, mice, and non-human primates. Users can filter the data using multiple criteria such as tissue type, cell type classification, disease status, and various other metadata fields. The tool requires the 'census-api' Python package to be installed, which can be done using pip with the command 'pip install tooluniverse[singlecell]'. The results returned include detailed cell metadata information. This tool is particularly useful for researchers who need to find cells matching specific criteria, explore cell type distributions across tissues, perform quality filtering on datasets, or select cohorts for downstream analysis tasks."
```
**Length**: 120 words  
**Problem**: Too verbose, reader fatigue

---

## Testing Your Descriptions

### The 30-Second Test

Give someone unfamiliar with the tool just the description. After 30 seconds, can they answer:

1. What does this tool do?
2. What do I need to provide?
3. What will I get back?
4. Do I need anything installed/configured?

If no to any = description needs improvement.

### The First-Try Test

Can a user successfully call the tool on their first attempt without:
- Reading external documentation
- Trial and error with parameters
- Asking for help

If no = improve parameter descriptions.

### The Decision Test

For parameters with options, can a user confidently choose which option is right for their use case?

If no = add trade-off explanations and recommendations.
