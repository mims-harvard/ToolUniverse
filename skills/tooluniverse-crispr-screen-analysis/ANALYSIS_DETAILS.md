# CRISPR Screen Analysis - Detailed Code & Procedures

## Phase 1: Data Import & sgRNA Count Processing

### Load sgRNA Count Matrix

```python
import pandas as pd
import numpy as np

def load_sgrna_counts(counts_file):
    """
    Load sgRNA count matrix from MAGeCK format or generic TSV.

    Expected format:
    sgRNA | Gene | Sample1 | Sample2 | Sample3 | ...
    """
    counts = pd.read_csv(counts_file, sep='\t')
    required_cols = ['sgRNA', 'Gene']
    if not all(col in counts.columns for col in required_cols):
        raise ValueError(f"Missing required columns: {required_cols}")

    sample_cols = [col for col in counts.columns if col not in ['sgRNA', 'Gene']]
    count_matrix = counts[sample_cols].copy()
    count_matrix.index = counts['sgRNA']
    sgrna_to_gene = dict(zip(counts['sgRNA'], counts['Gene']))

    metadata = {
        'n_sgrnas': len(counts), 'n_genes': counts['Gene'].nunique(),
        'n_samples': len(sample_cols), 'sample_names': sample_cols,
        'sgrna_to_gene': sgrna_to_gene
    }
    return count_matrix, metadata
```

### Create Experimental Design Table

```python
def create_design_matrix(sample_names, conditions, timepoints=None):
    """Create experimental design linking samples to conditions."""
    design = pd.DataFrame({'Sample': sample_names, 'Condition': conditions})
    if timepoints is not None:
        design['Timepoint'] = timepoints
    design['Replicate'] = design.groupby('Condition').cumcount() + 1
    return design
```

---

## Phase 2: Quality Control & Filtering

### Assess sgRNA Distribution

```python
def qc_sgrna_distribution(count_matrix, min_reads=30, min_samples=2):
    """
    Quality control for sgRNA distribution.
    - Remove sgRNAs with low read counts
    - Check for outlier samples
    - Assess library representation
    """
    results = {}
    library_sizes = count_matrix.sum(axis=0)
    results['library_sizes'] = library_sizes
    results['median_library_size'] = library_sizes.median()

    zero_counts = (count_matrix == 0).sum(axis=1)
    results['zero_counts'] = zero_counts
    results['sgrnas_with_zeros'] = (zero_counts > 0).sum()

    low_count_mask = (count_matrix < min_reads).sum(axis=1) > (len(count_matrix.columns) - min_samples)
    results['low_count_sgrnas'] = low_count_mask.sum()

    def gini_coefficient(counts):
        sorted_counts = np.sort(counts)
        n = len(counts)
        cumsum = np.cumsum(sorted_counts)
        return (2 * np.sum((np.arange(1, n+1)) * sorted_counts)) / (n * cumsum[-1]) - (n + 1) / n

    results['gini_per_sample'] = {col: gini_coefficient(count_matrix[col].values)
                                   for col in count_matrix.columns}
    results['filter_recommendation'] = {
        'min_reads': min_reads, 'min_samples_above_threshold': min_samples,
        'sgrnas_to_remove': low_count_mask.sum()
    }
    return results
```

### Filter Low-Count sgRNAs

```python
def filter_low_count_sgrnas(count_matrix, sgrna_to_gene, min_reads=30, min_samples=2):
    """Remove sgRNAs with insufficient read counts."""
    keep_mask = (count_matrix >= min_reads).sum(axis=1) >= min_samples
    filtered_counts = count_matrix[keep_mask].copy()
    filtered_mapping = {k: v for k, v in sgrna_to_gene.items() if k in filtered_counts.index}
    print(f"Filtered: {(~keep_mask).sum()} sgRNAs removed, {keep_mask.sum()} retained")
    return filtered_counts, filtered_mapping
```

---

## Phase 3: Normalization

### Library Size Normalization

```python
def normalize_counts(count_matrix, method='median'):
    """
    Normalize sgRNA counts to account for library size differences.
    Methods: 'median' (DESeq2-like), 'total' (CPM-like)
    """
    if method == 'median':
        pseudo_ref = np.exp(np.log(count_matrix + 1).mean(axis=1)) - 1
        size_factors = {}
        for col in count_matrix.columns:
            ratios = count_matrix[col] / pseudo_ref
            ratios = ratios[ratios > 0]
            size_factors[col] = ratios.median()
        normalized = count_matrix.div(pd.Series(size_factors), axis=1)
    elif method == 'total':
        size_factors = count_matrix.sum(axis=0) / 1e6
        normalized = count_matrix.div(size_factors, axis=1)
    else:
        raise ValueError(f"Unknown normalization method: {method}")
    return normalized, size_factors
```

