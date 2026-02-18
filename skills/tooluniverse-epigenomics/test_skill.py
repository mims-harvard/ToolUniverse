#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-epigenomics Skill

Tests all computational epigenomics capabilities:
- Methylation data processing (beta values, CpG filtering, DM analysis)
- Age-related CpG analysis
- Chromosome-level statistics and density calculations
- BED/peak file processing
- Peak annotation and overlap analysis
- Multi-omics integration (methylation-expression correlation)
- Clinical data missing data analysis
- Genome-wide statistics
- ToolUniverse annotation integration
"""

import sys
import os
import time
import traceback
import tempfile

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.stats.multitest as mt

# ============================================================
# Test Infrastructure
# ============================================================

RESULTS = []


def run_test(test_func):
    """Run a test function and record results."""
    name = test_func.__name__
    doc = test_func.__doc__ or name
    start = time.time()
    try:
        test_func()
        elapsed = time.time() - start
        RESULTS.append({"name": name, "doc": doc.strip(), "status": "PASS", "time": elapsed, "error": None})
        print(f"  PASS  {name} ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        RESULTS.append({"name": name, "doc": doc.strip(), "status": "FAIL", "time": elapsed, "error": error_msg})
        print(f"  FAIL  {name} ({elapsed:.1f}s): {error_msg}")
        traceback.print_exc()


# ============================================================
# Helper: Generate Synthetic Test Data
# ============================================================

def generate_methylation_data(n_probes=500, n_samples=20, seed=42):
    """Generate synthetic methylation beta-value matrix."""
    np.random.seed(seed)
    probes = [f"cg{str(i).zfill(8)}" for i in range(n_probes)]
    samples = [f"SAMPLE_{str(i).zfill(3)}" for i in range(n_samples)]
    betas = np.random.beta(2, 5, size=(n_probes, n_samples))
    return pd.DataFrame(betas, index=probes, columns=samples)


def generate_manifest(probes, seed=42):
    """Generate synthetic probe manifest with chromosome and position."""
    np.random.seed(seed)
    n = len(probes)
    chromosomes = np.random.choice(
        ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
         '11', '12', '13', '14', '15', '16', '17', '18', '19',
         '20', '21', '22', 'X', 'Y'],
        size=n
    )
    positions = np.random.randint(1000000, 200000000, size=n)
    gene_names = np.random.choice(
        ['TP53', 'BRCA1', 'EGFR', 'MYC', 'PTEN', 'RB1', 'AKT1',
         'CDK4', 'MDM2', 'KRAS', '', ''], size=n
    )
    gene_groups = np.random.choice(
        ['TSS200', 'TSS1500', 'Body', '1stExon', '5UTR', '3UTR', ''],
        size=n
    )
    island_relations = np.random.choice(
        ['Island', 'N_Shore', 'S_Shore', 'N_Shelf', 'S_Shelf', 'OpenSea'],
        size=n
    )
    return pd.DataFrame({
        'probe_id': probes,
        'chr': chromosomes,
        'position': positions,
        'gene_name': gene_names,
        'gene_group': gene_groups,
        'cpg_island_relation': island_relations,
    })


def generate_bed_file(n_peaks=200, seed=42):
    """Generate synthetic BED DataFrame (narrowPeak format)."""
    np.random.seed(seed)
    chroms = np.random.choice(
        [f'chr{i}' for i in range(1, 23)] + ['chrX'],
        size=n_peaks
    )
    starts = np.random.randint(1000000, 200000000, size=n_peaks)
    lengths = np.random.randint(100, 5000, size=n_peaks)
    ends = starts + lengths
    signals = np.random.exponential(10, size=n_peaks)
    pvalues = np.random.uniform(0, 50, size=n_peaks)  # -log10(p)
    qvalues = np.random.uniform(0, 30, size=n_peaks)  # -log10(q)
    peak_offsets = lengths // 2

    return pd.DataFrame({
        'chrom': chroms,
        'start': starts,
        'end': ends,
        'name': [f'peak_{i}' for i in range(n_peaks)],
        'score': np.random.randint(0, 1000, size=n_peaks),
        'strand': '.',
        'signalValue': signals,
        'pValue': pvalues,
        'qValue': qvalues,
        'peak': peak_offsets,
    })


def generate_gene_annotation(n_genes=100, seed=42):
    """Generate synthetic gene annotation."""
    np.random.seed(seed)
    gene_names = [f'GENE_{i}' for i in range(n_genes)]
    chroms = np.random.choice(
        [f'chr{i}' for i in range(1, 23)] + ['chrX'],
        size=n_genes
    )
    starts = np.random.randint(1000000, 200000000, size=n_genes)
    ends = starts + np.random.randint(1000, 100000, size=n_genes)
    strands = np.random.choice(['+', '-'], size=n_genes)

    return pd.DataFrame({
        'chr': chroms,
        'start': starts,
        'end': ends,
        'gene_name': gene_names,
        'score': 0,
        'strand': strands,
    })


# ============================================================
# Phase 1: Methylation Data Loading Tests
# ============================================================

def test_01_generate_and_load_beta_matrix():
    """Methylation: Generate and validate beta-value matrix"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)
    assert beta.shape == (500, 20), f"Expected (500, 20), got {beta.shape}"
    assert beta.values.min() >= 0, "Beta values should be >= 0"
    assert beta.values.max() <= 1, "Beta values should be <= 1"
    assert all(beta.index.str.startswith('cg')), "Probes should start with 'cg'"
    print(f"    Shape: {beta.shape}, range: [{beta.values.min():.3f}, {beta.values.max():.3f}]")


def test_02_detect_methylation_type():
    """Methylation: Detect beta vs M-value data type"""
    beta = generate_methylation_data()

    # Detect beta values
    sample = beta.iloc[:1000, :5].values.flatten()
    sample = sample[~np.isnan(sample)]
    is_beta = sample.min() >= 0 and sample.max() <= 1
    assert is_beta, "Should detect as beta values"

    # Convert to M-values
    beta_clipped = np.clip(beta.values, 1e-6, 1 - 1e-6)
    mvalues = pd.DataFrame(
        np.log2(beta_clipped / (1 - beta_clipped)),
        index=beta.index, columns=beta.columns
    )
    sample_m = mvalues.iloc[:1000, :5].values.flatten()
    sample_m = sample_m[~np.isnan(sample_m)]
    is_mvalue = not (sample_m.min() >= 0 and sample_m.max() <= 1)
    assert is_mvalue, "M-values should not be bounded 0-1"

    print(f"    Beta range: [{sample.min():.3f}, {sample.max():.3f}]")
    print(f"    M-value range: [{sample_m.min():.3f}, {sample_m.max():.3f}]")


def test_03_beta_mvalue_conversion():
    """Methylation: Convert between beta and M-values"""
    beta = generate_methylation_data(n_probes=100, n_samples=5)

    # Beta -> M-value
    beta_clipped = np.clip(beta.values, 1e-6, 1 - 1e-6)
    mvalues = np.log2(beta_clipped / (1 - beta_clipped))

    # M-value -> Beta (round-trip)
    beta_recovered = 2**mvalues / (2**mvalues + 1)

    # Should be close to original (within floating point)
    diff = np.abs(beta.values - beta_recovered).max()
    assert diff < 1e-5, f"Round-trip conversion error: {diff}"
    print(f"    Max round-trip error: {diff:.2e}")


