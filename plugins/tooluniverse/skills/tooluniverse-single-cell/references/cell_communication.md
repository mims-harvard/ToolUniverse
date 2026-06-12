# Cell-Cell Communication Analysis

Complete guide for analyzing ligand-receptor interactions and cell-cell communication using OmniPath database (integrates CellPhoneDB, CellChatDB, and 100+ other databases) via ToolUniverse.

---

## Overview

Cell-cell communication analysis identifies which cell types are signaling to each other through ligand-receptor (L-R) pairs. This is critical for understanding:
- Immune cell interactions (T cell exhaustion, activation)
- Tumor-immune communication (checkpoint blockade targets)
- Development and differentiation (niche signals)
- Tissue homeostasis (stromal-epithelial crosstalk)

**Data sources**: OmniPath integrates CellPhoneDB, CellChatDB, ICELLNET, Kirouac2010, Ramilowski2015, and 100+ other curated databases.

---

## Workflow Overview

```
1. Get L-R Pairs from OmniPath
   └─ Query databases (CellPhoneDB, CellChatDB)

2. Filter to Expressed Pairs
   └─ Check genes present in dataset
   └─ Filter by expression thresholds

3. Score Cell-Cell Communication
   └─ Sender-receiver matrix
   └─ Calculate communication scores

4. Identify Top Interactions
   └─ Rank by score
   └─ Filter by biology (e.g., tumor-immune)

5. Trace Signaling Cascades
   └─ Get downstream targets
   └─ Identify transcription factors

6. Validate and Report
   └─ Cross-check with literature
   └─ Generate communication network
```

---

## Step 1: Get Ligand-Receptor Pairs from OmniPath

```python
from tooluniverse import ToolUniverse
import pandas as pd

tu = ToolUniverse()
tu.load_tools()

def get_ligand_receptor_pairs(proteins=None, databases=None):
    """Get ligand-receptor pairs from OmniPath.

    Args:
        proteins: Comma-separated protein names (None = all)
        databases: Comma-separated database names (None = all)
                  Options: CellPhoneDB, CellChatDB, etc.

    Returns:
        DataFrame with L-R interactions
    """
    result = tu.run_tool(
        "OmniPath_get_ligand_receptor_interactions",
        proteins=proteins,
        databases=databases
    )

    if result['metadata']['success']:
        interactions = result['data']['interactions']
        df = pd.DataFrame(interactions)
        return df
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
        return pd.DataFrame()

# Example: Get all CellPhoneDB pairs
lr_pairs = get_ligand_receptor_pairs(databases="CellPhoneDB")
print(f"Found {len(lr_pairs)} L-R pairs from CellPhoneDB")

# Example: Get specific immune checkpoints
immune_checkpoints = "CD274,PDCD1,CTLA4,CD80,CD86,HAVCR2,TIGIT"
checkpoint_lr = get_ligand_receptor_pairs(proteins=immune_checkpoints)
print(checkpoint_lr[['source_genesymbol', 'target_genesymbol', 'curation_effort']])
```

**Important columns**:
- `source_genesymbol`: Ligand gene name
- `target_genesymbol`: Receptor gene name
- `is_directed`: True for directed interactions
- `sources`: Database sources (comma-separated)
- `references`: PubMed IDs
- `curation_effort`: Number of supporting evidences

---

## Step 2: Filter to Expressed L-R Pairs

