---
name: tooluniverse-rnaseq-deseq2
description: Production-ready RNA-seq differential expression analysis using PyDESeq2. Performs DESeq2 normalization, dispersion estimation, Wald testing, LFC shrinkage, and result filtering. Handles multi-factor designs, multiple contrasts, batch effects, and integrates with gene enrichment (gseapy) and ToolUniverse annotation tools (UniProt, Ensembl, OpenTargets). Supports CSV/TSV/H5AD input formats and any organism. Use when analyzing RNA-seq count matrices, identifying DEGs, performing differential expression with statistical rigor, or answering questions about gene expression changes.
---

# RNA-seq Differential Expression Analysis (DESeq2)

Comprehensive differential expression analysis of RNA-seq count data using PyDESeq2, with integrated enrichment analysis (gseapy) and gene annotation via ToolUniverse.

**KEY PRINCIPLES**:
1. **Data-first approach** - Load and validate count data and metadata BEFORE any analysis
2. **Statistical rigor** - Always use proper normalization, dispersion estimation, and multiple testing correction
3. **Flexible design** - Support single-factor, multi-factor, and interaction designs
4. **Threshold awareness** - Apply user-specified thresholds exactly (padj, log2FC, baseMean)
5. **Reproducible** - Set random seeds, document all parameters, output complete results
6. **Question-driven** - Parse what the user is actually asking and extract the specific answer
7. **Enrichment integration** - Chain DESeq2 results into pathway/GO enrichment when requested
8. **English-first queries** - Use English gene/pathway names in all tool calls

---

## When to Use This Skill

Apply when users:
- Have RNA-seq count matrices and want differential expression analysis
- Ask about DESeq2, DEGs, differential expression, padj, log2FC
- Need dispersion estimates or diagnostics
- Want enrichment analysis (GO, KEGG, Reactome) on DEGs
- Ask about specific gene expression changes between conditions
- Need to compare multiple strains/conditions/treatments
- Ask about batch effect correction in RNA-seq
- Questions mention "count data", "count matrix", "RNA-seq", "transcriptomics"

**BixBench Coverage**: Validated on 53 BixBench questions across 15 computational biology projects covering RNA-seq, miRNA-seq, and differential expression analysis tasks

---

## Required Python Packages

```python
# Core (MUST be installed)
import pandas as pd
import numpy as np
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
from scipy import stats

# Enrichment (for GO/KEGG/Reactome questions)
import gseapy as gp

# ToolUniverse (for gene annotation)
from tooluniverse import ToolUniverse
```

**Installation** (if not already present):
```bash
pip install pydeseq2 gseapy pandas numpy scipy anndata
```

---

## Phase 0: Question Parsing and Input Identification

**CRITICAL FIRST STEP**: Before writing ANY code, parse the question to identify:

### 0.1 What Data Files Are Available?

Look in the working directory or data folder for:
- **Count matrices**: `*.csv`, `*.tsv`, `*.txt`, `*.h5ad`, `*counts*`, `*expression*`
- **Metadata/sample info**: `*metadata*`, `*coldata*`, `*sample*`, `*design*`, `*pheno*`
- **Gene annotations**: `*annotation*`, `*gencode*`, `*gtf*`

```python
import os
import glob

# List all data files
data_dir = "."  # or specified path
all_files = glob.glob(os.path.join(data_dir, "**/*"), recursive=True)
data_files = [f for f in all_files if f.endswith(('.csv', '.tsv', '.txt', '.h5ad', '.rds', '.h5'))]
print("Available data files:", data_files)
```

### 0.2 Parse the Question Requirements

Extract these parameters from the question:

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

### 0.3 Decision Tree

```
Q: Is there a count matrix file?
  YES -> Phase 1 (load data)
  NO  -> Q: Is there an h5ad/AnnData file?
           YES -> Load with anndata, extract counts
           NO  -> Q: Is there processed DE results already?
                    YES -> Skip to Phase 4 (filtering/enrichment)
                    NO  -> ERROR: No suitable input data found
```

---

## Phase 1: Data Loading and Validation

### 1.1 Load Count Matrix

```python
import pandas as pd
import numpy as np
import os

def load_count_matrix(file_path, **kwargs):
    """Load count matrix from various formats.

    Expects: genes as rows/columns, samples as rows/columns.
    PyDESeq2 requires: samples as rows, genes as columns.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        df = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    elif ext in ['.h5ad']:
        import anndata
        adata = anndata.read_h5ad(file_path)
        df = pd.DataFrame(
            adata.X.toarray() if hasattr(adata.X, 'toarray') else adata.X,
            index=adata.obs_names,
            columns=adata.var_names
        )
        return df, adata.obs  # Return metadata too if available
    else:
        # Try tab-separated as default
        df = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return df
```