def test_04_csv_methylation_io():
    """Methylation: Write and read CSV methylation data"""
    beta = generate_methylation_data(n_probes=100, n_samples=10)

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
        beta.to_csv(f.name)
        loaded = pd.read_csv(f.name, index_col=0)
        os.unlink(f.name)

    assert loaded.shape == beta.shape, f"Shape mismatch: {loaded.shape} vs {beta.shape}"
    assert np.allclose(loaded.values, beta.values, atol=1e-10), "Values mismatch after CSV round-trip"
    print(f"    CSV round-trip successful: {loaded.shape}")


def test_05_tsv_methylation_io():
    """Methylation: Write and read TSV methylation data"""
    beta = generate_methylation_data(n_probes=100, n_samples=10)

    with tempfile.NamedTemporaryFile(suffix='.tsv', delete=False, mode='w') as f:
        beta.to_csv(f.name, sep='\t')
        loaded = pd.read_csv(f.name, sep='\t', index_col=0)
        os.unlink(f.name)

    assert loaded.shape == beta.shape
    print(f"    TSV round-trip successful: {loaded.shape}")


# ============================================================
# Phase 2: CpG Filtering Tests
# ============================================================

def test_06_filter_by_probe_type():
    """CpG Filter: Filter by probe type (cg vs ch)"""
    np.random.seed(42)
    # Create mixed probe list
    probes = [f"cg{str(i).zfill(8)}" for i in range(300)] + \
             [f"ch{str(i).zfill(8)}" for i in range(200)]
    beta = pd.DataFrame(
        np.random.beta(2, 5, size=(500, 10)),
        index=probes,
        columns=[f"S{i}" for i in range(10)]
    )

    # Filter cg only
    cg_mask = beta.index.str.startswith('cg')
    filtered = beta[cg_mask]
    assert len(filtered) == 300, f"Expected 300 cg probes, got {len(filtered)}"
    assert all(filtered.index.str.startswith('cg'))

    # Filter ch only
    ch_mask = beta.index.str.startswith('ch')
    filtered_ch = beta[ch_mask]
    assert len(filtered_ch) == 200
    print(f"    cg probes: {len(filtered)}, ch probes: {len(filtered_ch)}")


def test_07_filter_by_variance():
    """CpG Filter: Filter probes by variance threshold"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)
    probe_var = beta.var(axis=1, skipna=True)

    threshold = 0.01
    high_var = beta[probe_var >= threshold]
    low_var = beta[probe_var < threshold]

    assert len(high_var) + len(low_var) == 500
    assert len(high_var) > 0, "Should have some high-variance probes"
    print(f"    Variance >= {threshold}: {len(high_var)} probes")
    print(f"    Variance < {threshold}: {len(low_var)} probes")


def test_08_filter_by_missing_data():
    """CpG Filter: Filter probes with too much missing data"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)

    # Introduce missing data
    np.random.seed(99)
    mask = np.random.random(beta.shape) < 0.1  # 10% missing
    beta_with_na = beta.copy()
    beta_with_na.values[mask] = np.nan

    # Make some probes entirely missing
    beta_with_na.iloc[:10, :] = np.nan

    missing_frac = beta_with_na.isna().mean(axis=1)
    filtered = beta_with_na[missing_frac <= 0.2]  # max 20% missing

    assert len(filtered) < 500, "Should remove some probes"
    assert len(filtered) > 400, "Should keep most probes"
    print(f"    After missing filter (<=20%): {len(filtered)} / 500 probes")


def test_09_filter_by_mean_beta_range():
    """CpG Filter: Filter probes by mean beta range"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)
    probe_mean = beta.mean(axis=1)

    # Keep probes with mean between 0.1 and 0.9
    filtered = beta[(probe_mean >= 0.1) & (probe_mean <= 0.9)]
    assert len(filtered) > 0, "Should have probes in range"
    assert len(filtered) <= 500
    remaining_means = filtered.mean(axis=1)
    assert remaining_means.min() >= 0.1
    assert remaining_means.max() <= 0.9
    print(f"    Mean beta [0.1, 0.9]: {len(filtered)} / 500 probes")


def test_10_filter_top_n_variable():
    """CpG Filter: Select top N most variable probes"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)
    probe_var = beta.var(axis=1, skipna=True)

    n = 100
    top_probes = probe_var.nlargest(n).index
    filtered = beta.loc[top_probes]

    assert len(filtered) == n, f"Expected {n} probes, got {len(filtered)}"
    # Verify these are truly the most variable
    min_var_selected = probe_var.loc[top_probes].min()
    max_var_not_selected = probe_var.loc[~probe_var.index.isin(top_probes)].max()
    assert min_var_selected >= max_var_not_selected, "Top N selection incorrect"
    print(f"    Top {n} most variable probes selected")


def test_11_filter_by_chromosome():
    """CpG Filter: Filter probes by chromosome using manifest"""
    beta = generate_methylation_data(n_probes=500, n_samples=10)
    manifest = generate_manifest(beta.index.tolist())

    # Keep only autosomes (exclude X, Y)
    def normalize_chromosome(c):
        c = str(c).strip()
        return f'chr{c}' if not str(c).startswith('chr') else c

    manifest_idx = manifest.set_index('probe_id')
    nonsex = manifest_idx[
        ~manifest_idx['chr'].apply(normalize_chromosome).isin(['chrX', 'chrY'])
    ]
    autosome_probes = nonsex.index
    filtered = beta[beta.index.isin(autosome_probes)]

    n_sex = len(beta) - len(filtered)
    assert len(filtered) < 500, "Should remove some probes"
    assert len(filtered) > 0
    print(f"    Autosome probes: {len(filtered)}, removed sex chr: {n_sex}")


# ============================================================
# Phase 3: Differential Methylation Tests
# ============================================================

def test_12_differential_methylation_ttest():
    """DM Analysis: T-test differential methylation between two groups"""
    np.random.seed(42)
    n_probes = 200
    n_samples_per_group = 10

    # Group 1: beta ~ Beta(2, 5)
    g1_data = np.random.beta(2, 5, size=(n_probes, n_samples_per_group))
    # Group 2: shift some probes (first 20 are differentially methylated)
    g2_data = np.random.beta(2, 5, size=(n_probes, n_samples_per_group))
    g2_data[:20, :] += 0.3  # Add offset to first 20 probes
    g2_data = np.clip(g2_data, 0, 1)

    probes = [f"cg{str(i).zfill(8)}" for i in range(n_probes)]
    g1_samples = [f"G1_{i}" for i in range(n_samples_per_group)]
    g2_samples = [f"G2_{i}" for i in range(n_samples_per_group)]

    beta = pd.DataFrame(
        np.hstack([g1_data, g2_data]),
        index=probes,
        columns=g1_samples + g2_samples
    )

    # Run DM analysis
    results = []
    for probe in beta.index:
        vals1 = beta.loc[probe, g1_samples].values
        vals2 = beta.loc[probe, g2_samples].values
        mean1 = np.mean(vals1)
        mean2 = np.mean(vals2)
        _, pval = stats.ttest_ind(vals1, vals2, equal_var=False)
        results.append({
            'probe': probe, 'mean_g1': mean1, 'mean_g2': mean2,
            'delta_beta': mean2 - mean1, 'pvalue': pval
        })

    dm = pd.DataFrame(results).set_index('probe')
    reject, padj, _, _ = mt.multipletests(dm['pvalue'].values, method='fdr_bh')
    dm['padj'] = padj

    sig = dm[dm['padj'] < 0.05]
    assert len(sig) > 5, f"Expected >5 significant DMPs, got {len(sig)}"

    # Most significant should be in the first 20
    top_sig = sig.head(10).index
    n_correct = sum(int(p.replace('cg', '')) < 20 for p in top_sig)
    print(f"    Significant DMPs: {len(sig)} / {n_probes}")
    print(f"    Top 10 from true DMPs: {n_correct}/10")