### Log-Fold Change Calculation

```python
def calculate_lfc(norm_counts, design, control_condition='baseline', treatment_condition='treatment'):
    """Calculate log2 fold changes between treatment and control."""
    control_samples = design[design['Condition'] == control_condition]['Sample'].tolist()
    treatment_samples = design[design['Condition'] == treatment_condition]['Sample'].tolist()
    control_mean = norm_counts[control_samples].mean(axis=1)
    treatment_mean = norm_counts[treatment_samples].mean(axis=1)
    lfc = np.log2((treatment_mean + 1) / (control_mean + 1))
    return lfc, control_mean, treatment_mean
```

---

## Phase 4: Gene-Level Scoring (MAGeCK-like)

### Aggregate sgRNA Scores to Gene Level

```python
def mageck_gene_scoring(lfc, sgrna_to_gene, method='rra'):
    """
    Gene-level essentiality scoring using MAGeCK-like approach.
    Methods: 'rra' (Robust Rank Aggregation), 'mean' (Simple mean LFC)
    """
    gene_lfc = {}
    for sgrna, gene in sgrna_to_gene.items():
        if sgrna in lfc.index:
            if gene not in gene_lfc:
                gene_lfc[gene] = []
            gene_lfc[gene].append(lfc[sgrna])

    if method == 'rra':
        ranked_sgrnas = lfc.sort_values()
        ranks = {sgrna: rank for rank, sgrna in enumerate(ranked_sgrnas.index, 1)}
        gene_scores = {}
        for gene, sgrna_list in gene_lfc.items():
            gene_ranks = [ranks[sgrna] for sgrna in sgrna_list if sgrna in ranks]
            if len(gene_ranks) > 0:
                gene_scores[gene] = {
                    'score': np.mean(gene_ranks),
                    'n_sgrnas': len(gene_ranks),
                    'mean_lfc': np.mean([lfc[sg] for sg in sgrna_list if sg in lfc.index])
                }
        gene_df = pd.DataFrame(gene_scores).T
        gene_df['rank'] = gene_df['score'].rank()
    elif method == 'mean':
        gene_df = pd.DataFrame({
            gene: {'mean_lfc': np.mean(lfcs), 'n_sgrnas': len(lfcs), 'score': np.mean(lfcs)}
            for gene, lfcs in gene_lfc.items()
        }).T

    gene_df = gene_df.sort_values('mean_lfc')
    return gene_df
```

### Bayes Factor Scoring (BAGEL-like)

```python
def bagel_bayes_factor(lfc, sgrna_to_gene, essential_genes=None, nonessential_genes=None):
    """
    BAGEL-like Bayes Factor calculation for gene essentiality.
    Uses reference sets of known essential and non-essential genes.
    """
    if essential_genes is None:
        essential_genes = ['RPL5', 'RPS6', 'POLR2A', 'PSMC2', 'PSMD14']
    if nonessential_genes is None:
        nonessential_genes = ['AAVS1', 'ROSA26', 'HPRT1']

    essential_lfc = [lfc[sg] for sg, g in sgrna_to_gene.items()
                     if g in essential_genes and sg in lfc.index]
    nonessential_lfc = [lfc[sg] for sg, g in sgrna_to_gene.items()
                        if g in nonessential_genes and sg in lfc.index]

    if len(essential_lfc) < 3 or len(nonessential_lfc) < 3:
        print("Warning: Insufficient reference genes for BAGEL scoring")
        return None

    essential_mean, essential_std = np.mean(essential_lfc), np.std(essential_lfc)
    nonessential_mean, nonessential_std = np.mean(nonessential_lfc), np.std(nonessential_lfc)

    gene_lfc_map = {}
    for sgrna, gene in sgrna_to_gene.items():
        if sgrna in lfc.index:
            if gene not in gene_lfc_map:
                gene_lfc_map[gene] = []
            gene_lfc_map[gene].append(lfc[sgrna])

    gene_bf = {}
    for gene, sgrna_lfcs in gene_lfc_map.items():
        mean_lfc = np.mean(sgrna_lfcs)
        from scipy.stats import norm
        l_essential = norm.pdf(mean_lfc, essential_mean, essential_std)
        l_nonessential = norm.pdf(mean_lfc, nonessential_mean, nonessential_std)
        bf = l_essential / (l_nonessential + 1e-10)
        gene_bf[gene] = {'bayes_factor': bf, 'mean_lfc': mean_lfc, 'n_sgrnas': len(sgrna_lfcs)}

    bf_df = pd.DataFrame(gene_bf).T
    bf_df = bf_df.sort_values('bayes_factor', ascending=False)
    return bf_df
```

