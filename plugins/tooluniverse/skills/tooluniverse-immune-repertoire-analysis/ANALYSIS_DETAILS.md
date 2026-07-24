# Immune Repertoire Analysis - Detailed Code & Procedures

## Phase 1: Data Import & Clonotype Definition

### Load AIRR-seq Data

```python
import pandas as pd
import numpy as np
from collections import Counter

def load_airr_data(file_path, format='mixcr'):
    """
    Load immune repertoire data from common formats.

    Supported formats:
    - 'mixcr': MiXCR output
    - 'immunoseq': Adaptive Biotechnologies ImmunoSEQ
    - 'airr': AIRR Community Standard
    - '10x': 10x Genomics VDJ output
    """
    if format == 'mixcr':
        df = pd.read_csv(file_path, sep='\t')
        clonotype_df = pd.DataFrame({
            'cloneId': df.get('cloneId', range(len(df))),
            'count': df.get('cloneCount', df.get('count', 0)),
            'frequency': df.get('cloneFraction', df.get('frequency', 0)),
            'cdr3aa': df.get('aaSeqCDR3', df.get('cdr3', '')),
            'cdr3nt': df.get('nSeqCDR3', ''),
            'v_gene': df.get('allVHitsWithScore', df.get('v_call', '')),
            'j_gene': df.get('allJHitsWithScore', df.get('j_call', '')),
            'chain': df.get('chain', 'TRB')
        })

    elif format == '10x':
        df = pd.read_csv(file_path)
        clonotype_df = df.groupby('barcode').agg({
            'cdr3': lambda x: ','.join(x.dropna()),
            'cdr3_nt': lambda x: ','.join(x.dropna()),
            'v_gene': lambda x: ','.join(x.dropna()),
            'j_gene': lambda x: ','.join(x.dropna()),
            'chain': lambda x: ','.join(x.dropna()),
            'umis': 'sum'
        }).reset_index()
        clonotype_df = clonotype_df.rename(columns={
            'barcode': 'cloneId', 'cdr3': 'cdr3aa',
            'cdr3_nt': 'cdr3nt', 'umis': 'count'
        })
        clonotype_df['frequency'] = clonotype_df['count'] / clonotype_df['count'].sum()

    elif format == 'airr':
        df = pd.read_csv(file_path, sep='\t')
        clonotype_df = pd.DataFrame({
            'cloneId': df.get('clone_id', range(len(df))),
            'count': df.get('duplicate_count', 1),
            'frequency': df.get('clone_frequency', df.get('duplicate_count', 1) / df.get('duplicate_count', 1).sum()),
            'cdr3aa': df.get('junction_aa', ''),
            'cdr3nt': df.get('junction', ''),
            'v_gene': df.get('v_call', ''),
            'j_gene': df.get('j_call', ''),
            'chain': df.get('locus', 'TRB')
        })

    clonotype_df['cdr3_length'] = clonotype_df['cdr3aa'].str.len()
    return clonotype_df
```

### Define Clonotypes

```python
def define_clonotypes(df, method='cdr3aa'):
    """
    Define clonotypes based on various criteria.

    Methods:
    - 'cdr3aa': Amino acid CDR3 sequence only
    - 'cdr3nt': Nucleotide CDR3 sequence
    - 'vj_cdr3': V gene + J gene + CDR3aa (most common)
    """
    if method == 'cdr3aa':
        df['clonotype'] = df['cdr3aa']
    elif method == 'cdr3nt':
        df['clonotype'] = df['cdr3nt']
    elif method == 'vj_cdr3':
        df['v_family'] = df['v_gene'].str.extract(r'(TRB[VDJ]\d+)', expand=False)
        df['j_family'] = df['j_gene'].str.extract(r'(TRB[VDJ]\d+)', expand=False)
        df['clonotype'] = df['v_family'] + '_' + df['j_family'] + '_' + df['cdr3aa']

    clonotype_summary = df.groupby('clonotype').agg({
        'count': 'sum', 'frequency': 'sum'
    }).reset_index()
    clonotype_summary = clonotype_summary.sort_values('count', ascending=False)
    clonotype_summary['rank'] = range(1, len(clonotype_summary) + 1)
    return clonotype_summary
```

---