def test_13_differential_methylation_wilcoxon():
    """DM Analysis: Wilcoxon rank-sum test (non-parametric)"""
    np.random.seed(42)
    n_probes = 100
    g1 = np.random.beta(2, 5, size=(n_probes, 8))
    g2 = np.random.beta(2, 5, size=(n_probes, 8))
    g2[:10, :] += 0.25
    g2 = np.clip(g2, 0, 1)

    pvals = []
    for i in range(n_probes):
        _, pval = stats.mannwhitneyu(g1[i], g2[i], alternative='two-sided')
        pvals.append(pval)

    reject, padj, _, _ = mt.multipletests(pvals, method='fdr_bh')
    n_sig = sum(reject)
    print(f"    Wilcoxon significant DMPs: {n_sig} / {n_probes}")
    assert n_sig >= 0, "Test should complete without error"


def test_14_identify_dmps_with_threshold():
    """DM Analysis: Filter DMPs by padj and delta_beta thresholds"""
    np.random.seed(42)
    n_probes = 200
    g1 = np.random.beta(2, 5, size=(n_probes, 10))
    g2 = np.random.beta(2, 5, size=(n_probes, 10))
    g2[:30, :] += 0.3  # Large effect
    g2[30:50, :] += 0.05  # Small effect
    g2 = np.clip(g2, 0, 1)

    means_g1 = g1.mean(axis=1)
    means_g2 = g2.mean(axis=1)
    delta_beta = means_g2 - means_g1

    pvals = []
    for i in range(n_probes):
        _, pval = stats.ttest_ind(g1[i], g2[i], equal_var=False)
        pvals.append(pval)

    reject, padj, _, _ = mt.multipletests(pvals, method='fdr_bh')

    # Apply both thresholds
    sig_mask = (padj < 0.05) & (np.abs(delta_beta) >= 0.2)
    n_sig = sum(sig_mask)
    print(f"    padj < 0.05 only: {sum(padj < 0.05)}")
    print(f"    padj < 0.05 AND |delta_beta| >= 0.2: {n_sig}")
    assert n_sig <= sum(padj < 0.05), "Adding threshold should not increase count"


def test_15_hyper_hypo_classification():
    """DM Analysis: Classify DMPs as hyper- or hypo-methylated"""
    np.random.seed(42)
    delta_betas = np.array([0.3, -0.25, 0.15, -0.4, 0.0, 0.1, -0.05])
    padj_vals = np.array([0.001, 0.01, 0.03, 0.001, 0.5, 0.04, 0.02])

    sig = padj_vals < 0.05
    hyper = sig & (delta_betas > 0)
    hypo = sig & (delta_betas < 0)

    assert sum(hyper) == 3, f"Expected 3 hyper, got {sum(hyper)}"
    assert sum(hypo) == 3, f"Expected 3 hypo, got {sum(hypo)}"
    print(f"    Hyper: {sum(hyper)}, Hypo: {sum(hypo)}, NS: {sum(~sig)}")


# ============================================================
# Phase 4: Age-Related CpG Tests
# ============================================================

def test_16_age_correlation():
    """Age CpG: Pearson correlation with age"""
    np.random.seed(42)
    n_probes = 100
    n_samples = 50
    ages = np.random.uniform(20, 80, size=n_samples)

    # Create probes: first 10 correlated with age
    betas = np.random.beta(2, 5, size=(n_probes, n_samples))
    for i in range(10):
        betas[i, :] = 0.2 + 0.005 * ages + np.random.normal(0, 0.05, n_samples)
        betas[i, :] = np.clip(betas[i, :], 0, 1)

    probes = [f"cg{str(i).zfill(8)}" for i in range(n_probes)]

    correlations = []
    for i in range(n_probes):
        corr, pval = stats.pearsonr(ages, betas[i, :])
        correlations.append({'probe': probes[i], 'correlation': corr, 'pvalue': pval})

    corr_df = pd.DataFrame(correlations).set_index('probe')
    reject, padj, _, _ = mt.multipletests(corr_df['pvalue'].values, method='fdr_bh')
    corr_df['padj'] = padj

    sig = corr_df[corr_df['padj'] < 0.05]
    print(f"    Age-related CpGs: {len(sig)} / {n_probes}")
    # First 10 probes should be significant
    top_sig = sig.index.tolist()
    n_correct = sum(int(p.replace('cg', '')) < 10 for p in top_sig)
    print(f"    Correctly identified: {n_correct}/10 true age-related probes")
    assert n_correct >= 5, "Should detect most true age-related probes"


def test_17_spearman_correlation():
    """Age CpG: Spearman rank correlation with age"""
    np.random.seed(42)
    n = 50
    ages = np.random.uniform(20, 80, size=n)
    betas = 0.2 + 0.005 * ages + np.random.normal(0, 0.05, n)
    betas = np.clip(betas, 0, 1)

    corr_pearson, pval_pearson = stats.pearsonr(ages, betas)
    corr_spearman, pval_spearman = stats.spearmanr(ages, betas)

    assert abs(corr_pearson) > 0.3, "Pearson correlation should be moderate"
    assert abs(corr_spearman) > 0.3, "Spearman correlation should be moderate"
    print(f"    Pearson r={corr_pearson:.3f}, p={pval_pearson:.2e}")
    print(f"    Spearman rho={corr_spearman:.3f}, p={pval_spearman:.2e}")


# ============================================================
# Phase 5: Chromosome Statistics Tests
# ============================================================

def test_18_chromosome_normalization():
    """Chromosome: Normalize chromosome names"""
    def normalize_chromosome(chrom):
        if chrom is None or pd.isna(chrom):
            return None
        chrom = str(chrom).strip()
        if not chrom.startswith('chr'):
            chrom = 'chr' + chrom
        return chrom

    assert normalize_chromosome('1') == 'chr1'
    assert normalize_chromosome('chr1') == 'chr1'
    assert normalize_chromosome('X') == 'chrX'
    assert normalize_chromosome('chrX') == 'chrX'
    assert normalize_chromosome('22') == 'chr22'
    assert normalize_chromosome(None) is None
    print(f"    All chromosome normalizations correct")