### 1.2 Orient the Matrix

**CRITICAL**: PyDESeq2 expects samples as rows, genes as columns.

```python
def orient_count_matrix(df, metadata_samples=None):
    """Ensure samples are rows and genes are columns.

    Heuristic: if column count >> row count, genes are likely columns (correct).
    If row count >> column count, genes are likely rows (need transpose).
    If metadata_samples provided, match against index and columns.
    """
    if metadata_samples is not None:
        # Check if samples match rows or columns
        row_match = len(set(df.index) & set(metadata_samples))
        col_match = len(set(df.columns) & set(metadata_samples))
        if col_match > row_match:
            df = df.T
        return df

    # Heuristic: typical RNA-seq has 10-1000 samples and 10000-60000 genes
    if df.shape[0] > df.shape[1] * 5:  # Many more rows than columns
        df = df.T  # Transpose: genes were rows

    return df
```

### 1.3 Load Metadata

```python
def load_metadata(file_path, **kwargs):
    """Load sample metadata (colData in R)."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.csv']:
        meta = pd.read_csv(file_path, index_col=0, **kwargs)
    elif ext in ['.tsv', '.txt']:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)
    else:
        meta = pd.read_csv(file_path, sep='\t', index_col=0, **kwargs)

    return meta
```

### 1.4 Validate and Align

```python
def validate_inputs(counts, metadata):
    """Validate count matrix and metadata alignment."""
    issues = []

    # Check sample alignment
    count_samples = set(counts.index)
    meta_samples = set(metadata.index)

    if count_samples != meta_samples:
        common = count_samples & meta_samples
        if len(common) == 0:
            # Try matching columns
            if set(counts.columns) & meta_samples:
                counts = counts.T
                count_samples = set(counts.index)
                common = count_samples & meta_samples

        if len(common) > 0:
            counts = counts.loc[sorted(common)]
            metadata = metadata.loc[sorted(common)]
            issues.append(f"Aligned to {len(common)} common samples")
        else:
            issues.append("ERROR: No matching samples between counts and metadata")
            return None, None, issues

    # Ensure integer counts
    if counts.dtypes.apply(lambda x: x == float).any():
        if (counts % 1 == 0).all().all():
            counts = counts.astype(int)
        else:
            # Might be normalized data - round to integers for DESeq2
            issues.append("WARNING: Non-integer counts detected. Rounding to integers.")
            counts = counts.round().astype(int)

    # Remove genes with zero counts across all samples
    nonzero_mask = counts.sum(axis=0) > 0
    n_removed = (~nonzero_mask).sum()
    if n_removed > 0:
        counts = counts.loc[:, nonzero_mask]
        issues.append(f"Removed {n_removed} genes with zero counts across all samples")

    # Remove negative values
    if (counts < 0).any().any():
        issues.append("WARNING: Negative counts detected. Setting to 0.")
        counts = counts.clip(lower=0)

    return counts, metadata, issues
```

### 1.5 Subset Samples (if needed)

Many BixBench questions ask to analyze only a subset:
- "Control mice only"
- "CD4/CD8 cells only"
- "Excluding the third replicates"

```python
def subset_samples(counts, metadata, condition_col, values=None, exclude=None):
    """Subset samples based on metadata conditions."""
    if values is not None:
        mask = metadata[condition_col].isin(values)
    elif exclude is not None:
        mask = ~metadata[condition_col].isin(exclude)
    else:
        return counts, metadata

    metadata = metadata[mask]
    counts = counts.loc[metadata.index]
    return counts, metadata
```

---

## Phase 2: DESeq2 Analysis

### 2.1 Setup and Run DESeq2

```python
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

def run_deseq2(counts, metadata, design="~condition",
               continuous_factors=None, fit_type="parametric",
               min_replicates=7, quiet=True):
    """Run full DESeq2 pipeline.

    Args:
        counts: DataFrame with samples as rows, genes as columns (integer counts)
        metadata: DataFrame with sample annotations, index matching counts
        design: Design formula string (e.g., "~condition", "~strain + media")
        continuous_factors: List of continuous covariate names
        fit_type: "parametric" or "mean"
        min_replicates: Minimum replicates for Cook's distance filtering
        quiet: Suppress verbose output

    Returns:
        dds: DeseqDataSet object with fitted model
    """
    dds = DeseqDataSet(
        counts=counts,
        metadata=metadata,
        design=design,
        continuous_factors=continuous_factors,
        fit_type=fit_type,
        min_replicates=min_replicates,
        quiet=quiet
    )

    dds.deseq2()
    return dds
```

