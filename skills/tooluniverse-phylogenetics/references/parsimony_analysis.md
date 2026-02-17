# Parsimony Analysis and Statistical Comparisons

Comprehensive guide for batch phylogenetic analysis and statistical comparisons between groups.

---

## File Discovery

### Auto-discover Gene Files

```python
import glob
import os

def discover_gene_files(data_dir, group_name=None):
    """Discover paired alignment and tree files for a group.

    Handles common naming patterns:
    - gene1.fa + gene1.nwk
    - gene1.aligned.fa + gene1.treefile
    - gene1_alignment.fa + gene1_tree.nwk

    Args:
        data_dir: root directory to search
        group_name: optional subdirectory (e.g., "fungi", "animals")

    Returns: list of dicts with 'gene_id', 'aln_file', 'tree_file'
    """
    search_dir = os.path.join(data_dir, group_name) if group_name else data_dir

    # Find alignments
    aln_files = {}
    aln_extensions = ['*.fa', '*.fasta', '*.faa', '*.fna', '*.phy', '*.phylip', '*.nex']
    for ext in aln_extensions:
        for f in glob.glob(os.path.join(search_dir, '**', ext), recursive=True):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            # Remove common suffixes
            for suffix in ['.aligned', '.aln', '.msa', '_aligned', '_alignment']:
                gene_id = gene_id.replace(suffix, '')
            aln_files[gene_id] = f

    # Find trees
    tree_files = {}
    tree_extensions = ['*.nwk', '*.newick', '*.tre', '*.tree', '*.treefile']
    for ext in tree_extensions:
        for f in glob.glob(os.path.join(search_dir, '**', ext), recursive=True):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            for suffix in ['.treefile', '_tree', '.rooted', '_rooted']:
                gene_id = gene_id.replace(suffix, '')
            tree_files[gene_id] = f

    # Match pairs
    results = []
    all_gene_ids = set(aln_files.keys()) | set(tree_files.keys())
    for gene_id in sorted(all_gene_ids):
        entry = {'gene_id': gene_id}
        if gene_id in aln_files:
            entry['aln_file'] = aln_files[gene_id]
        if gene_id in tree_files:
            entry['tree_file'] = tree_files[gene_id]
        results.append(entry)

    return results
```

### Usage Examples

```python
# Find all genes in directory
all_genes = discover_gene_files("data/")

# Find genes for specific group
fungi_genes = discover_gene_files("data/", group_name="fungi")
animal_genes = discover_gene_files("data/", group_name="animals")

# Check what was found
print(f"Total genes: {len(all_genes)}")
print(f"With alignments: {sum(1 for g in all_genes if 'aln_file' in g)}")
print(f"With trees: {sum(1 for g in all_genes if 'tree_file' in g)}")
print(f"With both: {sum(1 for g in all_genes if 'aln_file' in g and 'tree_file' in g)}")
```

---

## Batch Metric Computation

### Generic Batch Function

```python
def batch_compute_metric(gene_files, metric_func, requires='tree'):
    """Compute a metric across all genes in a group.

    Args:
        gene_files: list from discover_gene_files()
        metric_func: function that takes file path(s) and returns a number
        requires: 'tree', 'alignment', or 'both'

    Returns: dict mapping gene_id -> metric_value (skipping failures)
    """
    results = {}
    for entry in gene_files:
        gene_id = entry['gene_id']
        try:
            if requires == 'tree' and 'tree_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'])
            elif requires == 'alignment' and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['aln_file'])
            elif requires == 'both' and 'tree_file' in entry and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'], entry['aln_file'])
        except Exception as e:
            # Skip genes that fail (common with malformed files)
            pass
    return results
```

### Specialized Batch Functions

