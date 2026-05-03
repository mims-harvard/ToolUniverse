# Tree Building and Analysis

Detailed guide for phylogenetic tree construction and analysis using Biopython, PhyKIT, and DendroPy.

---

## Tree File Loading

### Auto-detect Tree Format

```python
from Bio import Phylo
import io

def load_tree(filepath):
    """Load tree with auto-format detection.

    Supports: Newick, Nexus
    """
    with open(filepath, 'r') as f:
        content = f.read().strip()

    # Try Newick first (most common)
    try:
        tree = Phylo.read(io.StringIO(content), 'newick')
        return tree, 'newick'
    except Exception:
        pass

    # Try Nexus
    try:
        tree = Phylo.read(io.StringIO(content), 'nexus')
        return tree, 'nexus'
    except Exception:
        pass

    raise ValueError(f"Cannot parse tree: {filepath}")
```

### Usage

```python
# Load any tree format
tree, format_detected = load_tree("gene1.nwk")
print(f"Format: {format_detected}")
print(f"Terminals: {tree.count_terminals()}")
```

---

## PhyKIT Tree Metrics

### Treeness

```python
from phykit.services.tree.treeness import Treeness
from types import SimpleNamespace

def phykit_treeness(tree_file):
    """Calculate treeness (internal branch length / total branch length).

    Treeness measures the proportion of tree length on internal branches.
    Higher values (closer to 1) indicate stronger phylogenetic signal.

    Returns: float (0-1)
    """
    t = Treeness(SimpleNamespace(tree=tree_file))
    tree = t.read_tree_file()
    return t.calculate_treeness(tree)
```

### Tree Length

```python
from phykit.services.tree.total_tree_length import TotalTreeLength

def phykit_tree_length(tree_file):
    """Calculate total tree length (sum of all branch lengths).

    Returns: float
    """
    tl = TotalTreeLength(SimpleNamespace(tree=tree_file))
    tree = tl.read_tree_file()
    return tl.calculate_total_tree_length(tree)
```

### Evolutionary Rate

```python
from phykit.services.tree.evolutionary_rate import EvolutionaryRate

def phykit_evolutionary_rate(tree_file):
    """Calculate evolutionary rate (total branch length / number of terminals).

    Represents average substitution rate per lineage.

    Returns: float
    """
    er = EvolutionaryRate(SimpleNamespace(tree=tree_file))
    tree = er.read_tree_file()
    total_bl = tree.total_branch_length()
    num_terminals = tree.count_terminals()
    return total_bl / num_terminals
```

### Degree of Violation of Molecular Clock (DVMC)

```python
from phykit.services.tree.dvmc import DVMC

def phykit_dvmc(tree_file):
    """Calculate Degree of Violation of Molecular Clock.

    DVMC is the standard deviation of root-to-tip distances.
    Lower values indicate tree is more clock-like.

    Returns: float
    """
    d = DVMC(SimpleNamespace(tree=tree_file))
    tree = d.read_tree_file()
    return d.determine_dvmc(tree)
```

### Treeness/RCV

```python
def phykit_treeness_over_rcv(tree_file, aln_file):
    """Calculate treeness/RCV ratio.

    Combines phylogenetic signal (treeness) with compositional uniformity (RCV).
    Higher values indicate better phylogenetic quality.

    Returns: (treeness_over_rcv, treeness, rcv)
    """
    treeness = phykit_treeness(tree_file)
    rcv = phykit_rcv(aln_file)

    if rcv == 0:
        return float('inf'), treeness, rcv

    return treeness / rcv, treeness, rcv
```

---

## Distance-Based Tree Construction

### Neighbor-Joining (NJ)

```python
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor

def build_nj_tree(aln_file, model='identity'):
    """Build Neighbor-Joining tree from alignment.

    NJ is fast and reasonably accurate for most cases.

    Args:
        aln_file: path to alignment file
        model: distance model ('identity' or 'blosum62')

    Returns: Biopython Phylo.BaseTree
    """
    alignment, _ = load_alignment(aln_file)
    calculator = DistanceCalculator(model)
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    return constructor.nj(dm)
```

### UPGMA

```python
def build_upgma_tree(aln_file, model='identity'):
    """Build UPGMA tree from alignment.

    UPGMA assumes molecular clock. Only use for ultrametric data.

    Args:
        aln_file: path to alignment file
        model: distance model ('identity' or 'blosum62')

    Returns: Biopython Phylo.BaseTree
    """
    alignment, _ = load_alignment(aln_file)
    calculator = DistanceCalculator(model)
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    return constructor.upgma(dm)
```

### Saving Trees

```python
# Build tree
tree = build_nj_tree("alignment.fa")

# Save as Newick
Phylo.write(tree, "tree.nwk", "newick")

# Save as Nexus
Phylo.write(tree, "tree.nex", "nexus")
```

---

## Maximum Parsimony Tree Construction

### Simple Parsimony Search