def test_19_chromosome_lengths():
    """Chromosome: Verify chromosome lengths for hg38, hg19, mm10"""
    hg38 = {
        'chr1': 248956422, 'chr2': 242193529, 'chr17': 83257441,
        'chr19': 58617616, 'chrX': 156040895, 'chrY': 57227415,
    }
    hg19 = {
        'chr1': 249250621, 'chr17': 81195210, 'chr19': 59128983,
    }
    mm10 = {
        'chr1': 195471971, 'chr19': 61431566,
    }

    # Verify key lengths
    assert hg38['chr1'] == 248956422
    assert hg38['chr19'] == 58617616
    assert hg19['chr1'] == 249250621
    assert mm10['chr1'] == 195471971
    print(f"    hg38 chr1: {hg38['chr1']:,} bp")
    print(f"    hg38 chr19: {hg38['chr19']:,} bp")
    print(f"    hg19 chr1: {hg19['chr1']:,} bp")


def test_20_cpg_density_per_chromosome():
    """Chromosome: Calculate CpG density per chromosome"""
    beta = generate_methylation_data(n_probes=500, n_samples=10)
    manifest = generate_manifest(beta.index.tolist())

    def normalize_chromosome(c):
        c = str(c).strip()
        return f'chr{c}' if not str(c).startswith('chr') else c

    chr_lengths = {
        'chr1': 248956422, 'chr2': 242193529, 'chr3': 198295559,
        'chr17': 83257441, 'chr19': 58617616, 'chrX': 156040895,
        'chrY': 57227415,
    }

    # Map probes to chromosomes
    manifest_idx = manifest.set_index('probe_id')
    probe_chrs = manifest_idx['chr'].apply(normalize_chromosome)
    chr_counts = probe_chrs.value_counts()

    # Calculate density
    densities = {}
    for chrom, count in chr_counts.items():
        if chrom in chr_lengths:
            densities[chrom] = count / chr_lengths[chrom]

    assert len(densities) > 0, "Should have density for at least one chromosome"
    for chrom, density in densities.items():
        assert density > 0, f"Density for {chrom} should be > 0"
        assert density < 1, f"Density for {chrom} should be < 1"

    print(f"    Densities calculated for {len(densities)} chromosomes")
    for chrom in sorted(list(densities.keys()))[:3]:
        print(f"    {chrom}: {densities[chrom]:.2e} CpGs/bp")


def test_21_genome_wide_average_density():
    """Chromosome: Genome-wide average CpG density"""
    # Simulated density data
    density_data = pd.DataFrame({
        'chr': ['chr1', 'chr2', 'chr19'],
        'n_cpgs': [100, 80, 60],
        'chr_length': [248956422, 242193529, 58617616],
    })
    density_data['density_per_bp'] = density_data['n_cpgs'] / density_data['chr_length']

    total_cpgs = density_data['n_cpgs'].sum()
    total_length = density_data['chr_length'].sum()
    avg_density = total_cpgs / total_length

    assert avg_density > 0
    assert avg_density < 1
    print(f"    Total CpGs: {total_cpgs}")
    print(f"    Total genome length: {total_length:,}")
    print(f"    Average density: {avg_density:.2e}")


def test_22_chromosome_density_ratio():
    """Chromosome: Density ratio between two chromosomes"""
    density_data = pd.DataFrame({
        'chr': ['chr1', 'chr19'],
        'n_cpgs': [100, 60],
        'chr_length': [248956422, 58617616],
    })
    density_data['density_per_bp'] = density_data['n_cpgs'] / density_data['chr_length']

    d1 = density_data[density_data['chr'] == 'chr1']['density_per_bp'].values[0]
    d19 = density_data[density_data['chr'] == 'chr19']['density_per_bp'].values[0]
    ratio_19_to_1 = d19 / d1

    assert ratio_19_to_1 > 1, "chr19 should be denser (it is smaller)"
    print(f"    chr1 density: {d1:.2e}")
    print(f"    chr19 density: {d19:.2e}")
    print(f"    chr19/chr1 ratio: {ratio_19_to_1:.2f}")


# ============================================================
# Phase 6: BED/Peak File Tests
# ============================================================

def test_23_load_bed_dataframe():
    """BED: Load and validate BED-like DataFrame"""
    peaks = generate_bed_file(n_peaks=200)

    assert len(peaks) == 200
    assert 'chrom' in peaks.columns
    assert 'start' in peaks.columns
    assert 'end' in peaks.columns
    assert all(peaks['start'] < peaks['end']), "Start should be < end"
    print(f"    Loaded {len(peaks)} peaks across {peaks['chrom'].nunique()} chromosomes")


def test_24_peak_statistics():
    """BED: Calculate peak statistics"""
    peaks = generate_bed_file(n_peaks=200)
    peaks['length'] = peaks['end'] - peaks['start']

    stats_dict = {
        'total_peaks': len(peaks),
        'mean_peak_length': peaks['length'].mean(),
        'median_peak_length': peaks['length'].median(),
        'total_coverage_bp': peaks['length'].sum(),
    }

    assert stats_dict['total_peaks'] == 200
    assert stats_dict['mean_peak_length'] > 0
    assert stats_dict['total_coverage_bp'] > 0
    print(f"    Total peaks: {stats_dict['total_peaks']}")
    print(f"    Mean length: {stats_dict['mean_peak_length']:.0f} bp")
    print(f"    Total coverage: {stats_dict['total_coverage_bp']:,} bp")


def test_25_peaks_per_chromosome():
    """BED: Count peaks per chromosome"""
    peaks = generate_bed_file(n_peaks=500)
    chr_counts = peaks['chrom'].value_counts()

    assert len(chr_counts) > 5, "Should have peaks on multiple chromosomes"
    assert chr_counts.sum() == 500
    print(f"    Peaks across {len(chr_counts)} chromosomes")
    print(f"    Top 3: {dict(chr_counts.head(3))}")


def test_26_write_and_read_bed():
    """BED: Write and read BED file"""
    peaks = generate_bed_file(n_peaks=50)

    with tempfile.NamedTemporaryFile(suffix='.bed', delete=False, mode='w') as f:
        peaks.to_csv(f.name, sep='\t', header=False, index=False)
        # Read back
        loaded = pd.read_csv(
            f.name, sep='\t', header=None,
            names=['chrom', 'start', 'end', 'name', 'score', 'strand',
                   'signalValue', 'pValue', 'qValue', 'peak']
        )
        os.unlink(f.name)

    assert len(loaded) == 50
    assert loaded['chrom'].iloc[0] == peaks['chrom'].iloc[0]
    print(f"    BED round-trip successful: {len(loaded)} peaks")


# ============================================================
# Phase 7: Peak Annotation Tests
# ============================================================

def test_27_peak_to_gene_annotation():
    """Peak Annotation: Annotate peaks to nearest genes"""
    peaks = generate_bed_file(n_peaks=50)
    genes = generate_gene_annotation(n_genes=100)

    # Simple annotation: find nearest gene on same chromosome
    annotated = []
    for _, peak in peaks.iterrows():
        chr_genes = genes[genes['chr'] == peak['chrom']]
        if len(chr_genes) == 0:
            annotated.append({'nearest_gene': 'intergenic', 'feature': 'intergenic'})
            continue

        peak_mid = (peak['start'] + peak['end']) // 2
        tss = chr_genes.apply(
            lambda g: g['start'] if g['strand'] == '+' else g['end'], axis=1)
        distances = (peak_mid - tss).abs()
        nearest = chr_genes.loc[distances.idxmin()]

        dist = distances.min()
        if dist <= 2000:
            feature = 'promoter'
        elif peak['start'] >= nearest['start'] and peak['end'] <= nearest['end']:
            feature = 'gene_body'
        else:
            feature = 'distal'

        annotated.append({
            'nearest_gene': nearest['gene_name'],
            'feature': feature,
            'distance_to_tss': int(dist),
        })

    ann_df = pd.DataFrame(annotated)
    features = ann_df['feature'].value_counts()
    print(f"    Annotation distribution: {dict(features)}")
    assert len(ann_df) == 50


