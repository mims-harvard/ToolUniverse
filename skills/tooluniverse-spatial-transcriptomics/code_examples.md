# Spatial Transcriptomics Code Examples

## Phase 1: Data Import & Quality Control

### Data Loading (Visium)

```python
def load_visium_data(data_dir):
    """
    Load 10x Visium spatial transcriptomics data.

    Expected structure:
    data_dir/
      ├── filtered_feature_bc_matrix/
      │   ├── barcodes.tsv.gz
      │   ├── features.tsv.gz
      │   └── matrix.mtx.gz
      ├── spatial/
      │   ├── tissue_positions_list.csv
      │   ├── scalefactors_json.json
      │   └── tissue_hires_image.png

    Returns: AnnData object with spatial coordinates
    """
    import scanpy as sc
    adata = sc.read_visium(data_dir)
    return adata
```

### Quality Control

```python
def spatial_qc(adata):
    """Quality control for spatial transcriptomics data."""
    import scanpy as sc

    sc.pp.calculate_qc_metrics(adata, inplace=True)
    sc.pl.spatial(adata, color='n_genes_by_counts', title='Genes per Spot')
    sc.pl.spatial(adata, color='total_counts', title='UMI Counts per Spot')

    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_cells(adata, min_counts=500)

    adata.var['mt'] = adata.var_names.str.startswith('MT-')
    sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
    adata = adata[adata.obs['pct_counts_mt'] < 20].copy()

    return adata
```

### Spatial Alignment Verification

```python
def verify_spatial_alignment(adata):
    """Verify spatial coordinates align with tissue image."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 10))
    img = adata.uns['spatial']['tissue_hires_image']
    ax.imshow(img)

    coords = adata.obsm['spatial']
    ax.scatter(coords[:, 0], coords[:, 1], c='red', s=1, alpha=0.5)
    ax.set_title('Spatial Alignment Verification')
    plt.axis('off')
```

## Phase 2: Preprocessing & Normalization

### Normalization

```python
def normalize_spatial(adata):
    """Normalize spatial transcriptomics data."""
    import scanpy as sc

    sc.pp.filter_genes(adata, min_cells=3)
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)
    adata.raw = adata

    return adata
```

### Highly Variable Genes

```python
def select_hvg_spatial(adata):
    """Select highly variable genes for spatial analysis."""
    import scanpy as sc
    sc.pp.highly_variable_genes(adata, n_top_genes=2000)
    return adata
```

### Spatial Smoothing

```python
def spatial_smooth(adata, radius=2):
    """Smooth expression by averaging over spatial neighbors."""
    from sklearn.neighbors import NearestNeighbors

    coords = adata.obsm['spatial']
    nn = NearestNeighbors(n_neighbors=radius, metric='euclidean')
    nn.fit(coords)
    distances, indices = nn.kneighbors(coords)

    X_smooth = adata.X.copy()
    for i in range(adata.n_obs):
        neighbors = indices[i]
        X_smooth[i] = adata.X[neighbors].mean(axis=0)

    adata.layers['smoothed'] = X_smooth
    return adata
```

## Phase 3: Spatial Clustering

```python
def spatial_clustering(adata, n_neighbors=6):
    """Cluster spots into spatial domains using expression + spatial proximity."""
    import scanpy as sc
    import squidpy as sq

    sc.pp.pca(adata, n_comps=50)
    sq.gr.spatial_neighbors(adata, coord_type='generic', n_neighs=n_neighbors)
    sc.tl.leiden(adata, resolution=1.0, key_added='spatial_domain')
    sc.pl.spatial(adata, color='spatial_domain', title='Spatial Domains')

    return adata


def find_domain_markers(adata):
    """Identify marker genes for each spatial domain."""
    import scanpy as sc

    sc.tl.rank_genes_groups(adata, groupby='spatial_domain', method='wilcoxon')
    markers = sc.get.rank_genes_groups_df(adata, group=None)
    return markers
```

## Phase 4: Spatially Variable Genes