```python
# Tree metrics
def batch_treeness(gene_files):
    return batch_compute_metric(gene_files, phykit_treeness, requires='tree')

def batch_tree_length(gene_files):
    return batch_compute_metric(gene_files, phykit_tree_length, requires='tree')

def batch_evolutionary_rate(gene_files):
    return batch_compute_metric(gene_files, phykit_evolutionary_rate, requires='tree')

def batch_dvmc(gene_files):
    return batch_compute_metric(gene_files, phykit_dvmc, requires='tree')

# Alignment metrics
def batch_rcv(gene_files):
    return batch_compute_metric(gene_files, phykit_rcv, requires='alignment')

def batch_gap_percentage(gene_files):
    return batch_compute_metric(gene_files, alignment_gap_percentage, requires='alignment')

def batch_parsimony_informative(gene_files):
    """Returns dict of gene_id -> (count, aln_len, percentage)"""
    results = {}
    for entry in gene_files:
        if 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_parsimony_informative(entry['aln_file'])
            except Exception:
                pass
    return results

# Combined metrics
def batch_treeness_over_rcv(gene_files):
    """Returns dict of gene_id -> (treeness_over_rcv, treeness, rcv)"""
    results = {}
    for entry in gene_files:
        if 'tree_file' in entry and 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_treeness_over_rcv(
                    entry['tree_file'], entry['aln_file']
                )
            except Exception:
                pass
    return results
```

---

## Summary Statistics

### Basic Statistics

```python
import numpy as np

def summary_stats(values):
    """Compute standard summary statistics for a list of values.

    Returns: dict with count, mean, median, std, var, min, max, quartiles
    """
    arr = np.array(values)
    return {
        'count': len(arr),
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
        'std': float(np.std(arr, ddof=1)),
        'var': float(np.var(arr, ddof=1)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'q25': float(np.percentile(arr, 25)),
        'q75': float(np.percentile(arr, 75)),
    }
```

### Usage

```python
# Compute metric
dvmc_results = batch_dvmc(gene_files)
dvmc_values = list(dvmc_results.values())

# Get statistics
stats = summary_stats(dvmc_values)

print(f"Count: {stats['count']}")
print(f"Mean: {stats['mean']:.4f}")
print(f"Median: {stats['median']:.4f}")
print(f"Std Dev: {stats['std']:.4f}")
print(f"Min: {stats['min']:.4f}")
print(f"Max: {stats['max']:.4f}")
print(f"Q1: {stats['q25']:.4f}")
print(f"Q3: {stats['q75']:.4f}")
```

---

## Group Comparisons

### Mann-Whitney U Test

```python
from scipy import stats

def compare_groups(group1_values, group2_values, group1_name="Group1", group2_name="Group2"):
    """Compare two groups using Mann-Whitney U test.

    Mann-Whitney U is a non-parametric test for comparing distributions.
    Does not assume normality.

    Args:
        group1_values: list of values for group 1
        group2_values: list of values for group 2
        group1_name: label for group 1
        group2_name: label for group 2

    Returns: dict with U statistic, p-value, and summary stats for each group
    """
    arr1 = np.array(group1_values)
    arr2 = np.array(group2_values)

    # Mann-Whitney U test (two-sided, default)
    u_stat, p_value = stats.mannwhitneyu(arr1, arr2, alternative='two-sided')

    return {
        'u_statistic': float(u_stat),
        'p_value': float(p_value),
        group1_name: summary_stats(arr1.tolist()),
        group2_name: summary_stats(arr2.tolist()),
        'median_difference': float(np.median(arr1) - np.median(arr2)),
    }
```

### Usage

```python
# Compute metrics for both groups
fungi_treeness = batch_treeness(fungi_genes)
animal_treeness = batch_treeness(animal_genes)

# Compare
comparison = compare_groups(
    list(fungi_treeness.values()),
    list(animal_treeness.values()),
    group1_name="Fungi",
    group2_name="Animals"
)

print(f"Mann-Whitney U: {comparison['u_statistic']:.0f}")
print(f"P-value: {comparison['p_value']:.4e}")
print(f"Fungi median: {comparison['Fungi']['median']:.4f}")
print(f"Animals median: {comparison['Animals']['median']:.4f}")
print(f"Difference: {comparison['median_difference']:.4f}")
```

---

## Paired Comparisons

### Paired Gene Analysis