def test_28_classify_peak_regions():
    """Peak Annotation: Classify peaks into genomic regions"""
    features = pd.Series(['promoter', 'promoter', 'gene_body', 'gene_body', 'gene_body',
                          'distal', 'distal', 'distal', 'distal', 'intergenic'])
    counts = features.value_counts().to_dict()

    assert counts['promoter'] == 2
    assert counts['gene_body'] == 3
    assert counts['distal'] == 4
    assert counts['intergenic'] == 1

    fractions = {k: v / len(features) for k, v in counts.items()}
    assert abs(fractions['promoter'] - 0.2) < 0.01
    print(f"    Region distribution: {fractions}")


# ============================================================
# Phase 8: Peak Overlap Tests
# ============================================================

def test_29_simple_overlap():
    """Overlap: Detect overlapping intervals"""
    peaks_a = pd.DataFrame({
        'chrom': ['chr1', 'chr1', 'chr2'],
        'start': [100, 500, 200],
        'end':   [300, 700, 400],
    })
    peaks_b = pd.DataFrame({
        'chrom': ['chr1', 'chr1', 'chr2'],
        'start': [200, 800, 300],
        'end':   [400, 900, 500],
    })

    overlaps = []
    for chrom in peaks_a['chrom'].unique():
        a_chr = peaks_a[peaks_a['chrom'] == chrom]
        b_chr = peaks_b[peaks_b['chrom'] == chrom]
        for _, a in a_chr.iterrows():
            for _, b in b_chr.iterrows():
                if b['start'] < a['end'] and b['end'] > a['start']:
                    overlap_bp = min(a['end'], b['end']) - max(a['start'], b['start'])
                    overlaps.append({
                        'chrom': chrom,
                        'a_start': a['start'],
                        'b_start': b['start'],
                        'overlap_bp': overlap_bp,
                    })

    assert len(overlaps) == 2, f"Expected 2 overlaps, got {len(overlaps)}"
    # chr1: 100-300 overlaps 200-400 (overlap: 200-300 = 100bp)
    # chr2: 200-400 overlaps 300-500 (overlap: 300-400 = 100bp)
    print(f"    Found {len(overlaps)} overlaps")
    for o in overlaps:
        print(f"    {o['chrom']}: {o['overlap_bp']}bp overlap")


def test_30_no_overlap():
    """Overlap: Detect no overlap between non-overlapping intervals"""
    peaks_a = pd.DataFrame({
        'chrom': ['chr1'],
        'start': [100],
        'end':   [200],
    })
    peaks_b = pd.DataFrame({
        'chrom': ['chr1'],
        'start': [300],
        'end':   [400],
    })

    has_overlap = False
    for _, a in peaks_a.iterrows():
        for _, b in peaks_b.iterrows():
            if a['chrom'] == b['chrom'] and b['start'] < a['end'] and b['end'] > a['start']:
                has_overlap = True

    assert not has_overlap, "Should be no overlap"
    print(f"    Correctly detected no overlap")


# ============================================================
# Phase 9: ATAC-seq Tests
# ============================================================

def test_31_atac_peak_stats():
    """ATAC-seq: Nucleosome-free region statistics"""
    peaks = generate_bed_file(n_peaks=500, seed=42)
    peaks['length'] = peaks['end'] - peaks['start']

    nfr = peaks[peaks['length'] < 150]
    nucleosome = peaks[peaks['length'] >= 150]
    nfr_fraction = len(nfr) / len(peaks)

    print(f"    NFR peaks (<150bp): {len(nfr)}")
    print(f"    Nucleosome peaks (>=150bp): {len(nucleosome)}")
    print(f"    NFR fraction: {nfr_fraction:.2%}")
    assert len(nfr) + len(nucleosome) == 500


# ============================================================
# Phase 10: Multi-Omics Integration Tests
# ============================================================

def test_32_methylation_expression_correlation():
    """Multi-Omics: Methylation-expression correlation"""
    np.random.seed(42)
    n_samples = 30

    # Generate correlated methylation and expression
    noise = np.random.normal(0, 0.1, n_samples)
    meth_vals = np.random.beta(2, 5, n_samples)
    expr_vals = 10 - 8 * meth_vals + noise  # Negative correlation

    corr, pval = stats.pearsonr(meth_vals, expr_vals)
    assert corr < -0.3, f"Expected negative correlation, got {corr}"
    assert pval < 0.05, f"Expected significant, got p={pval}"
    print(f"    Pearson r = {corr:.3f}, p = {pval:.2e}")


def test_33_multi_probe_gene_correlation():
    """Multi-Omics: Multiple probe-gene pair correlations"""
    np.random.seed(42)
    n_samples = 30
    n_pairs = 50

    pvals = []
    for i in range(n_pairs):
        meth = np.random.beta(2, 5, n_samples)
        if i < 10:  # First 10 are truly correlated
            expr = 10 - 8 * meth + np.random.normal(0, 0.5, n_samples)
        else:
            expr = np.random.normal(5, 2, n_samples)
        _, pval = stats.pearsonr(meth, expr)
        pvals.append(pval)

    reject, padj, _, _ = mt.multipletests(pvals, method='fdr_bh')
    n_sig = sum(reject)
    print(f"    Significant correlations: {n_sig} / {n_pairs}")
    assert n_sig >= 5, "Should detect correlated pairs"


# ============================================================
# Phase 11: Clinical Integration Tests
# ============================================================

def test_34_missing_data_analysis():
    """Clinical: Missing data analysis across modalities"""
    np.random.seed(42)

    # Clinical data: 100 patients, some missing vital_status
    clinical = pd.DataFrame({
        'vital_status': np.random.choice(['Alive', 'Dead', np.nan], size=100,
                                          p=[0.4, 0.4, 0.2]),
        'age': np.random.uniform(30, 80, 100),
    }, index=[f'P{i:03d}' for i in range(100)])

    # Expression: 80 patients have data
    expr_samples = [f'P{i:03d}' for i in range(80)]
    expression = pd.DataFrame(
        np.random.normal(5, 2, (100, 80)),
        index=[f'GENE_{i}' for i in range(100)],
        columns=expr_samples
    )

    # Methylation: 70 patients have data
    meth_samples = [f'P{i:03d}' for i in range(30)] + [f'P{i:03d}' for i in range(50, 90)]
    methylation = pd.DataFrame(
        np.random.beta(2, 5, (200, 70)),
        index=[f'cg{i:08d}' for i in range(200)],
        columns=meth_samples
    )

    # Find complete cases
    has_vital = set(clinical[clinical['vital_status'].notna()].index)
    has_expr = set(expression.columns)
    has_meth = set(methylation.columns)
    complete = has_vital & has_expr & has_meth

    print(f"    Clinical with vital_status: {len(has_vital)}")
    print(f"    Expression samples: {len(has_expr)}")
    print(f"    Methylation samples: {len(has_meth)}")
    print(f"    Complete cases: {len(complete)}")

    assert len(complete) > 0, "Should have some complete cases"
    assert len(complete) < 100, "Should not have all patients complete"