```python
def identify_spatial_genes(adata):
    """Test for spatial autocorrelation using Moran's I."""
    import squidpy as sq

    sq.gr.spatial_autocorr(adata, mode='moran', n_perms=100, n_jobs=-1)
    spatial_genes = adata.uns['moranI'].sort_values('I', ascending=False)
    sig_spatial = spatial_genes[spatial_genes['pval_norm_fdr_bh'] < 0.05]
    return sig_spatial


def classify_spatial_patterns(adata, spatial_genes):
    """Classify types of spatial patterns: Gradient, Hotspot, Boundary, Periodic."""
    patterns = {}
    for gene in spatial_genes.index[:100]:
        expr = adata[:, gene].X.toarray().flatten()
        coords = adata.obsm['spatial']
        pattern_type = detect_pattern_type(expr, coords)
        patterns[gene] = pattern_type
    return patterns
```

## Phase 5: Neighborhood Analysis

```python
def analyze_neighborhoods(adata, radius=150):
    """Analyze spatial neighborhood composition."""
    import squidpy as sq

    sq.gr.nhood_enrichment(adata, cluster_key='spatial_domain')
    sq.pl.nhood_enrichment(adata, cluster_key='spatial_domain')
    return adata


def identify_interaction_zones(adata, domain_a, domain_b):
    """Find boundary regions between two spatial domains."""
    from sklearn.neighbors import NearestNeighbors

    spots_a = adata.obs['spatial_domain'] == domain_a
    spots_b = adata.obs['spatial_domain'] == domain_b

    coords = adata.obsm['spatial']
    nn = NearestNeighbors(n_neighbors=6)
    nn.fit(coords)
    distances, indices = nn.kneighbors(coords)

    interaction_spots = []
    for i, spot_in_a in enumerate(spots_a):
        if spot_in_a:
            neighbors = indices[i]
            if any(spots_b[neighbors]):
                interaction_spots.append(i)

    adata.obs['interaction_zone'] = False
    adata.obs.loc[interaction_spots, 'interaction_zone'] = True
    return adata
```

## Phase 6: Integration with Single-Cell RNA-seq

```python
def deconvolve_cell_types(adata_spatial, adata_sc):
    """Predict cell type composition per spatial spot using cell2location."""
    import cell2location

    cell_type_signatures = extract_signatures(adata_sc)
    mod = cell2location.models.Cell2location(
        adata_spatial, cell_state_df=cell_type_signatures
    )
    mod.train(max_epochs=30000)
    adata_spatial.obsm['cell_type_fractions'] = mod.get_cell_type_fractions()
    return adata_spatial


def map_cell_types_spatial(adata):
    """Visualize cell type spatial distributions."""
    import scanpy as sc

    cell_types = adata.obsm['cell_type_fractions'].columns
    for ct in cell_types:
        sc.pl.spatial(
            adata,
            color=adata.obsm['cell_type_fractions'][ct],
            title=f'{ct} Spatial Distribution'
        )
```

## Phase 7: Spatial Cell Communication

```python
def spatial_cell_communication(adata):
    """Identify cell-cell communication based on spatial proximity."""
    import squidpy as sq
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    lr_pairs = tu.run_one_function({
        "name": "OmniPath_get_ligand_receptor_interactions",
        "arguments": {"partners": ""}
    })

    sq.gr.ligrec(
        adata, n_perms=100, cluster_key='cell_type',
        interactions=lr_pairs, copy=False
    )
    sq.pl.ligrec(adata, cluster_key='cell_type')
    return adata


def map_communication_hotspots(adata, ligand, receptor):
    """Map spatial locations of specific L-R interactions."""
    ligand_expr = adata[:, ligand].X.toarray().flatten()
    receptor_expr = adata[:, receptor].X.toarray().flatten()
    interaction_score = ligand_expr * receptor_expr

    adata.obs[f'{ligand}_{receptor}_score'] = interaction_score
    sc.pl.spatial(adata, color=f'{ligand}_{receptor}_score',
                  title=f'{ligand}-{receptor} Interaction Hotspots')
```
