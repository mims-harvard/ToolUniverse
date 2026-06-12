# CRISPR Screen Analysis - Use Cases & Best Practices

## Use Case 1: Genome-Wide Essentiality Screen

```python
counts, meta = load_sgrna_counts("genome_wide_screen.txt")
design = create_design_matrix(
    sample_names=['T0_1', 'T0_2', 'T14_1', 'T14_2', 'T14_3'],
    conditions=['baseline', 'baseline', 'treatment', 'treatment', 'treatment']
)

qc_results = qc_sgrna_distribution(counts)
filtered_counts, filtered_mapping = filter_low_count_sgrnas(counts, meta['sgrna_to_gene'])
norm_counts, size_factors = normalize_counts(filtered_counts, method='median')
lfc, control_mean, treatment_mean = calculate_lfc(norm_counts, design)
gene_scores = mageck_gene_scoring(lfc, filtered_mapping, method='rra')
enrichment = enrich_essential_genes(gene_scores, top_n=100)
report = generate_crispr_report(gene_scores, enrichment, None)
```

## Use Case 2: Synthetic Lethality Screen (KRAS)

```python
counts_wt, meta_wt = load_sgrna_counts("kras_wildtype_screen.txt")
counts_mut, meta_mut = load_sgrna_counts("kras_mutant_screen.txt")

# Process both (same steps as Use Case 1)
# ... filtering, normalization, LFC calculation ...

gene_scores_wt = mageck_gene_scoring(lfc_wt, filtered_mapping_wt)
gene_scores_mut = mageck_gene_scoring(lfc_mut, filtered_mapping_mut)

sl_hits = detect_synthetic_lethality(gene_scores_wt, gene_scores_mut)
print(f"Identified {len(sl_hits)} synthetic lethal candidates with KRAS mutation")

drug_targets = prioritize_drug_targets(sl_hits)
```

## Use Case 3: Drug Target Discovery Pipeline

```python
# 1. Identify essential genes from screen
gene_scores = mageck_gene_scoring(lfc, filtered_mapping)

# 2. Filter for highly essential (stringent threshold)
highly_essential = gene_scores[gene_scores['mean_lfc'] < -1.5]

# 3. Prioritize with expression data (if available)
drug_targets = prioritize_drug_targets(highly_essential, expression_data=tumor_expression)

# 4. Find existing drugs
drug_candidates = find_drugs_for_targets(drug_targets.index.tolist())

# 5. Generate comprehensive report
report = generate_crispr_report(gene_scores, None, drug_targets)
```

## Use Case 4: Integration with Expression Data

```python
rna_results = pd.read_csv("deseq2_results.csv", index_col=0)

integrated = gene_scores.merge(
    rna_results[['log2FoldChange', 'padj']],
    left_index=True, right_index=True, how='inner'
)

# Genes that are essential AND overexpressed
targets = integrated[
    (integrated['mean_lfc'] < -1) &
    (integrated['log2FoldChange'] > 1) &
    (integrated['padj'] < 0.05)
]
print(f"Identified {len(targets)} genes essential and overexpressed in disease")
```

---

## Best Practices

1. **sgRNA Design Quality**: Ensure library uses validated sgRNA designs (e.g., Brunello, Avana libraries)
2. **Replicates**: Minimum 2 biological replicates per condition; 3+ preferred
3. **Sequencing Depth**: Aim for 500-1000 reads per sgRNA at T0; 200+ at final timepoint
4. **Reference Genes**: Include positive (essential) and negative (non-essential) control genes
5. **Timepoint Selection**: Balance cell doublings (14-21 days) vs. sgRNA dropout
6. **Normalization**: Use median ratio normalization for count data (more robust than CPM)
7. **Multiple Testing**: Apply FDR correction when calling essential genes (padj < 0.05)
8. **Validation**: Validate top hits with orthogonal methods (siRNA, small molecule inhibitors)
9. **Context Matters**: Gene essentiality is context-dependent (cell line, tissue, genetic background)
10. **Druggability**: Essential genes are not always druggable; check DGIdb early in prioritization

## Troubleshooting

**Problem**: Low library representation (many zero-count sgRNAs)
- **Solution**: Increase sequencing depth; check for PCR biases in library prep

**Problem**: High Gini coefficient (skewed distribution)
- **Solution**: Optimize PCR cycles; consider using unique molecular identifiers (UMIs)

**Problem**: No strong essential genes detected
- **Solution**: Check timepoint (may be too early); verify cell viability; confirm sgRNA cutting efficiency

**Problem**: Too many essential genes (>500)
- **Solution**: Timepoint may be too late; adjust LFC threshold; check for batch effects

**Problem**: Discordant sgRNAs for same gene
- **Solution**: Check for off-target effects; verify sgRNA sequences; consider removing outlier sgRNAs