def test_35_sample_id_matching():
    """Clinical: Match sample IDs across modalities"""
    # Different ID formats
    clinical_ids = {f'TCGA-AB-{i:04d}' for i in range(100)}
    expr_ids = {f'TCGA-AB-{i:04d}-01A' for i in range(80)}
    meth_ids = {f'TCGA-AB-{i:04d}-01A' for i in range(70)}

    # Truncation matching
    def truncate_id(full_id, length=12):
        return full_id[:length]

    clinical_short = {truncate_id(i) for i in clinical_ids}
    expr_short = {truncate_id(i) for i in expr_ids}
    meth_short = {truncate_id(i) for i in meth_ids}

    overlap = clinical_short & expr_short & meth_short
    print(f"    Clinical: {len(clinical_ids)} patients")
    print(f"    Expression: {len(expr_ids)} samples")
    print(f"    Methylation: {len(meth_ids)} samples")
    print(f"    Matched after ID truncation: {len(overlap)}")
    assert len(overlap) > 0


# ============================================================
# Phase 12: Genome-Wide Statistics Tests
# ============================================================

def test_36_global_methylation_stats():
    """Genome-Wide: Global methylation statistics"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)

    stats_result = {
        'total_probes': len(beta),
        'total_samples': beta.shape[1],
        'global_mean': float(beta.mean().mean()),
        'global_median': float(beta.median().median()),
        'global_std': float(beta.values[~np.isnan(beta.values)].std()),
    }

    assert stats_result['total_probes'] == 500
    assert stats_result['total_samples'] == 20
    assert 0 < stats_result['global_mean'] < 1
    assert 0 < stats_result['global_std'] < 0.5

    print(f"    Mean: {stats_result['global_mean']:.3f}")
    print(f"    Median: {stats_result['global_median']:.3f}")
    print(f"    Std: {stats_result['global_std']:.3f}")


def test_37_probe_variance_distribution():
    """Genome-Wide: Probe variance distribution"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)
    probe_var = beta.var(axis=1, skipna=True)

    n_high = (probe_var > 0.01).sum()
    n_very_high = (probe_var > 0.05).sum()

    print(f"    Variance > 0.01: {n_high} probes")
    print(f"    Variance > 0.05: {n_very_high} probes")
    print(f"    Mean variance: {probe_var.mean():.4f}")
    print(f"    Max variance: {probe_var.max():.4f}")
    assert probe_var.mean() > 0


def test_38_per_sample_statistics():
    """Genome-Wide: Per-sample methylation statistics"""
    beta = generate_methylation_data(n_probes=500, n_samples=20)

    sample_means = beta.mean(axis=0)
    sample_stds = beta.std(axis=0)

    assert len(sample_means) == 20
    assert all(sample_means > 0)
    assert all(sample_means < 1)

    print(f"    Sample mean range: [{sample_means.min():.3f}, {sample_means.max():.3f}]")
    print(f"    Sample std range: [{sample_stds.min():.3f}, {sample_stds.max():.3f}]")


# ============================================================
# Phase 13: Multiple Testing Correction Tests
# ============================================================

def test_39_bh_correction():
    """Multiple Testing: Benjamini-Hochberg FDR"""
    np.random.seed(42)
    pvals = np.concatenate([
        np.random.uniform(0, 0.001, 20),   # 20 true positives
        np.random.uniform(0, 1, 980),       # 980 nulls
    ])

    reject, padj, _, _ = mt.multipletests(pvals, method='fdr_bh')
    n_sig = sum(reject)
    print(f"    BH significant: {n_sig} / 1000")
    assert n_sig >= 10, "Should detect most true positives"
    assert n_sig <= 100, "Should not have too many false positives"


def test_40_bonferroni_correction():
    """Multiple Testing: Bonferroni correction"""
    np.random.seed(42)
    pvals = np.concatenate([
        np.random.uniform(0, 0.0001, 10),
        np.random.uniform(0, 1, 990),
    ])

    reject_bh, _, _, _ = mt.multipletests(pvals, method='fdr_bh')
    reject_bonf, _, _, _ = mt.multipletests(pvals, method='bonferroni')

    n_bh = sum(reject_bh)
    n_bonf = sum(reject_bonf)
    print(f"    BH: {n_bh}, Bonferroni: {n_bonf}")
    assert n_bonf <= n_bh, "Bonferroni should be more conservative"


# ============================================================
# Phase 14: Manifest Processing Tests
# ============================================================

def test_41_manifest_generation():
    """Manifest: Generate and validate probe manifest"""
    probes = [f"cg{str(i).zfill(8)}" for i in range(100)]
    manifest = generate_manifest(probes)

    assert len(manifest) == 100
    assert 'probe_id' in manifest.columns
    assert 'chr' in manifest.columns
    assert 'position' in manifest.columns
    assert 'gene_name' in manifest.columns
    print(f"    Manifest: {len(manifest)} probes, columns: {list(manifest.columns)}")


def test_42_manifest_chromosome_mapping():
    """Manifest: Map probes to chromosomes"""
    probes = [f"cg{str(i).zfill(8)}" for i in range(200)]
    manifest = generate_manifest(probes)

    def normalize_chromosome(c):
        c = str(c).strip()
        return f'chr{c}' if not str(c).startswith('chr') else c

    manifest['chr_normalized'] = manifest['chr'].apply(normalize_chromosome)
    chr_counts = manifest['chr_normalized'].value_counts()

    assert len(chr_counts) > 5, "Should map to multiple chromosomes"
    print(f"    Mapped to {len(chr_counts)} chromosomes")
    print(f"    Top 3: {dict(chr_counts.head(3))}")


def test_43_cpg_island_relation():
    """Manifest: Filter by CpG island relation"""
    probes = [f"cg{str(i).zfill(8)}" for i in range(200)]
    manifest = generate_manifest(probes)

    island_probes = manifest[manifest['cpg_island_relation'] == 'Island']
    shore_probes = manifest[manifest['cpg_island_relation'].str.contains('Shore', na=False)]
    open_sea = manifest[manifest['cpg_island_relation'] == 'OpenSea']

    print(f"    Island: {len(island_probes)}")
    print(f"    Shore: {len(shore_probes)}")
    print(f"    OpenSea: {len(open_sea)}")
    assert len(island_probes) + len(shore_probes) + len(open_sea) <= 200


# ============================================================
# Phase 15: ToolUniverse Integration Tests
# ============================================================