## Phase 2: Diversity & Clonality Analysis

### Calculate Diversity Metrics

```python
def calculate_diversity(clonotype_counts):
    """
    Calculate diversity metrics for immune repertoire.

    Metrics:
    - Shannon entropy: Overall diversity
    - Simpson index: Probability two random clones are same
    - Inverse Simpson: Effective number of clonotypes
    - Gini coefficient: Inequality in clonotype distribution
    """
    from scipy.stats import entropy

    if isinstance(clonotype_counts, pd.Series):
        counts = clonotype_counts.values
    else:
        counts = clonotype_counts

    freqs = counts / counts.sum()

    shannon = entropy(freqs, base=2)
    simpson = np.sum(freqs ** 2)
    inv_simpson = 1 / simpson if simpson > 0 else 0

    sorted_freqs = np.sort(freqs)
    n = len(freqs)
    cumsum = np.cumsum(sorted_freqs)
    gini = (2 * np.sum((np.arange(1, n+1)) * sorted_freqs)) / (n * cumsum[-1]) - (n + 1) / n

    richness = len(counts)
    max_entropy = np.log2(richness)
    evenness = shannon / max_entropy if max_entropy > 0 else 0
    clonality = 1 - evenness

    return {
        'richness': richness, 'shannon_entropy': shannon,
        'simpson_index': simpson, 'inverse_simpson': inv_simpson,
        'gini_coefficient': gini, 'evenness': evenness, 'clonality': clonality
    }
```

### Rarefaction Analysis

```python
def rarefaction_curve(df, n_samples=100, n_boots=10):
    """
    Generate rarefaction curve to assess sampling depth.
    Shows how clonotype richness increases with sequencing depth.
    """
    total_reads = df['count'].sum()
    sample_sizes = np.linspace(1000, total_reads, n_samples)

    richness_curves = []
    for _ in range(n_boots):
        richness_at_depth = []
        for sample_size in sample_sizes:
            sampled = np.random.choice(
                df.index, size=int(sample_size),
                p=df['frequency'].values, replace=True
            )
            unique_clonotypes = len(set(sampled))
            richness_at_depth.append(unique_clonotypes)
        richness_curves.append(richness_at_depth)

    mean_richness = np.mean(richness_curves, axis=0)
    std_richness = np.std(richness_curves, axis=0)
    return sample_sizes, mean_richness, std_richness
```

---

## Phase 3: V(D)J Gene Usage Analysis

### Analyze V and J Gene Usage

```python
def analyze_vdj_usage(df):
    """Analyze V(D)J gene usage patterns."""
    df['v_family'] = df['v_gene'].str.extract(r'(TRB[VDJ]\d+)', expand=False)
    df['j_family'] = df['j_gene'].str.extract(r'(TRB[VDJ]\d+)', expand=False)

    v_usage = df.groupby('v_family')['count'].sum().sort_values(ascending=False)
    v_usage_freq = v_usage / v_usage.sum()

    j_usage = df.groupby('j_family')['count'].sum().sort_values(ascending=False)
    j_usage_freq = j_usage / j_usage.sum()

    vj_pairs = df.groupby(['v_family', 'j_family'])['count'].sum().reset_index()
    vj_pairs['frequency'] = vj_pairs['count'] / vj_pairs['count'].sum()
    vj_pairs = vj_pairs.sort_values('count', ascending=False)

    return {'v_usage': v_usage_freq, 'j_usage': j_usage_freq, 'vj_pairs': vj_pairs}
```

### Statistical Testing for Biased Usage

```python
def test_vdj_bias(observed_usage, expected_frequencies=None):
    """Test whether V(D)J gene usage deviates from expected (uniform or reference)."""
    from scipy.stats import chisquare

    observed = observed_usage.values
    if expected_frequencies is None:
        expected = np.ones(len(observed)) / len(observed) * observed.sum()
    else:
        expected = expected_frequencies * observed.sum()

    chi2, pvalue = chisquare(observed, f_exp=expected)
    return {'chi2_statistic': chi2, 'p_value': pvalue, 'significant': pvalue < 0.05}
```

---

## Phase 4: CDR3 Sequence Analysis

### CDR3 Length Distribution

