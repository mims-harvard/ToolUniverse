# Multi-Omics Integration: Phase Details

Complete implementation details for each phase of the multi-omics integration workflow.

---

## Phase 1: Data Loading & QC

**Supported formats**:
- Expression: CSV/TSV matrices, HDF5, AnnData (.h5ad)
- Proteomics: MaxQuant output, Spectronaut, DIA-NN
- Methylation: IDAT files, beta value matrices
- Variants: VCF, SEG files (CNV)
- Metabolomics: Peak tables, identified metabolites

**QC per omics**:
```python
# RNA-seq: Filter low-count genes, normalize (TPM/DESeq2), log-transform
# Proteomics: Filter high-missing proteins, impute (KNN/minimum), median-normalize
# Methylation: Remove failed probes, ComBat batch correction, filter cross-reactive
# Variants: Use variant-analysis skill for VCF QC, CNV segmentation validation
```

---

## Phase 2: Sample Matching

```python
def match_samples_across_omics(omics_data_dict):
    """
    Match samples across multiple omics datasets.

    Parameters:
    omics_data_dict: {
        'rnaseq': DataFrame (genes x samples),
        'proteomics': DataFrame (proteins x samples),
        'methylation': DataFrame (CpGs x samples),
        'cnv': DataFrame (genes x samples)
    }
    """
    sample_ids = {
        omics_type: set(df.columns)
        for omics_type, df in omics_data_dict.items()
    }
    common_samples = set.intersection(*sample_ids.values())
    matched_data = {
        omics_type: df[sorted(common_samples)]
        for omics_type, df in omics_data_dict.items()
    }
    return sorted(common_samples), matched_data
```

**Handling missing omics**: Use pairwise integration if not all samples have all omics types.

---

## Phase 3: Feature Mapping

Map all features to gene-level identifiers:
- **RNA-seq**: Already gene-level
- **Proteomics**: Map protein to gene
- **Methylation**: Map CpG to gene (promoter TSS +/- 2kb, gene body)
- **CNV**: Map CNV regions to overlapping genes
- **Metabolomics**: Map metabolite to enzyme gene

---

## Phase 4: Cross-Omics Correlation

### 4.1: RNA vs Protein (Translation Efficiency)

```python
def correlate_rna_protein(rnaseq_data, proteomics_data):
    """Expected: Positive correlation (r ~ 0.4-0.6 typical)"""
    common_genes = set(rnaseq_data.index) & set(proteomics_data.index)
    correlations = {}
    for gene in common_genes:
        r, p = spearmanr(rnaseq_data.loc[gene], proteomics_data.loc[gene])
        correlations[gene] = {'r': r, 'p': p}
    discordant = {g: v for g, v in correlations.items() if abs(v['r']) < 0.2}
    return correlations, discordant
```

### 4.2: Methylation vs Expression

```python
def correlate_methylation_expression(methylation_data, rnaseq_data):
    """Expected: Negative correlation (increased methylation -> decreased expression)"""
    results = {}
    for gene in methylation_data.index:
        if gene in rnaseq_data.index:
            r, p = spearmanr(methylation_data.loc[gene], rnaseq_data.loc[gene])
            results[gene] = {'r': r, 'p': p, 'direction': 'repressive' if r < 0 else 'activating'}
    regulated = {g: v for g, v in results.items() if v['r'] < -0.5 and v['p'] < 0.01}
    return results, regulated
```

### 4.3: CNV vs Expression (Dosage Effect)

```python
def correlate_cnv_expression(cnv_data, rnaseq_data):
    """Expected: Positive correlation (gene dosage effect)"""
    results = {}
    for gene in cnv_data.index:
        if gene in rnaseq_data.index:
            r, p = pearsonr(cnv_data.loc[gene], rnaseq_data.loc[gene])
            results[gene] = {'r': r, 'p': p}
    dosage_genes = {g: v for g, v in results.items() if v['r'] > 0.5 and v['p'] < 0.01}
    return results, dosage_genes
```

---

## Phase 5: Multi-Omics Clustering

### MOFA+ (Multi-Omics Factor Analysis)

```python
# Conceptual workflow (uses R's MOFA2 or Python implementation)
# 1. Prepare multi-omics data as list of matrices
# 2. Run MOFA+ to identify factors
# 3. Inspect factor variance explained per omics
# 4. Cluster samples based on factor scores
#
# Example interpretation:
# Factor 1: 40% RNA-seq variance, 30% proteomics -> Cell proliferation
# Factor 2: 50% methylation variance -> Epigenetic subtype
# Factor 3: 20% CNV variance -> Genomic instability
```

### Joint NMF