### 2.2 Set Reference Level

**IMPORTANT**: In PyDESeq2 v0.5.4, `ref_level` parameter is deprecated. Instead, use `pd.Categorical` with ordered categories where the FIRST category is the reference.

```python
def set_reference_level(metadata, factor_col, ref_value):
    """Set reference level for a factor by reordering Categorical.

    The FIRST category becomes the reference level in PyDESeq2.
    """
    current_cats = metadata[factor_col].unique().tolist()
    if ref_value not in current_cats:
        raise ValueError(f"Reference '{ref_value}' not in categories: {current_cats}")

    # Put reference first
    ordered_cats = [ref_value] + [c for c in current_cats if c != ref_value]
    metadata[factor_col] = pd.Categorical(
        metadata[factor_col],
        categories=ordered_cats
    )
    return metadata
```

### 2.3 Extract Contrasts

```python
def extract_results(dds, contrast, alpha=0.05, lfc_shrink=False, quiet=True):
    """Extract DE results for a specific contrast.

    Args:
        dds: Fitted DeseqDataSet
        contrast: List of [factor, numerator, denominator]
                  e.g., ["condition", "treatment", "control"]
        alpha: Significance threshold for independent filtering
        lfc_shrink: Whether to apply LFC shrinkage
        quiet: Suppress output

    Returns:
        results_df: DataFrame with baseMean, log2FC, lfcSE, stat, pvalue, padj
    """
    stat_res = DeseqStats(dds, contrast=contrast, alpha=alpha, quiet=quiet)
    stat_res.run_wald_test()
    stat_res.summary()

    if lfc_shrink:
        # Determine coefficient name for shrinkage
        # Format: factor[T.numerator] (relative to reference)
        factor, numerator, denominator = contrast
        coeff = f"{factor}[T.{numerator}]"

        # Verify coeff exists
        available_coeffs = list(dds.varm['LFC'].columns)
        if coeff not in available_coeffs:
            # Try alternative format
            alt_coeff = f"{factor}_{numerator}_vs_{denominator}"
            if alt_coeff in available_coeffs:
                coeff = alt_coeff
            else:
                print(f"WARNING: Coefficient '{coeff}' not found. Available: {available_coeffs}")
                print("Skipping LFC shrinkage.")
                return stat_res.results_df

        stat_res.lfc_shrink(coeff=coeff)

    return stat_res.results_df
```

### 2.4 Multiple Testing Correction Methods

Some BixBench questions ask for specific correction methods beyond BH:

```python
from scipy import stats as scipy_stats
from statsmodels.stats.multitest import multipletests

def apply_multiple_testing_correction(pvalues, method='fdr_bh'):
    """Apply various multiple testing corrections.

    Methods:
        'fdr_bh': Benjamini-Hochberg (default, same as DESeq2)
        'fdr_by': Benjamini-Yekutieli
        'bonferroni': Bonferroni
        'holm': Holm-Bonferroni
    """
    # Handle NaN p-values
    mask = ~np.isnan(pvalues)
    adjusted = np.full_like(pvalues, np.nan)

    if mask.sum() > 0:
        _, adjusted[mask], _, _ = multipletests(pvalues[mask], method=method)

    return adjusted
```

---

## Phase 3: Dispersion Analysis

### 3.1 Access Dispersion Estimates

**CRITICAL**: In PyDESeq2, dispersions are stored in `dds.var` (NOT `dds.varm`).

```python
def get_dispersion_data(dds):
    """Extract all dispersion-related data from fitted DESeq2 model.

    Returns dict with:
        - genewise_dispersions: Per-gene maximum likelihood estimates
        - fitted_dispersions: Trend-fitted values
        - MAP_dispersions: Maximum a posteriori (after shrinkage to trend)
        - dispersions: Final dispersions used in testing
    """
    disp_data = {}

    # Key dispersion columns in dds.var
    disp_columns = [
        'genewise_dispersions',  # Pre-shrinkage (gene-wise MLE)
        'fitted_dispersions',     # Trend curve values
        'MAP_dispersions',        # Post-shrinkage (MAP estimates)
        'dispersions',            # Final (MAP or genewise for outliers)
    ]

    for col in disp_columns:
        if col in dds.var.columns:
            disp_data[col] = dds.var[col]

    return disp_data
```

### 3.2 Dispersion Diagnostics

