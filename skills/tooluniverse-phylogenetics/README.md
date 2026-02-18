# tooluniverse-phylogenetics

Production-ready phylogenetics and sequence analysis skill for the ToolUniverse ecosystem. Computes evolutionary metrics from multiple sequence alignments and phylogenetic trees using PhyKIT, Biopython, and DendroPy. Designed to solve BixBench phylogenetics questions with high accuracy.

## Coverage

- **33 BixBench questions** across 8 projects (bix-4, bix-11, bix-12, bix-25, bix-35, bix-38, bix-45, bix-60)
- Treeness, RCV, treeness/RCV, parsimony informative sites, evolutionary rate, DVMC, tree length
- Mann-Whitney U tests, medians, percentiles, paired comparisons
- Batch processing across hundreds of gene families

## Capabilities

| Capability | Description |
|-----------|-------------|
| **Treeness** | Internal branch length / total branch length (PhyKIT) |
| **RCV** | Relative Composition Variability (PhyKIT) |
| **Treeness/RCV** | Combined metric for alignment and tree quality |
| **Parsimony informative sites** | Sites with 2+ characters each appearing 2+ times |
| **Evolutionary rate** | Total branch length / number of terminals |
| **DVMC** | Degree of Violation of Molecular Clock |
| **Tree length** | Total sum of branch lengths |
| **Gap statistics** | Alignment gap percentage |
| **Tree construction** | NJ, UPGMA, Maximum Parsimony (Biopython) |
| **Tree comparison** | Robinson-Foulds distance (DendroPy) |
| **Bootstrap analysis** | Bootstrap support values |
| **Statistical tests** | Mann-Whitney U, paired differences, percentiles |

## Dependencies

```bash
pip install phykit dendropy ete3 biopython pandas numpy scipy
```

## File Structure

```
tooluniverse-phylogenetics/
  SKILL.md              # Full skill specification with all phases
  QUICK_START.md        # Quick start examples
  README.md             # This file
  test_phylogenetics.py # Comprehensive test suite (85 tests)
```

## Quick Example

```python
from types import SimpleNamespace
from phykit.services.tree.treeness import Treeness

t = Treeness(SimpleNamespace(tree="gene.nwk"))
tree = t.read_tree_file()
treeness = t.calculate_treeness(tree)
print(f"Treeness: {round(treeness, 4)}")
```

## Supported Formats

- **Alignments**: FASTA, PHYLIP, PHYLIP-relaxed, Nexus, Clustal, Stockholm
- **Trees**: Newick, Nexus

## ToolUniverse Integration

- NCBI sequence retrieval
- Ensembl Compara gene trees
- Open Tree of Life species trees
- UniProt sequence retrieval
