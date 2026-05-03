# Sequence Alignment Analysis

Detailed guide for analyzing multiple sequence alignments using Biopython and PhyKIT.

---

## File Loading and Format Detection

### Auto-detect Alignment Format

```python
from Bio import AlignIO

def load_alignment(filepath):
    """Load alignment with auto-format detection.

    Supports: FASTA, PHYLIP, PHYLIP-relaxed, Nexus, Clustal, Stockholm
    """
    # Try phylip-relaxed BEFORE phylip to avoid misparse of long names
    formats_to_try = ['fasta', 'phylip-relaxed', 'phylip', 'nexus', 'clustal', 'stockholm']

    for fmt in formats_to_try:
        try:
            alignment = AlignIO.read(filepath, fmt)
            return alignment, fmt
        except Exception:
            continue

    raise ValueError(f"Cannot parse alignment: {filepath}")
```

### Usage

```python
# Load any alignment format
alignment, format_detected = load_alignment("gene1.fa")
print(f"Format: {format_detected}")
print(f"Sequences: {len(alignment)}")
print(f"Length: {alignment.get_alignment_length()}")
```

---

## Parsimony Informative Sites

### PhyKIT Implementation

```python
from phykit.services.alignment.parsimony_informative_sites import ParsimonyInformative
from types import SimpleNamespace

def phykit_parsimony_informative(aln_file):
    """Calculate parsimony informative sites.

    Parsimony informative site: A site with at least 2 different characters
    appearing at least 2 times each (excluding gaps).

    Returns: (pi_sites_count, alignment_length, pi_percentage)
    """
    pi = ParsimonyInformative(SimpleNamespace(alignment=aln_file))
    alignment, _, _ = pi.get_alignment_and_format()
    return pi.calculate_parsimony_informative_sites(alignment)
```

### Example

```python
# Compute parsimony informative sites
pi_count, aln_len, pi_pct = phykit_parsimony_informative("alignment.fa")

print(f"Parsimony informative sites: {pi_count}")
print(f"Alignment length: {aln_len}")
print(f"Percentage: {pi_pct:.4f}%")
```

### Batch Processing

```python
def batch_parsimony_informative(gene_files):
    """Compute PI sites for multiple genes."""
    results = {}
    for entry in gene_files:
        if 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_parsimony_informative(entry['aln_file'])
            except Exception:
                pass  # Skip genes that fail
    return results

# Usage
pi_results = batch_parsimony_informative(gene_files)

# Extract just counts
pi_counts = {gene: result[0] for gene, result in pi_results.items()}

# Extract percentages
pi_percentages = {gene: result[2] for gene, result in pi_results.items()}
```

---

## Relative Composition Variability (RCV)

### PhyKIT Implementation

```python
from phykit.services.alignment.rcv import RelativeCompositionVariability

def phykit_rcv(aln_file):
    """Calculate Relative Composition Variability.

    RCV measures compositional heterogeneity across sequences.
    Lower values indicate more uniform base composition.

    Returns: float (RCV score)
    """
    rcv = RelativeCompositionVariability(SimpleNamespace(alignment=aln_file))
    return rcv.calculate_rcv()
```

### Example

```python
# Single alignment
rcv_score = phykit_rcv("alignment.fa")
print(f"RCV: {rcv_score:.4f}")

# Batch processing
def batch_rcv(gene_files):
    return batch_compute_metric(gene_files, phykit_rcv, requires='alignment')

rcv_results = batch_rcv(gene_files)
```

---

## Alignment Gap Analysis

### Gap Percentage

```python
import numpy as np

def alignment_gap_percentage(aln_file):
    """Calculate overall gap percentage in alignment.

    Gap characters: '-', '.', '?'

    Returns: percentage (0-100)
    """
    alignment, fmt = load_alignment(aln_file)
    n_seqs = len(alignment)
    aln_len = alignment.get_alignment_length()
    total_chars = n_seqs * aln_len

    # Convert to numpy array
    arr = np.array([[c for c in str(rec.seq)] for rec in alignment])

    # Count gaps
    gap_count = np.sum(np.isin(arr, ['-', '.', '?']))

    return (gap_count / total_chars) * 100
```

### Per-Sequence Gap Statistics

```python
def per_sequence_gaps(aln_file):
    """Calculate gap percentage for each sequence."""
    alignment, _ = load_alignment(aln_file)

    results = []
    for record in alignment:
        seq_str = str(record.seq)
        gap_count = seq_str.count('-') + seq_str.count('.') + seq_str.count('?')
        gap_pct = (gap_count / len(seq_str)) * 100
        results.append({
            'seq_id': record.id,
            'gap_count': gap_count,
            'gap_percentage': gap_pct
        })

    return results
```

---

## Comprehensive Alignment Statistics

### All-in-One Function