```python
def paired_comparison(group1_dict, group2_dict):
    """Compare matched pairs (same gene IDs in both groups).

    Useful when comparing orthologs between species.

    Args:
        group1_dict: dict of gene_id -> value for group 1
        group2_dict: dict of gene_id -> value for group 2

    Returns: dict with paired differences and statistics
    """
    common_genes = set(group1_dict.keys()) & set(group2_dict.keys())

    diffs = []
    ratios = []
    for gene in sorted(common_genes):
        v1 = group1_dict[gene]
        v2 = group2_dict[gene]
        diffs.append(v1 - v2)
        if v2 != 0:
            ratios.append(v1 / v2)

    result = {
        'n_pairs': len(common_genes),
        'differences': summary_stats(diffs),
        'median_difference': float(np.median(diffs)),
    }

    if ratios:
        result['ratios'] = summary_stats(ratios)
        result['median_ratio'] = float(np.median(ratios))

    return result
```

### Usage

```python
# Compute tree length for both groups
fungi_lengths = batch_tree_length(fungi_genes)
animal_lengths = batch_tree_length(animal_genes)

# Paired comparison
paired = paired_comparison(fungi_lengths, animal_lengths)

print(f"Paired genes: {paired['n_pairs']}")
print(f"Median difference: {paired['median_difference']:.4f}")
print(f"Median ratio: {paired['median_ratio']:.4f}")
```

---

## Complete Workflow Examples

### Example 1: DVMC Comparison (BixBench bix-4)

```python
# Question: "What is the median DVMC for fungi, and the Mann-Whitney U statistic comparing fungi vs animals?"

# 1. Discover files
fungi_genes = discover_gene_files("data/", group_name="fungi")
animal_genes = discover_gene_files("data/", group_name="animals")

print(f"Fungi genes: {len(fungi_genes)}")
print(f"Animal genes: {len(animal_genes)}")

# 2. Compute DVMC for both groups
fungi_dvmc = batch_dvmc(fungi_genes)
animal_dvmc = batch_dvmc(animal_genes)

print(f"Computed DVMC for {len(fungi_dvmc)} fungi genes")
print(f"Computed DVMC for {len(animal_dvmc)} animal genes")

# 3. Extract values
fungi_values = list(fungi_dvmc.values())
animal_values = list(animal_dvmc.values())

# 4. Compute median for fungi
fungi_median = np.median(fungi_values)
print(f"\nFungi median DVMC: {fungi_median:.4f}")

# 5. Mann-Whitney U test
u_stat, p_value = stats.mannwhitneyu(fungi_values, animal_values, alternative='two-sided')
print(f"Mann-Whitney U statistic: {u_stat:.0f}")
print(f"P-value: {p_value:.4e}")

# Answer: fungi_median (rounded to 4 decimals), u_stat (integer)
```

### Example 2: Treeness with Filtering (BixBench bix-25)

```python
# Question: "What is the median treeness/RCV for alignments with <5% gaps?"

# 1. Discover files
gene_files = discover_gene_files("data/")

# 2. Filter by gap percentage
valid_genes = []
for entry in gene_files:
    if 'aln_file' in entry and 'tree_file' in entry:
        try:
            gap_pct = alignment_gap_percentage(entry['aln_file'])
            if gap_pct < 5.0:
                valid_genes.append(entry)
        except Exception:
            pass

print(f"Genes with <5% gaps: {len(valid_genes)}/{len(gene_files)}")

# 3. Compute treeness/RCV
results = batch_treeness_over_rcv(valid_genes)

# 4. Extract ratios
ratios = [result[0] for result in results.values()]  # First element is ratio

# 5. Compute median
median_ratio = np.median(ratios)
print(f"Median treeness/RCV: {median_ratio:.4f}")

# Answer: median_ratio (rounded to 4 decimals)
```

### Example 3: Parsimony Sites Comparison (BixBench bix-12)

```python
# Question: "What is the ratio of minimum PI sites (fungi / animals)?"

# 1. Compute PI sites
fungi_pi = batch_parsimony_informative(fungi_genes)
animal_pi = batch_parsimony_informative(animal_genes)

# 2. Extract counts (first element of tuple)
fungi_counts = [result[0] for result in fungi_pi.values()]
animal_counts = [result[0] for result in animal_pi.values()]

# 3. Find minimums
fungi_min = min(fungi_counts)
animal_min = min(animal_counts)

# 4. Compute ratio
ratio = fungi_min / animal_min

print(f"Fungi min PI sites: {fungi_min}")
print(f"Animals min PI sites: {animal_min}")
print(f"Ratio: {ratio:.4f}")

# Answer: ratio (rounded to 4 decimals)
```

