---
name: tooluniverse-phylogenetics
description: "Phylogenetics: tree analysis, treeness, saturation, parsimony sites, PhyKIT, DVMC, alignment gaps, MAFFT."
disable-model-invocation: true
---

# Phylogenetics and Sequence Analysis

PhyKIT, Biopython, and DendroPy for alignment/tree analysis, evolutionary metrics, and comparative genomics.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first.

---

## When to Use

FASTA/PHYLIP/Nexus/Newick files; treeness, RCV, DVMC, evolutionary rate, parsimony sites, tree length, bootstrap; group comparisons (Mann-Whitney U); tree construction (NJ/UPGMA/parsimony); Robinson-Foulds distance.

**BixBench**: 33 questions across bix-4, bix-11, bix-12, bix-25, bix-35, bix-38, bix-45, bix-60.

**NOT for**: MSA generation (MUSCLE/MAFFT), ML trees (IQ-TREE/RAxML), Bayesian (MrBayes/BEAST).

---

## Required Packages

```python
import numpy as np, pandas as pd
from scipy import stats
from Bio import AlignIO, Phylo, SeqIO
from phykit.services.tree.treeness import Treeness
from phykit.services.tree.total_tree_length import TotalTreeLength
from phykit.services.tree.evolutionary_rate import EvolutionaryRate
from phykit.services.tree.dvmc import DVMC
from phykit.services.tree.treeness_over_rcv import TreenessOverRCV
from phykit.services.alignment.parsimony_informative_sites import ParsimonyInformative
from phykit.services.alignment.rcv import RelativeCompositionVariability
import dendropy
```

---

## Workflow Decision Tree

```
ALIGNMENT ANALYSIS (FASTA/PHYLIP):
  Parsimony sites → phykit_parsimony_informative()
  RCV → phykit_rcv()
  Gap % → alignment_gap_percentage()

TREE ANALYSIS (Newick):
  Treeness → phykit_treeness()
  Tree length → phykit_tree_length()
  Evolutionary rate → phykit_evolutionary_rate()
  DVMC → phykit_dvmc()
  Bootstrap → extract_bootstrap_support()

COMBINED: Treeness/RCV → phykit_treeness_over_rcv(tree, aln)

TREE CONSTRUCTION: NJ → build_nj_tree(); UPGMA → build_upgma_tree(); Parsimony → build_parsimony_tree()

GROUP COMPARISON: batch metrics → Mann-Whitney U → summary stats

TREE COMPARISON: Robinson-Foulds → robinson_foulds_distance()
```

---

## Quick Reference

| Metric | Input | Description |
|--------|-------|-------------|
| Treeness | Newick | Internal / total branch length |
| RCV | FASTA/PHYLIP | Relative Composition Variability |
| Treeness/RCV | Both | Signal quality ratio |
| Tree Length | Newick | Sum of all branch lengths |
| Evolutionary Rate | Newick | Total length / num terminals |
| DVMC | Newick | Degree of Violation of Molecular Clock |
| Parsimony Sites | FASTA/PHYLIP | Sites with >=2 chars appearing >=2 times |

---

## Common Patterns

### Single Metric Across Groups
```python
fungi_dvmc = batch_dvmc(discover_gene_files("data/fungi"))
animal_dvmc = batch_dvmc(discover_gene_files("data/animals"))
print(f"Fungi median: {np.median(list(fungi_dvmc.values())):.4f}")
```

### Statistical Comparison
```python
u_stat, p_value = stats.mannwhitneyu(list(g1.values()), list(g2.values()), alternative='two-sided')
```

### Filtering + Metric
Filter by gap percentage < 5%, then compute treeness/RCV on filtered set.

### Batch Processing
```python
gene_files = discover_gene_files("data/")  # → [{gene_id, aln_file, tree_file}]
treeness_results = batch_treeness(gene_files)  # → {gene_id: value}
```

---

## Answer Extraction

| Pattern | Method |
|---------|--------|
| "median X" | `np.median(values)` |
| "maximum X" | `np.max(values)` |
| "difference in median" | `abs(np.median(a) - np.median(b))` |
| "Mann-Whitney U" | `stats.mannwhitneyu(a, b)[0]` |
| "fold-change" | `np.median(a) / np.median(b)` |

**Rounding**: PhyKIT default 4 decimals. U stats = integer. Question wording overrides.

---

## Interpretation

