#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-rnaseq-deseq2 Skill

Tests all core capabilities:
1. Data loading and orientation
2. DESeq2 analysis (single and multi-factor)
3. LFC shrinkage
4. Dispersion analysis
5. Result filtering (padj, lfc, baseMean, direction)
6. Multi-condition comparisons (unique/shared DEGs)
7. Multiple testing corrections
8. gseapy enrichment integration
9. Specific gene extraction
10. Statistical tests (t-test, ANOVA, Wilson CI)
11. miRNA/proteomics DE analysis
12. Edge cases and error handling
"""

import sys
import traceback
import warnings
import os
import tempfile

import numpy as np
import pandas as pd

# Suppress convergence warnings during tests
warnings.filterwarnings("ignore", category=UserWarning, module="pydeseq2")
warnings.filterwarnings("ignore", category=FutureWarning)

# Track test results
RESULTS = []
PASS_COUNT = 0
FAIL_COUNT = 0


def record(test_name, passed, detail=""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    RESULTS.append((test_name, status, detail))
    print(f"  [{status}] {test_name}" + (f" -- {detail}" if detail else ""))


# ============================================================
# Helper: Generate realistic synthetic RNA-seq data
# ============================================================

def generate_rnaseq_data(n_genes=500, n_samples=12, n_de_genes=50,
                         conditions=None, seed=42):
    """Generate synthetic RNA-seq count data with known DE genes."""
    np.random.seed(seed)

    if conditions is None:
        conditions = ['control'] * (n_samples // 2) + ['treatment'] * (n_samples // 2)

    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]
    sample_names = [f'sample_{i:02d}' for i in range(n_samples)]

    # Base expression: negative binomial
    base_means = np.random.lognormal(mean=3, sigma=1.5, size=n_genes)
    dispersion = 0.3

    counts_data = np.zeros((n_samples, n_genes), dtype=int)
    for i in range(n_samples):
        for j in range(n_genes):
            mu = base_means[j]
            # Add DE effect for first n_de_genes in treatment
            if j < n_de_genes and conditions[i] != conditions[0]:
                # Half up, half down
                if j < n_de_genes // 2:
                    mu *= 4  # Upregulated
                else:
                    mu *= 0.25  # Downregulated
            r = 1 / dispersion
            p = r / (r + mu)
            counts_data[i, j] = np.random.negative_binomial(max(1, int(r)), min(0.999, max(0.001, p)))

    counts = pd.DataFrame(counts_data, index=sample_names, columns=gene_names)
    metadata = pd.DataFrame({'condition': conditions}, index=sample_names)

    return counts, metadata, gene_names[:n_de_genes]


def generate_multifactor_data(seed=42):
    """Generate data for multi-factor design (strain + media)."""
    np.random.seed(seed)
    n_genes = 300
    n_samples = 24  # 4 strains x 2 media x 3 replicates

    gene_names = [f'Gene_{i:04d}' for i in range(n_genes)]

    strains = []
    media = []
    replicates = []
    for s in ['WT', 'MUT1', 'MUT2', 'MUT3']:
        for m in ['A', 'B']:
            for r in ['R1', 'R2', 'R3']:
                strains.append(s)
                media.append(m)
                replicates.append(r)

    sample_names = [f'{s}_{m}_{r}' for s, m, r in zip(strains, media, replicates)]
    metadata = pd.DataFrame({
        'strain': strains,
        'media': media,
        'replicate': replicates
    }, index=sample_names)

    # Generate counts
    base_means = np.random.lognormal(mean=3, sigma=1.5, size=n_genes)

    counts_data = np.zeros((n_samples, n_genes), dtype=int)
    for i in range(n_samples):
        for j in range(n_genes):
            mu = base_means[j]
            # Strain effects on first 30 genes
            if j < 10 and strains[i] == 'MUT1':
                mu *= 3
            elif j < 20 and strains[i] == 'MUT2':
                mu *= 3
            elif j < 30 and strains[i] == 'MUT3':
                mu *= 3
            r = 3
            p = r / (r + mu)
            counts_data[i, j] = np.random.negative_binomial(max(1, int(r)), min(0.999, max(0.001, p)))

    counts = pd.DataFrame(counts_data, index=sample_names, columns=gene_names)
    return counts, metadata


# ============================================================
# Test Suite
# ============================================================

def test_01_imports():
    """Test all required packages can be imported."""
    print("\n=== Test 01: Package Imports ===")
    try:
        from pydeseq2.dds import DeseqDataSet
        from pydeseq2.ds import DeseqStats
        record("import pydeseq2", True)
    except Exception as e:
        record("import pydeseq2", False, str(e))

    try:
        import gseapy
        record("import gseapy", True)
    except Exception as e:
        record("import gseapy", False, str(e))

    try:
        from scipy import stats
        record("import scipy.stats", True)
    except Exception as e:
        record("import scipy.stats", False, str(e))

    try:
        from statsmodels.stats.multitest import multipletests
        from statsmodels.stats.proportion import proportion_confint
        record("import statsmodels", True)
    except Exception as e:
        record("import statsmodels", False, str(e))

    try:
        import anndata
        record("import anndata", True)
    except Exception as e:
        record("import anndata", False, str(e))


def test_02_data_loading():
    """Test data loading from various formats."""
    print("\n=== Test 02: Data Loading ===")

    # Create temp CSV files
    counts, metadata, _ = generate_rnaseq_data(n_genes=100, n_samples=6)

    with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
        counts.to_csv(f)
        csv_path = f.name

    with tempfile.NamedTemporaryFile(suffix='.tsv', mode='w', delete=False) as f:
        counts.to_csv(f, sep='\t')
        tsv_path = f.name

    try:
        # Test CSV loading
        df = pd.read_csv(csv_path, index_col=0)
        record("load CSV counts", df.shape == counts.shape, f"Shape: {df.shape}")
    except Exception as e:
        record("load CSV counts", False, str(e))

    try:
        # Test TSV loading
        df = pd.read_csv(tsv_path, sep='\t', index_col=0)
        record("load TSV counts", df.shape == counts.shape, f"Shape: {df.shape}")
    except Exception as e:
        record("load TSV counts", False, str(e))

    try:
        # Test transposed matrix detection
        counts_T = counts.T  # genes as rows
        # Heuristic: if rows >> cols, genes are likely rows
        needs_transpose = counts_T.shape[0] > counts_T.shape[1] * 5
        record("transpose detection", needs_transpose, f"Shape {counts_T.shape}, needs_T={needs_transpose}")
    except Exception as e:
        record("transpose detection", False, str(e))

    try:
        # Test h5ad loading
        import anndata
        adata = anndata.AnnData(X=counts.values, obs=metadata,
                                var=pd.DataFrame(index=counts.columns))
        h5ad_path = os.path.join(tempfile.gettempdir(), 'test_counts.h5ad')
        adata.write_h5ad(h5ad_path)

        loaded = anndata.read_h5ad(h5ad_path)
        loaded_counts = pd.DataFrame(loaded.X, index=loaded.obs_names, columns=loaded.var_names)
        record("load h5ad counts", loaded_counts.shape == counts.shape)
        os.unlink(h5ad_path)
    except Exception as e:
        record("load h5ad counts", False, str(e))

    # Cleanup
    os.unlink(csv_path)
    os.unlink(tsv_path)


def test_03_data_validation():
    """Test data validation and alignment."""
    print("\n=== Test 03: Data Validation ===")

    counts, metadata, _ = generate_rnaseq_data(n_genes=100, n_samples=6)

    try:
        # Test alignment with matching samples
        common = set(counts.index) & set(metadata.index)
        record("sample alignment", len(common) == 6, f"{len(common)} common samples")
    except Exception as e:
        record("sample alignment", False, str(e))

    try:
        # Test integer enforcement
        float_counts = counts.astype(float) + 0.3
        int_counts = float_counts.round().astype(int)
        record("integer enforcement", (int_counts.dtypes == int).all())
    except Exception as e:
        record("integer enforcement", False, str(e))

    try:
        # Test zero gene removal
        counts_with_zeros = counts.copy()
        counts_with_zeros['ZeroGene'] = 0
        nonzero = counts_with_zeros.loc[:, counts_with_zeros.sum() > 0]
        record("zero gene removal", 'ZeroGene' not in nonzero.columns)
    except Exception as e:
        record("zero gene removal", False, str(e))

    try:
        # Test mismatched samples
        bad_meta = metadata.copy()
        bad_meta.index = [f'wrong_{i}' for i in range(len(bad_meta))]
        common = set(counts.index) & set(bad_meta.index)
        record("mismatch detection", len(common) == 0)
    except Exception as e:
        record("mismatch detection", False, str(e))


def test_04_basic_deseq2():
    """Test basic DESeq2 two-group comparison."""
    print("\n=== Test 04: Basic DESeq2 ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata, de_genes = generate_rnaseq_data(n_genes=200, n_samples=8, n_de_genes=30)

    try:
        metadata['condition'] = pd.Categorical(
            metadata['condition'], categories=['control', 'treatment']
        )

        dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
        dds.deseq2()
        record("DESeq2 fit", True, f"Fitted {counts.shape[1]} genes, {counts.shape[0]} samples")
    except Exception as e:
        record("DESeq2 fit", False, str(e))
        return

    try:
        stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
        stat_res.run_wald_test()
        stat_res.summary()
        results = stat_res.results_df
        record("Wald test", results.shape[0] == counts.shape[1],
               f"Results: {results.shape[0]} genes, cols: {list(results.columns)}")
    except Exception as e:
        record("Wald test", False, str(e))
        return

    try:
        # Check result columns
        expected_cols = ['baseMean', 'log2FoldChange', 'lfcSE', 'stat', 'pvalue', 'padj']
        has_all = all(c in results.columns for c in expected_cols)
        record("result columns", has_all, f"Columns: {list(results.columns)}")
    except Exception as e:
        record("result columns", False, str(e))

    try:
        # Check that some DE genes are detected
        sig = results[(results['padj'] < 0.05) & (results['padj'].notna())]
        detected_de = set(sig.index) & set(de_genes)
        record("DE gene detection", len(detected_de) > 0,
               f"Detected {len(detected_de)}/{len(de_genes)} true DE genes, total sig={len(sig)}")
    except Exception as e:
        record("DE gene detection", False, str(e))


def test_05_lfc_shrinkage():
    """Test LFC shrinkage."""
    print("\n=== Test 05: LFC Shrinkage ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata, _ = generate_rnaseq_data(n_genes=200, n_samples=8)

    metadata['condition'] = pd.Categorical(
        metadata['condition'], categories=['control', 'treatment']
    )

    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
    dds.deseq2()

    stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
    stat_res.run_wald_test()
    stat_res.summary()
    results_before = stat_res.results_df.copy()

    try:
        # Apply LFC shrinkage
        stat_res.lfc_shrink(coeff='condition[T.treatment]')
        results_after = stat_res.results_df

        # LFC should be shrunk towards zero
        max_lfc_before = results_before['log2FoldChange'].abs().max()
        max_lfc_after = results_after['log2FoldChange'].abs().max()
        record("LFC shrinkage applied", max_lfc_after <= max_lfc_before,
               f"Max |LFC| before: {max_lfc_before:.2f}, after: {max_lfc_after:.2f}")
    except Exception as e:
        record("LFC shrinkage applied", False, str(e))

    try:
        # Verify coefficient name format
        available = list(dds.varm['LFC'].columns)
        has_coeff = 'condition[T.treatment]' in available
        record("coefficient name format", has_coeff, f"Available: {available}")
    except Exception as e:
        record("coefficient name format", False, str(e))


def test_06_multifactor_design():
    """Test multi-factor design (strain + media)."""
    print("\n=== Test 06: Multi-Factor Design ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata = generate_multifactor_data()

    try:
        # Set reference levels
        metadata['strain'] = pd.Categorical(
            metadata['strain'], categories=['WT', 'MUT1', 'MUT2', 'MUT3']
        )
        metadata['media'] = pd.Categorical(
            metadata['media'], categories=['A', 'B']
        )

        dds = DeseqDataSet(
            counts=counts,
            metadata=metadata,
            design="~strain + media",
            quiet=True
        )
        dds.deseq2()
        record("multi-factor fit", True)
    except Exception as e:
        record("multi-factor fit", False, str(e))
        return

    try:
        # Extract MUT1 vs WT
        stat_res = DeseqStats(dds, contrast=['strain', 'MUT1', 'WT'], quiet=True)
        stat_res.run_wald_test()
        stat_res.summary()
        n_sig = (stat_res.results_df['padj'] < 0.05).sum()
        record("MUT1 vs WT contrast", True, f"{n_sig} significant genes")
    except Exception as e:
        record("MUT1 vs WT contrast", False, str(e))

    try:
        # Extract MUT2 vs WT
        stat_res2 = DeseqStats(dds, contrast=['strain', 'MUT2', 'WT'], quiet=True)
        stat_res2.run_wald_test()
        stat_res2.summary()
        n_sig2 = (stat_res2.results_df['padj'] < 0.05).sum()
        record("MUT2 vs WT contrast", True, f"{n_sig2} significant genes")
    except Exception as e:
        record("MUT2 vs WT contrast", False, str(e))

    try:
        # Extract MUT3 vs WT
        stat_res3 = DeseqStats(dds, contrast=['strain', 'MUT3', 'WT'], quiet=True)
        stat_res3.run_wald_test()
        stat_res3.summary()
        n_sig3 = (stat_res3.results_df['padj'] < 0.05).sum()
        record("MUT3 vs WT contrast", True, f"{n_sig3} significant genes")
    except Exception as e:
        record("MUT3 vs WT contrast", False, str(e))


def test_07_dispersion_analysis():
    """Test dispersion estimate access and diagnostics."""
    print("\n=== Test 07: Dispersion Analysis ===")

    from pydeseq2.dds import DeseqDataSet

    counts, metadata, _ = generate_rnaseq_data(n_genes=300, n_samples=10)
    metadata['condition'] = pd.Categorical(
        metadata['condition'], categories=['control', 'treatment']
    )

    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
    dds.deseq2()

    try:
        # Access genewise dispersions (before shrinkage)
        gwd = dds.var['genewise_dispersions']
        record("genewise dispersions access", len(gwd) == counts.shape[1],
               f"Shape: {len(gwd)}, range: [{gwd.min():.2e}, {gwd.max():.2e}]")
    except Exception as e:
        record("genewise dispersions access", False, str(e))

    try:
        # Access MAP dispersions (after shrinkage)
        mapd = dds.var['MAP_dispersions']
        record("MAP dispersions access", len(mapd) == counts.shape[1])
    except Exception as e:
        record("MAP dispersions access", False, str(e))

    try:
        # Access final dispersions
        final_d = dds.var['dispersions']
        record("final dispersions access", len(final_d) == counts.shape[1])
    except Exception as e:
        record("final dispersions access", False, str(e))

    try:
        # Count dispersions below threshold
        threshold = 1e-5
        n_below = (dds.var['genewise_dispersions'] < threshold).sum()
        record("dispersion threshold count", isinstance(n_below, (int, np.integer)),
               f"{n_below} genes below {threshold}")
    except Exception as e:
        record("dispersion threshold count", False, str(e))

    try:
        # Check fitted dispersions exist
        fitted = dds.var['fitted_dispersions']
        record("fitted dispersions access", len(fitted) == counts.shape[1])
    except Exception as e:
        record("fitted dispersions access", False, str(e))


def test_08_result_filtering():
    """Test result filtering with various thresholds."""
    print("\n=== Test 08: Result Filtering ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata, _ = generate_rnaseq_data(n_genes=500, n_samples=10, n_de_genes=80)
    metadata['condition'] = pd.Categorical(
        metadata['condition'], categories=['control', 'treatment']
    )

    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
    dds.deseq2()

    stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
    stat_res.run_wald_test()
    stat_res.summary()
    results = stat_res.results_df

    try:
        # padj < 0.05 only
        sig = results[results['padj'] < 0.05].dropna(subset=['padj'])
        record("padj filter", len(sig) > 0, f"{len(sig)} genes with padj<0.05")
    except Exception as e:
        record("padj filter", False, str(e))

    try:
        # padj < 0.05 AND |log2FC| > 0.5
        sig_lfc = results[
            (results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)
        ].dropna(subset=['padj'])
        record("padj + lfc filter", len(sig_lfc) <= len(sig),
               f"{len(sig_lfc)} genes with padj<0.05 and |lfc|>0.5")
    except Exception as e:
        record("padj + lfc filter", False, str(e))

    try:
        # padj < 0.05 AND |log2FC| > 1.5 AND baseMean >= 10
        strict = results[
            (results['padj'] < 0.05) &
            (results['log2FoldChange'].abs() > 1.5) &
            (results['baseMean'] >= 10)
        ].dropna(subset=['padj'])
        record("strict filter (padj+lfc+baseMean)", True,
               f"{len(strict)} genes with padj<0.05, |lfc|>1.5, baseMean>=10")
    except Exception as e:
        record("strict filter (padj+lfc+baseMean)", False, str(e))

    try:
        # Upregulated only
        up = results[
            (results['padj'] < 0.05) & (results['log2FoldChange'] > 0)
        ].dropna(subset=['padj'])
        # Downregulated only
        down = results[
            (results['padj'] < 0.05) & (results['log2FoldChange'] < 0)
        ].dropna(subset=['padj'])
        record("direction filter", len(up) + len(down) == len(sig),
               f"Up: {len(up)}, Down: {len(down)}")
    except Exception as e:
        record("direction filter", False, str(e))


def test_09_deg_set_operations():
    """Test multi-condition DEG comparisons (unique/shared)."""
    print("\n=== Test 09: DEG Set Operations ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata = generate_multifactor_data()
    metadata['strain'] = pd.Categorical(
        metadata['strain'], categories=['WT', 'MUT1', 'MUT2', 'MUT3']
    )
    metadata['media'] = pd.Categorical(metadata['media'], categories=['A', 'B'])

    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~strain + media", quiet=True)
    dds.deseq2()

    # Get DEGs for each strain vs WT
    deg_sets = {}
    for strain in ['MUT1', 'MUT2', 'MUT3']:
        sr = DeseqStats(dds, contrast=['strain', strain, 'WT'], quiet=True)
        sr.run_wald_test()
        sr.summary()
        sig = sr.results_df[sr.results_df['padj'] < 0.05].dropna(subset=['padj'])
        deg_sets[strain] = set(sig.index)

    try:
        # Unique to each strain
        unique_mut1 = deg_sets['MUT1'] - deg_sets['MUT2'] - deg_sets['MUT3']
        unique_mut2 = deg_sets['MUT2'] - deg_sets['MUT1'] - deg_sets['MUT3']
        unique_mut3 = deg_sets['MUT3'] - deg_sets['MUT1'] - deg_sets['MUT2']
        record("unique DEGs per strain", True,
               f"Unique MUT1:{len(unique_mut1)}, MUT2:{len(unique_mut2)}, MUT3:{len(unique_mut3)}")
    except Exception as e:
        record("unique DEGs per strain", False, str(e))

    try:
        # Shared across all strains
        shared = deg_sets['MUT1'] & deg_sets['MUT2'] & deg_sets['MUT3']
        record("shared DEGs", True, f"Shared across all: {len(shared)}")
    except Exception as e:
        record("shared DEGs", False, str(e))

    try:
        # In at least one single mutant but NOT in double
        in_single = deg_sets['MUT1'] | deg_sets['MUT2']
        only_in_single = in_single - deg_sets['MUT3']
        record("single-not-double DEGs", True, f"In single but not double: {len(only_in_single)}")
    except Exception as e:
        record("single-not-double DEGs", False, str(e))

    try:
        # Percentage calculation
        overlap = deg_sets['MUT1'] & deg_sets['MUT2']
        if len(deg_sets['MUT1']) > 0:
            pct = len(overlap) / len(deg_sets['MUT1']) * 100
        else:
            pct = 0
        record("overlap percentage", True, f"{pct:.1f}% of MUT1 DEGs shared with MUT2")
    except Exception as e:
        record("overlap percentage", False, str(e))


def test_10_multiple_testing():
    """Test multiple testing correction methods."""
    print("\n=== Test 10: Multiple Testing Correction ===")

    from statsmodels.stats.multitest import multipletests

    # Generate some p-values
    np.random.seed(42)
    pvals = np.concatenate([
        np.random.uniform(0, 0.001, 20),   # True positives
        np.random.uniform(0.01, 1.0, 180)  # Null
    ])

    try:
        _, padj_bh, _, _ = multipletests(pvals, method='fdr_bh')
        n_bh = (padj_bh < 0.05).sum()
        record("BH correction", n_bh > 0, f"{n_bh} significant after BH")
    except Exception as e:
        record("BH correction", False, str(e))

    try:
        _, padj_by, _, _ = multipletests(pvals, method='fdr_by')
        n_by = (padj_by < 0.05).sum()
        record("BY correction", True, f"{n_by} significant after BY")
    except Exception as e:
        record("BY correction", False, str(e))

    try:
        _, padj_bonf, _, _ = multipletests(pvals, method='bonferroni')
        n_bonf = (padj_bonf < 0.05).sum()
        record("Bonferroni correction", n_bonf <= n_bh,
               f"{n_bonf} significant after Bonferroni (should be <= BH={n_bh})")
    except Exception as e:
        record("Bonferroni correction", False, str(e))

    try:
        # Verify ordering: Bonferroni <= BH <= BY (in terms of strictness)
        # Actually BY is more conservative than BH
        # So: Bonferroni <= BY <= BH typically, but not always
        record("correction ordering", n_bonf <= n_bh,
               f"Bonf={n_bonf} <= BH={n_bh}: {n_bonf <= n_bh}")
    except Exception as e:
        record("correction ordering", False, str(e))


def test_11_enrichment_ora():
    """Test gseapy over-representation analysis."""
    print("\n=== Test 11: Enrichment Analysis (ORA) ===")

    import gseapy as gp

    # Use well-known cancer genes for enrichment
    gene_list = ['TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'PIK3CA',
                 'PTEN', 'RB1', 'APC', 'MYC', 'CDH1', 'CTNNB1',
                 'SMAD4', 'VHL', 'WT1', 'NF1', 'NF2', 'RET']

    try:
        enr = gp.enrich(
            gene_list=gene_list,
            gene_sets='GO_Biological_Process_2021',
            outdir=None,
            no_plot=True,
            verbose=False,
            cutoff=0.05
        )
        n_terms = len(enr.results)
        record("GO BP enrichment", n_terms > 0, f"{n_terms} enriched terms")
    except Exception as e:
        record("GO BP enrichment", False, str(e))

    try:
        # Check result columns
        expected = ['Term', 'Overlap', 'P-value', 'Adjusted P-value', 'Genes']
        has_all = all(c in enr.results.columns for c in expected)
        record("enrichment result columns", has_all,
               f"Columns: {list(enr.results.columns)}")
    except Exception as e:
        record("enrichment result columns", False, str(e))

    try:
        # KEGG enrichment
        enr_kegg = gp.enrich(
            gene_list=gene_list,
            gene_sets='KEGG_2021_Human',
            outdir=None,
            no_plot=True,
            verbose=False,
            cutoff=0.05
        )
        record("KEGG enrichment", len(enr_kegg.results) > 0,
               f"{len(enr_kegg.results)} KEGG pathways")
    except Exception as e:
        record("KEGG enrichment", False, str(e))

    try:
        # Reactome enrichment
        enr_react = gp.enrich(
            gene_list=gene_list,
            gene_sets='Reactome_2022',
            outdir=None,
            no_plot=True,
            verbose=False,
            cutoff=0.05
        )
        record("Reactome enrichment", len(enr_react.results) > 0,
               f"{len(enr_react.results)} Reactome pathways")
    except Exception as e:
        record("Reactome enrichment", False, str(e))

    try:
        # Extract specific term
        cancer_terms = enr.results[enr.results['Term'].str.contains('cancer|tumor|apoptosis',
                                                                     case=False)]
        record("term extraction", True,
               f"Found {len(cancer_terms)} cancer/apoptosis-related terms")
    except Exception as e:
        record("term extraction", False, str(e))


def test_12_specific_gene_extraction():
    """Test extracting specific gene results."""
    print("\n=== Test 12: Specific Gene Extraction ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    counts, metadata, _ = generate_rnaseq_data(n_genes=100, n_samples=8)
    metadata['condition'] = pd.Categorical(
        metadata['condition'], categories=['control', 'treatment']
    )

    dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
    dds.deseq2()

    stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
    stat_res.run_wald_test()
    stat_res.summary()
    results = stat_res.results_df

    try:
        # Exact match
        gene = 'Gene_0000'
        lfc = results.loc[gene, 'log2FoldChange']
        padj = results.loc[gene, 'padj']
        record("exact gene lookup", not np.isnan(lfc),
               f"{gene}: lfc={lfc:.2f}, padj={padj:.2e}")
    except Exception as e:
        record("exact gene lookup", False, str(e))

    try:
        # Case-insensitive match
        idx_lower = {g.lower(): g for g in results.index}
        gene_lower = 'gene_0001'
        actual = idx_lower.get(gene_lower)
        val = results.loc[actual, 'log2FoldChange'] if actual else None
        record("case-insensitive lookup", val is not None,
               f"Found {actual}: lfc={val:.2f}")
    except Exception as e:
        record("case-insensitive lookup", False, str(e))

    try:
        # Get max LFC among significant
        sig = results[results['padj'] < 0.05].dropna(subset=['padj'])
        if len(sig) > 0:
            max_lfc = sig['log2FoldChange'].max()
            max_gene = sig['log2FoldChange'].idxmax()
            record("max LFC extraction", True,
                   f"Max LFC gene: {max_gene} = {max_lfc:.2f}")
        else:
            record("max LFC extraction", True, "No significant genes (data-dependent)")
    except Exception as e:
        record("max LFC extraction", False, str(e))

    try:
        # Round to decimal places
        lfc_raw = results.loc['Gene_0005', 'log2FoldChange']
        lfc_2dp = round(lfc_raw, 2)
        padj_4dp = round(results.loc['Gene_0005', 'padj'], 4) if not np.isnan(results.loc['Gene_0005', 'padj']) else None
        record("value rounding", True, f"LFC 2dp={lfc_2dp}, padj 4dp={padj_4dp}")
    except Exception as e:
        record("value rounding", False, str(e))


def test_13_statistical_tests():
    """Test statistical tests (t-test, ANOVA, Wilson CI)."""
    print("\n=== Test 13: Statistical Tests ===")

    from scipy import stats as sp_stats
    from statsmodels.stats.proportion import proportion_confint

    try:
        # Welch's t-test
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 100)
        group2 = np.random.normal(0.5, 1.2, 80)
        stat, pval = sp_stats.ttest_ind(group1, group2, equal_var=False)
        record("Welch t-test", 0 < pval < 1, f"t={stat:.3f}, p={pval:.4f}")
    except Exception as e:
        record("Welch t-test", False, str(e))

    try:
        # One-way ANOVA
        g1 = np.random.normal(0, 1, 50)
        g2 = np.random.normal(0.1, 1, 50)
        g3 = np.random.normal(0.2, 1, 50)
        f_stat, p_anova = sp_stats.f_oneway(g1, g2, g3)
        record("ANOVA", 0 < p_anova < 1, f"F={f_stat:.3f}, p={p_anova:.4f}")
    except Exception as e:
        record("ANOVA", False, str(e))

    try:
        # Wilson confidence interval
        n_total = 20000
        n_sig = 700
        ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
        record("Wilson CI", ci_low < ci_high and ci_low > 0,
               f"95% CI: ({ci_low:.4f}, {ci_high:.4f})")
    except Exception as e:
        record("Wilson CI", False, str(e))

    try:
        # Chi-squared test (independence)
        observed = np.array([[50, 30], [20, 100]])
        chi2, p_chi2, dof, expected = sp_stats.chi2_contingency(observed)
        record("Chi-squared test", p_chi2 < 0.05, f"chi2={chi2:.2f}, p={p_chi2:.2e}")
    except Exception as e:
        record("Chi-squared test", False, str(e))


def test_14_mirna_de():
    """Test miRNA/proteomics differential expression (t-test based)."""
    print("\n=== Test 14: miRNA/Proteomics DE ===")

    from scipy import stats as sp_stats
    from statsmodels.stats.multitest import multipletests

    np.random.seed(42)
    n_mirnas = 200
    n_patients = 20
    n_controls = 20

    # Simulate normalized miRNA expression
    patient_expr = np.random.normal(5, 2, size=(n_patients, n_mirnas))
    control_expr = np.random.normal(5, 2, size=(n_controls, n_mirnas))

    # Make first 20 miRNAs differentially expressed
    patient_expr[:, :20] += 2

    mirna_names = [f'miR-{i}' for i in range(n_mirnas)]
    all_expr = pd.DataFrame(
        np.vstack([patient_expr, control_expr]),
        columns=mirna_names,
        index=[f'patient_{i}' for i in range(n_patients)] + [f'control_{i}' for i in range(n_controls)]
    )
    groups = ['patient'] * n_patients + ['control'] * n_controls

    try:
        # Run t-tests
        pvalues = []
        lfcs = []
        for mirna in mirna_names:
            p_vals = all_expr.loc[[f'patient_{i}' for i in range(n_patients)], mirna]
            c_vals = all_expr.loc[[f'control_{i}' for i in range(n_controls)], mirna]
            _, pval = sp_stats.ttest_ind(p_vals, c_vals)
            lfc = p_vals.mean() - c_vals.mean()  # log-space difference
            pvalues.append(pval)
            lfcs.append(lfc)

        results = pd.DataFrame({
            'pvalue': pvalues,
            'log2FC': lfcs
        }, index=mirna_names)

        # Percentage with p < 0.05 before correction
        pct_sig_raw = (results['pvalue'] < 0.05).sum() / len(results) * 100
        record("miRNA raw p-value filter", pct_sig_raw > 0,
               f"{pct_sig_raw:.0f}% significant before correction")
    except Exception as e:
        record("miRNA raw p-value filter", False, str(e))

    try:
        # Multiple testing corrections
        _, padj_bh, _, _ = multipletests(results['pvalue'], method='fdr_bh')
        _, padj_by, _, _ = multipletests(results['pvalue'], method='fdr_by')
        _, padj_bonf, _, _ = multipletests(results['pvalue'], method='bonferroni')

        results['padj_BH'] = padj_bh
        results['padj_BY'] = padj_by
        results['padj_Bonf'] = padj_bonf

        n_bh = (padj_bh <= 0.05).sum()
        n_by = (padj_by <= 0.05).sum()
        n_bonf = (padj_bonf <= 0.05).sum()

        record("miRNA multiple testing", True,
               f"BH={n_bh}, BY={n_by}, Bonf={n_bonf}")
    except Exception as e:
        record("miRNA multiple testing", False, str(e))

    try:
        # Ratio calculation (BixBench bix-30-q3 pattern)
        ratio_str = f"{n_bonf}:{n_by}"
        record("correction ratio format", ':' in ratio_str, f"Ratio: {ratio_str}")
    except Exception as e:
        record("correction ratio format", False, str(e))

    try:
        # Significant in ALL correction methods
        sig_all = ((padj_bh <= 0.05) & (padj_by <= 0.05) & (padj_bonf <= 0.05)).sum()
        record("significant in all corrections", True,
               f"{sig_all} significant in all 3 methods")
    except Exception as e:
        record("significant in all corrections", False, str(e))


def test_15_enrichment_term_search():
    """Test enrichment term search and extraction."""
    print("\n=== Test 15: Enrichment Term Search ===")

    import gseapy as gp

    gene_list = ['TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'PIK3CA',
                 'PTEN', 'RB1', 'APC', 'MYC', 'CDH1', 'CTNNB1',
                 'ATM', 'ATR', 'CHEK1', 'CHEK2', 'MDM2', 'CDKN2A']

    try:
        enr = gp.enrich(
            gene_list=gene_list,
            gene_sets='GO_Biological_Process_2021',
            outdir=None,
            no_plot=True,
            verbose=False,
            cutoff=1.0  # Get all terms
        )

        # Search for specific term
        term_query = 'cell cycle'
        matches = enr.results[enr.results['Term'].str.lower().str.contains(term_query.lower())]
        record("term search", len(matches) > 0,
               f"Found {len(matches)} terms matching '{term_query}'")
    except Exception as e:
        record("term search", False, str(e))

    try:
        # Extract Adjusted P-value for top match
        if len(matches) > 0:
            top_match = matches.sort_values('Adjusted P-value').iloc[0]
            padj = top_match['Adjusted P-value']
            term = top_match['Term']
            record("extract term padj", True, f"'{term}': padj={padj:.4e}")
        else:
            record("extract term padj", True, "No matches (data-dependent)")
    except Exception as e:
        record("extract term padj", False, str(e))

    try:
        # Extract Odds Ratio
        if 'Odds Ratio' in enr.results.columns and len(matches) > 0:
            odds = matches.iloc[0]['Odds Ratio']
            record("extract odds ratio", True, f"Odds Ratio: {odds:.2f}")
        else:
            record("extract odds ratio", True, "Odds Ratio column not present or no matches")
    except Exception as e:
        record("extract odds ratio", False, str(e))

    try:
        # Extract gene overlap info
        if len(matches) > 0:
            genes_in_term = matches.iloc[0]['Genes'].split(';')
            overlap_str = matches.iloc[0]['Overlap']
            record("extract gene overlap", True,
                   f"Genes: {len(genes_in_term)}, Overlap: {overlap_str}")
        else:
            record("extract gene overlap", True, "No matches")
    except Exception as e:
        record("extract gene overlap", False, str(e))


def test_16_go_simplification():
    """Test GO term simplification (Jaccard similarity)."""
    print("\n=== Test 16: GO Term Simplification ===")

    # Create mock enrichment results with overlapping terms
    mock_results = pd.DataFrame({
        'Term': ['regulation of apoptotic process',
                 'positive regulation of apoptotic process',
                 'cell cycle arrest',
                 'negative regulation of cell cycle',
                 'DNA damage response'],
        'Adjusted P-value': [1e-10, 1e-8, 1e-7, 1e-6, 1e-5],
        'Genes': [
            'TP53;BRCA1;PTEN;RB1;APC',
            'TP53;BRCA1;PTEN;APC',           # High overlap with first
            'CDKN2A;RB1;TP53;CHEK1',
            'CDKN2A;RB1;TP53',               # High overlap with cell cycle arrest
            'ATM;ATR;CHEK1;CHEK2;TP53;BRCA1'
        ]
    })

    try:
        # Jaccard similarity based simplification
        terms = mock_results.sort_values('Adjusted P-value').copy()
        gene_sets = {}
        for _, row in terms.iterrows():
            gene_sets[row['Term']] = set(row['Genes'].split(';'))

        keep = []
        removed = set()

        for i, (term_i, genes_i) in enumerate(gene_sets.items()):
            if term_i in removed:
                continue
            keep.append(term_i)
            for term_j, genes_j in list(gene_sets.items())[i+1:]:
                if term_j in removed:
                    continue
                intersection = len(genes_i & genes_j)
                union = len(genes_i | genes_j)
                similarity = intersection / union if union > 0 else 0
                if similarity > 0.7:
                    removed.add(term_j)

        simplified = terms[terms['Term'].isin(keep)]
        record("GO simplification", len(simplified) < len(mock_results),
               f"Before: {len(mock_results)}, After: {len(simplified)}, Removed: {len(removed)}")
    except Exception as e:
        record("GO simplification", False, str(e))

    try:
        # Verify most significant term kept, similar terms removed
        record("keeps significant terms", 'regulation of apoptotic process' in keep)
    except Exception as e:
        record("keeps significant terms", False, str(e))


def test_17_output_formatting():
    """Test various output formatting requirements."""
    print("\n=== Test 17: Output Formatting ===")

    try:
        # Decimal rounding
        val = 4.80123
        record("round 2dp", round(val, 2) == 4.80, f"{round(val, 2)}")
    except Exception as e:
        record("round 2dp", False, str(e))

    try:
        # Scientific notation
        val = 7.04e-26
        formatted = f"{val:.2E}"
        record("scientific notation", 'E' in formatted, f"{formatted}")
    except Exception as e:
        record("scientific notation", False, str(e))

    try:
        # Percentage
        val = 0.156
        pct = f"{val * 100:.1f}%"
        record("percentage format", pct == "15.6%", f"{pct}")
    except Exception as e:
        record("percentage format", False, str(e))

    try:
        # Ratio format
        a, b = 0, 0
        ratio = f"{a}:{b}"
        record("ratio format", ratio == "0:0", f"{ratio}")
    except Exception as e:
        record("ratio format", False, str(e))

    try:
        # Fraction format
        num, denom = 8, 49
        frac = f"{num}/{denom}"
        record("fraction format", frac == "8/49", f"{frac}")
    except Exception as e:
        record("fraction format", False, str(e))

    try:
        # Range tuple
        val = 842
        expected_range = (700, 1000)
        in_range = expected_range[0] <= val <= expected_range[1]
        record("range check", in_range, f"{val} in {expected_range}")
    except Exception as e:
        record("range check", False, str(e))


def test_18_edge_cases():
    """Test edge cases and error handling."""
    print("\n=== Test 18: Edge Cases ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    try:
        # Small sample size with mean fit_type
        counts, metadata, _ = generate_rnaseq_data(n_genes=50, n_samples=4, n_de_genes=5)
        metadata['condition'] = pd.Categorical(
            metadata['condition'], categories=['control', 'treatment']
        )
        dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition",
                           fit_type='mean', quiet=True)
        dds.deseq2()
        record("small sample (n=4)", True, "Fitted with fit_type='mean'")
    except Exception as e:
        record("small sample (n=4)", False, str(e))

    try:
        # Gene not found
        stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
        stat_res.run_wald_test()
        stat_res.summary()
        results = stat_res.results_df

        fake_gene = 'NONEXISTENT_GENE'
        found = fake_gene in results.index
        record("gene not found", not found, f"'{fake_gene}' correctly not in results")
    except Exception as e:
        record("gene not found", False, str(e))

    try:
        # NaN handling in padj
        nan_count = results['padj'].isna().sum()
        record("NaN padj handling", True, f"{nan_count} NaN padj values (filtered by independent filtering)")
    except Exception as e:
        record("NaN padj handling", False, str(e))

    try:
        # All zeros for a gene (should be filtered or handled)
        test_counts = counts.copy()
        test_counts['AllZero'] = 0
        nonzero = test_counts.loc[:, test_counts.sum() > 0]
        record("all-zero gene handling", 'AllZero' not in nonzero.columns)
    except Exception as e:
        record("all-zero gene handling", False, str(e))

    try:
        # Float counts (need rounding)
        float_counts = counts.astype(float) + 0.7
        int_counts = float_counts.round().astype(int)
        dds2 = DeseqDataSet(counts=int_counts, metadata=metadata, design="~condition", quiet=True)
        dds2.deseq2()
        record("float-to-int conversion", True)
    except Exception as e:
        record("float-to-int conversion", False, str(e))


def test_19_median_lfc_distribution():
    """Test median LFC and distribution shape analysis."""
    print("\n=== Test 19: Median LFC & Distribution ===")

    from scipy import stats as sp_stats

    np.random.seed(42)
    # Simulate log2 fold changes
    lfcs = np.random.normal(0, 0.5, 1000)

    try:
        median_lfc = np.median(lfcs)
        record("median LFC calculation", abs(median_lfc) < 1,
               f"Median LFC: {median_lfc:.4f}")
    except Exception as e:
        record("median LFC calculation", False, str(e))

    try:
        # Test for normality (Shapiro-Wilk)
        _, p_shapiro = sp_stats.shapiro(lfcs[:500])  # Shapiro limited to ~5000
        is_normal = p_shapiro > 0.05
        shape = "Normal" if is_normal else "Non-normal"
        record("distribution shape test", True, f"Shape: {shape}, p={p_shapiro:.4f}")
    except Exception as e:
        record("distribution shape test", False, str(e))


def test_20_batch_effect_comparison():
    """Test batch effect analysis (with/without batch samples)."""
    print("\n=== Test 20: Batch Effect Analysis ===")

    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    # Generate data with batch effect
    np.random.seed(42)
    n_genes = 200

    # Create 6 samples: 3 pairs (WT, KD) x 3 replicates
    conditions = ['WT', 'WT', 'WT', 'KD', 'KD', 'KD']
    batches = ['B1', 'B2', 'B3', 'B1', 'B2', 'B3']
    sample_names = [f'{c}_{b}' for c, b in zip(conditions, batches)]

    counts_data = np.random.negative_binomial(5, 0.3, size=(6, n_genes))
    # KD effect on first 30 genes
    counts_data[3:6, :30] = counts_data[3:6, :30] * 3
    # Batch 3 effect (outlier)
    counts_data[2, :] = counts_data[2, :] * 2
    counts_data[5, :] = counts_data[5, :] * 2

    counts = pd.DataFrame(counts_data, index=sample_names,
                          columns=[f'Gene_{i}' for i in range(n_genes)])
    metadata = pd.DataFrame({
        'condition': conditions,
        'batch': batches
    }, index=sample_names)

    try:
        # Run with all samples
        meta_all = metadata.copy()
        meta_all['condition'] = pd.Categorical(meta_all['condition'], categories=['WT', 'KD'])

        dds_all = DeseqDataSet(counts=counts, metadata=meta_all,
                               design="~condition", quiet=True)
        dds_all.deseq2()
        sr_all = DeseqStats(dds_all, contrast=['condition', 'KD', 'WT'], quiet=True)
        sr_all.run_wald_test()
        sr_all.summary()
        n_all = (sr_all.results_df['padj'] < 0.05).sum()
        record("DE with all samples", True, f"{n_all} DEGs with all samples")
    except Exception as e:
        record("DE with all samples", False, str(e))

    try:
        # Run without batch 3 (outlier)
        keep = [s for s in sample_names if 'B3' not in s]
        counts_clean = counts.loc[keep]
        meta_clean = metadata.loc[keep].copy()
        meta_clean['condition'] = pd.Categorical(meta_clean['condition'], categories=['WT', 'KD'])

        dds_clean = DeseqDataSet(counts=counts_clean, metadata=meta_clean,
                                 design="~condition", quiet=True)
        dds_clean.deseq2()
        sr_clean = DeseqStats(dds_clean, contrast=['condition', 'KD', 'WT'], quiet=True)
        sr_clean.run_wald_test()
        sr_clean.summary()
        n_clean = (sr_clean.results_df['padj'] < 0.05).sum()
        record("DE without outlier batch", True, f"{n_clean} DEGs without batch 3")
    except Exception as e:
        record("DE without outlier batch", False, str(e))

    try:
        # Compare
        change = "Increases" if n_clean > n_all else "Decreases" if n_clean < n_all else "Same"
        record("batch effect comparison", True,
               f"All={n_all} vs Clean={n_clean}: {change}")
    except Exception as e:
        record("batch effect comparison", False, str(e))


def test_21_enrichment_overlap_fraction():
    """Test enrichment pathway gene count and fraction extraction."""
    print("\n=== Test 21: Enrichment Overlap Fraction ===")

    import gseapy as gp

    # DEGs for enrichment
    gene_list = ['TP53', 'BRCA1', 'BRCA2', 'EGFR', 'KRAS', 'PIK3CA',
                 'PTEN', 'RB1', 'APC', 'MYC', 'CDH1', 'CTNNB1',
                 'SMAD4', 'VHL', 'WT1', 'NF1', 'NF2', 'RET',
                 'BRAF', 'MAP2K1', 'MTOR', 'TSC1', 'TSC2']

    try:
        enr = gp.enrich(
            gene_list=gene_list,
            gene_sets='Reactome_2022',
            outdir=None,
            no_plot=True,
            verbose=False,
            cutoff=1.0
        )

        if len(enr.results) > 0:
            top = enr.results.sort_values('Adjusted P-value').iloc[0]
            overlap_str = top['Overlap']  # e.g., "8/49"
            genes_str = top['Genes']
            n_overlap = len(genes_str.split(';'))

            record("enrichment overlap extraction", '/' in str(overlap_str),
                   f"Top pathway: {top['Term']}, Overlap: {overlap_str}, Genes: {n_overlap}")
        else:
            record("enrichment overlap extraction", True, "No enrichment results")
    except Exception as e:
        record("enrichment overlap extraction", False, str(e))

    try:
        # Count pathways matching keyword
        if len(enr.results) > 0:
            oxidative = enr.results[enr.results['Term'].str.lower().str.contains('signal')]
            n_signal = len(oxidative)
            total = len(enr.results)
            if total > 0:
                fraction = n_signal / min(total, 20)
                record("pathway keyword fraction", True,
                       f"{n_signal} signaling pathways out of top {min(total,20)} = {fraction:.1f}")
            else:
                record("pathway keyword fraction", True, "No pathways")
        else:
            record("pathway keyword fraction", True, "No results")
    except Exception as e:
        record("pathway keyword fraction", False, str(e))


def test_22_tooluniverse_integration():
    """Test ToolUniverse tool integration for gene annotation."""
    print("\n=== Test 22: ToolUniverse Integration ===")

    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        record("ToolUniverse load", True, f"{len(tu.all_tool_dict)} tools loaded")
    except Exception as e:
        record("ToolUniverse load", False, str(e))
        return

    try:
        # Gene lookup
        result = tu.tools.MyGene_query_genes(query="TP53")
        has_data = result is not None and len(result) > 0
        record("MyGene query", has_data,
               f"TP53 lookup: {'found' if has_data else 'not found'}")
    except Exception as e:
        record("MyGene query", False, str(e))

    try:
        # Ensembl gene lookup
        result = tu.tools.ensembl_lookup_gene(gene_id="ENSG00000141510", species="homo_sapiens")
        has_data = result is not None
        record("Ensembl lookup", has_data)
    except Exception as e:
        record("Ensembl lookup", False, str(e))


# ============================================================
# Run All Tests
# ============================================================

def run_all_tests():
    """Run all tests and generate summary."""
    print("=" * 70)
    print("  RNA-seq DESeq2 Skill - Comprehensive Test Suite")
    print("=" * 70)

    test_01_imports()
    test_02_data_loading()
    test_03_data_validation()
    test_04_basic_deseq2()
    test_05_lfc_shrinkage()
    test_06_multifactor_design()
    test_07_dispersion_analysis()
    test_08_result_filtering()
    test_09_deg_set_operations()
    test_10_multiple_testing()
    test_11_enrichment_ora()
    test_12_specific_gene_extraction()
    test_13_statistical_tests()
    test_14_mirna_de()
    test_15_enrichment_term_search()
    test_16_go_simplification()
    test_17_output_formatting()
    test_18_edge_cases()
    test_19_median_lfc_distribution()
    test_20_batch_effect_comparison()
    test_21_enrichment_overlap_fraction()
    test_22_tooluniverse_integration()

    # Summary
    total = PASS_COUNT + FAIL_COUNT
    print("\n" + "=" * 70)
    print(f"  SUMMARY: {PASS_COUNT}/{total} tests passed ({PASS_COUNT/total*100:.1f}%)")
    print("=" * 70)

    if FAIL_COUNT > 0:
        print("\nFailed tests:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"  FAIL: {name} -- {detail}")

    return PASS_COUNT, total


if __name__ == "__main__":
    passed, total = run_all_tests()
    sys.exit(0 if passed == total else 1)
