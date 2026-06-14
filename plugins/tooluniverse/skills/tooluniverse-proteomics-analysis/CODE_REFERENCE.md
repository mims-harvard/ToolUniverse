# Code Reference: Proteomics Analysis

## Data Loading

### MaxQuant proteinGroups.txt

```python
def load_maxquant_proteins(protein_groups_file):
    """Load MaxQuant proteinGroups.txt file."""
    import pandas as pd

    df = pd.read_csv(protein_groups_file, sep='\t')

    # Extract intensity columns (LFQ or raw)
    intensity_cols = [col for col in df.columns if 'LFQ intensity' in col or 'Intensity ' in col]

    intensity_matrix = df[intensity_cols].copy()
    intensity_matrix.columns = [col.replace('LFQ intensity ', '').replace('Intensity ', '')
                                 for col in intensity_cols]

    metadata = df[['Protein IDs', 'Gene names', 'Fasta headers',
                   'Peptides', 'Sequence coverage [%]']].copy()

    return intensity_matrix, metadata
```

## Quality Control

### Missing Value Assessment

```python
def assess_missing_values(intensity_matrix):
    """Calculate percentage of missing values per protein and sample."""
    missing_per_protein = (intensity_matrix == 0).sum(axis=1) / intensity_matrix.shape[1]
    missing_per_sample = (intensity_matrix == 0).sum(axis=0) / intensity_matrix.shape[0]
    return missing_per_protein, missing_per_sample
```

### Intensity Distribution

```python
def plot_intensity_distributions(intensity_matrix):
    """Plot log10 intensity distributions per sample."""
    import matplotlib.pyplot as plt
    import numpy as np

    log_intensities = np.log10(intensity_matrix.replace(0, np.nan))
    log_intensities.plot(kind='box')
    plt.ylabel('log10 Intensity')
    plt.title('Intensity Distribution per Sample')
```

### Sample Correlation

```python
def plot_sample_correlation(intensity_matrix):
    """Calculate and visualize sample-sample correlation."""
    import numpy as np
    import seaborn as sns

    log_data = np.log2(intensity_matrix.replace(0, np.nan))
    corr_matrix = log_data.corr(method='pearson')
    sns.heatmap(corr_matrix, annot=True, cmap='RdYlBu_r', vmin=0.8, vmax=1.0)
```

### PCA

```python
def perform_pca(intensity_matrix, sample_groups):
    """Principal component analysis for sample clustering."""
    import numpy as np
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA

    log_data = np.log2(intensity_matrix.replace(0, np.nan))
    imputed = log_data.fillna(log_data.min().min())

    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(imputed.T)

    plt.scatter(pca_result[:, 0], pca_result[:, 1], c=sample_groups)
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
```

## Preprocessing

### Filtering

```python
def filter_proteins(intensity_matrix, metadata, min_valid=3):
    """Filter out low-confidence proteins."""
    valid_proteins = metadata['Peptides'] >= 2
    n_detected = (intensity_matrix > 0).sum(axis=1)
    valid_detection = n_detected >= min_valid
    is_contaminant = metadata['Protein IDs'].str.contains('CON__', na=False)
    is_reverse = metadata['Protein IDs'].str.contains('REV__', na=False)
    keep = valid_proteins & valid_detection & ~is_contaminant & ~is_reverse
    return intensity_matrix[keep], metadata[keep]
```

### Missing Value Imputation

```python
def impute_missing_values(intensity_matrix, method='MinProb'):
    """Impute missing protein intensities."""
    import numpy as np
    import pandas as pd

    if method == 'MinProb':
        min_val = intensity_matrix[intensity_matrix > 0].min().min()
        width, shift = 0.3, 1.8
        imputed = intensity_matrix.copy()
        missing_mask = imputed == 0
        n_missing = missing_mask.sum().sum()
        random_vals = np.random.normal(loc=min_val - shift, scale=width, size=n_missing)
        imputed.values[missing_mask.values] = random_vals
        return imputed
    elif method == 'KNN':
        from sklearn.impute import KNNImputer
        imputer = KNNImputer(n_neighbors=5)
        imputed = pd.DataFrame(
            imputer.fit_transform(intensity_matrix.replace(0, np.nan)),
            index=intensity_matrix.index, columns=intensity_matrix.columns
        )
        return imputed
```

### Normalization

