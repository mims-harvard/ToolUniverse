---
name: tooluniverse-phylogenetics
description: Production-ready phylogenetics and sequence analysis skill for alignment processing, tree analysis, and evolutionary metrics. Computes treeness, RCV, treeness/RCV, parsimony informative sites, evolutionary rate, DVMC, tree length, alignment gap statistics, GC content, and bootstrap support using PhyKIT, Biopython, and DendroPy. Performs NJ/UPGMA/parsimony tree construction, Robinson-Foulds distance, Mann-Whitney U tests, and batch analysis across gene families. Integrates with ToolUniverse for sequence retrieval (NCBI, UniProt, Ensembl) and tree annotation. Use when processing FASTA/PHYLIP/Nexus/Newick files, computing phylogenetic metrics, comparing taxa groups, or answering questions about alignments, trees, parsimony, or molecular evolution.
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

## References

`references/sequence_alignment.md`, `references/tree_building.md`, `references/parsimony_analysis.md`, `scripts/tree_statistics.py`
- PhyKIT: https://jlsteenwyk.com/PhyKIT/
- Biopython Phylo: https://biopython.org/wiki/Phylo
- DendroPy: https://dendropy.org/