```python
def alignment_statistics(aln_file):
    """Comprehensive alignment statistics.

    Returns dict with:
    - n_seqs: Number of sequences
    - aln_len: Alignment length
    - gap_pct: Gap percentage
    - gc_pct: GC content
    - pi_sites: Parsimony informative sites count
    - pi_pct: Parsimony informative sites percentage
    - variable_sites: Number of variable sites
    - variable_pct: Variable sites percentage
    """
    alignment, fmt = load_alignment(aln_file)
    n_seqs = len(alignment)
    aln_len = alignment.get_alignment_length()

    # Convert to numpy array
    arr = np.array([[c.upper() for c in str(rec.seq)] for rec in alignment])

    # Gap percentage
    gap_count = np.sum(np.isin(arr, ['-', '.', '?']))
    gap_pct = (gap_count / (n_seqs * aln_len)) * 100

    # GC content (excluding gaps)
    non_gap = arr[~np.isin(arr, ['-', '.', '?', 'N'])]
    gc_count = np.sum(np.isin(non_gap, ['G', 'C']))
    gc_pct = (gc_count / len(non_gap)) * 100 if len(non_gap) > 0 else 0

    # Parsimony informative sites
    pi_sites, _, pi_pct = phykit_parsimony_informative(aln_file)

    # Variable sites
    variable_count = 0
    for i in range(aln_len):
        col = arr[:, i]
        non_gap_col = col[~np.isin(col, ['-', '.', '?'])]
        if len(np.unique(non_gap_col)) > 1:
            variable_count += 1

    return {
        'n_seqs': n_seqs,
        'aln_len': aln_len,
        'gap_pct': round(gap_pct, 4),
        'gc_pct': round(gc_pct, 4),
        'pi_sites': pi_sites,
        'pi_pct': round(pi_pct, 4),
        'variable_sites': variable_count,
        'variable_pct': round((variable_count / aln_len) * 100, 4)
    }
```

### Example

```python
# Get comprehensive stats
stats = alignment_statistics("alignment.fa")

print(f"Sequences: {stats['n_seqs']}")
print(f"Length: {stats['aln_len']}")
print(f"Gaps: {stats['gap_pct']:.2f}%")
print(f"GC: {stats['gc_pct']:.2f}%")
print(f"PI sites: {stats['pi_sites']} ({stats['pi_pct']:.2f}%)")
print(f"Variable sites: {stats['variable_sites']} ({stats['variable_pct']:.2f}%)")
```

---

## Format Conversion

### Convert Between Formats

```python
def convert_alignment_format(input_file, output_file, output_format='fasta'):
    """Convert alignment to different format.

    Supported formats: fasta, phylip, phylip-relaxed, nexus, clustal
    """
    alignment, input_format = load_alignment(input_file)
    AlignIO.write(alignment, output_file, output_format)
    return output_format
```

### Example

```python
# Convert PHYLIP to FASTA
convert_alignment_format("alignment.phy", "alignment.fa", "fasta")

# Convert FASTA to Nexus
convert_alignment_format("alignment.fa", "alignment.nex", "nexus")
```

---

## Filtering Alignments

### By Gap Threshold

```python
def filter_by_gap_threshold(gene_files, max_gap_pct=5.0):
    """Filter alignments by maximum gap percentage.

    Returns: list of gene entries passing threshold
    """
    valid_genes = []
    for entry in gene_files:
        if 'aln_file' in entry:
            try:
                gap_pct = alignment_gap_percentage(entry['aln_file'])
                if gap_pct <= max_gap_pct:
                    valid_genes.append(entry)
            except Exception:
                pass
    return valid_genes
```

### By Minimum Sequences

```python
def filter_by_min_sequences(gene_files, min_seqs=4):
    """Filter alignments by minimum number of sequences."""
    valid_genes = []
    for entry in gene_files:
        if 'aln_file' in entry:
            try:
                alignment, _ = load_alignment(entry['aln_file'])
                if len(alignment) >= min_seqs:
                    valid_genes.append(entry)
            except Exception:
                pass
    return valid_genes
```

### Combined Filtering

```python
# Filter by multiple criteria
valid_genes = gene_files
valid_genes = filter_by_gap_threshold(valid_genes, max_gap_pct=5.0)
valid_genes = filter_by_min_sequences(valid_genes, min_seqs=4)

print(f"Genes passing filters: {len(valid_genes)}/{len(gene_files)}")
```

---

## BixBench Patterns

### Pattern: Median Parsimony Sites

```python
# Question: "What is the median number of parsimony informative sites?"

# 1. Batch compute
pi_results = batch_parsimony_informative(gene_files)

# 2. Extract counts
pi_counts = [result[0] for result in pi_results.values()]

# 3. Compute median
median_pi = np.median(pi_counts)

print(f"Median PI sites: {median_pi:.4f}")
```

### Pattern: Percentage Above Threshold

```python
# Question: "What percentage of alignments have >100 PI sites?"

pi_counts = [result[0] for result in pi_results.values()]
above_threshold = sum(1 for count in pi_counts if count > 100)
percentage = (above_threshold / len(pi_counts)) * 100

print(f"Percentage > 100 PI sites: {percentage:.2f}%")
```

### Pattern: Ratio of Minimums

```python
# Question: "What is the ratio of minimum PI sites (fungi / animals)?"

fungi_pi = batch_parsimony_informative(fungi_genes)
animal_pi = batch_parsimony_informative(animal_genes)

fungi_counts = [r[0] for r in fungi_pi.values()]
animal_counts = [r[0] for r in animal_pi.values()]

ratio = min(fungi_counts) / min(animal_counts)

print(f"Ratio of minimums: {ratio:.4f}")
```

---

## Troubleshooting

### "Cannot parse alignment" Error

**Cause**: Format detection failed.

**Solution**: Try specifying format explicitly:
```python
alignment = AlignIO.read("file.phy", "phylip-relaxed")
```

### Long Sequence Names in PHYLIP

**Issue**: PHYLIP format truncates names to 10 characters.

**Solution**: Use `phylip-relaxed` format:
```python
alignment = AlignIO.read("file.phy", "phylip-relaxed")
```

### Empty PI Sites

**Cause**: Alignment lacks informative sites (too few sequences or too conserved).

**Solution**: Check alignment quality:
```python
stats = alignment_statistics("alignment.fa")
print(f"Variable sites: {stats['variable_sites']}")
```

---

## See Also

- `tree_building.md` - Tree construction from alignments
- `parsimony_analysis.md` - Statistical comparison workflows
- `scripts/format_alignment.py` - Format conversion utilities