```python
def dispersion_diagnostics(dds, threshold=1e-5):
    """Analyze dispersion estimates for diagnostics.

    Common BixBench question: "How many genes have a dispersion estimate
    below 1e-05 prior to dispersion fitting?"

    Answer: Count genewise_dispersions < threshold
    """
    disp_data = get_dispersion_data(dds)

    diagnostics = {}

    if 'genewise_dispersions' in disp_data:
        gwd = disp_data['genewise_dispersions']
        diagnostics['genewise_below_threshold'] = (gwd < threshold).sum()
        diagnostics['genewise_min'] = gwd.min()
        diagnostics['genewise_max'] = gwd.max()
        diagnostics['genewise_median'] = gwd.median()

    if 'MAP_dispersions' in disp_data:
        mapd = disp_data['MAP_dispersions']
        diagnostics['MAP_below_threshold'] = (mapd < threshold).sum()

    if 'dispersions' in disp_data:
        d = disp_data['dispersions']
        diagnostics['final_below_threshold'] = (d < threshold).sum()

    return diagnostics
```

### 3.3 Dispersion Question Interpretation

| Question Phrasing | Which Dispersion | PyDESeq2 Column |
|---|---|---|
| "prior to dispersion fitting" | Gene-wise MLE | `genewise_dispersions` |
| "prior to shrinkage" | Gene-wise MLE | `genewise_dispersions` |
| "fitted dispersions" | Trend curve | `fitted_dispersions` |
| "after shrinkage" / "MAP" | MAP estimates | `MAP_dispersions` |
| "dispersion estimate" (general) | Final | `dispersions` |
| "before dispersion fitting" | Gene-wise MLE | `genewise_dispersions` |

---

## Phase 4: Result Filtering and Extraction

### 4.1 Filter DEGs

```python
def filter_degs(results_df, padj_threshold=0.05, lfc_threshold=0,
                basemean_threshold=0, direction='both'):
    """Filter differentially expressed genes.

    Args:
        results_df: DESeq2 results DataFrame
        padj_threshold: Adjusted p-value cutoff
        lfc_threshold: Absolute log2 fold change cutoff (0 = no filter)
        basemean_threshold: Minimum mean expression
        direction: 'both', 'up', or 'down'

    Returns:
        Filtered DataFrame
    """
    df = results_df.dropna(subset=['padj'])  # Remove NaN padj

    # Apply filters
    mask = df['padj'] < padj_threshold

    if lfc_threshold > 0:
        mask = mask & (df['log2FoldChange'].abs() > lfc_threshold)

    if basemean_threshold > 0:
        mask = mask & (df['baseMean'] >= basemean_threshold)

    if direction == 'up':
        mask = mask & (df['log2FoldChange'] > 0)
    elif direction == 'down':
        mask = mask & (df['log2FoldChange'] < 0)

    return df[mask]
```

### 4.2 Extract Specific Gene Results

```python
def get_gene_result(results_df, gene_name, column='log2FoldChange'):
    """Get a specific value for a specific gene.

    Handles case-insensitive matching and common naming issues.
    """
    # Try exact match first
    if gene_name in results_df.index:
        return results_df.loc[gene_name, column]

    # Case-insensitive match
    idx_lower = {g.lower(): g for g in results_df.index}
    if gene_name.lower() in idx_lower:
        actual_name = idx_lower[gene_name.lower()]
        return results_df.loc[actual_name, column]

    # Partial match (for gene IDs like PA14_35160)
    matches = [g for g in results_df.index if gene_name.lower() in g.lower()]
    if len(matches) == 1:
        return results_df.loc[matches[0], column]
    elif len(matches) > 1:
        return {m: results_df.loc[m, column] for m in matches}

    return None  # Gene not found
```

### 4.3 Set Operations on DEG Lists

Many BixBench questions ask about overlapping/unique DEGs across conditions:

```python
def compare_deg_sets(deg_sets, operation='unique'):
    """Compare DEG sets across conditions.

    Args:
        deg_sets: Dict of {condition_name: set_of_gene_names}
        operation: 'unique' (per condition), 'shared' (intersection),
                   'union', 'venn' (all combinations)

    Returns:
        Dict with results
    """
    results = {}
    condition_names = list(deg_sets.keys())
    all_genes = set()
    for genes in deg_sets.values():
        all_genes |= genes

    if operation == 'unique':
        # Genes unique to each condition (not in any other)
        for cond in condition_names:
            others = set()
            for other_cond in condition_names:
                if other_cond != cond:
                    others |= deg_sets[other_cond]
            results[cond] = deg_sets[cond] - others

    elif operation == 'shared':
        # Intersection of all
        shared = deg_sets[condition_names[0]]
        for cond in condition_names[1:]:
            shared = shared & deg_sets[cond]
        results['shared'] = shared

    elif operation == 'union':
        results['union'] = all_genes

    elif operation == 'venn':
        # All combinations
        from itertools import combinations
        for r in range(1, len(condition_names) + 1):
            for combo in combinations(condition_names, r):
                label = ' & '.join(combo)
                intersection = deg_sets[combo[0]]
                for cond in combo[1:]:
                    intersection = intersection & deg_sets[cond]
                # Remove genes that appear in conditions not in this combo
                others = [c for c in condition_names if c not in combo]
                for other in others:
                    intersection = intersection - deg_sets[other]
                results[label] = intersection

    return results
```