```python
def filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.1, min_mean=0.1):
    """Filter L-R pairs to only those expressed in the dataset.

    Args:
        adata: AnnData object with normalized expression
        lr_pairs: DataFrame from get_ligand_receptor_pairs()
        min_frac: Minimum fraction of cells expressing (default 0.1 = 10%)
        min_mean: Minimum mean expression level (default 0.1)

    Returns:
        DataFrame with expressed L-R pairs
    """
    from scipy.sparse import issparse

    # Get genes in dataset
    genes_in_data = set(adata.var_names)

    # Filter to genes in data
    expressed_lr = lr_pairs[
        lr_pairs['source_genesymbol'].isin(genes_in_data) &
        lr_pairs['target_genesymbol'].isin(genes_in_data)
    ].copy()

    # Calculate expression statistics
    def gene_stats(gene):
        if gene not in genes_in_data:
            return 0, 0
        X = adata[:, gene].X
        if issparse(X):
            X = X.toarray()
        mean_expr = X.mean()
        frac_expr = (X > 0).mean()
        return mean_expr, frac_expr

    expressed_lr['ligand_mean'] = expressed_lr['source_genesymbol'].apply(
        lambda g: gene_stats(g)[0]
    )
    expressed_lr['ligand_frac'] = expressed_lr['source_genesymbol'].apply(
        lambda g: gene_stats(g)[1]
    )
    expressed_lr['receptor_mean'] = expressed_lr['target_genesymbol'].apply(
        lambda g: gene_stats(g)[0]
    )
    expressed_lr['receptor_frac'] = expressed_lr['target_genesymbol'].apply(
        lambda g: gene_stats(g)[1]
    )

    # Filter by thresholds
    expressed_lr = expressed_lr[
        (expressed_lr['ligand_mean'] >= min_mean) &
        (expressed_lr['receptor_mean'] >= min_mean) &
        (expressed_lr['ligand_frac'] >= min_frac) &
        (expressed_lr['receptor_frac'] >= min_frac)
    ]

    return expressed_lr

# Example
expressed_lr = filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.05, min_mean=0.05)
print(f"Expressed: {len(expressed_lr)}/{len(lr_pairs)} L-R pairs ({100*len(expressed_lr)/len(lr_pairs):.1f}%)")
```

---

## Step 3: Score Cell-Cell Communication

```python
def score_cell_communication(adata, lr_pairs, cell_type_col='cell_type',
                             method='mean_product'):
    """Score cell-cell communication for each cell type pair.

    Args:
        adata: AnnData with cell type annotations
        lr_pairs: Expressed L-R pairs from filter_expressed_lr_pairs()
        cell_type_col: Column in adata.obs with cell type labels
        method: 'mean_product' or 'fraction_product'

    Returns:
        DataFrame with columns: sender, receiver, ligand, receptor, score
    """
    import numpy as np
    from scipy.sparse import issparse

    cell_types = adata.obs[cell_type_col].unique()
    results = []

    for _, row in lr_pairs.iterrows():
        ligand = row['source_genesymbol']
        receptor = row['target_genesymbol']

        if ligand not in adata.var_names or receptor not in adata.var_names:
            continue

        for sender_ct in cell_types:
            for receiver_ct in cell_types:
                # Sender cells
                sender_mask = adata.obs[cell_type_col] == sender_ct
                ligand_expr = adata[sender_mask, ligand].X
                if issparse(ligand_expr):
                    ligand_expr = ligand_expr.toarray().flatten()

                # Receiver cells
                receiver_mask = adata.obs[cell_type_col] == receiver_ct
                receptor_expr = adata[receiver_mask, receptor].X
                if issparse(receptor_expr):
                    receptor_expr = receptor_expr.toarray().flatten()

                # Calculate score
                if method == 'mean_product':
                    ligand_mean = np.mean(ligand_expr)
                    receptor_mean = np.mean(receptor_expr)
                    score = ligand_mean * receptor_mean

                elif method == 'fraction_product':
                    ligand_frac = np.mean(ligand_expr > 0)
                    receptor_frac = np.mean(receptor_expr > 0)
                    ligand_mean = np.mean(ligand_expr[ligand_expr > 0]) if ligand_frac > 0 else 0
                    receptor_mean = np.mean(receptor_expr[receptor_expr > 0]) if receptor_frac > 0 else 0
                    score = ligand_frac * receptor_frac * ligand_mean * receptor_mean

                if score > 0:
                    results.append({
                        'sender': sender_ct,
                        'receiver': receiver_ct,
                        'ligand': ligand,
                        'receptor': receptor,
                        'ligand_mean': ligand_mean,
                        'receptor_mean': receptor_mean,
                        'score': score,
                        'curation_effort': row.get('curation_effort', 0),
                        'databases': row.get('sources', 'Unknown')
                    })

    return pd.DataFrame(results)

# Example
communication_scores = score_cell_communication(
    adata, expressed_lr, cell_type_col='cell_type'
)

# Top 20 interactions
top_20 = communication_scores.nlargest(20, 'score')
print("\nTop 20 cell-cell interactions:")
print(top_20[['sender', 'receiver', 'ligand', 'receptor', 'score']])
```

