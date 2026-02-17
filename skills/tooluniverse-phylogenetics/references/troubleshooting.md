# Troubleshooting Guide

Common issues and solutions for phylogenetics skill.

---

## File Loading Issues

### "Cannot parse alignment" Error

**Symptoms**: `ValueError: Cannot parse alignment: file.fa`

**Causes**:
1. Invalid file format
2. Corrupted file
3. Wrong file extension

**Solutions**:

```python
# Try specifying format explicitly
from Bio import AlignIO
alignment = AlignIO.read("file.phy", "phylip-relaxed")

# Check file contents
with open("file.fa", 'r') as f:
    print(f.read()[:200])  # First 200 characters

# Try different formats
for fmt in ['fasta', 'phylip', 'phylip-relaxed', 'nexus', 'clustal']:
    try:
        aln = AlignIO.read("file.fa", fmt)
        print(f"Success with format: {fmt}")
        break
    except Exception as e:
        print(f"Failed with {fmt}: {e}")
```

### "Cannot parse tree" Error

**Symptoms**: `ValueError: Cannot parse tree: file.nwk`

**Causes**:
1. Missing semicolon (Newick must end with `;`)
2. Invalid Newick syntax
3. File encoding issues

**Solutions**:

```python
# Check tree syntax
with open("file.nwk", 'r') as f:
    content = f.read()
    print(content)
    if not content.strip().endswith(';'):
        print("ERROR: Newick tree must end with semicolon")

# Fix missing semicolon
with open("file.nwk", 'r') as f:
    content = f.read().strip()
if not content.endswith(';'):
    with open("file_fixed.nwk", 'w') as f:
        f.write(content + ';\n')

# Try loading
from Bio import Phylo
tree = Phylo.read("file_fixed.nwk", "newick")
```

---

## PhyKIT Errors

### "PhyKIT: AttributeError: 'NoneType' object has no attribute..."

**Symptoms**: PhyKIT functions crash with NoneType errors

**Causes**:
1. Tree has no branch lengths
2. Invalid tree structure
3. Empty alignment

**Solutions**:

```python
# Check if tree has branch lengths
from Bio import Phylo
tree = Phylo.read("tree.nwk", "newick")

has_branch_lengths = all(
    clade.branch_length is not None
    for clade in tree.find_clades()
)

if not has_branch_lengths:
    print("ERROR: Tree missing branch lengths")
    print("Solution: Rebuild tree with distance method (NJ, UPGMA)")

# Rebuild with NJ
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
alignment = AlignIO.read("alignment.fa", "fasta")
calculator = DistanceCalculator('identity')
dm = calculator.get_distance(alignment)
constructor = DistanceTreeConstructor()
tree_with_lengths = constructor.nj(dm)
Phylo.write(tree_with_lengths, "tree_fixed.nwk", "newick")
```

### PhyKIT Returns Unexpected Values

**Symptoms**: Treeness > 1.0 or negative values

**Causes**:
1. Invalid input data
2. PhyKIT version mismatch

**Solutions**:

```python
# Check PhyKIT version
import phykit
print(f"PhyKIT version: {phykit.__version__}")

# Validate tree
tree = Phylo.read("tree.nwk", "newick")
total_length = sum(c.branch_length for c in tree.find_clades() if c.branch_length)
print(f"Total tree length: {total_length}")

if total_length <= 0:
    print("ERROR: Tree has zero or negative branch lengths")
```

---

## Data Discovery Issues

### No Files Found by `discover_gene_files()`

**Symptoms**: Function returns empty list

**Causes**:
1. Wrong directory path
2. Unexpected file extensions
3. Subdirectory structure not as expected

**Solutions**:

```python
import os
import glob

# Check directory exists
data_dir = "data/"
if not os.path.exists(data_dir):
    print(f"ERROR: Directory {data_dir} not found")

# List files manually
print("Files in directory:")
for root, dirs, files in os.walk(data_dir):
    for f in files:
        print(os.path.join(root, f))

# Check for specific extensions
aln_files = glob.glob(os.path.join(data_dir, '**', '*.fa'), recursive=True)
tree_files = glob.glob(os.path.join(data_dir, '**', '*.nwk'), recursive=True)
print(f"Found {len(aln_files)} .fa files")
print(f"Found {len(tree_files)} .nwk files")

# Adjust extensions if needed
if len(aln_files) == 0:
    # Try other extensions
    for ext in ['*.fasta', '*.faa', '*.phy']:
        files = glob.glob(os.path.join(data_dir, '**', ext), recursive=True)
        if files:
            print(f"Found {len(files)} {ext} files")
```

### Mismatched Gene IDs

**Symptoms**: Alignment and tree files don't match

**Causes**:
1. Different naming conventions
2. Suffixes not handled by `discover_gene_files()`

