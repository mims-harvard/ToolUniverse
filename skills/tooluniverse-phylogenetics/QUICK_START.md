# Quick Start: Phylogenetics Skill

Fast reference for common phylogenetic analysis tasks.

---

## Installation

```bash
pip install phykit dendropy biopython pandas numpy scipy
```

---

## Common Tasks

### 1. Compute Single Tree Metric

```python
from scripts.tree_statistics import phykit_treeness, phykit_tree_length

# Treeness
treeness = phykit_treeness("tree.nwk")
print(f"Treeness: {treeness:.4f}")

# Tree length
length = phykit_tree_length("tree.nwk")
print(f"Tree length: {length:.4f}")
```

### 2. Compute Single Alignment Metric

```python
from scripts.tree_statistics import phykit_parsimony_informative, phykit_rcv

# Parsimony informative sites
pi_count, aln_len, pi_pct = phykit_parsimony_informative("alignment.fa")
print(f"PI sites: {pi_count} / {aln_len} ({pi_pct:.2f}%)")

# RCV
rcv = phykit_rcv("alignment.fa")
print(f"RCV: {rcv:.4f}")
```

### 3. Batch Analysis

```python
from scripts.format_alignment import discover_gene_files
from scripts.tree_statistics import batch_treeness, batch_dvmc
import numpy as np

# Discover files
gene_files = discover_gene_files("data/")
print(f"Found {len(gene_files)} genes")

# Compute metric for all genes
treeness_results = batch_treeness(gene_files)
dvmc_results = batch_dvmc(gene_files)

# Get median
print(f"Median treeness: {np.median(list(treeness_results.values())):.4f}")
print(f"Median DVMC: {np.median(list(dvmc_results.values())):.4f}")
```

### 4. Compare Two Groups

```python
from scipy import stats

# Get metrics for both groups
fungi_genes = discover_gene_files("data/", group_name="fungi")
animal_genes = discover_gene_files("data/", group_name="animals")

fungi_treeness = batch_treeness(fungi_genes)
animal_treeness = batch_treeness(animal_genes)

# Mann-Whitney U test
u_stat, p_value = stats.mannwhitneyu(
    list(fungi_treeness.values()),
    list(animal_treeness.values())
)

print(f"U statistic: {u_stat:.0f}")
print(f"P-value: {p_value:.4e}")
```

### 5. Filter and Analyze

```python
from scripts.format_alignment import filter_by_gap_threshold
from scripts.tree_statistics import batch_treeness_over_rcv

# Filter by gap percentage
valid_genes = filter_by_gap_threshold(gene_files, max_gap_pct=5.0)
print(f"Genes with <5% gaps: {len(valid_genes)}")

# Compute treeness/RCV for valid genes
results = batch_treeness_over_rcv(valid_genes)

# Extract ratios
ratios = [r[0] for r in results.values()]
print(f"Median treeness/RCV: {np.median(ratios):.4f}")
```

### 6. Convert Alignment Format

```bash
# Single file
python scripts/format_alignment.py convert input.phy output.fa --format fasta

# Batch convert
python scripts/format_alignment.py batch-convert input_dir/ output_dir/ --format phylip-relaxed
```

---

## Quick Reference: Metrics

| Function | Input | Output |
|----------|-------|--------|
| `phykit_treeness()` | tree.nwk | float (0-1) |
| `phykit_tree_length()` | tree.nwk | float |
| `phykit_evolutionary_rate()` | tree.nwk | float |
| `phykit_dvmc()` | tree.nwk | float |
| `phykit_rcv()` | alignment.fa | float |
| `phykit_parsimony_informative()` | alignment.fa | (count, length, pct) |
| `phykit_treeness_over_rcv()` | tree.nwk, alignment.fa | (ratio, treeness, rcv) |
| `alignment_gap_percentage()` | alignment.fa | float (0-100) |

---

## Directory Structure

```
data/
├── fungi/
│   ├── gene1.fa
│   ├── gene1.nwk
│   ├── gene2.fa
│   └── gene2.nwk
└── animals/
    ├── gene1.fa
    ├── gene1.nwk
    ├── gene2.fa
    └── gene2.nwk
```

---

## Common Workflows

### Workflow 1: DVMC Comparison

```python
# Question: "What is the median DVMC for fungi?"

fungi_genes = discover_gene_files("data/", group_name="fungi")
fungi_dvmc = batch_dvmc(fungi_genes)
median_dvmc = np.median(list(fungi_dvmc.values()))

print(f"Median DVMC: {median_dvmc:.4f}")
```

### Workflow 2: Parsimony Sites Ratio

```python
# Question: "What is the ratio of minimum PI sites (fungi / animals)?"

fungi_pi = batch_parsimony_informative(fungi_genes)
animal_pi = batch_parsimony_informative(animal_genes)

fungi_counts = [r[0] for r in fungi_pi.values()]
animal_counts = [r[0] for r in animal_pi.values()]

ratio = min(fungi_counts) / min(animal_counts)

print(f"Ratio: {ratio:.4f}")
```

### Workflow 3: Percentage Above Threshold

```python
# Question: "What percentage of trees have treeness > 0.45?"

treeness_results = batch_treeness(gene_files)
values = list(treeness_results.values())

above = sum(1 for v in values if v > 0.45)
percentage = (above / len(values)) * 100

print(f"Percentage: {percentage:.2f}%")
```

---

## Command-Line Tools

### Discover Files

```bash
python scripts/format_alignment.py discover data/ --group fungi
```

### Filter Alignments

```bash
python scripts/format_alignment.py filter data/ --max-gap 5.0 --min-seqs 4
```

### Compute Tree Statistics

```bash
python scripts/tree_statistics.py tree.nwk alignment.fa
```

### Remove Gappy Sequences

```bash
python scripts/format_alignment.py remove-gappy-seqs input.fa output.fa --max-gap 50.0
```

### Remove Gappy Columns

```bash
python scripts/format_alignment.py remove-gappy-cols input.fa output.fa --max-gap 50.0
```

---

## Troubleshooting

### "Cannot parse alignment/tree"
- Check file format (FASTA must be `>name\nseq`, Newick must end with `;`)
- See `references/troubleshooting.md`

### No files found
- Check directory structure
- Run: `python scripts/format_alignment.py discover data/`

### Different results from expected
- Check rounding (PhyKIT default: 4 decimals)
- Check PhyKIT version: `pip show phykit`

---

## Next Steps

- **Detailed workflows**: See `SKILL.md`
- **Alignment analysis**: See `references/sequence_alignment.md`
- **Tree construction**: See `references/tree_building.md`
- **Statistical comparisons**: See `references/parsimony_analysis.md`
- **Troubleshooting**: See `references/troubleshooting.md`

---

## Import Statements

```python
# Core imports for most tasks
import numpy as np
import pandas as pd
from scipy import stats

# Load functions from scripts
from scripts.format_alignment import discover_gene_files
from scripts.tree_statistics import (
    phykit_treeness,
    phykit_tree_length,
    phykit_evolutionary_rate,
    phykit_dvmc,
    phykit_rcv,
    phykit_parsimony_informative,
    phykit_treeness_over_rcv,
    batch_treeness,
    batch_dvmc,
    batch_rcv,
    summary_stats,
    compare_groups
)
```