---

## Step 4: Identify Top Interactions

### Filter by Cell Type Pair
```python
# Example: Tumor → T cell interactions
tumor_to_tcell = communication_scores[
    (communication_scores['sender'] == 'Tumor') &
    (communication_scores['receiver'].str.contains('T cell|CD4|CD8'))
]

print(f"\nTumor → T cell interactions: {len(tumor_to_tcell)}")
print(tumor_to_tcell.nlargest(10, 'score'))
```

### Filter by Pathway
```python
# Immune checkpoints
checkpoints = ['CD274', 'PDCD1', 'CTLA4', 'CD80', 'CD86', 'HAVCR2', 'TIGIT']
checkpoint_interactions = communication_scores[
    communication_scores['ligand'].isin(checkpoints) |
    communication_scores['receptor'].isin(checkpoints)
].sort_values('score', ascending=False)

print(f"\nCheckpoint interactions: {len(checkpoint_interactions)}")
print(checkpoint_interactions.head(10))
```

---

## Step 5: Trace Downstream Signaling

```python
def get_downstream_signaling(receptor_gene):
    """Get downstream signaling from a receptor.

    Args:
        receptor_gene: Receptor gene symbol

    Returns:
        DataFrame with signaling interactions
    """
    result = tu.run_tool(
        "OmniPath_get_signaling_interactions",
        proteins=receptor_gene,
        is_directed=True
    )

    if result['metadata']['success']:
        interactions = result['data']['interactions']
        df = pd.DataFrame(interactions)

        # Filter to receptor as source
        df = df[df['source_genesymbol'] == receptor_gene]

        return df[[
            'source_genesymbol', 'target_genesymbol',
            'is_stimulation', 'is_inhibition',
            'sources', 'references'
        ]]

    return pd.DataFrame()

# Example: PDCD1 (PD-1) signaling
pdcd1_signaling = get_downstream_signaling('PDCD1')
print(f"\nPDCD1 signals to {len(pdcd1_signaling)} targets")
print(pdcd1_signaling.head(10))

# Find transcription factors
tfs = pdcd1_signaling[pdcd1_signaling['target_genesymbol'].str.contains('NFAT|FOS|JUN|STAT')]
print(f"\nTranscription factors: {list(tfs['target_genesymbol'])}")
```

---

## Step 6: Handle Protein Complexes

Some receptors are multi-subunit complexes (e.g., TGF-beta receptors):

```python
def check_complex_expression(adata, complex_name, cell_type=None):
    """Check if all subunits of a protein complex are expressed.

    Args:
        adata: AnnData object
        complex_name: Complex name (e.g., "TGFBR2")
        cell_type: Optional cell type to subset

    Returns:
        List of dicts with complex info
    """
    import numpy as np

    # Get complex composition from OmniPath
    result = tu.run_tool("OmniPath_get_complexes", proteins=complex_name)

    if not result['metadata']['success'] or not result['data']['complexes']:
        return {'complex_found': False}

    complexes = result['data']['complexes']

    # Subset to cell type
    if cell_type:
        adata_subset = adata[adata.obs.cell_type == cell_type, :]
    else:
        adata_subset = adata

    results = []
    for complex_info in complexes:
        components = complex_info.get('components_genesymbols', '').split('_')

        # Check expression of each component
        component_expr = {}
        for comp in components:
            if comp in adata_subset.var_names:
                X = adata_subset[:, comp].X
                if issparse(X):
                    X = X.toarray().flatten()
                mean_expr = np.mean(X)
                frac_expr = np.mean(X > 0)
                component_expr[comp] = {'mean': mean_expr, 'fraction': frac_expr}
            else:
                component_expr[comp] = {'mean': 0, 'fraction': 0}

        # Complex score = minimum of subunit expressions
        min_mean = min([v['mean'] for v in component_expr.values()])
        min_frac = min([v['fraction'] for v in component_expr.values()])

        results.append({
            'complex_name': complex_info.get('name', 'Unknown'),
            'components': components,
            'component_expression': component_expr,
            'complex_score': min_mean * min_frac,
            'all_subunits_expressed': all([v['fraction'] > 0.1 for v in component_expr.values()])
        })

    return results

# Example: TGF-beta receptor
tgfb_receptor = check_complex_expression(adata, "TGFBR2", cell_type="Fibroblast")
for comp_result in tgfb_receptor:
    print(f"\nComplex: {comp_result['complex_name']}")
    print(f"Components: {comp_result['components']}")
    print(f"All expressed: {comp_result['all_subunits_expressed']}")
    print(f"Score: {comp_result['complex_score']:.4f}")
```