```python
def analyze_cdr3_length(df):
    """
    Analyze CDR3 length distribution.
    Typical TCR CDR3 length: 12-18 amino acids
    Typical BCR CDR3 length: 10-20 amino acids
    """
    length_dist = df.groupby('cdr3_length')['count'].sum().sort_index()
    length_freq = length_dist / length_dist.sum()
    mean_length = (df['cdr3_length'] * df['count']).sum() / df['count'].sum()
    median_length = df['cdr3_length'].median()
    return {
        'length_distribution': length_freq,
        'mean_length': mean_length,
        'median_length': median_length
    }
```

### Amino Acid Composition

```python
def analyze_cdr3_composition(cdr3_sequences, weights=None):
    """Analyze amino acid composition in CDR3 regions."""
    from collections import Counter

    if weights is None:
        weights = np.ones(len(cdr3_sequences))

    aa_counts = Counter()
    total_aa = 0
    for seq, weight in zip(cdr3_sequences, weights):
        for aa in seq:
            aa_counts[aa] += weight
            total_aa += weight

    aa_freq = {aa: count / total_aa for aa, count in aa_counts.items()}
    aa_freq_df = pd.DataFrame.from_dict(aa_freq, orient='index', columns=['frequency'])
    aa_freq_df = aa_freq_df.sort_values('frequency', ascending=False)
    return aa_freq_df
```

---

## Phase 5: Clonal Expansion Detection

### Identify Expanded Clonotypes

```python
def detect_expanded_clones(clonotypes, threshold_percentile=95):
    """
    Identify clonally expanded T/B cell populations.
    Expanded clonotypes = clones above frequency threshold.
    """
    threshold = np.percentile(clonotypes['frequency'], threshold_percentile)
    expanded = clonotypes[clonotypes['frequency'] >= threshold].copy()
    expanded = expanded.sort_values('frequency', ascending=False)
    total_expanded_freq = expanded['frequency'].sum()
    n_expanded = len(expanded)
    return {
        'expanded_clonotypes': expanded,
        'n_expanded': n_expanded,
        'expanded_frequency': total_expanded_freq,
        'threshold': threshold
    }
```

### Longitudinal Clonotype Tracking

```python
def track_clonotypes_longitudinal(timepoint_dataframes, clonotype_col='clonotype'):
    """
    Track clonotype dynamics across multiple timepoints.
    Input: List of DataFrames, each representing one timepoint
    """
    all_timepoints = []
    for i, df in enumerate(timepoint_dataframes):
        df_copy = df.copy()
        df_copy['timepoint'] = i
        all_timepoints.append(df_copy[[clonotype_col, 'frequency', 'timepoint']])

    merged = pd.concat(all_timepoints, ignore_index=True)
    tracking = merged.pivot(index=clonotype_col, columns='timepoint', values='frequency')
    tracking = tracking.fillna(0)
    tracking['persistence'] = (tracking > 0).sum(axis=1)
    tracking['mean_frequency'] = tracking.iloc[:, :-1].mean(axis=1)
    tracking['max_frequency'] = tracking.iloc[:, :-1].max(axis=1)
    tracking = tracking.sort_values(['persistence', 'max_frequency'], ascending=False)
    return tracking
```

---

## Phase 6: Convergence & Public Clonotypes

### Detect Convergent Recombination

```python
def detect_convergent_recombination(df):
    """
    Identify cases where different nucleotide sequences encode same CDR3 amino acid.
    Convergent recombination = same CDR3aa from different CDR3nt sequences.
    """
    convergence = df.groupby('cdr3aa').agg({
        'cdr3nt': lambda x: len(set(x)),
        'count': 'sum', 'frequency': 'sum'
    }).reset_index()
    convergent = convergence[convergence['cdr3nt'] > 1].copy()
    convergent = convergent.rename(columns={'cdr3nt': 'n_nucleotide_variants'})
    convergent = convergent.sort_values('n_nucleotide_variants', ascending=False)
    return convergent
```

### Identify Public (Shared) Clonotypes