---

## Phase 5: Synthetic Lethality Detection

### Identify Context-Specific Essential Genes

```python
def detect_synthetic_lethality(gene_scores_wildtype, gene_scores_mutant,
                                lfc_threshold=-1.0, rank_diff_threshold=100):
    """
    Identify genes selectively essential in mutant context (synthetic lethal).
    Compare essentiality scores between wildtype and mutant cell lines.
    """
    comparison = pd.merge(
        gene_scores_wildtype[['mean_lfc', 'rank']],
        gene_scores_mutant[['mean_lfc', 'rank']],
        left_index=True, right_index=True, suffixes=('_wt', '_mut')
    )
    comparison['delta_lfc'] = comparison['mean_lfc_mut'] - comparison['mean_lfc_wt']
    comparison['delta_rank'] = comparison['rank_wt'] - comparison['rank_mut']

    sl_candidates = comparison[
        (comparison['mean_lfc_mut'] < lfc_threshold) &
        (comparison['mean_lfc_wt'] > -0.5) &
        (comparison['delta_rank'] > rank_diff_threshold)
    ].copy()
    sl_candidates = sl_candidates.sort_values('delta_lfc')
    return sl_candidates
```

### Query DepMap for Known Dependencies

```python
def query_depmap_dependencies(gene_symbol):
    """Query literature for gene dependency information."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    result = tu.run_one_function({
        "name": "PubMed_search_articles",
        "arguments": {
            "query": f'("{gene_symbol}"[Gene]) AND ("CRISPR screen" OR "gene essentiality" OR "DepMap")',
            "max_results": 20
        }
    })
    if 'data' in result and 'papers' in result['data']:
        return result['data']['papers']
    return []
```

---

## Phase 6: Pathway Enrichment Analysis

### Enrichment of Essential Genes

```python
def enrich_essential_genes(gene_scores, top_n=100, databases=['KEGG_2021_Human', 'GO_Biological_Process_2021']):
    """Perform pathway enrichment on top essential genes."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    top_genes = gene_scores.head(top_n).index.tolist()
    result = tu.run_one_function({
        "name": "enrichr_gene_enrichment_analysis",
        "arguments": {"gene_list": top_genes, "description": "CRISPR_screen_essential_genes"}
    })
    if 'data' not in result or 'userListId' not in result['data']:
        return None

    user_list_id = result['data']['userListId']
    all_results = {}
    for db in databases:
        enrich_result = tu.run_one_function({
            "name": "Enrichr_get_results",
            "arguments": {"userListId": user_list_id, "backgroundType": db}
        })
        if 'data' in enrich_result and db in enrich_result['data']:
            all_results[db] = pd.DataFrame(enrich_result['data'][db])
    return all_results
```

---

## Phase 7: Drug Target Prioritization

### Integrate with Expression & Mutation Data

```python
def prioritize_drug_targets(gene_scores, expression_data=None, mutation_data=None):
    """
    Prioritize CRISPR hits as drug targets based on:
    1. Essentiality score (from CRISPR screen)
    2. Expression level in disease vs normal
    3. Mutation frequency in tumors
    4. Druggability (query DGIdb)
    """
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    candidates = gene_scores.head(50).copy()
    if expression_data is not None:
        candidates = candidates.merge(expression_data, left_index=True, right_index=True, how='left')
    if mutation_data is not None:
        candidates = candidates.merge(mutation_data, left_index=True, right_index=True, how='left')

    druggability_scores = {}
    for gene in candidates.index[:20]:
        result = tu.run_one_function({
            "name": "DGIdb_get_drug_gene_interactions", "arguments": {"genes": [gene]}
        })
        if 'data' in result and 'matchedTerms' in result['data']:
            matches = result['data']['matchedTerms']
            n_drugs = len(matches[0].get('interactions', [])) if len(matches) > 0 else 0
            druggability_scores[gene] = n_drugs
        else:
            druggability_scores[gene] = 0

    candidates['n_drugs'] = pd.Series(druggability_scores)
    candidates['essentiality_norm'] = (candidates['mean_lfc'].min() - candidates['mean_lfc']) / \
                                       (candidates['mean_lfc'].min() - candidates['mean_lfc'].max())
    if 'log2fc' in candidates.columns:
        candidates['expression_norm'] = (candidates['log2fc'] - candidates['log2fc'].min()) / \
                                        (candidates['log2fc'].max() - candidates['log2fc'].min())
    else:
        candidates['expression_norm'] = 0
    candidates['druggability_norm'] = candidates['n_drugs'] / (candidates['n_drugs'].max() + 1)
    candidates['priority_score'] = (
        0.5 * candidates['essentiality_norm'] +
        0.3 * candidates['expression_norm'] +
        0.2 * candidates['druggability_norm']
    )
    candidates = candidates.sort_values('priority_score', ascending=False)
    return candidates
```