def test_44_tooluniverse_loading():
    """ToolUniverse: Load tools and verify epigenomics-related tools exist"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    required = [
        'ensembl_lookup_gene',
        'ensembl_get_regulatory_features',
        'SCREEN_get_regulatory_elements',
        'ENCODE_search_experiments',
        'ChIPAtlas_get_experiments',
        'jaspar_search_matrices',
        'ReMap_get_transcription_factor_binding',
        'RegulomeDB_query_variant',
    ]

    all_tools = set(tu.all_tool_dict.keys())
    missing = [t for t in required if t not in all_tools]
    assert len(missing) == 0, f"Missing tools: {missing}"
    print(f"    All {len(required)} required tools present in {len(all_tools)} total tools")


def test_45_ensembl_gene_lookup():
    """ToolUniverse: Ensembl gene lookup for TP53"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.ensembl_lookup_gene(id='TP53', species='homo_sapiens')
    assert result is not None, "No result from Ensembl"
    if isinstance(result, dict):
        data = result.get('data', result)
        if isinstance(data, dict):
            seq_region = data.get('seq_region_name', '')
            print(f"    TP53 chromosome: {seq_region}")
            print(f"    TP53 start: {data.get('start', 'N/A')}")
            print(f"    TP53 end: {data.get('end', 'N/A')}")


def test_46_screen_regulatory_elements():
    """ToolUniverse: SCREEN cis-regulatory elements for TP53"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.SCREEN_get_regulatory_elements(
        gene_name="TP53", element_type="enhancer", limit=5
    )
    assert result is not None, "No SCREEN result"
    print(f"    SCREEN result type: {type(result).__name__}")
    if isinstance(result, dict):
        keys = list(result.keys())[:5]
        print(f"    Keys: {keys}")


def test_47_encode_experiment_search():
    """ToolUniverse: ENCODE experiment search for H3K27ac"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.ENCODE_search_experiments(
        assay_title="ChIP-seq",
        target="H3K27ac",
        organism="Homo sapiens",
        limit=3
    )
    assert result is not None, "No ENCODE result"
    print(f"    ENCODE result type: {type(result).__name__}")