---

## Step 7: Generate Communication Report

```python
def generate_communication_report(adata, cell_type_col='cell_type',
                                 databases="CellPhoneDB,CellChatDB",
                                 min_score=0.01):
    """Generate complete cell-cell communication report."""

    report = []
    report.append("# Cell-Cell Communication Analysis Report\n")

    # Step 1: Get L-R pairs
    report.append("## 1. Ligand-Receptor Database Query")
    lr_pairs = get_ligand_receptor_pairs(databases=databases)
    report.append(f"- Total L-R pairs: {len(lr_pairs)}")
    report.append(f"- Databases: {databases}\n")

    # Step 2: Filter expressed
    report.append("## 2. Expressed Ligand-Receptor Pairs")
    expressed_lr = filter_expressed_lr_pairs(adata, lr_pairs, min_frac=0.05, min_mean=0.05)
    report.append(f"- Expressed: {len(expressed_lr)}/{len(lr_pairs)} ({100*len(expressed_lr)/len(lr_pairs):.1f}%)")
    report.append(f"- Thresholds: >5% cells, mean >0.05\n")

    # Step 3: Score communication
    report.append("## 3. Cell-Cell Communication Scores")
    communication_scores = score_cell_communication(adata, expressed_lr, cell_type_col=cell_type_col)
    communication_scores = communication_scores[communication_scores['score'] >= min_score]
    report.append(f"- Total interactions: {len(communication_scores)}")
    report.append(f"- Min score: {min_score}\n")

    # Top 20 table
    report.append("### Top 20 Interactions")
    report.append("| Sender | Receiver | Ligand | Receptor | Score | Curation |")
    report.append("|--------|----------|--------|----------|-------|----------|")
    for _, row in communication_scores.nlargest(20, 'score').iterrows():
        report.append(
            f"| {row['sender']} | {row['receiver']} | {row['ligand']} | "
            f"{row['receptor']} | {row['score']:.4f} | {row['curation_effort']} |"
        )
    report.append("")

    # Communication by cell type
    report.append("## 4. Communication Summary by Cell Type")
    sender_counts = communication_scores.groupby('sender').size().sort_values(ascending=False)
    receiver_counts = communication_scores.groupby('receiver').size().sort_values(ascending=False)

    report.append("\n### Top Sender Cell Types")
    report.append("| Cell Type | Outgoing Interactions |")
    report.append("|-----------|----------------------|")
    for ct, count in sender_counts.head(10).items():
        report.append(f"| {ct} | {count} |")

    report.append("\n### Top Receiver Cell Types")
    report.append("| Cell Type | Incoming Interactions |")
    report.append("|-----------|----------------------|")
    for ct, count in receiver_counts.head(10).items():
        report.append(f"| {ct} | {count} |")

    return "\n".join(report)

# Generate and save report
report = generate_communication_report(adata, cell_type_col='cell_type')
print(report)

with open('cell_communication_report.md', 'w') as f:
    f.write(report)
```

---

## Example: Tumor-Immune Cell Communication

Complete workflow for T cell exhaustion analysis:

```python
# Step 1: Get immune checkpoint L-R pairs
checkpoint_proteins = "CD274,PDCD1,CTLA4,CD80,CD86,HAVCR2,TIGIT,CD96,NECTIN2,LAG3"
checkpoint_lr = get_ligand_receptor_pairs(proteins=checkpoint_proteins)

# Step 2: Filter to expressed
expressed_checkpoints = filter_expressed_lr_pairs(adata, checkpoint_lr, min_frac=0.05)

# Step 3: Score communication
communication_scores = score_cell_communication(adata, expressed_checkpoints)

# Step 4: Tumor-T cell interactions
tumor_tcell = communication_scores[
    ((communication_scores['sender'] == 'Tumor') &
     (communication_scores['receiver'].str.contains('T cell|CD4|CD8'))) |
    ((communication_scores['receiver'] == 'Tumor') &
     (communication_scores['sender'].str.contains('T cell|CD4|CD8')))
]

# Step 5: Find exhaustion signals
exhaustion_pairs = tumor_tcell[
    tumor_tcell['ligand'].isin(['CD274', 'HAVCR2']) |  # PD-L1, TIM-3
    tumor_tcell['receptor'].isin(['PDCD1', 'HAVCR2', 'CTLA4', 'LAG3'])
].sort_values('score', ascending=False)

print("\nTop tumor-T cell exhaustion signals:")
print(exhaustion_pairs[['sender', 'receiver', 'ligand', 'receptor', 'score']])

# Step 6: Expression levels
print(f"\nCD274 (PD-L1) in tumor: {adata[adata.obs.cell_type=='Tumor', 'CD274'].X.mean():.3f}")
print(f"PDCD1 (PD-1) in T cells: {adata[adata.obs.cell_type.str.contains('T cell'), 'PDCD1'].X.mean():.3f}")

# Step 7: Downstream signaling
pdcd1_cascade = get_downstream_signaling('PDCD1')
print(f"\nPDCD1 downstream targets: {len(pdcd1_cascade)}")
```

---

## Visualization

```python
def plot_communication_network(communication_scores, top_n=50, min_score=0.01):
    """Plot cell-cell communication network."""
    import matplotlib.pyplot as plt
    import networkx as nx

    # Filter
    comm_filtered = communication_scores[communication_scores['score'] >= min_score]
    comm_top = comm_filtered.nlargest(top_n, 'score')

    # Build network
    G = nx.DiGraph()
    for _, row in comm_top.iterrows():
        edge_label = f"{row['ligand']}→{row['receptor']}"
        G.add_edge(row['sender'], row['receiver'],
                  weight=row['score'], label=edge_label)

    # Plot
    plt.figure(figsize=(12, 10))
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Nodes
    nx.draw_networkx_nodes(G, pos, node_size=3000, node_color='lightblue', alpha=0.9)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

    # Edges
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    max_weight = max(weights)
    widths = [5 * w / max_weight for w in weights]

    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.6,
                          edge_color='gray', arrows=True, arrowsize=20)

    plt.title(f"Cell-Cell Communication Network (Top {top_n})", fontsize=14)
    plt.axis('off')
    plt.tight_layout()

    return plt

# Plot
plot = plot_communication_network(communication_scores, top_n=30)
plot.savefig('communication_network.png', dpi=300, bbox_inches='tight')
```

---

## Tips and Best Practices

1. **Expression thresholds**: Balance sensitivity vs specificity
   - Stringent: min_frac=0.1, min_mean=0.1 (fewer false positives)
   - Permissive: min_frac=0.05, min_mean=0.05 (capture rare interactions)

2. **Communication score**: Mean product method is simple and interpretable
   - Fraction product accounts for expression breadth
   - Can add log-transform for very skewed distributions

3. **Database selection**:
   - CellPhoneDB: Well-curated, human-focused
   - CellChatDB: Broader coverage, mouse + human
   - Use both for comprehensive analysis

4. **Validation**: Always cross-validate top hits:
   - Check expression in UMAP/violin plots
   - Verify with literature (PubMed IDs in `references` column)
   - Compare across replicates/cohorts

5. **Protein complexes**: Check multi-subunit receptors
   - Use `check_complex_expression()` for receptors like TGFBR1/2
   - All subunits must be expressed for functional complex

6. **Statistical testing**: For rigorous analysis:
   - Permutation test (shuffle cell labels)
   - Compare to random cell type assignments
   - Correct for multiple testing

---

## See Also

- **scanpy_workflow.md** - Load and normalize data before communication analysis
- **marker_identification.md** - Cell type annotation for communication analysis
- **troubleshooting.md** - Common OmniPath API issues