```python
from Bio.Phylo.TreeConstruction import ParsimonyScorer, NNITreeSearcher, ParsimonyTreeConstructor

def build_parsimony_tree(aln_file):
    """Build Maximum Parsimony tree from alignment.

    Uses Nearest Neighbor Interchange (NNI) search.
    Best for small alignments (<50 sequences).

    Returns: Biopython Phylo.BaseTree
    """
    alignment, _ = load_alignment(aln_file)

    # Start with NJ tree
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    starting_tree = constructor.nj(dm)

    # Parsimony search
    scorer = ParsimonyScorer()
    searcher = NNITreeSearcher(scorer)
    pars_constructor = ParsimonyTreeConstructor(searcher, starting_tree)

    return pars_constructor.build_tree(alignment)
```

### Getting Parsimony Score

```python
from Bio.Phylo.TreeConstruction import ParsimonyScorer

def get_parsimony_score(tree, alignment):
    """Calculate parsimony score for a tree.

    Lower scores indicate fewer required substitutions.

    Returns: int (total substitutions)
    """
    scorer = ParsimonyScorer()
    return scorer.get_score(tree, alignment)
```

---

## Bootstrap Analysis

### Bootstrap Support

```python
from Bio.Phylo.Consensus import bootstrap_consensus, bootstrap_trees, majority_consensus

def bootstrap_analysis(aln_file, n_replicates=100, model='identity'):
    """Perform bootstrap analysis on alignment.

    Generates bootstrap replicates and builds consensus tree.

    Args:
        aln_file: path to alignment
        n_replicates: number of bootstrap replicates (default 100)
        model: distance model

    Returns: consensus tree with support values
    """
    alignment, _ = load_alignment(aln_file)
    calculator = DistanceCalculator(model)
    constructor = DistanceTreeConstructor(calculator, 'nj')

    # Generate bootstrap trees
    trees = list(bootstrap_trees(alignment, n_replicates, constructor))

    # Build majority consensus
    consensus = majority_consensus(trees, cutoff=0.5)

    return consensus
```

### Extracting Bootstrap Support Values

```python
def extract_bootstrap_support(tree_file):
    """Extract bootstrap support values from internal nodes.

    Returns: dict with support statistics
    """
    tree, _ = load_tree(tree_file)

    supports = []
    for clade in tree.get_nonterminals():
        if clade.confidence is not None:
            supports.append(clade.confidence)

    if not supports:
        return {'supports': [], 'mean': None, 'median': None}

    return {
        'supports': supports,
        'mean': float(np.mean(supports)),
        'median': float(np.median(supports)),
        'min': float(np.min(supports)),
        'max': float(np.max(supports)),
        'n_nodes': len(supports),
        'above_70': sum(1 for s in supports if s >= 70),
        'above_90': sum(1 for s in supports if s >= 90),
    }
```

---

## Branch Length Analysis

### Branch Statistics

```python
def tree_branch_stats(tree_file):
    """Compute branch length statistics from a tree.

    Returns: dict with branch statistics
    """
    tree, _ = load_tree(tree_file)

    internal_lengths = []
    terminal_lengths = []

    for clade in tree.find_clades():
        if clade.branch_length is not None:
            if clade.is_terminal():
                terminal_lengths.append(clade.branch_length)
            else:
                internal_lengths.append(clade.branch_length)

    all_lengths = internal_lengths + terminal_lengths

    return {
        'total_length': sum(all_lengths),
        'n_internal': len(internal_lengths),
        'n_terminal': len(terminal_lengths),
        'internal_sum': sum(internal_lengths),
        'terminal_sum': sum(terminal_lengths),
        'mean_branch': np.mean(all_lengths) if all_lengths else 0,
        'max_branch': max(all_lengths) if all_lengths else 0,
        'min_branch': min(all_lengths) if all_lengths else 0,
    }
```

### Example

```python
stats = tree_branch_stats("tree.nwk")

print(f"Total length: {stats['total_length']:.4f}")
print(f"Internal branches: {stats['n_internal']}")
print(f"Terminal branches: {stats['n_terminal']}")
print(f"Mean branch length: {stats['mean_branch']:.4f}")
```

---

## Tree Comparison

### Robinson-Foulds Distance

```python
import dendropy
from dendropy.calculate import treecompare

def robinson_foulds_distance(tree_file1, tree_file2):
    """Calculate Robinson-Foulds distance between two trees.

    RF distance measures topological difference between trees.
    0 = identical topology, higher = more different.

    Returns: int (number of differing splits)
    """
    tree1 = dendropy.Tree.get(path=tree_file1, schema="newick")
    tree2 = dendropy.Tree.get(
        path=tree_file2,
        schema="newick",
        taxon_namespace=tree1.taxon_namespace  # Must share namespace
    )

    return treecompare.symmetric_difference(tree1, tree2)
```

### Weighted Robinson-Foulds