### Query Existing Drugs for Top Targets

```python
def find_drugs_for_targets(target_genes, max_per_gene=5):
    """Find existing drugs targeting top candidate genes."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    drug_results = {}
    for gene in target_genes[:10]:
        result = tu.run_one_function({
            "name": "DGIdb_get_drug_gene_interactions", "arguments": {"genes": [gene]}
        })
        if 'data' in result and 'matchedTerms' in result['data']:
            matches = result['data']['matchedTerms']
            if len(matches) > 0:
                interactions = matches[0].get('interactions', [])
                drugs = []
                for interaction in interactions[:max_per_gene]:
                    drugs.append({
                        'drug_name': interaction.get('drugName', 'Unknown'),
                        'interaction_type': interaction.get('interactionTypes', ['Unknown'])[0],
                        'source': interaction.get('source', 'Unknown')
                    })
                drug_results[gene] = drugs
    return drug_results
```

---

## Phase 8: Report Generation

### Comprehensive CRISPR Screen Report

```python
def generate_crispr_report(gene_scores, enrichment_results, drug_targets,
                           output_file="crispr_screen_report.md"):
    """Generate comprehensive CRISPR screen analysis report."""
    with open(output_file, 'w') as f:
        f.write("# CRISPR Screen Analysis Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total genes analyzed**: {len(gene_scores)}\n")
        f.write(f"- **Essential genes** (LFC < -1): {(gene_scores['mean_lfc'] < -1).sum()}\n")
        f.write(f"- **Non-essential genes** (LFC > -0.5): {(gene_scores['mean_lfc'] > -0.5).sum()}\n\n")

        f.write("## Top 20 Essential Genes\n\n")
        f.write("| Rank | Gene | Mean LFC | sgRNAs | Score |\n")
        f.write("|------|------|----------|--------|-------|\n")
        for idx, (gene, row) in enumerate(gene_scores.head(20).iterrows(), 1):
            f.write(f"| {idx} | {gene} | {row['mean_lfc']:.3f} | {int(row['n_sgrnas'])} | {row['score']:.2f} |\n")
        f.write("\n")

        if enrichment_results:
            f.write("## Pathway Enrichment\n\n")
            for db, results in enrichment_results.items():
                f.write(f"### {db}\n\n")
                f.write("| Term | P-value | Adjusted P-value | Genes |\n")
                f.write("|------|---------|------------------|-------|\n")
                for _, row in results.head(10).iterrows():
                    f.write(f"| {row.get('Term', 'Unknown')} | {row.get('P-value', 1.0):.2e} | {row.get('Adjusted P-value', 1.0):.2e} | {str(row.get('Genes', ''))[:50]}... |\n")
                f.write("\n")

        if drug_targets is not None:
            f.write("## Top Drug Target Candidates\n\n")
            f.write("| Rank | Gene | Essentiality | Expression FC | Druggable | Priority Score |\n")
            f.write("|------|------|--------------|---------------|-----------|----------------|\n")
            for idx, (gene, row) in enumerate(drug_targets.head(10).iterrows(), 1):
                f.write(f"| {idx} | {gene} | {row['mean_lfc']:.3f} | {row.get('log2fc', 0):.2f} | {int(row.get('n_drugs', 0))} | {row['priority_score']:.3f} |\n")
            f.write("\n")

        f.write("## Methods\n\n")
        f.write("**sgRNA Processing**: MAGeCK-like robust rank aggregation\n\n")
        f.write("**Normalization**: Median ratio normalization\n\n")
        f.write("**Scoring**: Gene-level LFC aggregation with rank-based scoring\n\n")
        f.write("**Enrichment**: Enrichr (KEGG, GO)\n\n")
        f.write("**Druggability**: DGIdb v4.0\n\n")
    return output_file
```