**Solutions**:

```python
# Debug gene ID extraction
import os

def debug_gene_id_extraction(filepath):
    basename = os.path.basename(filepath)
    gene_id = os.path.splitext(basename)[0]
    print(f"File: {basename} -> Gene ID: {gene_id}")

# Test on your files
debug_gene_id_extraction("gene1.aligned.fa")
debug_gene_id_extraction("gene1.nwk")

# If IDs don't match, add custom suffix handling
def discover_gene_files_custom(data_dir):
    # Add your custom suffixes
    custom_suffixes = ['.aligned', '.aln', '.msa', '_aligned',
                      '.treefile', '_tree', '.YOUR_SUFFIX']
    # ... rest of function
```

---

## Batch Processing Issues

### Some Genes Fail Silently

**Symptoms**: Fewer results than input genes

**Causes**:
1. Malformed files (expected, handled by try/except)
2. Missing required files
3. Computation errors

**Solutions**:

```python
# Track failures explicitly
def batch_compute_metric_verbose(gene_files, metric_func, requires='tree'):
    results = {}
    failures = []

    for entry in gene_files:
        gene_id = entry['gene_id']
        try:
            if requires == 'tree' and 'tree_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'])
            elif requires == 'alignment' and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['aln_file'])
        except Exception as e:
            failures.append({
                'gene_id': gene_id,
                'error': str(e),
                'file': entry.get('tree_file') or entry.get('aln_file')
            })

    print(f"Success: {len(results)}/{len(gene_files)}")
    print(f"Failures: {len(failures)}")

    if failures:
        print("\nFirst 5 failures:")
        for fail in failures[:5]:
            print(f"  {fail['gene_id']}: {fail['error'][:50]}")

    return results, failures

# Use verbose version for debugging
results, failures = batch_compute_metric_verbose(
    gene_files, phykit_treeness, requires='tree'
)
```

### Out of Memory Errors

**Symptoms**: Process crashes with large datasets

**Causes**:
1. Too many genes processed at once
2. Large alignment files

**Solutions**:

```python
# Process in batches
def batch_compute_in_chunks(gene_files, metric_func, requires='tree', chunk_size=100):
    all_results = {}

    for i in range(0, len(gene_files), chunk_size):
        chunk = gene_files[i:i+chunk_size]
        print(f"Processing chunk {i//chunk_size + 1} ({len(chunk)} genes)...")

        chunk_results = batch_compute_metric(chunk, metric_func, requires)
        all_results.update(chunk_results)

    return all_results

# Use chunked processing
results = batch_compute_in_chunks(gene_files, phykit_treeness, chunk_size=50)
```

---

## Statistical Analysis Issues

### Mann-Whitney U Test Fails

**Symptoms**: `ValueError: All numbers are identical` or similar

**Causes**:
1. No variation in data (all values identical)
2. Too few samples

**Solutions**:

```python
# Check for variation
import numpy as np

def safe_mannwhitneyu(group1, group2):
    """Mann-Whitney U with error handling."""
    arr1 = np.array(group1)
    arr2 = np.array(group2)

    # Check for variation
    if len(np.unique(arr1)) == 1 and len(np.unique(arr2)) == 1:
        if arr1[0] == arr2[0]:
            print("WARNING: No variation in either group")
            return None, 1.0  # p=1.0 means no difference

    # Check sample size
    if len(arr1) < 3 or len(arr2) < 3:
        print("WARNING: Sample size too small for Mann-Whitney U")
        return None, None

    try:
        return stats.mannwhitneyu(arr1, arr2, alternative='two-sided')
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None

# Usage
u_stat, p_value = safe_mannwhitneyu(group1_values, group2_values)
if u_stat is not None:
    print(f"U: {u_stat:.0f}, p: {p_value:.4e}")
```

---

## Rounding and Precision Issues

### Answer Doesn't Match Expected

**Symptoms**: Your answer is close but not exact

**Causes**:
1. Wrong rounding precision
2. Different PhyKIT version
3. Float precision differences

**Solutions**:

```python
# Check PhyKIT default precision
value = phykit_treeness("tree.nwk")
print(f"Raw value: {value}")
print(f"4 decimals: {round(value, 4)}")
print(f"3 decimals: {round(value, 3)}")
print(f"2 decimals: {round(value, 2)}")

# Match question rounding
# "rounded to 3 decimal places" -> round(value, 3)
# "rounded to nearest integer" -> round(value)
# "multiplied by 1000" -> round(value * 1000)

# For percentages, check format
percentage = 34.5678
print(f"Integer: {round(percentage)}")  # 35
print(f"1 decimal: {round(percentage, 1)}")  # 34.6
print(f"2 decimals: {round(percentage, 2)}")  # 34.57
```

---

## Tree Construction Issues