---

## Phase 5: Gene Enrichment Analysis (Optional)

### 5.1 When to Run Enrichment

Run enrichment analysis when the question mentions:
- "enrichGO", "GO enrichment", "Gene Ontology"
- "KEGG pathway", "pathway enrichment"
- "gseapy", "enrichment analysis"
- "Reactome", "WikiPathways"
- "clusterProfiler" (use gseapy as Python equivalent)

### 5.2 Over-Representation Analysis (ORA) with gseapy

```python
import gseapy as gp

def run_enrichment_ora(gene_list, gene_sets='GO_Biological_Process_2021',
                       background=None, cutoff=0.05):
    """Run over-representation analysis using gseapy.

    Args:
        gene_list: List of gene symbols (DEGs)
        gene_sets: Library name(s) for enrichment
                  Common options:
                    - 'GO_Biological_Process_2021' / 'GO_Biological_Process_2023'
                    - 'GO_Molecular_Function_2021'
                    - 'GO_Cellular_Component_2021'
                    - 'KEGG_2021_Human' / 'KEGG_2019_Mouse'
                    - 'Reactome_2022'
                    - 'WikiPathways_2019_Mouse' / 'WikiPathways_2019_Human'
        background: Background gene list (or int for genome size)
        cutoff: P-value cutoff for enrichment results

    NOTE: gseapy >= 1.1 removed the `organism` parameter from gp.enrich().
    The organism specificity is encoded in the gene_sets library name
    (e.g., 'KEGG_2021_Human' vs 'KEGG_2019_Mouse').

    Returns:
        DataFrame with enrichment results
    """
    enr = gp.enrich(
        gene_list=gene_list,
        gene_sets=gene_sets,
        background=background,
        outdir=None,  # Don't save files
        cutoff=cutoff,
        no_plot=True,
        verbose=False
    )

    return enr.results
```

### 5.3 Gene Set Library Selection

| Question Mentions | gseapy Library | Notes |
|---|---|---|
| "enrichGO" + human | `GO_Biological_Process_2021` or `GO_Biological_Process_2023` | Try 2023 first |
| "KEGG" + human | `KEGG_2021_Human` | |
| "KEGG" + mouse | `KEGG_2019_Mouse` | |
| "Reactome" | `Reactome_2022` | |
| "WikiPathways" + mouse | `WikiPathways_2019_Mouse` | |
| "WikiPathways" + human | `WikiPathways_2019_Human` | |
| "GO Process" | `GO_Biological_Process_2021` | |
| "GO Function" | `GO_Molecular_Function_2021` | |
| "GO Component" | `GO_Cellular_Component_2021` | |

### 5.4 Interpret Enrichment Results

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
            return matches[[' Term', metric]]
        else:
            return None

    # Return top result
    return enr_results.sort_values(metric).head(1)