```python
def normalize_intensities(intensity_matrix, method='median'):
    """Normalize protein intensities across samples."""
    if method == 'median':
        medians = intensity_matrix.median(axis=0)
        global_median = medians.median()
        norm_factors = global_median / medians
        return intensity_matrix * norm_factors
    elif method == 'quantile':
        from sklearn.preprocessing import quantile_transform
        import pandas as pd
        return pd.DataFrame(
            quantile_transform(intensity_matrix, axis=1),
            index=intensity_matrix.index, columns=intensity_matrix.columns
        )
```

## Differential Expression

```python
def differential_expression_limma(log2_intensities, group1_samples, group2_samples):
    """Perform differential expression using limma-like approach."""
    import numpy as np
    import pandas as pd
    from scipy import stats
    from statsmodels.stats.multitest import multipletests

    results = []
    for protein in log2_intensities.index:
        group1 = log2_intensities.loc[protein, group1_samples]
        group2 = log2_intensities.loc[protein, group2_samples]
        log2fc = group2.mean() - group1.mean()
        t_stat, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        results.append({
            'protein': protein, 'log2FC': log2fc,
            'mean_group1': group1.mean(), 'mean_group2': group2.mean(),
            'p_value': p_value, 't_statistic': t_stat
        })

    results_df = pd.DataFrame(results)
    results_df['adj_p_value'] = multipletests(results_df['p_value'], method='fdr_bh')[1]
    results_df['significant'] = (
        (results_df['adj_p_value'] < 0.05) & (np.abs(results_df['log2FC']) > 1.0)
    )
    return results_df
```

### Volcano Plot

```python
def plot_volcano(de_results, title='Volcano Plot'):
    """Visualize differential expression results."""
    import matplotlib.pyplot as plt
    import numpy as np

    plt.figure(figsize=(8, 6))
    non_sig = de_results[~de_results['significant']]
    plt.scatter(non_sig['log2FC'], -np.log10(non_sig['p_value']), c='gray', alpha=0.5, s=10)
    sig = de_results[de_results['significant']]
    plt.scatter(sig['log2FC'], -np.log10(sig['p_value']), c='red', alpha=0.7, s=20)
    plt.axhline(-np.log10(0.05), color='blue', linestyle='--', label='p=0.05')
    plt.axvline(-1, color='blue', linestyle='--')
    plt.axvline(1, color='blue', linestyle='--', label='|log2FC|=1')
    plt.xlabel('log2 Fold Change')
    plt.ylabel('-log10(p-value)')
    plt.title(title)
    plt.legend()
```

## PTM Analysis

```python
def analyze_phosphosites(phospho_sites_file, intensity_matrix):
    """Analyze phosphorylation site changes from MaxQuant Phospho (STY)Sites.txt."""
    import pandas as pd

    phospho = pd.read_csv(phospho_sites_file, sep='\t')
    phospho_confident = phospho[phospho['Localization prob'] > 0.75]
    phospho_confident['site'] = (
        phospho_confident['Gene names'] + '_' +
        phospho_confident['Amino acid'] +
        phospho_confident['Position'].astype(str)
    )
    return phospho_confident
```

## PPI Network

```python
def build_protein_network(protein_list, confidence=0.7):
    """Build PPI network using STRING database."""
    import networkx as nx
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()

    interactions = tu.run_one_function({
        "name": "string_get_interactions",
        "arguments": {
            "proteins": ",".join(protein_list),
            "species": 9606, "score_threshold": int(confidence * 1000)
        }
    })

    G = nx.Graph()
    for interaction in interactions['data']:
        G.add_edge(interaction['protein1'], interaction['protein2'], score=interaction['score'])
    return G

def detect_protein_modules(network_graph):
    """Identify tightly connected protein modules."""
    from networkx.algorithms import community
    communities = community.greedy_modularity_communities(network_graph)
    return [{'module_id': i, 'proteins': list(comm), 'size': len(comm)}
            for i, comm in enumerate(communities)]
```

## Protein-RNA Correlation

```python
def correlate_protein_rna(protein_data, rna_data, common_samples):
    """Correlate protein and mRNA levels. Expected r ~ 0.4-0.6."""
    from scipy.stats import spearmanr

    common_genes = set(protein_data.index) & set(rna_data.index)
    correlations = {}
    for gene in common_genes:
        protein = protein_data.loc[gene, common_samples]
        rna = rna_data.loc[gene, common_samples]
        r, p = spearmanr(protein, rna)
        correlations[gene] = {'r': r, 'p': p}
    return correlations
```