### Example 4: Percentage Above Threshold (BixBench bix-11)

```python
# Question: "What percentage of animal genes have treeness > 0.45?"

# 1. Compute treeness
animal_treeness = batch_treeness(animal_genes)
treeness_values = list(animal_treeness.values())

# 2. Count above threshold
above_threshold = sum(1 for v in treeness_values if v > 0.45)

# 3. Compute percentage
percentage = (above_threshold / len(treeness_values)) * 100

print(f"Total genes: {len(treeness_values)}")
print(f"Above 0.45: {above_threshold}")
print(f"Percentage: {percentage:.2f}%")

# Answer: percentage (rounded to 2 decimals if question asks for "XX.XX%")
```

### Example 5: Specific Gene Lookup (BixBench bix-35)

```python
# Question: "What is the evolutionary rate for gene ENSG00000141510?"

# 1. Discover files
gene_files = discover_gene_files("data/")

# 2. Find specific gene
target_gene = [g for g in gene_files if g['gene_id'] == 'ENSG00000141510'][0]

# 3. Compute evolutionary rate
evo_rate = phykit_evolutionary_rate(target_gene['tree_file'])

print(f"Evolutionary rate for ENSG00000141510: {evo_rate:.4f}")

# Answer: evo_rate (rounded to 4 decimals)
```

---

## Answer Extraction Patterns

### Common Patterns

```python
# Median
answer = np.median(values)

# Mean
answer = np.mean(values)

# Maximum
answer = np.max(values)

# Minimum
answer = np.min(values)

# Standard deviation
answer = np.std(values, ddof=1)

# Variance
answer = np.var(values, ddof=1)

# Percentile (e.g., 75th)
answer = np.percentile(values, 75)

# Count above threshold
answer = sum(1 for v in values if v > threshold)

# Percentage above threshold
answer = (sum(1 for v in values if v > threshold) / len(values)) * 100

# Difference in medians
answer = np.median(group1) - np.median(group2)

# Absolute difference
answer = abs(np.median(group1) - np.median(group2))

# Fold change (ratio)
answer = np.median(group1) / np.median(group2)

# Mann-Whitney U statistic
answer = stats.mannwhitneyu(group1, group2)[0]

# Mann-Whitney p-value
answer = stats.mannwhitneyu(group1, group2)[1]
```

### Rounding Guide

```python
# PhyKIT default: 4 decimals
answer = round(value, 4)

# Percentages: match question format
# "35%" -> integer
answer = round(percentage)

# "3.5%" -> 1 decimal
answer = round(percentage, 1)

# P-values: scientific notation for small values
if p_value < 0.0001:
    answer_str = f"{p_value:.2e}"
else:
    answer_str = f"{p_value:.4f}"

# U statistics: integer
answer = int(round(u_stat))

# Special: "multiplied by 1000"
answer = round(value * 1000)
```

---

## Troubleshooting

### No Files Found

**Issue**: `discover_gene_files()` returns empty list.

**Solution**: Check directory structure and file extensions:
```python
import os
print(os.listdir("data/"))
print(os.listdir("data/fungi/"))
```

### Mismatched Gene Counts

**Issue**: Different numbers of genes between groups.

**Solution**: This is normal. Use paired comparison only for matched genes:
```python
paired = paired_comparison(fungi_results, animal_results)
print(f"Matched genes: {paired['n_pairs']}")
```

### Failed Metric Computation

**Issue**: Some genes fail during batch processing.

**Solution**: This is expected (malformed files, missing data). Failures are silently skipped:
```python
# Check success rate
total_genes = len(gene_files)
successful = len(results)
print(f"Success rate: {successful}/{total_genes} ({successful/total_genes*100:.1f}%)")
```

---

## See Also

- `sequence_alignment.md` - Alignment-specific metrics
- `tree_building.md` - Tree-specific metrics
- `troubleshooting.md` - Common errors and solutions
- `scripts/tree_statistics.py` - Implementation code