### NJ/UPGMA Tree Construction Fails

**Symptoms**: Error during tree building

**Causes**:
1. Alignment too short
2. Sequences too similar (zero distances)
3. Invalid alignment

**Solutions**:

```python
# Check alignment quality
from Bio import AlignIO

alignment = AlignIO.read("alignment.fa", "fasta")
print(f"Sequences: {len(alignment)}")
print(f"Length: {alignment.get_alignment_length()}")

if len(alignment) < 3:
    print("ERROR: Need at least 3 sequences for tree")

if alignment.get_alignment_length() < 10:
    print("WARNING: Alignment very short")

# Check distance matrix
from Bio.Phylo.TreeConstruction import DistanceCalculator

calculator = DistanceCalculator('identity')
dm = calculator.get_distance(alignment)
print("Distance matrix:")
print(dm)

# If all distances are 0, sequences are identical
```

### Parsimony Tree Takes Too Long

**Symptoms**: `build_parsimony_tree()` doesn't finish

**Causes**:
1. Too many sequences (parsimony is slow)
2. Long alignment

**Solutions**:

```python
# Check size
alignment = AlignIO.read("alignment.fa", "fasta")
n_seqs = len(alignment)
aln_len = alignment.get_alignment_length()

print(f"Size: {n_seqs} sequences x {aln_len} sites")

if n_seqs > 50:
    print("WARNING: Parsimony will be very slow for >50 sequences")
    print("Recommendation: Use NJ instead, or use external tools (IQ-TREE, RAxML)")

# Use NJ as faster alternative
tree = build_nj_tree("alignment.fa")
```

---

## Performance Issues

### Slow Batch Processing

**Symptoms**: Processing takes very long

**Causes**:
1. Many genes
2. Large files
3. Inefficient I/O

**Solutions**:

```python
# Add progress tracking
from tqdm import tqdm

def batch_compute_with_progress(gene_files, metric_func, requires='tree'):
    results = {}
    for entry in tqdm(gene_files, desc="Processing genes"):
        gene_id = entry['gene_id']
        try:
            if requires == 'tree' and 'tree_file' in entry:
                results[gene_id] = metric_func(entry['tree_file'])
            elif requires == 'alignment' and 'aln_file' in entry:
                results[gene_id] = metric_func(entry['aln_file'])
        except Exception:
            pass
    return results

# Use with progress bar
results = batch_compute_with_progress(gene_files, phykit_treeness)
```

---

## BixBench-Specific Issues

### Answer Format Mismatch

**Symptoms**: Answer rejected by BixBench

**Causes**:
1. Wrong type (float vs int)
2. Wrong precision
3. Scientific notation vs decimal

**Solutions**:

```python
# Common BixBench answer formats

# Integer (U statistic, counts)
answer = int(round(value))

# Float with 4 decimals (PhyKIT default)
answer = round(value, 4)

# Percentage as integer
answer = int(round(percentage))

# Percentage with decimals
answer = round(percentage, 2)

# Scientific notation for small p-values
if p_value < 0.0001:
    answer = f"{p_value:.2e}"  # e.g., "1.23e-05"
else:
    answer = round(p_value, 4)

# Multiplied values
answer = int(round(value * 1000))
```

---

## Getting Help

### Enable Debug Output

```python
# For PhyKIT issues
import logging
logging.basicConfig(level=logging.DEBUG)

# For Biopython issues
from Bio import BiopythonWarning
import warnings
warnings.simplefilter('always', BiopythonWarning)
```

### Check Versions

```python
import phykit
import Bio
import dendropy
import numpy
import scipy

print(f"PhyKIT: {phykit.__version__}")
print(f"Biopython: {Bio.__version__}")
print(f"DendroPy: {dendropy.__version__}")
print(f"NumPy: {numpy.__version__}")
print(f"SciPy: {scipy.__version__}")
```

### Test with Simple Example

```python
# Create minimal test files
test_alignment = ">seq1\nACGT\n>seq2\nACGT\n>seq3\nTCGA\n"
with open("test.fa", 'w') as f:
    f.write(test_alignment)

# Test alignment loading
alignment = AlignIO.read("test.fa", "fasta")
print(f"Loaded {len(alignment)} sequences")

# Test tree building
tree = build_nj_tree("test.fa")
Phylo.write(tree, "test.nwk", "newick")

# Test PhyKIT
treeness = phykit_treeness("test.nwk")
print(f"Treeness: {treeness:.4f}")
```

---

## See Also

- `sequence_alignment.md` - Alignment analysis details
- `tree_building.md` - Tree construction methods
- `parsimony_analysis.md` - Statistical workflows
- PhyKIT documentation: https://jlsteenwyk.com/PhyKIT/
- Biopython Phylo tutorial: https://biopython.org/wiki/Phylo