```python
def joint_nmf_clustering(omics_data_dict, n_clusters=3):
    """Joint NMF across omics for clustering."""
    combined_matrix = np.vstack([
        omics_data_dict['rnaseq'].values,
        omics_data_dict['proteomics'].values,
        omics_data_dict['methylation'].values
    ])
    from sklearn.decomposition import NMF
    model = NMF(n_components=n_clusters, init='nndsvd', random_state=42)
    W = model.fit_transform(combined_matrix)
    H = model.components_
    from sklearn.cluster import KMeans
    clusters = KMeans(n_clusters=n_clusters).fit_predict(H.T)
    return clusters, W, H
```

---

## Phase 6: Pathway-Level Integration

```python
def integrate_pathway_evidence(omics_results, pathway_genes):
    """Score pathway dysregulation across omics."""
    pathway_scores = []
    for gene in pathway_genes:
        gene_score = 0
        evidence_count = 0
        for omics_type in ['rnaseq', 'proteomics', 'methylation', 'cnv']:
            if gene in omics_results[omics_type]:
                gene_score += abs(omics_results[omics_type][gene])
                evidence_count += 1
        if evidence_count > 0:
            pathway_scores.append(gene_score / evidence_count)
    return {
        'pathway_score': np.mean(pathway_scores) if pathway_scores else 0,
        'n_genes_with_evidence': len(pathway_scores),
    }
```

**ToolUniverse enrichment**:
```python
tu = ToolUniverse()
all_dysregulated = set(rnaseq_degs) | set(diff_proteins) | set(methylation_dmgs)
enrichment = tu.run_one_function({
    "name": "enrichr_enrich",
    "arguments": {"gene_list": ",".join(all_dysregulated), "library": "KEGG_2021_Human"}
})
```

---

## Phase 7: Biomarker Discovery

```python
def select_multiomics_features(X_dict, y, n_features=50):
    """Select top features across omics for classification."""
    from sklearn.feature_selection import SelectKBest, f_classif
    selected_features = {}
    for omics_type, X in X_dict.items():
        selector = SelectKBest(f_classif, k=min(n_features, X.shape[1]))
        selector.fit(X, y)
        selected_features[omics_type] = X.columns[selector.get_support()].tolist()
    return selected_features

def multiomics_classification(X_dict, y, selected_features):
    """Train classifier using multi-omics features."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    X_combined = pd.concat([X_dict[k][v] for k, v in selected_features.items()], axis=1)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(clf, X_combined, y, cv=5, scoring='roc_auc')
    return {'mean_auc': scores.mean(), 'std_auc': scores.std(), 'n_features': X_combined.shape[1]}
```

---

## Phase 8: Report Template

```markdown
# Multi-Omics Integration Report

## Dataset Summary
- **Omics Types**: RNA-seq, Proteomics, Methylation, CNV
- **Common Samples**: N patients (disease/control split)
- **Features**: genes, proteins, CpGs, CNV regions

## Cross-Omics Correlation
### RNA-Protein: Overall r, highly correlated count, discordant genes
### Methylation-Expression: Anticorrelation, epigenetically regulated genes
### CNV-Expression: Dosage effect genes

## Multi-Omics Clustering (MOFA+/NMF)
### Factors and variance explained
### Patient subtypes with molecular profiles

## Pathway Integration
### Top dysregulated pathways with multi-omics scores

## Multi-Omics Biomarkers
### Classification performance (AUC, features per omics)
### Top biomarker features

## Biological Interpretation
### Summary of findings across molecular layers
```

---

## Use Cases (Detailed)

### Cancer Multi-Omics
1. Load 4 omics types for N patients
2. Match samples (find common across all omics)
3. Correlate RNA-protein (translation-regulated genes)
4. Correlate methylation-expression (epigenetically silenced genes)
5. Correlate CNV-expression (dosage-sensitive genes)
6. Run MOFA+ for latent factors
7. Identify subtypes with distinct multi-omics profiles
8. Pathway enrichment per subtype
9. Select multi-omics biomarkers

### eQTL + Expression + Methylation
1. Load genotype, expression, methylation data
2. For each GWAS SNP: test eQTL, test meQTL, test CpG-gene correlation
3. Identify SNP -> methylation -> expression regulatory chains

### Drug Response Multi-Omics
1. Load baseline multi-omics (pre-treatment) + drug response
2. Correlate each omics with response
3. Select predictive multi-omics features
4. Train classifier, identify resistance/sensitivity pathways

---

## Advanced Analysis Patterns

- **Omics-Driven Patient Stratification**: Precision medicine applications
- **Multi-Omics Network Analysis**: Integrated PPI + co-expression + regulatory networks
- **Temporal Multi-Omics**: Longitudinal data / treatment response
- **Spatial Multi-Omics**: Spatial transcriptomics + proteomics