| Metric | Good | Acceptable | Poor |
|--------|------|-----------|------|
| Treeness | >0.8 | 0.5-0.8 | <0.5 |
| RCV | <0.2 | 0.2-0.5 | >0.5 |
| Treeness/RCV | >2.0 | 1.0-2.0 | <1.0 |
| Bootstrap | >95% | 70-95% | <70% |
| Parsimony sites | >30% | 10-30% | <10% |

## Completeness Checklist

All files identified; group structure detected; correct PhyKIT function; ALL genes processed (not sample); correct test; 4-decimal rounding; specific statistic (median/max/U/p); Mann-Whitney `alternative='two-sided'`.

---

## BixBench-verified conventions

### MANDATORY: Use `phykit_batch_analysis` tool for batch computations
For ANY question asking for statistics across multiple trees/alignments (median treeness, mean saturation, DVMC percentage, gap percentage, long branch scores), use the ToolUniverse tool:
```bash
tu run phykit_batch_analysis '{"operation":"batch","function":"treeness","directory":"./trees","extension":".treefile"}'
tu run phykit_batch_analysis '{"operation":"batch","function":"saturation","directory":"./alignments","extension":".fa","tree_directory":"./trees","tree_extension":".treefile"}'
tu run phykit_batch_analysis '{"operation":"gap_percentage","directory":"./alignments","extension":".fa"}'
```
Do NOT run phykit manually in a loop — the tool handles all files and returns correct summary statistics.

### Parsimony informative sites
- Exclude **gap-only columns** before counting — a column that is all gaps is not informative.
- A site is parsimony informative when ≥2 different non-gap characters each appear in ≥2 taxa.
- Use Biopython `AlignIO` or the AMAS tool to iterate columns and count.

### Treeness (RCV ratio)
Treeness = sum of internal branch lengths / total tree length. Internal branches are those that do not lead to a leaf (tip).

### PhyKIT usage
PhyKIT (`pip install phykit`) provides command-line functions for tree and alignment statistics. Common functions:
- `phykit treeness <tree_file>` — outputs treeness (RCV) value
- `phykit saturation <alignment_file> -t <tree_file>` — outputs saturation value
- `phykit dvmc <tree_file>` — degree of violation of the molecular clock
- `phykit long_branch_score <tree_file>` — long-branch score (LBS)
- `phykit alignment_length <alignment_file>` — alignment length
- `phykit parsimony_informative <alignment_file>` — count parsimony informative sites

When running PhyKIT on multiple gene trees/alignments, **use the bundled batch script**:

```bash
# Treeness across all trees
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir scogs_fungi --function treeness --ext .treefile --stat median

# Saturation with paired alignment+tree
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir alignments --function saturation --tree-dir trees \
  --ext .fa --tree-ext .treefile --stat median

# Long branch score (mean per tree, then median across trees)
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir trees --function long_branch_score --ext .treefile \
  --per-tree-stat mean --stat median

# DVMC
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir trees --function dvmc --ext .treefile --stat all

# Gap percentage across all alignments
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir alignments --function gap_percentage --ext .fa
```

**Preferred: use the `phykit_batch_analysis` ToolUniverse tool** instead of running PhyKIT manually:
```bash
# Via CLI
tu run phykit_batch_analysis '{"operation":"batch","function":"treeness","directory":"/path/to/trees","extension":".treefile"}'

# Via SDK
tu.run_one_function({"name": "phykit_batch_analysis", "arguments": {"operation": "batch", "function": "saturation", "directory": "/path/to/alignments", "extension": ".fa", "tree_directory": "/path/to/trees"}})

# Gap percentage
tu run phykit_batch_analysis '{"operation":"gap_percentage","directory":"/path/to/alignments","extension":".fa"}'
```

Key rules:
1. **Process ALL files** — don't stop at a subset. The tool handles this automatically
2. **Gap percentage**: total gaps / total positions across all alignments (not per-file average)
3. **Long branch score**: each tree produces per-taxon scores → summarize per tree (mean) → then summarize across trees (median). Use `"per_tree_stat":"mean"`
4. **Fungi vs animal comparisons**: match genes by ortholog ID (filename stem), not by file order. Run the tool on each organism's directory separately, then compare medians

## References

`references/sequence_alignment.md`, `references/tree_building.md`, `references/parsimony_analysis.md`, `scripts/tree_statistics.py`
- PhyKIT: https://jlsteenwyk.com/PhyKIT/
- Biopython Phylo: https://biopython.org/wiki/Phylo
- DendroPy: https://dendropy.org/