```python
def identify_public_clonotypes(sample_dataframes, min_samples=2):
    """
    Identify public (shared) clonotypes present in multiple samples.
    Input: List of DataFrames, each representing one sample
    """
    all_samples = []
    for i, df in enumerate(sample_dataframes):
        df_copy = df[['clonotype', 'frequency']].copy()
        df_copy['sample_id'] = f'Sample_{i+1}'
        all_samples.append(df_copy)

    merged = pd.concat(all_samples, ignore_index=True)
    public_counts = merged.groupby('clonotype').agg({
        'sample_id': lambda x: len(set(x)), 'frequency': 'mean'
    }).reset_index()
    public_counts = public_counts.rename(columns={'sample_id': 'n_samples'})
    public = public_counts[public_counts['n_samples'] >= min_samples].copy()
    public = public.sort_values(['n_samples', 'frequency'], ascending=False)
    return public
```

---

## Phase 7: Epitope Prediction & Specificity

### Query IEDB for Known Epitopes

```python
def query_epitope_database(cdr3_sequences, organism='human', top_n=10):
    """Query IEDB for known T-cell epitopes matching CDR3 sequences."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    epitope_matches = {}
    for cdr3 in cdr3_sequences[:top_n]:
        result = tu.run_one_function({
            "name": "IEDB_search_tcells",
            "arguments": {"receptor": cdr3, "organism": organism}
        })
        if 'data' in result and 'epitopes' in result['data']:
            epitopes = result['data']['epitopes']
            if len(epitopes) > 0:
                epitope_matches[cdr3] = epitopes
    return epitope_matches
```

### Predict Epitope Specificity with VDJdb

```python
def predict_specificity_vdjdb(cdr3_sequences, chain='TRB'):
    """
    Predict antigen specificity using VDJdb (TCR database).
    VDJdb contains TCR sequences with known epitope specificity.
    """
    # VDJdb: https://vdjdb.cdr3.net/search
    # Alternative: Use PubMed literature search
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    specificity_results = {}
    for cdr3 in cdr3_sequences[:5]:
        result = tu.run_one_function({
            "name": "PubMed_search_articles",
            "arguments": {
                "query": f'"{cdr3}" AND (epitope OR antigen OR specificity)',
                "max_results": 10
            }
        })
        if 'data' in result and 'papers' in result['data']:
            papers = result['data']['papers']
            if len(papers) > 0:
                specificity_results[cdr3] = papers
    return specificity_results
```

---

## Phase 8: Integration with Single-Cell Data

### Link Clonotypes to Cell Phenotypes

```python
def integrate_with_single_cell(vdj_df, gex_adata, barcode_col='barcode'):
    """
    Integrate TCR/BCR clonotypes with single-cell gene expression.
    Requires: vdj_df (DataFrame), gex_adata (AnnData object)
    """
    import scanpy as sc
    clonotype_map = dict(zip(vdj_df[barcode_col], vdj_df['clonotype']))
    gex_adata.obs['clonotype'] = gex_adata.obs.index.map(clonotype_map)
    gex_adata.obs['has_clonotype'] = ~gex_adata.obs['clonotype'].isna()
    clonotype_counts = gex_adata.obs['clonotype'].value_counts()
    expanded_clonotypes = clonotype_counts[clonotype_counts > 5].index.tolist()
    gex_adata.obs['is_expanded'] = gex_adata.obs['clonotype'].isin(expanded_clonotypes)
    return gex_adata
```

### Clonotype-Phenotype Association

```python
def analyze_clonotype_phenotype(adata, clonotype_col='clonotype', cluster_col='leiden'):
    """Analyze association between clonotypes and cell phenotypes/clusters."""
    import scanpy as sc
    cells_with_tcr = adata[~adata.obs[clonotype_col].isna()].copy()
    clonotype_cluster = pd.crosstab(
        cells_with_tcr.obs[clonotype_col],
        cells_with_tcr.obs[cluster_col], normalize='index'
    )
    cluster_specific = clonotype_cluster[clonotype_cluster.max(axis=1) > 0.8]
    top_per_cluster = {}
    for cluster in clonotype_cluster.columns:
        top_clonotypes = clonotype_cluster[cluster].sort_values(ascending=False).head(5)
        top_per_cluster[cluster] = top_clonotypes.index.tolist()
    return {
        'clonotype_cluster_matrix': clonotype_cluster,
        'cluster_specific_clonotypes': cluster_specific,
        'top_clonotypes_per_cluster': top_per_cluster
    }
```
