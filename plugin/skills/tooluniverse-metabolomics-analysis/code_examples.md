# Metabolomics Analysis Code Examples

## Phase 1: Data Import & Metabolite Identification

### Data Loading

```python
def load_metabolomics_data(file_path, file_type='peak_table'):
    """
    Load metabolomics data.
    file_type: 'peak_table' (CSV/TSV), 'mzml' (raw LC-MS), 'nmr'
    """
    import pandas as pd

    if file_type == 'peak_table':
        data = pd.read_csv(file_path, index_col=0)
        # Rows = samples, Columns = metabolites
        return data
    elif file_type == 'mzml':
        # Process raw MS data (requires pymzml)
        pass
```

### Metabolite Identification

```python
def identify_metabolites(feature_data, mass_list, rt_list=None):
    """Match features to metabolite databases (HMDB, KEGG, PubChem)."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    identified_metabolites = []
    for i, mass in enumerate(mass_list):
        hmdb_result = tu.run_one_function({
            "name": "hmdb_search_by_mass",
            "arguments": {"mass": mass, "mass_tolerance": 0.005}
        })
        if hmdb_result and 'data' in hmdb_result:
            matches = hmdb_result['data']
            identified_metabolites.append({
                'feature_id': i,
                'metabolite_name': matches[0]['name'],
                'hmdb_id': matches[0]['accession'],
                'formula': matches[0]['chemical_formula'],
                'confidence': calculate_confidence(matches[0])
            })
    return identified_metabolites
```

**Confidence scoring**:
```
Level 1: Confirmed with authentic standard (MS + RT match)
Level 2: Probable structure (accurate mass + MS/MS)
Level 3: Tentative match (accurate mass only)
Level 4: Unknown metabolite
```

## Phase 2: Quality Control & Filtering

```python
def metabolomics_qc(data, sample_metadata):
    """
    QC metrics: CV in QC samples (<30%), blank ratios (>3x),
    missing values (<50%), total ion current per sample.
    """
    qc_samples = sample_metadata['sample_type'] == 'QC'
    qc_data = data[qc_samples]
    cv_per_metabolite = qc_data.std() / qc_data.mean()

    blank_samples = sample_metadata['sample_type'] == 'Blank'
    blank_data = data[blank_samples]
    blank_means = blank_data.mean()
    sample_means = data[~blank_samples & ~qc_samples].mean()
    blank_ratio = sample_means / blank_means

    keep_metabolites = blank_ratio > 3
    missing_per_metabolite = (data == 0).sum() / data.shape[0]
    keep_metabolites &= (missing_per_metabolite < 0.5)

    return data.loc[:, keep_metabolites]
```

## Phase 3: Normalization

### Total Ion Current (TIC)

```python
def normalize_tic(data):
    """Assumes total metabolite abundance is similar across samples."""
    tic = data.sum(axis=1)
    median_tic = tic.median()
    norm_factors = median_tic / tic
    return data.multiply(norm_factors, axis=0)
```

### Probabilistic Quotient Normalization (PQN)

```python
def normalize_pqn(data, reference_sample=None):
    """More robust than TIC to large metabolite changes."""
    import numpy as np

    if reference_sample is None:
        reference = data.median(axis=0)
    else:
        reference = data.loc[reference_sample]

    quotients = data.div(reference, axis=1)
    norm_factors = quotients.median(axis=1)
    return data.div(norm_factors, axis=0)
```

### Internal Standard Normalization

```python
def normalize_internal_standard(data, is_metabolite):
    """Most accurate if added before sample processing."""
    is_abundance = data[is_metabolite]
    norm_factors = is_abundance.median() / is_abundance
    normalized = data.multiply(norm_factors, axis=0)
    return normalized.drop(columns=[is_metabolite])
```

### Transformation

```python
def transform_data(data, method='log'):
    """Methods: 'log' (log2), 'pareto' (mean-center/sqrt(std)), 'auto' (z-score)."""
    import numpy as np

    if method == 'log':
        return np.log2(data + 1)
    elif method == 'pareto':
        mean, std = data.mean(axis=0), data.std(axis=0)
        return (data - mean) / np.sqrt(std)
    elif method == 'auto':
        mean, std = data.mean(axis=0), data.std(axis=0)
        return (data - mean) / std
```

## Phase 4: Exploratory Analysis

```python
def perform_pca_metabolomics(data, sample_groups):
    """PCA for sample clustering and outlier detection."""
    from sklearn.decomposition import PCA
    import matplotlib.pyplot as plt

    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(data)

    plt.figure(figsize=(8, 6))
    for group in sample_groups.unique():
        mask = sample_groups == group
        plt.scatter(pca_result[mask, 0], pca_result[mask, 1], label=group)
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
    plt.legend()
    plt.title('PCA - Metabolomics Data')


def plsda_analysis(X, y, n_components=2):
    """PLS-DA for supervised separation (better than PCA for classification)."""
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.preprocessing import LabelEncoder

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    pls = PLSRegression(n_components=n_components)
    X_pls = pls.fit_transform(X, y_encoded)[0]
    return X_pls
```

## Phase 5: Differential Metabolite Analysis

```python
def differential_metabolites(data, group1_samples, group2_samples):
    """Identify differential metabolites with FDR correction."""
    from scipy import stats
    from statsmodels.stats.multitest import multipletests
    import numpy as np
    import pandas as pd

    results = []
    for metabolite in data.columns:
        group1 = data.loc[group1_samples, metabolite]
        group2 = data.loc[group2_samples, metabolite]
        fold_change = group2.mean() / group1.mean()
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        results.append({
            'metabolite': metabolite,
            'fold_change': fold_change,
            'log2FC': np.log2(fold_change),
            'mean_group1': group1.mean(),
            'mean_group2': group2.mean(),
            'p_value': p_value,
            't_statistic': t_stat
        })

    results_df = pd.DataFrame(results)
    results_df['adj_p_value'] = multipletests(results_df['p_value'], method='fdr_bh')[1]
    results_df['significant'] = (
        (results_df['adj_p_value'] < 0.05) & (np.abs(results_df['log2FC']) > 1.0)
    )
    return results_df
```

## Phase 6: Metabolic Pathway Analysis

```python
def pathway_enrichment_metabolites(metabolite_list, organism='human'):
    """Perform pathway enrichment using KEGG metabolic pathways."""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    kegg_ids = []
    for metabolite in metabolite_list:
        result = tu.run_one_function({
            "name": "kegg_find_compound",
            "arguments": {"query": metabolite}
        })
        if result and 'data' in result:
            kegg_ids.append(result['data'][0]['entry_id'])

    enrichment = tu.run_one_function({
        "name": "kegg_enrich_pathway",
        "arguments": {"compound_list": ",".join(kegg_ids), "organism": organism}
    })
    return enrichment
```

## Phase 7: Multi-Omics Integration

```python
def correlate_metabolite_enzyme(metabolite_data, enzyme_expression):
    """Correlate metabolite levels with enzyme expression (Spearman)."""
    from scipy.stats import spearmanr

    correlations = {}
    for metabolite in metabolite_data.columns:
        enzymes = find_metabolite_enzymes(metabolite)
        for enzyme in enzymes:
            if enzyme in enzyme_expression.index:
                r, p = spearmanr(
                    metabolite_data[metabolite],
                    enzyme_expression.loc[enzyme]
                )
                correlations[f'{metabolite}_{enzyme}'] = {
                    'r': r, 'p': p,
                    'relationship': 'product' if r > 0 else 'substrate'
                }
    return correlations
```