```python
def weighted_robinson_foulds(tree_file1, tree_file2):
    """Calculate weighted RF distance (includes branch lengths)."""
    tree1 = dendropy.Tree.get(path=tree_file1, schema="newick")
    tree2 = dendropy.Tree.get(
        path=tree_file2,
        schema="newick",
        taxon_namespace=tree1.taxon_namespace
    )

    return treecompare.weighted_robinson_foulds_distance(tree1, tree2)
```

---

## Batch Processing

### Tree Metric Batching

```python
def batch_treeness(gene_files):
    """Compute treeness for all genes."""
    return batch_compute_metric(gene_files, phykit_treeness, requires='tree')

def batch_tree_length(gene_files):
    """Compute tree length for all genes."""
    return batch_compute_metric(gene_files, phykit_tree_length, requires='tree')

def batch_evolutionary_rate(gene_files):
    """Compute evolutionary rate for all genes."""
    return batch_compute_metric(gene_files, phykit_evolutionary_rate, requires='tree')

def batch_dvmc(gene_files):
    """Compute DVMC for all genes."""
    return batch_compute_metric(gene_files, phykit_dvmc, requires='tree')

def batch_treeness_over_rcv(gene_files):
    """Compute treeness/RCV for all genes (requires both tree and alignment)."""
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

## Decision Guide: Which Tree Method?

### For Exploratory Analysis

**Use Neighbor-Joining (NJ)**:
- Fast and reasonably accurate
- No assumptions about clock-like evolution
- Good for initial tree estimation

```python
tree = build_nj_tree("alignment.fa")
```

### For Clock-Like Data

**Use UPGMA**:
- Assumes molecular clock (equal evolutionary rates)
- Faster than NJ
- Only if data truly clock-like

```python
tree = build_upgma_tree("alignment.fa")
```

### For Small Datasets

**Use Maximum Parsimony**:
- Good for discrete characters
- Interpretable (minimum substitutions)
- Slow for large datasets

```python
tree = build_parsimony_tree("alignment.fa")
```

### For Production Analysis

**Use External Tools**:
- **IQ-TREE**: Fast Maximum Likelihood, automatic model selection
- **RAxML**: Maximum Likelihood, bootstrap support
- **PhyML**: Fast ML for moderate datasets
- **MrBayes**: Bayesian inference

Then analyze resulting trees with this skill:
```python
# After running IQ-TREE externally
treeness = phykit_treeness("iqtree_output.treefile")
dvmc = phykit_dvmc("iqtree_output.treefile")
```

---

## BixBench Patterns

### Pattern: Median Treeness

```python
# Question: "What is the median treeness for fungi?"

# 1. Discover and compute
fungi_genes = discover_gene_files("data/fungi")
fungi_treeness = batch_treeness(fungi_genes)

# 2. Extract values
treeness_values = list(fungi_treeness.values())

# 3. Compute median
median_treeness = np.median(treeness_values)

print(f"Median treeness: {median_treeness:.4f}")
```

### Pattern: Percentage Above Threshold

```python
# Question: "What percentage of trees have treeness > 0.5?"

treeness_values = list(batch_treeness(gene_files).values())
above_threshold = sum(1 for v in treeness_values if v > 0.5)
percentage = (above_threshold / len(treeness_values)) * 100

print(f"Percentage > 0.5: {percentage:.2f}%")
```

### Pattern: Fold Change

```python
# Question: "What is the fold change in median tree length (fungi / animals)?"

fungi_lengths = list(batch_tree_length(fungi_genes).values())
animal_lengths = list(batch_tree_length(animal_genes).values())

fold_change = np.median(fungi_lengths) / np.median(animal_lengths)

print(f"Fold change: {fold_change:.4f}")
```

---

## Troubleshooting

### "Cannot parse tree" Error

**Cause**: Format detection failed or malformed Newick.

**Solution**: Check Newick syntax:
```python
# Valid Newick must end with semicolon
# (A:0.1,B:0.2,(C:0.3,D:0.4):0.5);
```

### Missing Branch Lengths

**Issue**: Tree has no branch lengths for PhyKIT metrics.

**Solution**: PhyKIT requires branch lengths. Rebuild tree with distances:
```python
tree = build_nj_tree("alignment.fa")  # NJ always has branch lengths
```

### Bootstrap Values Not Found

**Issue**: `extract_bootstrap_support()` returns empty list.

**Solution**: Check if tree has confidence values:
```python
tree, _ = load_tree("tree.nwk")
for clade in tree.get_nonterminals():
    print(f"Confidence: {clade.confidence}")
```

If None, tree doesn't have bootstrap support. Run bootstrap analysis:
```python
consensus = bootstrap_analysis("alignment.fa", n_replicates=100)
```

---

## See Also

- `sequence_alignment.md` - Alignment analysis
- `parsimony_analysis.md` - Statistical workflows
- `scripts/tree_statistics.py` - Implementation code