```

### 5.5 GO Term Simplification

For questions that mention `clusterProfiler::simplify()` with similarity threshold:

```python
def simplify_go_terms(enr_results, similarity_threshold=0.7):
    """Simplify GO terms by removing highly similar terms.

    This is an approximation of R clusterProfiler::simplify().
    Uses semantic similarity based on term overlap of gene sets.

    For exact R clusterProfiler::simplify() behavior, use rpy2 bridge (Phase 7).
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
```

---

## Phase 6: ToolUniverse Gene Annotation (Optional)

### 6.1 When to Use ToolUniverse

Use ToolUniverse tools for:
- Gene ID conversion (Ensembl, Entrez, Symbol)
- Gene function annotation
- Protein-coding vs non-coding classification
- Pathway context for specific genes

### 6.2 Gene ID Conversion

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Gene symbol to Ensembl ID
result = tu.tools.MyGene_query_genes(query="TP53")
# Filter for exact symbol match
# result may contain multiple hits - always verify symbol

# Ensembl gene lookup
result = tu.tools.ensembl_lookup_gene(gene_id="ENSG00000141510", species="homo_sapiens")
```

### 6.3 Gene Classification

```python
def classify_genes(gene_list, tu):
    """Classify genes as protein-coding or non-protein-coding.

    Useful for BixBench questions like:
    "Compare sex-specific DE between protein-coding and non-protein-coding genes"
    """
    classifications = {}
    for gene in gene_list:
        try:
            result = tu.tools.MyGene_query_genes(query=gene)
            if isinstance(result, list) and len(result) > 0:
                gene_type = result[0].get('type_of_gene', 'unknown')
                classifications[gene] = gene_type
        except Exception:
            classifications[gene] = 'unknown'
    return classifications
```

---

## Phase 7: R Bridge for Exact Reproducibility (Advanced)

For questions requiring exact R DESeq2/clusterProfiler output:

```python
# Only use if Python pydeseq2 results don't match expected answers
# and the question explicitly requires R packages

try:
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri
    from rpy2.robjects.packages import importr
    pandas2ri.activate()

    deseq2 = importr('DESeq2')
    # ... R code here
    HAS_RPY2 = True
except ImportError:
    HAS_RPY2 = False
    # Fall back to pydeseq2 (covers 90%+ of cases)
```

**Note**: PyDESeq2 produces results very close to R DESeq2. Minor numerical differences are expected due to different optimization implementations. For BixBench, PyDESeq2 is sufficient for most questions.

---

## Phase 8: miRNA and Proteomics DE Analysis

### 8.1 miRNA Differential Expression

For miRNA data, which is often pre-normalized rather than raw counts, you may not need full DESeq2:

```python
def mirna_de_analysis(expression_df, groups, method='ttest'):
    """Simple differential expression for miRNA or proteomics data.

    For pre-normalized expression data (not raw counts),
    use t-test or Wilcoxon test instead of DESeq2.
    """
    from scipy import stats

    group_labels = expression_df.index.map(groups)
    unique_groups = group_labels.unique()
    assert len(unique_groups) == 2, "Need exactly 2 groups"

    g1 = expression_df[group_labels == unique_groups[0]]
    g2 = expression_df[group_labels == unique_groups[1]]

    results = []
    for gene in expression_df.columns:
        if method == 'ttest':
            stat, pval = stats.ttest_ind(g1[gene].dropna(), g2[gene].dropna())
        elif method == 'wilcoxon':
            stat, pval = stats.mannwhitneyu(g1[gene].dropna(), g2[gene].dropna())

        lfc = np.log2(g2[gene].mean() / g1[gene].mean()) if g1[gene].mean() > 0 else np.nan
        results.append({
            'gene': gene,
            'log2FoldChange': lfc,
            'pvalue': pval,
            'stat': stat
        })

    results_df = pd.DataFrame(results).set_index('gene')

    # Multiple testing correction
    from statsmodels.stats.multitest import multipletests
    mask = ~results_df['pvalue'].isna()
    _, results_df.loc[mask, 'padj_BH'], _, _ = multipletests(
        results_df.loc[mask, 'pvalue'], method='fdr_bh'
    )
    _, results_df.loc[mask, 'padj_BY'], _, _ = multipletests(
        results_df.loc[mask, 'pvalue'], method='fdr_by'
    )
    _, results_df.loc[mask, 'padj_bonf'], _, _ = multipletests(
        results_df.loc[mask, 'pvalue'], method='bonferroni'
    )

    return results_df
```

### 8.2 Proteomics DE

For proteomics data (normalized intensity values), use limma-like approach or simple t-test:

```python
def proteomics_de(expression_df, condition_col, conditions, metadata):
    """Differential expression for proteomics (normalized intensity) data."""
    # Same as miRNA but with log2-transformed intensity values
    # Use t-test for two-group comparison
    pass  # Use mirna_de_analysis with appropriate method
```

---

## Common BixBench Question Patterns

### Pattern 1: Basic DEG Count
**Example**: "How many genes show significant DE (padj < 0.05, |log2FC| > 0.5)?"
```python
degs = filter_degs(results_df, padj_threshold=0.05, lfc_threshold=0.5)
answer = len(degs)
```

### Pattern 2: Specific Gene Value
**Example**: "What is the log2FC of gene X?"
```python
answer = round(get_gene_result(results_df, "GENE_X", "log2FoldChange"), 2)
```

### Pattern 3: Direction-Specific DEGs
**Example**: "How many genes are upregulated?"
```python
up_degs = filter_degs(results_df, padj_threshold=0.05, direction='up')
answer = len(up_degs)
```

### Pattern 4: Multi-Condition Comparison
**Example**: "How many genes are uniquely DE in condition A but not B or C?"
```python
degs_A = set(filter_degs(res_A, padj_threshold=0.05).index)
degs_B = set(filter_degs(res_B, padj_threshold=0.05).index)
degs_C = set(filter_degs(res_C, padj_threshold=0.05).index)
unique_A = degs_A - degs_B - degs_C
answer = len(unique_A)
```

### Pattern 5: Dispersion Count
**Example**: "How many genes have dispersion below 1e-5 prior to shrinkage?"
```python
diag = dispersion_diagnostics(dds, threshold=1e-5)
answer = diag['genewise_below_threshold']
```

### Pattern 6: DEGs + Enrichment
**Example**: "What is the adjusted p-value for pathway X in enrichment of DEGs?"
```python
degs = filter_degs(results_df, padj_threshold=0.05)
gene_list = degs.index.tolist()
enr = run_enrichment_ora(gene_list, gene_sets='KEGG_2021_Human')
answer = extract_enrichment_answer(enr, term_query='ABC transporters')
```

### Pattern 7: Percentage Calculation
**Example**: "What percentage of DE genes in A are also DE in B?"
```python
degs_A = set(filter_degs(res_A, padj_threshold=0.05).index)
degs_B = set(filter_degs(res_B, padj_threshold=0.05).index)
overlap = degs_A & degs_B
percentage = round(len(overlap) / len(degs_A) * 100, 1)
```

### Pattern 8: Wilson Confidence Interval
**Example**: "What is the 95% CI for the proportion of DEGs using Wilson method?"
```python
from statsmodels.stats.proportion import proportion_confint
n_total = len(results_df.dropna(subset=['padj']))
n_sig = len(filter_degs(results_df, padj_threshold=0.05, lfc_threshold=1))
ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
answer = (round(ci_low, 2), round(ci_high, 2))
```

### Pattern 9: Enrichment Gene Count in Pathway
**Example**: "How many DEGs contribute to pathway X enrichment?"
```python
enr = run_enrichment_ora(gene_list, gene_sets='KEGG_2021_Human')
pathway_row = enr[enr['Term'].str.contains('ABC transporters')]
# Genes column contains semicolon-separated gene list
n_genes = len(pathway_row.iloc[0]['Genes'].split(';'))
overlap_info = pathway_row.iloc[0]['Overlap']  # e.g., "11/42"
```

### Pattern 10: Batch Effect Assessment
**Example**: "How does removing batch-affected samples change DEG count?"
```python
# Run with all samples
res_all = extract_results(dds_all, contrast, lfc_shrink=True)
n_all = len(filter_degs(res_all, padj_threshold=0.05, lfc_threshold=1))

# Run without batch-affected samples
res_clean = extract_results(dds_clean, contrast, lfc_shrink=True)
n_clean = len(filter_degs(res_clean, padj_threshold=0.05, lfc_threshold=1))

if n_clean > n_all:
    answer = "Increases the number of differentially expressed genes"
else:
    answer = "Decreases the number of differentially expressed genes"
```

---

## Error Handling

### Common Issues and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "No matching samples" | Count matrix and metadata have different sample names | Check if counts need transposing; try matching after stripping whitespace |
| "Dispersion trend did not converge" | Small sample size or low variation | Use `fit_type='mean'` instead of 'parametric' |
| "Contrast not found" | Wrong factor/level names in contrast | Check `metadata[factor].unique()` for exact level names |
| "All genes filtered out" | Too strict pre-filtering or all counts zero | Lower `min_mu`, check if data is already normalized |
| "Non-integer counts" | Data is normalized (FPKM/TPM) | Round to integers OR use t-test instead of DESeq2 |
| "Single replicate" | Only 1 sample per condition | Cannot run DESeq2; use fold-change only |
| "Memory error" | Too many genes | Pre-filter low-count genes before DESeq2 |
| "NaN in padj" | Independent filtering removed genes | These genes have insufficient evidence; exclude from DEG counts |

### Debugging Checklist

1. [ ] Count matrix has samples as rows, genes as columns
2. [ ] Counts are non-negative integers
3. [ ] Metadata index matches count matrix index exactly
4. [ ] Design formula references valid column names in metadata
5. [ ] Reference level is set correctly (first category in Categorical)
6. [ ] Contrast factor and levels exist in metadata
7. [ ] LFC shrinkage coefficient name matches pydeseq2 format: `factor[T.level]`

---

## Tool Reference

### Core Python Packages

| Package | Purpose | Key Functions |
|---------|---------|---------------|
| `pydeseq2` | DESeq2 implementation in Python | `DeseqDataSet`, `DeseqStats` |
| `gseapy` | Enrichment analysis (ORA, GSEA) | `gp.enrich()`, `gp.gsea()` |
| `pandas` | Data manipulation | DataFrame operations |
| `numpy` | Numerical computing | Array operations |
| `scipy.stats` | Statistical tests | `ttest_ind`, `mannwhitneyu`, `f_oneway` |
| `statsmodels` | Multiple testing correction | `multipletests`, `proportion_confint` |
| `anndata` | Single-cell data format | `read_h5ad()` |

### ToolUniverse Tools (for annotation)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `MyGene_query_genes` | Gene ID lookup | `query` (gene symbol) |
| `ensembl_lookup_gene` | Ensembl gene details | `gene_id`, `species='homo_sapiens'` |
| `UniProt_get_function_by_accession` | Protein function | `accession` (UniProt ID) |
| `EBIProteins_get_features` | Protein features | `accession` |
| `enrichr_gene_enrichment_analysis` | Alternative enrichment | `gene_list`, `libs` |
| `STRING_functional_enrichment` | STRING enrichment | `protein_ids`, `species` |

---

## Completeness Checklist

Every DE analysis MUST include:

### Data Loading (Required)
- [ ] Count matrix loaded and oriented correctly (samples x genes)
- [ ] Metadata loaded and aligned with counts
- [ ] Data validation passed (integer counts, matching samples)
- [ ] Pre-filtering applied if needed (zero genes removed)

### DESeq2 Analysis (Required)
- [ ] Design formula matches question requirements
- [ ] Reference level set correctly
- [ ] DESeq2 ran successfully (deseq2() completed)
- [ ] Correct contrast extracted
- [ ] LFC shrinkage applied if question requires it

### Results (Required)
- [ ] Filtering thresholds match question exactly (padj, lfc, baseMean)
- [ ] Direction filter applied if question specifies up/down
- [ ] Specific answer extracted (count, value, percentage, etc.)
- [ ] Answer formatted to match expected format (decimal places, scientific notation)

### Enrichment (If Requested)
- [ ] Correct gene set library used
- [ ] Background gene set specified if question mentions it
- [ ] GO simplification applied if question mentions similarity threshold
- [ ] Specific pathway/term result extracted

### Quality Checks
- [ ] Number of DEGs is reasonable for the comparison
- [ ] P-values are between 0 and 1
- [ ] Log2FC values are finite
- [ ] No silent failures (empty results with no warning)

---

## Output Formatting

### Numeric Answers

| Format Requested | Python Code |
|---|---|
| "rounded to 2 decimal points" | `round(value, 2)` |
| "rounded to 4 decimal points" | `round(value, 4)` |
| "in scientific notation" | `f"{value:.2E}"` |
| "as a percentage" | `f"{value * 100:.1f}%"` or `f"{round(value * 100, 1)}%"` |
| "as a ratio X:Y" | `f"{x}:{y}"` |
| "as a fraction" | `f"{numerator}/{denominator}"` |

### Range Answers

For `range_verifier` evaluation mode, the answer should fall within the specified range:
```python
# Expected: (700, 1000)
# Your answer: 842  -> PASS (within range)
```

---

## Example End-to-End Workflow

```python
import pandas as pd
import numpy as np
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# 1. Load data
counts = pd.read_csv("counts.csv", index_col=0)
metadata = pd.read_csv("metadata.csv", index_col=0)

# 2. Orient matrix (samples as rows)
if counts.shape[0] > counts.shape[1] * 5:
    counts = counts.T

# 3. Align samples
common = sorted(set(counts.index) & set(metadata.index))
counts = counts.loc[common]
metadata = metadata.loc[common]

# 4. Ensure integer counts
counts = counts.round().astype(int)

# 5. Set reference level
metadata['condition'] = pd.Categorical(
    metadata['condition'],
    categories=['control', 'treatment']  # control is reference
)

# 6. Run DESeq2
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()

# 7. Extract results
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()

# 8. Apply LFC shrinkage (if needed)
stat_res.lfc_shrink(coeff='condition[T.treatment]')

# 9. Filter DEGs
results = stat_res.results_df
sig_genes = results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)]
print(f"Significant DEGs: {len(sig_genes)}")

# 10. Run enrichment (if needed)
import gseapy as gp
enr = gp.enrich(
    gene_list=sig_genes.index.tolist(),
    gene_sets='GO_Biological_Process_2021',
    outdir=None,
    no_plot=True,
    verbose=False
)
print(enr.results.head())
```