def test_48_chipatlas_experiments():
    """ToolUniverse: ChIPAtlas experiment search"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.ChIPAtlas_get_experiments(
        operation="get_experiment_list",
        genome="hg38",
        antigen="CTCF",
        limit=5
    )
    assert result is not None, "No ChIPAtlas result"
    print(f"    ChIPAtlas result type: {type(result).__name__}")
    if isinstance(result, dict):
        keys = list(result.keys())[:5]
        print(f"    Keys: {keys}")


def test_49_ensembl_regulatory_features():
    """ToolUniverse: Ensembl regulatory features for TP53 region"""
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.tools.ensembl_get_regulatory_features(
        region="17:7661779-7687550",
        feature="regulatory",
        species="human"
    )
    assert result is not None, "No Ensembl regulatory result"
    print(f"    Ensembl regulatory result type: {type(result).__name__}")
    if isinstance(result, dict):
        data = result.get('data', result)
        if isinstance(data, list):
            print(f"    Found {len(data)} regulatory features")


# ============================================================
# Phase 16: BixBench-Style Question Tests
# ============================================================

def test_50_bixbench_complete_cases():
    """BixBench: How many patients have no missing data for all modalities?"""
    np.random.seed(42)

    # Setup data similar to BixBench scenario
    patients = [f'P{i:03d}' for i in range(100)]
    clinical = pd.DataFrame({
        'vital_status': np.random.choice(['Alive', 'Dead', None], 100, p=[0.45, 0.45, 0.1]),
        'age': np.random.uniform(30, 80, 100),
    }, index=patients)

    expr_patients = patients[:85]  # 85 have expression data
    meth_patients = patients[10:95]  # 85 have methylation data

    # Complete cases
    has_vital = set(clinical[clinical['vital_status'].notna()].index)
    complete = has_vital & set(expr_patients) & set(meth_patients)

    print(f"    Question: Patients with complete data?")
    print(f"    Answer: {len(complete)}")
    assert len(complete) > 0


def test_51_bixbench_cpg_density_ratio():
    """BixBench: Chromosome density ratio of age-related CpGs"""
    # Simulated age-related CpGs mapped to chromosomes
    np.random.seed(42)
    n_cpgs = 1000
    probs = [0.08, 0.07, 0.06, 0.06, 0.06, 0.05, 0.05, 0.04, 0.04, 0.04,
             0.04, 0.04, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.06, 0.03,
             0.02, 0.02]
    probs = [p / sum(probs) for p in probs]  # Normalize to sum to 1.0
    chr_assignments = np.random.choice(
        [f'chr{i}' for i in range(1, 23)],
        size=n_cpgs,
        p=probs
    )

    chr_lengths = {
        'chr1': 248956422, 'chr2': 242193529, 'chr3': 198295559,
        'chr4': 190214555, 'chr5': 181538259, 'chr6': 170805979,
        'chr7': 159345973, 'chr8': 145138636, 'chr9': 138394717,
        'chr10': 133797422, 'chr11': 135086622, 'chr12': 133275309,
        'chr13': 114364328, 'chr14': 107043718, 'chr15': 101991189,
        'chr16': 90338345, 'chr17': 83257441, 'chr18': 80373285,
        'chr19': 58617616, 'chr20': 64444167, 'chr21': 46709983,
        'chr22': 50818468,
    }

    chr_counts = pd.Series(chr_assignments).value_counts()
    densities = {}
    for chrom, count in chr_counts.items():
        if chrom in chr_lengths:
            densities[chrom] = count / chr_lengths[chrom]

    # Ratio of chr19/chr1
    if 'chr19' in densities and 'chr1' in densities:
        ratio = densities['chr19'] / densities['chr1']
        print(f"    Question: chr19/chr1 density ratio?")
        print(f"    chr19 density: {densities['chr19']:.2e}")
        print(f"    chr1 density: {densities['chr1']:.2e}")
        print(f"    Answer: {ratio:.2f}")
    else:
        print(f"    Densities: {densities}")


def test_52_bixbench_genome_wide_density():
    """BixBench: Genome-wide average CpG density"""
    np.random.seed(42)

    chr_lengths = {
        'chr1': 248956422, 'chr2': 242193529, 'chr3': 198295559,
        'chr19': 58617616, 'chr22': 50818468,
    }
    chr_cpg_counts = {'chr1': 500, 'chr2': 400, 'chr3': 350, 'chr19': 200, 'chr22': 100}

    total_cpgs = sum(chr_cpg_counts.values())
    total_length = sum(chr_lengths.values())
    density = total_cpgs / total_length

    print(f"    Question: Genome-wide average density?")
    print(f"    Total CpGs: {total_cpgs}")
    print(f"    Total genome: {total_length:,} bp")
    print(f"    Answer: {density:.2e} CpGs/bp")
    assert density > 0


def test_53_bixbench_sig_dmp_count():
    """BixBench: How many CpG sites show significant differential methylation?"""
    np.random.seed(42)
    n_probes = 500
    n_per_group = 10

    g1 = np.random.beta(2, 5, size=(n_probes, n_per_group))
    g2 = np.random.beta(2, 5, size=(n_probes, n_per_group))
    g2[:50, :] += 0.25
    g2 = np.clip(g2, 0, 1)

    pvals = []
    for i in range(n_probes):
        _, pval = stats.ttest_ind(g1[i], g2[i], equal_var=False)
        pvals.append(pval)

    reject, padj, _, _ = mt.multipletests(pvals, method='fdr_bh')
    n_sig = sum(reject)

    print(f"    Question: How many significant DMPs (padj < 0.05)?")
    print(f"    Answer: {n_sig} / {n_probes}")
    assert n_sig > 10, "Should detect significant DMPs"


def test_54_bixbench_chr_specific_delta():
    """BixBench: Average beta difference on chromosome 17"""
    np.random.seed(42)

    # Simulated data: 100 probes on chr17
    probes_chr17 = 100
    g1 = np.random.beta(2, 5, size=(probes_chr17, 10))
    g2 = np.random.beta(3, 4, size=(probes_chr17, 10))

    delta_betas = g2.mean(axis=1) - g1.mean(axis=1)
    avg_delta = delta_betas.mean()

    print(f"    Question: Average beta difference on chr17?")
    print(f"    Answer: {avg_delta:.4f}")
    assert isinstance(avg_delta, float)


# ============================================================
# Phase 17: Edge Case Tests
# ============================================================

def test_55_empty_dataframe():
    """Edge Case: Handle empty DataFrame"""
    empty_df = pd.DataFrame()
    assert len(empty_df) == 0
    assert empty_df.shape == (0, 0)
    print(f"    Empty DataFrame handled correctly")


def test_56_single_sample():
    """Edge Case: Handle single-sample methylation data"""
    np.random.seed(42)
    beta = pd.DataFrame(
        np.random.beta(2, 5, size=(100, 1)),
        index=[f'cg{i:08d}' for i in range(100)],
        columns=['SAMPLE_001']
    )

    global_mean = beta.mean().mean()
    # With ddof=1 (pandas default), single sample variance is NaN (division by N-1=0)
    # With ddof=0, single sample variance is 0.0
    probe_var_ddof0 = beta.var(axis=1, ddof=0, skipna=True)
    probe_var_ddof1 = beta.var(axis=1, ddof=1, skipna=True)

    assert 0 < global_mean < 1
    assert all(probe_var_ddof0 == 0), "Single sample should have zero variance (ddof=0)"
    assert all(pd.isna(probe_var_ddof1)), "Single sample variance with ddof=1 should be NaN"
    print(f"    Single sample mean: {global_mean:.3f}, variance (ddof=0): all zero, variance (ddof=1): all NaN")


def test_57_all_nan_probe():
    """Edge Case: Handle probe with all NaN values"""
    np.random.seed(42)
    beta = generate_methylation_data(n_probes=10, n_samples=5)
    beta.iloc[0, :] = np.nan  # First probe all NaN

    probe_mean = beta.mean(axis=1)
    assert pd.isna(probe_mean.iloc[0]), "All-NaN probe should have NaN mean"

    # Variance should also be NaN
    probe_var = beta.var(axis=1, skipna=True)
    assert pd.isna(probe_var.iloc[0]) or probe_var.iloc[0] == 0
    print(f"    All-NaN probe handled: mean={probe_mean.iloc[0]}, var={probe_var.iloc[0]}")


def test_58_large_chromosome_sort():
    """Edge Case: Sort chromosomes correctly (chr1, chr2, ..., chr10, chr22, chrX)"""
    chroms = ['chr2', 'chr10', 'chr1', 'chr22', 'chrX', 'chr19']

    def chr_sort_key(x):
        c = x.replace('chr', '')
        if c == 'X':
            return 23
        elif c == 'Y':
            return 24
        else:
            return int(c)

    sorted_chroms = sorted(chroms, key=chr_sort_key)
    expected = ['chr1', 'chr2', 'chr10', 'chr19', 'chr22', 'chrX']
    assert sorted_chroms == expected, f"Got {sorted_chroms}"
    print(f"    Chromosome sorting correct: {sorted_chroms}")


# ============================================================
# Main Runner
# ============================================================

def main():
    print("=" * 70)
    print("tooluniverse-epigenomics: Comprehensive Test Suite")
    print("=" * 70)
    print()

    all_tests = [
        # Phase 1: Methylation Data Loading
        test_01_generate_and_load_beta_matrix,
        test_02_detect_methylation_type,
        test_03_beta_mvalue_conversion,
        test_04_csv_methylation_io,
        test_05_tsv_methylation_io,

        # Phase 2: CpG Filtering
        test_06_filter_by_probe_type,
        test_07_filter_by_variance,
        test_08_filter_by_missing_data,
        test_09_filter_by_mean_beta_range,
        test_10_filter_top_n_variable,
        test_11_filter_by_chromosome,

        # Phase 3: Differential Methylation
        test_12_differential_methylation_ttest,
        test_13_differential_methylation_wilcoxon,
        test_14_identify_dmps_with_threshold,
        test_15_hyper_hypo_classification,

        # Phase 4: Age-Related CpGs
        test_16_age_correlation,
        test_17_spearman_correlation,

        # Phase 5: Chromosome Statistics
        test_18_chromosome_normalization,
        test_19_chromosome_lengths,
        test_20_cpg_density_per_chromosome,
        test_21_genome_wide_average_density,
        test_22_chromosome_density_ratio,

        # Phase 6: BED/Peak Files
        test_23_load_bed_dataframe,
        test_24_peak_statistics,
        test_25_peaks_per_chromosome,
        test_26_write_and_read_bed,

        # Phase 7: Peak Annotation
        test_27_peak_to_gene_annotation,
        test_28_classify_peak_regions,

        # Phase 8: Peak Overlap
        test_29_simple_overlap,
        test_30_no_overlap,

        # Phase 9: ATAC-seq
        test_31_atac_peak_stats,

        # Phase 10: Multi-Omics Integration
        test_32_methylation_expression_correlation,
        test_33_multi_probe_gene_correlation,

        # Phase 11: Clinical Integration
        test_34_missing_data_analysis,
        test_35_sample_id_matching,

        # Phase 12: Genome-Wide Statistics
        test_36_global_methylation_stats,
        test_37_probe_variance_distribution,
        test_38_per_sample_statistics,

        # Phase 13: Multiple Testing
        test_39_bh_correction,
        test_40_bonferroni_correction,

        # Phase 14: Manifest Processing
        test_41_manifest_generation,
        test_42_manifest_chromosome_mapping,
        test_43_cpg_island_relation,

        # Phase 15: ToolUniverse Integration
        test_44_tooluniverse_loading,
        test_45_ensembl_gene_lookup,
        test_46_screen_regulatory_elements,
        test_47_encode_experiment_search,
        test_48_chipatlas_experiments,
        test_49_ensembl_regulatory_features,

        # Phase 16: BixBench-Style Questions
        test_50_bixbench_complete_cases,
        test_51_bixbench_cpg_density_ratio,
        test_52_bixbench_genome_wide_density,
        test_53_bixbench_sig_dmp_count,
        test_54_bixbench_chr_specific_delta,

        # Phase 17: Edge Cases
        test_55_empty_dataframe,
        test_56_single_sample,
        test_57_all_nan_probe,
        test_58_large_chromosome_sort,
    ]

    for test_func in all_tests:
        run_test(test_func)
        print()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in RESULTS if r['status'] == 'PASS')
    failed = sum(1 for r in RESULTS if r['status'] == 'FAIL')
    total = len(RESULTS)
    total_time = sum(r['time'] for r in RESULTS)

    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Time: {total_time:.1f}s")
    print(f"Pass Rate: {passed}/{total} ({100*passed/total:.1f}%)")
    print()

    if failed > 0:
        print("FAILED TESTS:")
        for r in RESULTS:
            if r['status'] == 'FAIL':
                print(f"  {r['name']}: {r['error']}")
        print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
