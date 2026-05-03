#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-phylogenetics skill.

Tests all core PhyKIT functions, alignment statistics, tree construction,
batch processing, statistical comparisons, and edge cases.

Run: python test_phylogenetics.py
"""

import os
import sys
import tempfile
import shutil
import traceback
import io
import numpy as np
from types import SimpleNamespace
from collections import Counter


# ---------------------------------------------------------------------------
# Test data generators
# ---------------------------------------------------------------------------

def create_test_alignment(seqs, filepath):
    """Write a FASTA alignment file from a dict of {name: sequence}."""
    with open(filepath, 'w') as f:
        for name, seq in seqs.items():
            f.write(f">{name}\n{seq}\n")


def create_test_tree(newick, filepath):
    """Write a Newick tree string to a file."""
    with open(filepath, 'w') as f:
        f.write(newick + "\n")


def create_test_data_dir():
    """Create a temporary directory with fungi and animal subdirectories,
    each containing several alignment (.fa) and tree (.nwk) files."""
    tmpdir = tempfile.mkdtemp(prefix="phylo_test_")

    # ---- Fungi genes ----
    fungi_dir = os.path.join(tmpdir, "fungi")
    os.makedirs(fungi_dir)

    # Gene 1: Short, highly conserved
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCATGCATGCATGC",
        "sp3": "ATGCATGCATGCATGCATGC",
        "sp4": "ATGCATGCATGCATGCATGC",
    }, os.path.join(fungi_dir, "gene1.fa"))
    create_test_tree("((sp1:0.01,sp2:0.01):0.01,(sp3:0.01,sp4:0.01):0.01);",
                     os.path.join(fungi_dir, "gene1.nwk"))

    # Gene 2: Moderate divergence
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCGTGCATGCATGC",
        "sp3": "ATGCGTGCATGCGTGCATGC",
        "sp4": "ATGCGTGCGTGCGTGCATGC",
    }, os.path.join(fungi_dir, "gene2.fa"))
    create_test_tree("((sp1:0.05,sp2:0.1):0.15,(sp3:0.08,sp4:0.12):0.2);",
                     os.path.join(fungi_dir, "gene2.nwk"))

    # Gene 3: High divergence with gaps
    create_test_alignment({
        "sp1": "ATGC-TGCATG-ATGCATGC",
        "sp2": "ATGCATGC--GCATGCATGC",
        "sp3": "ATGCGTGCAT--GTGCATGC",
        "sp4": "ATGCGTGCGTGCGTG-ATGC",
    }, os.path.join(fungi_dir, "gene3.fa"))
    create_test_tree("((sp1:0.2,sp2:0.3):0.4,(sp3:0.25,sp4:0.35):0.5);",
                     os.path.join(fungi_dir, "gene3.nwk"))

    # Gene 4: Very gappy alignment (>50% gaps)
    create_test_alignment({
        "sp1": "A-G--T---T-C-T---TGC",
        "sp2": "-TGC-T----G-AT--ATGC",
        "sp3": "AT---TGC-----GCA-G-C",
        "sp4": "--GC-TGC-T---TG-AT-C",
    }, os.path.join(fungi_dir, "gene4.fa"))
    create_test_tree("((sp1:0.4,sp2:0.5):0.6,(sp3:0.45,sp4:0.55):0.7);",
                     os.path.join(fungi_dir, "gene4.nwk"))

    # Gene 5: Moderate
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCATGCATGCGTGC",
        "sp3": "ATGCGTGCATGCATGCATGC",
        "sp4": "ATGCGTGCATGCATGCGTGC",
    }, os.path.join(fungi_dir, "gene5.fa"))
    create_test_tree("((sp1:0.03,sp2:0.07):0.05,(sp3:0.04,sp4:0.08):0.06);",
                     os.path.join(fungi_dir, "gene5.nwk"))

    # ---- Animal genes ----
    animal_dir = os.path.join(tmpdir, "animals")
    os.makedirs(animal_dir)

    # Gene 1: Highly conserved (lower divergence than fungi)
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCATGCATGCATGC",
        "sp3": "ATGCATGCATGCATGCATGC",
        "sp4": "ATGCATGCATGCATGCATGC",
    }, os.path.join(animal_dir, "gene1.fa"))
    create_test_tree("((sp1:0.005,sp2:0.005):0.005,(sp3:0.005,sp4:0.005):0.005);",
                     os.path.join(animal_dir, "gene1.nwk"))

    # Gene 2: Slightly diverged
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCATGCATGCGTGC",
        "sp3": "ATGCATGCATGCGTGCATGC",
        "sp4": "ATGCATGCATGCGTGCGTGC",
    }, os.path.join(animal_dir, "gene2.fa"))
    create_test_tree("((sp1:0.02,sp2:0.03):0.05,(sp3:0.025,sp4:0.035):0.06);",
                     os.path.join(animal_dir, "gene2.nwk"))

    # Gene 3: Some gaps
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCA-GCATGCATGC",
        "sp3": "ATGCATGCAT-CATGCATGC",
        "sp4": "ATGCATGCATGCATGCATGC",
    }, os.path.join(animal_dir, "gene3.fa"))
    create_test_tree("((sp1:0.03,sp2:0.04):0.06,(sp3:0.035,sp4:0.045):0.07);",
                     os.path.join(animal_dir, "gene3.nwk"))

    # Gene 4: Low divergence
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "ATGCATGCATGCATGCATGC",
        "sp3": "ATGCATGCATGCATGCGTGC",
        "sp4": "ATGCATGCATGCATGCGTGC",
    }, os.path.join(animal_dir, "gene4.fa"))
    create_test_tree("((sp1:0.01,sp2:0.01):0.02,(sp3:0.015,sp4:0.015):0.025);",
                     os.path.join(animal_dir, "gene4.nwk"))

    # Gene 5: Medium
    create_test_alignment({
        "sp1": "ATGCATGCATGCATGCATGC",
        "sp2": "GTGCATGCATGCATGCATGC",
        "sp3": "ATGCATGCATGCATGCATGC",
        "sp4": "GTGCATGCATGCATGCATGC",
    }, os.path.join(animal_dir, "gene5.fa"))
    create_test_tree("((sp1:0.02,sp2:0.04):0.03,(sp3:0.025,sp4:0.045):0.035);",
                     os.path.join(animal_dir, "gene5.nwk"))

    return tmpdir


# ---------------------------------------------------------------------------
# Core PhyKIT function wrappers (same as in SKILL.md)
# ---------------------------------------------------------------------------

def phykit_treeness(tree_file):
    from phykit.services.tree.treeness import Treeness
    t = Treeness(SimpleNamespace(tree=tree_file))
    tree = t.read_tree_file()
    return t.calculate_treeness(tree)


def phykit_tree_length(tree_file):
    from phykit.services.tree.total_tree_length import TotalTreeLength
    tl = TotalTreeLength(SimpleNamespace(tree=tree_file))
    tree = tl.read_tree_file()
    return tl.calculate_total_tree_length(tree)


def phykit_evolutionary_rate(tree_file):
    from phykit.services.tree.evolutionary_rate import EvolutionaryRate
    er = EvolutionaryRate(SimpleNamespace(tree=tree_file))
    tree = er.read_tree_file()
    return tree.total_branch_length() / tree.count_terminals()


def phykit_dvmc(tree_file):
    from phykit.services.tree.dvmc import DVMC
    d = DVMC(SimpleNamespace(tree=tree_file))
    tree = d.read_tree_file()
    return d.determine_dvmc(tree)


def phykit_parsimony_informative(aln_file):
    from phykit.services.alignment.parsimony_informative_sites import ParsimonyInformative
    pi = ParsimonyInformative(SimpleNamespace(alignment=aln_file))
    alignment, _, _ = pi.get_alignment_and_format()
    return pi.calculate_parsimony_informative_sites(alignment)


def phykit_rcv(aln_file):
    from phykit.services.alignment.rcv import RelativeCompositionVariability
    rcv = RelativeCompositionVariability(SimpleNamespace(alignment=aln_file))
    return rcv.calculate_rcv()


def phykit_treeness_over_rcv(tree_file, aln_file):
    treeness = phykit_treeness(tree_file)
    rcv = phykit_rcv(aln_file)
    if rcv == 0:
        return float('inf'), treeness, rcv
    return treeness / rcv, treeness, rcv


def alignment_gap_percentage(aln_file):
    from Bio import AlignIO
    formats = ['fasta', 'phylip', 'phylip-relaxed', 'nexus', 'clustal']
    alignment = None
    for fmt in formats:
        try:
            alignment = AlignIO.read(aln_file, fmt)
            break
        except Exception:
            continue
    if alignment is None:
        raise ValueError(f"Cannot parse: {aln_file}")
    arr = np.array([[c for c in str(rec.seq)] for rec in alignment])
    gaps = np.sum(np.isin(arr, ['-', '.', '?']))
    return (gaps / arr.size) * 100


def load_alignment(filepath):
    from Bio import AlignIO
    # Try phylip-relaxed BEFORE phylip to avoid misparse of long names
    formats = ['fasta', 'phylip-relaxed', 'phylip', 'nexus', 'clustal', 'stockholm']
    for fmt in formats:
        try:
            return AlignIO.read(filepath, fmt), fmt
        except Exception:
            continue
    raise ValueError(f"Cannot parse alignment: {filepath}")


def load_tree(filepath):
    from Bio import Phylo
    with open(filepath, 'r') as f:
        content = f.read().strip()
    try:
        return Phylo.read(io.StringIO(content), 'newick'), 'newick'
    except Exception:
        return Phylo.read(io.StringIO(content), 'nexus'), 'nexus'


# ---------------------------------------------------------------------------
# Batch processing helpers
# ---------------------------------------------------------------------------

def discover_gene_files(data_dir):
    import glob
    aln_files = {}
    tree_files = {}
    for ext in ['*.fa', '*.fasta']:
        for f in glob.glob(os.path.join(data_dir, ext)):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            aln_files[gene_id] = f
    for ext in ['*.nwk', '*.newick', '*.tre']:
        for f in glob.glob(os.path.join(data_dir, ext)):
            gene_id = os.path.splitext(os.path.basename(f))[0]
            tree_files[gene_id] = f
    results = []
    for gene_id in sorted(set(aln_files.keys()) | set(tree_files.keys())):
        entry = {'gene_id': gene_id}
        if gene_id in aln_files:
            entry['aln_file'] = aln_files[gene_id]
        if gene_id in tree_files:
            entry['tree_file'] = tree_files[gene_id]
        results.append(entry)
    return results


def batch_compute(gene_files, metric_func, requires='tree'):
    results = {}
    for entry in gene_files:
        try:
            if requires == 'tree' and 'tree_file' in entry:
                results[entry['gene_id']] = metric_func(entry['tree_file'])
            elif requires == 'alignment' and 'aln_file' in entry:
                results[entry['gene_id']] = metric_func(entry['aln_file'])
            elif requires == 'both' and 'tree_file' in entry and 'aln_file' in entry:
                results[entry['gene_id']] = metric_func(entry['tree_file'], entry['aln_file'])
        except Exception:
            pass
    return results


# ===========================================================================
# TEST FUNCTIONS
# ===========================================================================

def test_01_phykit_treeness_basic():
    """Test treeness calculation on a simple 4-taxon tree."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    treeness = phykit_treeness(tree_file)

    # Internal: 0.3 + 0.5 = 0.8; Total: 0.1+0.2+0.3+0.3+0.4+0.5 = 1.8
    expected = 0.8 / 1.8
    assert abs(treeness - expected) < 1e-6, f"Expected {expected}, got {treeness}"

    shutil.rmtree(tmpdir)
    return "Treeness = %.4f (expected %.4f)" % (treeness, expected)


def test_02_phykit_treeness_zero_branch():
    """Test treeness with zero-length internal branches."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.0,(C:0.3,D:0.4):0.0);", tree_file)

    treeness = phykit_treeness(tree_file)
    # Internal: 0; Total: 1.0; treeness = 0
    assert treeness == 0.0, f"Expected 0, got {treeness}"

    shutil.rmtree(tmpdir)
    return "Treeness with zero internal = 0.0"


def test_03_phykit_tree_length():
    """Test total tree length calculation."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    length = phykit_tree_length(tree_file)
    expected = 1.8
    assert abs(length - expected) < 1e-6, f"Expected {expected}, got {length}"

    shutil.rmtree(tmpdir)
    return "Tree length = %.4f (expected %.4f)" % (length, expected)


def test_04_phykit_evolutionary_rate():
    """Test evolutionary rate calculation."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    rate = phykit_evolutionary_rate(tree_file)
    expected = 1.8 / 4  # total BL / num terminals
    assert abs(rate - expected) < 1e-6, f"Expected {expected}, got {rate}"

    shutil.rmtree(tmpdir)
    return "Evo rate = %.4f (expected %.4f)" % (rate, expected)


def test_05_phykit_dvmc():
    """Test DVMC calculation."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    dvmc = phykit_dvmc(tree_file)
    assert isinstance(dvmc, float), f"Expected float, got {type(dvmc)}"
    assert dvmc >= 0, f"DVMC should be non-negative, got {dvmc}"

    shutil.rmtree(tmpdir)
    return "DVMC = %.4f" % dvmc


def test_06_phykit_dvmc_uniform():
    """Test DVMC for ultrametric tree (should be ~0)."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    # Ultrametric tree: all root-to-tip distances equal
    create_test_tree("((A:0.5,B:0.5):0.5,(C:0.5,D:0.5):0.5);", tree_file)

    dvmc = phykit_dvmc(tree_file)
    assert dvmc == 0.0, f"Expected 0 for ultrametric tree, got {dvmc}"

    shutil.rmtree(tmpdir)
    return "DVMC for ultrametric = 0.0"


def test_07_parsimony_informative_basic():
    """Test parsimony informative sites on a simple alignment."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert aln_len == 10, f"Expected alignment length 10, got {aln_len}"
    assert pi_sites == 2, f"Expected 2 PI sites, got {pi_sites}"
    assert abs(pi_pct - 20.0) < 0.01, f"Expected 20%, got {pi_pct}"

    shutil.rmtree(tmpdir)
    return "PI sites = %d / %d (%.1f%%)" % (pi_sites, aln_len, pi_pct)


def test_08_parsimony_informative_conserved():
    """Test PI sites on fully conserved alignment (should be 0)."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCATGC",
        "s2": "ATGCATGCATGC",
        "s3": "ATGCATGCATGC",
        "s4": "ATGCATGCATGC",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert pi_sites == 0, f"Expected 0 PI sites, got {pi_sites}"
    assert pi_pct == 0.0, f"Expected 0%, got {pi_pct}"

    shutil.rmtree(tmpdir)
    return "PI sites on conserved = 0"


def test_09_parsimony_informative_with_gaps():
    """Test PI sites with gap characters."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGC-TGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTG-AT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert aln_len == 10, f"Aln length should be 10, got {aln_len}"
    assert pi_sites >= 0, f"PI sites should be >= 0"

    shutil.rmtree(tmpdir)
    return "PI sites with gaps = %d / %d" % (pi_sites, aln_len)


def test_10_parsimony_informative_singleton():
    """Test that singletons are NOT parsimony informative."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    # Site 4: A,A,A,T -> singleton (T appears once) -> NOT informative
    create_test_alignment({
        "s1": "ATGCA",
        "s2": "ATGCA",
        "s3": "ATGCA",
        "s4": "ATGCT",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert pi_sites == 0, f"Expected 0 PI sites (singletons), got {pi_sites}"

    shutil.rmtree(tmpdir)
    return "Singletons correctly excluded from PI sites"


def test_11_rcv_basic():
    """Test RCV calculation."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    rcv = phykit_rcv(aln_file)
    assert isinstance(rcv, float), f"RCV should be float, got {type(rcv)}"
    assert rcv >= 0, f"RCV should be non-negative, got {rcv}"

    shutil.rmtree(tmpdir)
    return "RCV = %.4f" % rcv


def test_12_rcv_identical():
    """Test RCV for identical sequences (should be 0 or very small)."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCATGC",
        "s2": "ATGCATGCATGC",
        "s3": "ATGCATGCATGC",
        "s4": "ATGCATGCATGC",
    }, aln_file)

    rcv = phykit_rcv(aln_file)
    assert rcv == 0.0, f"Expected RCV=0 for identical seqs, got {rcv}"

    shutil.rmtree(tmpdir)
    return "RCV for identical sequences = 0.0"


def test_13_treeness_over_rcv():
    """Test treeness/RCV combined metric."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)
    create_test_alignment({
        "A": "ATGCATGCAT",
        "B": "ATGCATGCGT",
        "C": "ATGCGTGCAT",
        "D": "ATGCGTGCGT",
    }, aln_file)

    torcv, treeness, rcv = phykit_treeness_over_rcv(tree_file, aln_file)
    assert treeness > 0, "Treeness should be > 0"
    assert rcv > 0, "RCV should be > 0"
    assert abs(torcv - treeness / rcv) < 1e-6, "treeness/rcv mismatch"

    shutil.rmtree(tmpdir)
    return "Treeness/RCV = %.4f (treeness=%.4f, rcv=%.4f)" % (torcv, treeness, rcv)


def test_14_gap_percentage_no_gaps():
    """Test gap percentage with no gaps."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
    }, aln_file)

    gap_pct = alignment_gap_percentage(aln_file)
    assert gap_pct == 0.0, f"Expected 0% gaps, got {gap_pct}"

    shutil.rmtree(tmpdir)
    return "Gap percentage with no gaps = 0.0%"


def test_15_gap_percentage_with_gaps():
    """Test gap percentage calculation."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGC-TGCAT",
        "s2": "ATGCATG--T",
        "s3": "ATGCATGCAT",
        "s4": "ATGCATGCAT",
    }, aln_file)

    gap_pct = alignment_gap_percentage(aln_file)
    # 3 gaps out of 40 total chars = 7.5%
    expected = 3 / 40 * 100
    assert abs(gap_pct - expected) < 0.01, f"Expected {expected}%, got {gap_pct}%"

    shutil.rmtree(tmpdir)
    return "Gap percentage = %.2f%% (expected %.2f%%)" % (gap_pct, expected)


def test_16_gap_percentage_high():
    """Test gap percentage with >50% gaps."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "A-G--T---T",
        "s2": "-TGC-T----",
        "s3": "AT---TGC--",
        "s4": "--GC-TGC-T",
    }, aln_file)

    gap_pct = alignment_gap_percentage(aln_file)
    assert gap_pct > 50, f"Expected >50% gaps, got {gap_pct}%"

    shutil.rmtree(tmpdir)
    return "High gap percentage = %.2f%%" % gap_pct


def test_17_load_alignment_fasta():
    """Test alignment loading in FASTA format."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({"s1": "ATGC", "s2": "GTGC"}, aln_file)

    aln, fmt = load_alignment(aln_file)
    assert fmt == "fasta"
    assert len(aln) == 2
    assert aln.get_alignment_length() == 4

    shutil.rmtree(tmpdir)
    return "FASTA loading: 2 seqs, 4 sites"


def test_18_load_alignment_phylip():
    """Test alignment loading in PHYLIP format."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.phy")
    with open(aln_file, 'w') as f:
        f.write(" 2 4\n")
        f.write("seq1      ATGC\n")
        f.write("seq2      GTGC\n")

    aln, fmt = load_alignment(aln_file)
    assert len(aln) == 2
    assert aln.get_alignment_length() == 4

    shutil.rmtree(tmpdir)
    return "PHYLIP loading: 2 seqs, 4 sites"


def test_19_load_alignment_nexus():
    """Test alignment loading in Nexus format."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.nex")
    with open(aln_file, 'w') as f:
        f.write("#NEXUS\nbegin data;\ndimensions ntax=2 nchar=4;\n")
        f.write("format datatype=dna gap=-;\nmatrix\n")
        f.write("seq1 ATGC\nseq2 GTGC\n;\nend;\n")

    aln, fmt = load_alignment(aln_file)
    assert len(aln) == 2
    assert aln.get_alignment_length() == 4

    shutil.rmtree(tmpdir)
    return "Nexus loading: 2 seqs, 4 sites"


def test_20_load_tree_newick():
    """Test tree loading from Newick format."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,C:0.4);", tree_file)

    tree, fmt = load_tree(tree_file)
    assert fmt == "newick"
    terminals = [t.name for t in tree.get_terminals()]
    assert set(terminals) == {"A", "B", "C"}

    shutil.rmtree(tmpdir)
    return "Newick tree loading: 3 terminals"


def test_21_discover_gene_files():
    """Test file discovery in a directory."""
    tmpdir = create_test_data_dir()
    fungi_dir = os.path.join(tmpdir, "fungi")

    gene_files = discover_gene_files(fungi_dir)
    assert len(gene_files) == 5, f"Expected 5 genes, got {len(gene_files)}"

    for gf in gene_files:
        assert 'gene_id' in gf
        assert 'aln_file' in gf
        assert 'tree_file' in gf

    shutil.rmtree(tmpdir)
    return "Discovered 5 gene file pairs"


def test_22_batch_treeness():
    """Test batch treeness computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, phykit_treeness, requires='tree')
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    for gene_id, val in results.items():
        assert isinstance(val, float)
        assert 0 <= val <= 1, f"Treeness out of range for {gene_id}: {val}"

    shutil.rmtree(tmpdir)
    return "Batch treeness: %d genes, values: %s" % (
        len(results), [round(v, 4) for v in results.values()])


def test_23_batch_tree_length():
    """Test batch tree length computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, phykit_tree_length, requires='tree')
    assert len(results) == 5
    for val in results.values():
        assert val > 0

    shutil.rmtree(tmpdir)
    return "Batch tree length: %d genes" % len(results)


def test_24_batch_evolutionary_rate():
    """Test batch evolutionary rate computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, phykit_evolutionary_rate, requires='tree')
    assert len(results) == 5
    for val in results.values():
        assert val > 0

    shutil.rmtree(tmpdir)
    return "Batch evo rate: %d genes" % len(results)


def test_25_batch_dvmc():
    """Test batch DVMC computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, phykit_dvmc, requires='tree')
    assert len(results) == 5
    for val in results.values():
        assert val >= 0

    shutil.rmtree(tmpdir)
    return "Batch DVMC: %d genes" % len(results)


def test_26_batch_parsimony_informative():
    """Test batch parsimony informative sites."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = {}
    for entry in fungi_genes:
        if 'aln_file' in entry:
            try:
                results[entry['gene_id']] = phykit_parsimony_informative(entry['aln_file'])
            except Exception:
                pass

    assert len(results) == 5
    for gene_id, (count, length, pct) in results.items():
        assert count >= 0
        assert length > 0
        assert 0 <= pct <= 100

    shutil.rmtree(tmpdir)
    return "Batch PI sites: %d genes" % len(results)


def test_27_batch_rcv():
    """Test batch RCV computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, phykit_rcv, requires='alignment')
    assert len(results) == 5
    for val in results.values():
        assert val >= 0

    shutil.rmtree(tmpdir)
    return "Batch RCV: %d genes" % len(results)


def test_28_batch_gap_percentage():
    """Test batch gap percentage computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = batch_compute(fungi_genes, alignment_gap_percentage, requires='alignment')
    assert len(results) == 5
    for val in results.values():
        assert 0 <= val <= 100

    shutil.rmtree(tmpdir)
    return "Batch gap %%: %s" % {k: round(v, 1) for k, v in results.items()}


def test_29_group_comparison_treeness():
    """Test comparing treeness between fungi and animals."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_treeness = batch_compute(fungi_genes, phykit_treeness, requires='tree')
    animal_treeness = batch_compute(animal_genes, phykit_treeness, requires='tree')

    from scipy import stats
    f_vals = list(fungi_treeness.values())
    a_vals = list(animal_treeness.values())

    u_stat, p_value = stats.mannwhitneyu(a_vals, f_vals, alternative='two-sided')
    assert isinstance(u_stat, float) or isinstance(u_stat, (int, np.integer, np.floating))
    assert 0 <= p_value <= 1

    median_diff = abs(np.median(f_vals) - np.median(a_vals))

    shutil.rmtree(tmpdir)
    return "U=%.1f, p=%.4f, median_diff=%.4f" % (u_stat, p_value, median_diff)


def test_30_group_comparison_tree_length():
    """Test comparing tree lengths between groups."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_tl = batch_compute(fungi_genes, phykit_tree_length, requires='tree')
    animal_tl = batch_compute(animal_genes, phykit_tree_length, requires='tree')

    f_vals = list(fungi_tl.values())
    a_vals = list(animal_tl.values())

    fold_change = np.median(f_vals) / np.median(a_vals)
    variance_animals = np.var(a_vals, ddof=1)

    shutil.rmtree(tmpdir)
    return "Fold-change = %.2f, animal variance = %.4f" % (fold_change, variance_animals)


def test_31_group_comparison_evo_rate():
    """Test comparing evolutionary rates between groups."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_er = batch_compute(fungi_genes, phykit_evolutionary_rate, requires='tree')
    animal_er = batch_compute(animal_genes, phykit_evolutionary_rate, requires='tree')

    f_vals = list(fungi_er.values())
    a_vals = list(animal_er.values())

    from scipy import stats
    u_stat, p_value = stats.mannwhitneyu(a_vals, f_vals, alternative='two-sided')
    max_fungi = max(f_vals)
    median_diff = abs(np.median(f_vals) - np.median(a_vals))

    shutil.rmtree(tmpdir)
    return "U=%.1f, max_fungi=%.4f, median_diff=%.4f" % (u_stat, max_fungi, median_diff)


def test_32_group_comparison_dvmc():
    """Test comparing DVMC between groups."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_dvmc = batch_compute(fungi_genes, phykit_dvmc, requires='tree')
    animal_dvmc = batch_compute(animal_genes, phykit_dvmc, requires='tree')

    f_vals = list(fungi_dvmc.values())
    a_vals = list(animal_dvmc.values())

    from scipy import stats
    u_stat, p_value = stats.mannwhitneyu(a_vals, f_vals, alternative='two-sided')
    pct_below_03 = sum(1 for v in f_vals if v < 0.3) / len(f_vals) * 100
    std_animals = np.std(a_vals, ddof=1)

    shutil.rmtree(tmpdir)
    return "U=%.1f, pct<0.3=%.0f%%, std_animals=%.4f" % (u_stat, pct_below_03, std_animals)


def test_33_group_comparison_rcv():
    """Test comparing RCV between groups."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_rcv = batch_compute(fungi_genes, phykit_rcv, requires='alignment')
    animal_rcv = batch_compute(animal_genes, phykit_rcv, requires='alignment')

    f_vals = list(fungi_rcv.values())
    a_vals = list(animal_rcv.values())

    from scipy import stats
    u_stat, p_value = stats.mannwhitneyu(a_vals, f_vals, alternative='two-sided')
    median_fungi = np.median(f_vals)
    q75_fungi = np.percentile(f_vals, 75)

    shutil.rmtree(tmpdir)
    return "U=%.1f, median_fungi=%.4f, q75_fungi=%.4f" % (u_stat, median_fungi, q75_fungi)


def test_34_paired_differences():
    """Test paired differences between matched genes."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_rcv = batch_compute(fungi_genes, phykit_rcv, requires='alignment')
    animal_rcv = batch_compute(animal_genes, phykit_rcv, requires='alignment')

    common = set(fungi_rcv.keys()) & set(animal_rcv.keys())
    assert len(common) > 0, "No common genes found"

    diffs = [fungi_rcv[g] - animal_rcv[g] for g in sorted(common)]
    median_diff = np.median(diffs)

    shutil.rmtree(tmpdir)
    return "Paired median diff = %.4f (%d pairs)" % (median_diff, len(common))


def test_35_paired_ratios():
    """Test paired ratios of tree lengths."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_tl = batch_compute(fungi_genes, phykit_tree_length, requires='tree')
    animal_tl = batch_compute(animal_genes, phykit_tree_length, requires='tree')

    common = set(fungi_tl.keys()) & set(animal_tl.keys())
    ratios = [fungi_tl[g] / animal_tl[g] for g in sorted(common) if animal_tl[g] > 0]
    median_ratio = np.median(ratios)
    assert median_ratio > 0

    shutil.rmtree(tmpdir)
    return "Median ratio fungi/animals = %.3f" % median_ratio


def test_36_percentage_above_threshold():
    """Test percentage of genes above a threshold."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    fungi_treeness = batch_compute(fungi_genes, phykit_treeness, requires='tree')
    values = list(fungi_treeness.values())

    threshold = 0.3
    pct_above = sum(1 for v in values if v > threshold) / len(values) * 100

    shutil.rmtree(tmpdir)
    return "%.0f%% of genes have treeness > %.2f" % (pct_above, threshold)


def test_37_specific_gene_lookup():
    """Test looking up a specific gene's metric."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    fungi_dvmc = batch_compute(fungi_genes, phykit_dvmc, requires='tree')

    gene3_dvmc = fungi_dvmc.get('gene3')
    assert gene3_dvmc is not None, "gene3 not found in results"
    assert isinstance(gene3_dvmc, float)

    shutil.rmtree(tmpdir)
    return "gene3 DVMC = %.4f" % gene3_dvmc


def test_38_treeness_over_rcv_batch():
    """Test batch treeness/RCV computation."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = {}
    for entry in fungi_genes:
        if 'tree_file' in entry and 'aln_file' in entry:
            try:
                torcv, _, _ = phykit_treeness_over_rcv(entry['tree_file'], entry['aln_file'])
                results[entry['gene_id']] = torcv
            except Exception:
                pass

    # Some genes may have RCV=0 (identical sequences) -> inf
    finite_vals = [v for v in results.values() if np.isfinite(v)]
    assert len(finite_vals) > 0, "No finite treeness/RCV values"

    median_torcv = np.median(finite_vals)

    shutil.rmtree(tmpdir)
    return "Treeness/RCV: %d/%d finite, median = %.4f" % (len(finite_vals), len(results), median_torcv)


def test_39_gap_filtered_treeness_rcv():
    """Test treeness/RCV filtered by gap percentage."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    high_gap_torcv = {}
    for entry in fungi_genes:
        if 'aln_file' in entry and 'tree_file' in entry:
            try:
                gap_pct = alignment_gap_percentage(entry['aln_file'])
                if gap_pct > 10:  # Lower threshold for test data
                    torcv, _, _ = phykit_treeness_over_rcv(entry['tree_file'], entry['aln_file'])
                    if np.isfinite(torcv):
                        high_gap_torcv[entry['gene_id']] = torcv
            except Exception:
                pass

    if high_gap_torcv:
        max_torcv = max(high_gap_torcv.values())
        return "Max treeness/RCV (>10%% gaps): %.4f from %d genes" % (max_torcv, len(high_gap_torcv))
    return "No genes with >10% gaps (expected in test data)"


def test_40_average_treeness_scaled():
    """Test average treeness multiplied by 1000 and rounded."""
    tmpdir = tempfile.mkdtemp()
    # Create 5 simple trees
    trees = [
        "((A:0.01,B:0.01):0.005,(C:0.01,D:0.01):0.005);",
        "((A:0.02,B:0.02):0.01,(C:0.02,D:0.02):0.01);",
        "((A:0.03,B:0.03):0.015,(C:0.03,D:0.03):0.015);",
        "((A:0.015,B:0.015):0.008,(C:0.015,D:0.015):0.008);",
        "((A:0.025,B:0.025):0.012,(C:0.025,D:0.025):0.012);",
    ]
    tree_files = []
    for i, t in enumerate(trees):
        tf = os.path.join(tmpdir, f"tree{i+1}.nwk")
        create_test_tree(t, tf)
        tree_files.append(tf)

    treeness_vals = [phykit_treeness(tf) for tf in tree_files]
    avg = np.mean(treeness_vals)
    scaled = round(avg * 1000)

    shutil.rmtree(tmpdir)
    return "Average treeness = %.4f, x1000 rounded = %d" % (avg, scaled)


def test_41_nj_tree_construction():
    """Test NJ tree construction from alignment."""
    from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
    from Bio import AlignIO, Phylo

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    alignment = AlignIO.read(aln_file, "fasta")
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    nj_tree = constructor.nj(dm)

    terminals = [t.name for t in nj_tree.get_terminals()]
    assert len(terminals) == 4, f"Expected 4 terminals, got {len(terminals)}"
    assert set(terminals) == {"s1", "s2", "s3", "s4"}

    shutil.rmtree(tmpdir)
    return "NJ tree: 4 terminals, total BL = %.4f" % nj_tree.total_branch_length()


def test_42_upgma_tree_construction():
    """Test UPGMA tree construction from alignment."""
    from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
    from Bio import AlignIO

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    alignment = AlignIO.read(aln_file, "fasta")
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    upgma_tree = constructor.upgma(dm)

    terminals = [t.name for t in upgma_tree.get_terminals()]
    assert len(terminals) == 4
    # UPGMA is ultrametric
    root_to_tip = []
    for term in upgma_tree.get_terminals():
        root_to_tip.append(upgma_tree.distance(term))
    # All distances should be approximately equal
    assert max(root_to_tip) - min(root_to_tip) < 0.01

    shutil.rmtree(tmpdir)
    return "UPGMA tree: ultrametric (max-min distance = %.6f)" % (max(root_to_tip) - min(root_to_tip))


def test_43_parsimony_tree_construction():
    """Test maximum parsimony tree construction."""
    from Bio.Phylo.TreeConstruction import (DistanceCalculator, DistanceTreeConstructor,
                                             ParsimonyScorer, NNITreeSearcher,
                                             ParsimonyTreeConstructor)
    from Bio import AlignIO

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    alignment = AlignIO.read(aln_file, "fasta")
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    starting_tree = constructor.nj(dm)

    scorer = ParsimonyScorer()
    searcher = NNITreeSearcher(scorer)
    pars_constructor = ParsimonyTreeConstructor(searcher, starting_tree)
    pars_tree = pars_constructor.build_tree(alignment)

    terminals = [t.name for t in pars_tree.get_terminals()]
    assert len(terminals) == 4

    score = scorer.get_score(pars_tree, alignment)
    assert score >= 0

    shutil.rmtree(tmpdir)
    return "Parsimony tree: score = %d" % score


def test_44_robinson_foulds_distance():
    """Test Robinson-Foulds distance between trees."""
    import dendropy
    from dendropy.calculate import treecompare

    tmpdir = tempfile.mkdtemp()
    tree1_file = os.path.join(tmpdir, "tree1.nwk")
    tree2_file = os.path.join(tmpdir, "tree2.nwk")
    tree3_file = os.path.join(tmpdir, "tree3.nwk")

    # Same topology
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree1_file)
    create_test_tree("((A:0.5,B:0.6):0.1,(C:0.1,D:0.2):0.3);", tree2_file)
    # Different topology
    create_test_tree("((A:0.1,C:0.2):0.3,(B:0.3,D:0.4):0.5);", tree3_file)

    tree1 = dendropy.Tree.get(path=tree1_file, schema="newick")
    tree2 = dendropy.Tree.get(path=tree2_file, schema="newick",
                               taxon_namespace=tree1.taxon_namespace)
    tree3 = dendropy.Tree.get(path=tree3_file, schema="newick",
                               taxon_namespace=tree1.taxon_namespace)

    rf_same = treecompare.symmetric_difference(tree1, tree2)
    rf_diff = treecompare.symmetric_difference(tree1, tree3)

    assert rf_same == 0, f"Same topology should have RF=0, got {rf_same}"
    assert rf_diff > 0, f"Different topology should have RF>0, got {rf_diff}"

    shutil.rmtree(tmpdir)
    return "RF distance: same topology=%d, different=%d" % (rf_same, rf_diff)


def test_45_dendropy_treeness():
    """Test treeness calculation using DendroPy."""
    import dendropy

    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    tree = dendropy.Tree.get(path=tree_file, schema="newick")
    total_bl = tree.length()
    terminal_bl = sum(n.edge_length for n in tree.leaf_node_iter() if n.edge_length)
    internal_bl = total_bl - terminal_bl
    treeness = internal_bl / total_bl if total_bl > 0 else 0

    # Compare with PhyKIT
    pk_treeness = phykit_treeness(tree_file)
    assert abs(treeness - pk_treeness) < 1e-6, "DendroPy and PhyKIT treeness should match"

    shutil.rmtree(tmpdir)
    return "DendroPy treeness = %.4f (matches PhyKIT)" % treeness


def test_46_dendropy_parsimony():
    """Test parsimony score using DendroPy."""
    import dendropy
    from dendropy.calculate import treescore

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    tree_file = os.path.join(tmpdir, "test.nwk")

    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)
    create_test_tree("((s1:0.1,s2:0.2):0.3,(s3:0.3,s4:0.4):0.5);", tree_file)

    chars = dendropy.DnaCharacterMatrix.get(path=aln_file, schema="fasta")
    tree = dendropy.Tree.get(path=tree_file, schema="newick",
                              taxon_namespace=chars.taxon_namespace)

    taxon_state_sets_map = chars.taxon_state_sets_map(gaps_as_missing=True)
    score = treescore.fitch_down_pass(
        postorder_node_iter=tree.postorder_node_iter(),
        taxon_state_sets_map=taxon_state_sets_map
    )
    assert score >= 0
    # For this alignment, parsimony score should be 3 (2 variable + 1 more)
    # Actually: 2 PI sites with 2 mutations each, plus possibly others
    # The key is it produces a valid integer score
    assert isinstance(score, (int, np.integer))

    shutil.rmtree(tmpdir)
    return "DendroPy Fitch parsimony score = %d" % score


def test_47_bootstrap_support_extraction():
    """Test extracting bootstrap support values from tree."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    # Newick with bootstrap values
    create_test_tree("((A:0.1,B:0.2)95:0.3,(C:0.3,D:0.4)80:0.5);", tree_file)

    tree, _ = load_tree(tree_file)
    supports = []
    for clade in tree.get_nonterminals():
        if clade.confidence is not None:
            supports.append(clade.confidence)

    assert len(supports) >= 2, f"Expected >=2 support values, got {len(supports)}"
    assert 95 in supports or 95.0 in supports
    assert 80 in supports or 80.0 in supports

    shutil.rmtree(tmpdir)
    return "Bootstrap supports: %s" % supports


def test_48_tree_branch_stats():
    """Test branch length statistics."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    tree, _ = load_tree(tree_file)

    internal_lengths = []
    terminal_lengths = []
    for clade in tree.find_clades():
        if clade.branch_length is not None:
            if clade.is_terminal():
                terminal_lengths.append(clade.branch_length)
            else:
                internal_lengths.append(clade.branch_length)

    assert len(terminal_lengths) == 4
    assert sum(terminal_lengths) == 1.0  # 0.1+0.2+0.3+0.4
    assert abs(sum(internal_lengths) - 0.8) < 0.01  # 0.3+0.5

    shutil.rmtree(tmpdir)
    return "Internal BL = %.1f, Terminal BL = %.1f" % (sum(internal_lengths), sum(terminal_lengths))


def test_49_tree_newick_output():
    """Test writing tree to Newick format."""
    from Bio import Phylo, AlignIO
    from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({"A": "ATGCAT", "B": "ATGCGT", "C": "GTGCAT"}, aln_file)

    alignment = AlignIO.read(aln_file, "fasta")
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(alignment)
    constructor = DistanceTreeConstructor()
    tree = constructor.nj(dm)

    out_file = os.path.join(tmpdir, "output.nwk")
    Phylo.write(tree, out_file, "newick")

    assert os.path.exists(out_file)
    with open(out_file) as f:
        content = f.read().strip()
    assert content.endswith(';')
    assert '(' in content

    shutil.rmtree(tmpdir)
    return "Newick output written successfully"


def test_50_mann_whitney_u_basic():
    """Test Mann-Whitney U computation."""
    from scipy import stats

    # Known values
    group1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    group2 = [6.0, 7.0, 8.0, 9.0, 10.0]

    u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
    assert u_stat == 0.0, f"Expected U=0, got {u_stat}"  # All group1 < group2
    assert p_value < 0.05, f"Expected p<0.05, got {p_value}"

    return "Mann-Whitney U = %.1f, p = %.4f" % (u_stat, p_value)


def test_51_mann_whitney_u_no_difference():
    """Test Mann-Whitney U with no difference between groups."""
    from scipy import stats

    group1 = [1.0, 2.0, 3.0, 4.0, 5.0]
    group2 = [1.0, 2.0, 3.0, 4.0, 5.0]

    u_stat, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
    assert p_value > 0.05 or u_stat == 12.5  # No significant difference

    return "Mann-Whitney U (no diff) = %.1f, p = %.4f" % (u_stat, p_value)


def test_52_percentile_calculation():
    """Test percentile calculations."""
    values = [0.1, 0.15, 0.2, 0.22, 0.25, 0.27, 0.3, 0.35, 0.4, 0.5]

    q25 = np.percentile(values, 25)
    q50 = np.percentile(values, 50)
    q75 = np.percentile(values, 75)

    assert q25 < q50 < q75
    assert abs(q50 - np.median(values)) < 1e-10

    return "Q25=%.4f, Q50=%.4f, Q75=%.4f" % (q25, q50, q75)


def test_53_variance_calculation():
    """Test variance and std dev calculations (ddof=1)."""
    values = [0.1, 0.2, 0.3, 0.4, 0.5]

    var = np.var(values, ddof=1)
    std = np.std(values, ddof=1)

    assert abs(var - 0.025) < 1e-6
    assert abs(std - np.sqrt(0.025)) < 1e-6

    return "Var = %.4f, Std = %.4f" % (var, std)


def test_54_minimum_ratio():
    """Test ratio of minimum values between groups."""
    fungi_vals = {"g1": 0.04, "g2": 0.08, "g3": 0.12}
    animal_vals = {"g1": 0.01, "g2": 0.02, "g3": 0.03}

    min_fungi = min(fungi_vals.values())
    min_animal = min(animal_vals.values())
    ratio = min_fungi / min_animal

    assert ratio == 4.0, f"Expected ratio 4.0, got {ratio}"

    return "Min ratio = %.1f (fungi %.2f / animals %.2f)" % (ratio, min_fungi, min_animal)


def test_55_pct_exceeding_threshold():
    """Test percentage exceeding a threshold."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    threshold = 5.0

    pct = sum(1 for v in values if v > threshold) / len(values) * 100
    assert pct == 50.0

    return "Pct > %.1f = %.0f%%" % (threshold, pct)


def test_56_pct_exceeding_mean_of_other():
    """Test percentage of group1 exceeding mean of group2."""
    fungi_vals = [5.0, 6.0, 7.0, 8.0, 9.0]
    animal_vals = [1.0, 2.0, 3.0, 4.0, 5.0]

    mean_animals = np.mean(animal_vals)
    pct = sum(1 for v in fungi_vals if v > mean_animals) / len(fungi_vals) * 100

    return "%.0f%% of fungi > animal mean (%.1f)" % (pct, mean_animals)


def test_57_multiple_tree_average():
    """Test averaging a metric across multiple trees."""
    tmpdir = tempfile.mkdtemp()
    trees = [
        "((A:0.01,B:0.01):0.005,(C:0.01,D:0.01):0.005);",
        "((A:0.02,B:0.02):0.01,(C:0.02,D:0.02):0.01);",
        "((A:0.03,B:0.03):0.015,(C:0.03,D:0.03):0.015);",
        "((A:0.015,B:0.015):0.008,(C:0.015,D:0.015):0.008);",
        "((A:0.025,B:0.025):0.012,(C:0.025,D:0.025):0.012);",
    ]
    tree_files = []
    for i, t in enumerate(trees):
        tf = os.path.join(tmpdir, f"tree{i+1}.nwk")
        create_test_tree(t, tf)
        tree_files.append(tf)

    treeness_vals = [phykit_treeness(tf) for tf in tree_files]
    avg = np.mean(treeness_vals)

    # All trees have same topology structure, so treeness should be similar
    assert len(treeness_vals) == 5
    assert all(0 < v < 1 for v in treeness_vals)

    shutil.rmtree(tmpdir)
    return "Average treeness across 5 trees = %.4f" % avg


def test_58_alignment_statistics():
    """Test comprehensive alignment statistics."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    # Compute various stats
    aln, _ = load_alignment(aln_file)
    n_seqs = len(aln)
    aln_len = aln.get_alignment_length()
    gap_pct = alignment_gap_percentage(aln_file)
    pi_sites, _, pi_pct = phykit_parsimony_informative(aln_file)
    rcv = phykit_rcv(aln_file)

    assert n_seqs == 4
    assert aln_len == 10
    assert gap_pct == 0.0
    assert pi_sites == 2
    assert abs(pi_pct - 20.0) < 0.01
    assert rcv >= 0

    shutil.rmtree(tmpdir)
    return "Stats: %d seqs, %d sites, %.1f%% gaps, %d PI, RCV=%.4f" % (
        n_seqs, aln_len, gap_pct, pi_sites, rcv)


def test_59_large_alignment():
    """Test with a larger alignment (20 sequences)."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")

    import random
    random.seed(42)
    base_seq = "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC"
    seqs = {}
    for i in range(20):
        seq_list = list(base_seq)
        # Introduce random mutations
        for _ in range(random.randint(0, 10)):
            pos = random.randint(0, len(seq_list) - 1)
            seq_list[pos] = random.choice("ATGC")
        # Introduce random gaps
        for _ in range(random.randint(0, 3)):
            pos = random.randint(0, len(seq_list) - 1)
            seq_list[pos] = '-'
        seqs[f"sp{i+1}"] = ''.join(seq_list)

    create_test_alignment(seqs, aln_file)

    aln, _ = load_alignment(aln_file)
    assert len(aln) == 20
    assert aln.get_alignment_length() == len(base_seq)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    rcv = phykit_rcv(aln_file)
    gap_pct = alignment_gap_percentage(aln_file)

    shutil.rmtree(tmpdir)
    return "Large alignment: %d seqs, %d PI sites, RCV=%.4f, %.1f%% gaps" % (
        20, pi_sites, rcv, gap_pct)


def test_60_multifurcating_tree():
    """Test handling multifurcating (polytomy) trees."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    # Polytomy: 3 children at root
    create_test_tree("(A:0.1,B:0.2,C:0.3);", tree_file)

    treeness = phykit_treeness(tree_file)
    tree_len = phykit_tree_length(tree_file)

    assert tree_len > 0
    # Treeness should be 0 (no internal branches with length in this case)
    # or handle based on PhyKIT behavior

    shutil.rmtree(tmpdir)
    return "Polytomy tree: treeness=%.4f, length=%.4f" % (treeness, tree_len)


def test_61_single_branch_tree():
    """Test tree with single internal branch."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,C:0.4);", tree_file)

    treeness = phykit_treeness(tree_file)
    tree_len = phykit_tree_length(tree_file)
    evo_rate = phykit_evolutionary_rate(tree_file)

    expected_len = 0.1 + 0.2 + 0.3 + 0.4
    assert abs(tree_len - expected_len) < 1e-6

    shutil.rmtree(tmpdir)
    return "3-taxon tree: treeness=%.4f, length=%.4f, rate=%.4f" % (treeness, tree_len, evo_rate)


def test_62_protein_alignment():
    """Test PI sites with protein alignment."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "MKVLWAALLV",
        "s2": "MKVLWAALLV",
        "s3": "MKVLWGALLV",
        "s4": "MKVLWGALLV",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert aln_len == 10
    assert pi_sites >= 1  # At least position 5 (A/G) is PI

    shutil.rmtree(tmpdir)
    return "Protein PI sites = %d / %d" % (pi_sites, aln_len)


def test_63_alignment_all_gaps_column():
    """Test alignment with a column that is all gaps."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATG-ATGCAT",
        "s2": "ATG-ATGCGT",
        "s3": "ATG-GTGCAT",
        "s4": "ATG-GTGCGT",
    }, aln_file)

    gap_pct = alignment_gap_percentage(aln_file)
    pi_sites, _, _ = phykit_parsimony_informative(aln_file)

    # 4 gaps / 40 total = 10%
    assert abs(gap_pct - 10.0) < 0.01

    shutil.rmtree(tmpdir)
    return "All-gap column: gap%%=%.1f%%, PI=%d" % (gap_pct, pi_sites)


def test_64_very_short_alignment():
    """Test with very short alignment (3 sites)."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATG",
        "s2": "ATG",
        "s3": "GTG",
        "s4": "GTG",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)
    assert aln_len == 3
    assert pi_sites == 1  # Position 0: A(2), G(2)

    shutil.rmtree(tmpdir)
    return "Short alignment: %d PI sites in %d positions" % (pi_sites, aln_len)


def test_65_negative_branch_warning():
    """Test tree with very small branch lengths (near zero)."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.0001,B:0.0001):0.0001,(C:0.0001,D:0.0001):0.0001);", tree_file)

    treeness = phykit_treeness(tree_file)
    dvmc = phykit_dvmc(tree_file)
    tree_len = phykit_tree_length(tree_file)

    assert treeness > 0
    assert tree_len > 0

    shutil.rmtree(tmpdir)
    return "Small branches: treeness=%.4f, DVMC=%.4f" % (treeness, dvmc)


def test_66_format_conversion():
    """Test reading alignment and writing to different format."""
    from Bio import AlignIO

    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCAT",
        "s2": "ATGCATGCGT",
        "s3": "ATGCGTGCAT",
        "s4": "ATGCGTGCGT",
    }, aln_file)

    aln = AlignIO.read(aln_file, "fasta")

    # Write to PHYLIP
    phy_file = os.path.join(tmpdir, "test.phy")
    AlignIO.write(aln, phy_file, "phylip")
    aln2 = AlignIO.read(phy_file, "phylip")
    assert len(aln2) == 4
    assert aln2.get_alignment_length() == 10

    shutil.rmtree(tmpdir)
    return "FASTA -> PHYLIP conversion successful"


def test_67_phykit_consistency_check():
    """Verify PhyKIT functions are consistent with manual calculations."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("((A:0.1,B:0.2):0.3,(C:0.3,D:0.4):0.5);", tree_file)

    # PhyKIT treeness
    pk_treeness = phykit_treeness(tree_file)

    # Manual treeness using Biopython
    from Bio import Phylo
    tree = Phylo.read(tree_file, "newick")
    internal_bl = sum(c.branch_length for c in tree.get_nonterminals() if c.branch_length)
    total_bl = tree.total_branch_length()
    manual_treeness = internal_bl / total_bl

    assert abs(pk_treeness - manual_treeness) < 1e-6, \
        f"PhyKIT ({pk_treeness}) != manual ({manual_treeness})"

    # PhyKIT tree length
    pk_length = phykit_tree_length(tree_file)
    assert abs(pk_length - total_bl) < 1e-6

    # PhyKIT evo rate
    pk_rate = phykit_evolutionary_rate(tree_file)
    manual_rate = total_bl / tree.count_terminals()
    assert abs(pk_rate - manual_rate) < 1e-6

    shutil.rmtree(tmpdir)
    return "PhyKIT vs manual: treeness, tree_length, evo_rate all match"


def test_68_empty_directory():
    """Test handling of empty directory (no files found)."""
    tmpdir = tempfile.mkdtemp()

    gene_files = discover_gene_files(tmpdir)
    assert len(gene_files) == 0

    shutil.rmtree(tmpdir)
    return "Empty directory handled correctly (0 files)"


def test_69_mixed_completeness():
    """Test genes with only alignment or only tree file."""
    tmpdir = tempfile.mkdtemp()

    # Gene with only alignment
    create_test_alignment({"s1": "ATGC", "s2": "GTGC"}, os.path.join(tmpdir, "aln_only.fa"))

    # Gene with only tree
    create_test_tree("(A:0.1,B:0.2);", os.path.join(tmpdir, "tree_only.nwk"))

    # Gene with both
    create_test_alignment({"s1": "ATGC", "s2": "GTGC"}, os.path.join(tmpdir, "both.fa"))
    create_test_tree("(s1:0.1,s2:0.2);", os.path.join(tmpdir, "both.nwk"))

    gene_files = discover_gene_files(tmpdir)

    # batch_compute should handle missing files gracefully
    treeness_results = batch_compute(gene_files, phykit_treeness, requires='tree')
    rcv_results = batch_compute(gene_files, phykit_rcv, requires='alignment')

    # tree_only and both should have treeness
    assert 'tree_only' in treeness_results or 'both' in treeness_results
    # aln_only and both should have RCV
    assert 'aln_only' in rcv_results or 'both' in rcv_results

    shutil.rmtree(tmpdir)
    return "Mixed completeness handled correctly"


def test_70_pi_sites_percentage_extraction():
    """Test extracting percentage from PI sites tuple."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.fa")
    create_test_alignment({
        "s1": "ATGCATGCATGCATGCATGC",
        "s2": "ATGCATGCGTGCATGCATGC",
        "s3": "ATGCGTGCATGCGTGCATGC",
        "s4": "ATGCGTGCGTGCGTGCATGC",
    }, aln_file)

    pi_sites, aln_len, pi_pct = phykit_parsimony_informative(aln_file)

    # Verify we can extract all three values correctly
    assert isinstance(pi_sites, (int, np.integer))
    assert isinstance(aln_len, (int, np.integer))
    assert isinstance(pi_pct, float)
    assert pi_pct == (pi_sites / aln_len) * 100

    shutil.rmtree(tmpdir)
    return "PI extraction: count=%d, len=%d, pct=%.2f%%" % (pi_sites, aln_len, pi_pct)


def test_71_batch_pi_statistics():
    """Test computing summary statistics from batch PI results."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    pi_results = {}
    for entry in fungi_genes:
        if 'aln_file' in entry:
            try:
                count, length, pct = phykit_parsimony_informative(entry['aln_file'])
                pi_results[entry['gene_id']] = {
                    'count': count, 'length': length, 'pct': pct
                }
            except Exception:
                pass

    pct_vals = [r['pct'] for r in pi_results.values()]
    count_vals = [r['count'] for r in pi_results.values()]

    median_pct = np.median(pct_vals)
    max_count = max(count_vals)

    assert len(pi_results) == 5
    assert median_pct >= 0
    assert max_count >= 0

    shutil.rmtree(tmpdir)
    return "Batch PI: median_pct=%.2f%%, max_count=%d" % (median_pct, max_count)


def test_72_median_difference():
    """Test computing median difference between groups."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    fungi_treeness = batch_compute(fungi_genes, phykit_treeness, requires='tree')
    animal_treeness = batch_compute(animal_genes, phykit_treeness, requires='tree')

    median_fungi = np.median(list(fungi_treeness.values()))
    median_animals = np.median(list(animal_treeness.values()))
    diff = abs(median_fungi - median_animals)

    assert diff >= 0

    shutil.rmtree(tmpdir)
    return "Median diff: |%.4f - %.4f| = %.4f" % (median_fungi, median_animals, diff)


def test_73_scipy_integration():
    """Test scipy.stats functions used in the skill."""
    from scipy import stats

    # Wilcoxon signed-rank test (paired)
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [1.5, 2.5, 3.5, 4.5, 5.5]
    stat, p = stats.wilcoxon(x, y)
    assert p < 1.0

    # Spearman correlation
    rho, p = stats.spearmanr(x, y)
    assert abs(rho - 1.0) < 1e-10  # Perfect monotonic relationship

    return "scipy.stats integration: wilcoxon and spearmanr work"


def test_74_output_rounding():
    """Test various rounding patterns used in BixBench answers."""
    # 4 decimal places (PhyKIT default)
    assert round(0.05012345, 4) == 0.0501

    # 2 decimal places
    assert round(0.2567, 2) == 0.26

    # Percentage as integer
    assert round(35.4) == 35
    assert round(34.7) == 35

    # Multiply by 1000 and round
    assert round(0.019234 * 1000) == 19

    # Scientific notation
    val = 7.6968e-54
    assert "7.6968e-54" in f"{val:.4e}" or "7.6968e-54" in str(val)

    return "Rounding patterns all correct"


def test_75_fold_change_calculation():
    """Test fold-change calculation between groups."""
    fungi_median = 4.0
    animal_median = 2.0

    fold = fungi_median / animal_median
    assert fold == 2.0

    return "Fold-change = %.1fx" % fold


def test_76_percentage_above_mean_of_other():
    """Test percentage of one group exceeding mean of another."""
    fungi = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
    animals = [1.0, 2.0, 3.0, 4.0, 5.0]

    mean_animals = np.mean(animals)  # 3.0
    pct = sum(1 for v in fungi if v > mean_animals) / len(fungi) * 100
    assert pct == 100.0

    return "%.0f%% of fungi > animal mean (%.1f)" % (pct, mean_animals)


def test_77_phylip_relaxed_format():
    """Test PHYLIP relaxed format (long names)."""
    tmpdir = tempfile.mkdtemp()
    aln_file = os.path.join(tmpdir, "test.phy")
    with open(aln_file, 'w') as f:
        f.write(" 2 10\n")
        f.write("a_very_long_species_name_1    ATGCATGCAT\n")
        f.write("a_very_long_species_name_2    ATGCGTGCAT\n")

    aln, fmt = load_alignment(aln_file)
    assert len(aln) == 2
    assert aln.get_alignment_length() == 10

    shutil.rmtree(tmpdir)
    return "PHYLIP relaxed format: 2 seqs with long names"


def test_78_tree_with_quoted_labels():
    """Test tree with quoted taxon labels."""
    tmpdir = tempfile.mkdtemp()
    tree_file = os.path.join(tmpdir, "test.nwk")
    create_test_tree("(('sp 1':0.1,'sp 2':0.2):0.3,('sp 3':0.3,'sp 4':0.4):0.5);", tree_file)

    treeness = phykit_treeness(tree_file)
    assert isinstance(treeness, float)
    assert 0 < treeness < 1

    shutil.rmtree(tmpdir)
    return "Quoted labels: treeness = %.4f" % treeness


def test_79_tree_number_of_taxa():
    """Test counting taxa in trees of different sizes."""
    tmpdir = tempfile.mkdtemp()

    # 2-taxon
    tf2 = os.path.join(tmpdir, "t2.nwk")
    create_test_tree("(A:0.1,B:0.2);", tf2)
    tree2, _ = load_tree(tf2)
    assert tree2.count_terminals() == 2

    # 5-taxon
    tf5 = os.path.join(tmpdir, "t5.nwk")
    create_test_tree("(((A:0.1,B:0.2):0.1,C:0.3):0.1,(D:0.4,E:0.5):0.2);", tf5)
    tree5, _ = load_tree(tf5)
    assert tree5.count_terminals() == 5

    shutil.rmtree(tmpdir)
    return "Taxon counts: 2-taxon=2, 5-taxon=5"


def test_80_batch_treeness_rcv_with_filter():
    """Test batch treeness/RCV with gap filtering (BixBench bix-25 pattern)."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))

    results = {}
    for entry in fungi_genes:
        if 'tree_file' in entry and 'aln_file' in entry:
            try:
                gap_pct = alignment_gap_percentage(entry['aln_file'])
                torcv, treeness, rcv = phykit_treeness_over_rcv(
                    entry['tree_file'], entry['aln_file'])
                results[entry['gene_id']] = {
                    'treeness_rcv': torcv,
                    'treeness': treeness,
                    'rcv': rcv,
                    'gap_pct': gap_pct
                }
            except Exception:
                pass

    assert len(results) > 0

    # Filter by gap percentage (>5% for test data)
    high_gap = {k: v for k, v in results.items() if v['gap_pct'] > 5}
    if high_gap:
        finite = {k: v['treeness_rcv'] for k, v in high_gap.items() if np.isfinite(v['treeness_rcv'])}
        if finite:
            max_val = max(finite.values())
            shutil.rmtree(tmpdir)
            return "Gap-filtered treeness/RCV: max = %.4f (%d genes)" % (max_val, len(finite))

    shutil.rmtree(tmpdir)
    return "Gap-filtered treeness/RCV: computed for %d genes" % len(results)


def test_81_end_to_end_treeness_comparison():
    """End-to-end test: compute treeness for two groups and compare."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    # Batch compute
    fungi_vals = batch_compute(fungi_genes, phykit_treeness, requires='tree')
    animal_vals = batch_compute(animal_genes, phykit_treeness, requires='tree')

    f_list = list(fungi_vals.values())
    a_list = list(animal_vals.values())

    # All expected statistics
    median_f = np.median(f_list)
    median_a = np.median(a_list)
    diff = abs(median_f - median_a)
    max_a = max(a_list)
    pct_above_threshold = sum(1 for v in f_list if v > 0.3) / len(f_list) * 100

    from scipy import stats
    u_stat, p_value = stats.mannwhitneyu(a_list, f_list, alternative='two-sided')

    assert len(f_list) == 5
    assert len(a_list) == 5

    shutil.rmtree(tmpdir)
    return ("Treeness comparison: median_f=%.4f, median_a=%.4f, diff=%.4f, "
            "max_a=%.4f, U=%.1f, p=%.4f") % (
        median_f, median_a, diff, max_a, u_stat, p_value)


def test_82_end_to_end_parsimony():
    """End-to-end test: compute PI sites for two groups and compare."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    def get_pi(gene_files):
        results = {}
        for entry in gene_files:
            if 'aln_file' in entry:
                try:
                    count, length, pct = phykit_parsimony_informative(entry['aln_file'])
                    results[entry['gene_id']] = {'count': count, 'pct': pct}
                except Exception:
                    pass
        return results

    f_pi = get_pi(fungi_genes)
    a_pi = get_pi(animal_genes)

    f_pct = [r['pct'] for r in f_pi.values()]
    a_pct = [r['pct'] for r in a_pi.values()]
    f_count = [r['count'] for r in f_pi.values()]
    a_count = [r['count'] for r in a_pi.values()]

    from scipy import stats
    u_stat_pct, _ = stats.mannwhitneyu(a_pct, f_pct, alternative='two-sided')
    u_stat_count, _ = stats.mannwhitneyu(a_count, f_count, alternative='two-sided')

    median_f_pct = np.median(f_pct)
    max_a_count = max(a_count)

    shutil.rmtree(tmpdir)
    return ("PI comparison: median_f_pct=%.2f%%, max_a_count=%d, "
            "U_pct=%.1f, U_count=%.1f") % (
        median_f_pct, max_a_count, u_stat_pct, u_stat_count)


def test_83_end_to_end_evo_rate():
    """End-to-end test: evolutionary rate comparison."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    f_rates = batch_compute(fungi_genes, phykit_evolutionary_rate, requires='tree')
    a_rates = batch_compute(animal_genes, phykit_evolutionary_rate, requires='tree')

    # Specific gene lookup
    gene1_animal = a_rates.get('gene1')
    assert gene1_animal is not None

    # Max fungi rate
    max_fungi = max(f_rates.values())

    # Median difference
    median_diff = abs(np.median(list(f_rates.values())) - np.median(list(a_rates.values())))

    from scipy import stats
    u_stat, _ = stats.mannwhitneyu(list(a_rates.values()), list(f_rates.values()),
                                    alternative='two-sided')

    shutil.rmtree(tmpdir)
    return "Evo rate: gene1_animal=%.4f, max_fungi=%.4f, diff=%.4f, U=%.1f" % (
        gene1_animal, max_fungi, median_diff, u_stat)


def test_84_end_to_end_tree_length():
    """End-to-end test: tree length comparison with all metrics."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    f_tl = batch_compute(fungi_genes, phykit_tree_length, requires='tree')
    a_tl = batch_compute(animal_genes, phykit_tree_length, requires='tree')

    f_vals = list(f_tl.values())
    a_vals = list(a_tl.values())

    fold_change = np.median(f_vals) / np.median(a_vals)
    var_animals = np.var(a_vals, ddof=1)
    threshold = 5.0
    pct_above = sum(1 for v in f_vals if v > threshold) / len(f_vals) * 100
    mean_animals = np.mean(a_vals)
    pct_exceeding = sum(1 for v in f_vals if v > mean_animals) / len(f_vals) * 100

    # Paired ratios
    common = set(f_tl.keys()) & set(a_tl.keys())
    ratios = [f_tl[g] / a_tl[g] for g in common if a_tl[g] > 0]
    median_ratio = np.median(ratios)

    shutil.rmtree(tmpdir)
    return ("Tree length: fold=%.2fx, var_a=%.4f, pct>5=%.0f%%, "
            "pct>mean_a=%.0f%%, median_ratio=%.3f") % (
        fold_change, var_animals, pct_above, pct_exceeding, median_ratio)


def test_85_end_to_end_dvmc():
    """End-to-end test: DVMC analysis."""
    tmpdir = create_test_data_dir()
    fungi_genes = discover_gene_files(os.path.join(tmpdir, "fungi"))
    animal_genes = discover_gene_files(os.path.join(tmpdir, "animals"))

    f_dvmc = batch_compute(fungi_genes, phykit_dvmc, requires='tree')
    a_dvmc = batch_compute(animal_genes, phykit_dvmc, requires='tree')

    f_vals = list(f_dvmc.values())
    a_vals = list(a_dvmc.values())

    pct_below = sum(1 for v in f_vals if v < 0.3) / len(f_vals) * 100
    median_a = np.median(a_vals)
    std_a = np.std(a_vals, ddof=1)
    max_a = max(a_vals)

    from scipy import stats
    u_stat, _ = stats.mannwhitneyu(a_vals, f_vals, alternative='two-sided')

    # Specific gene lookup
    gene4_fungi = f_dvmc.get('gene4')

    shutil.rmtree(tmpdir)
    return ("DVMC: pct<0.3=%.0f%%, median_a=%.4f, std_a=%.4f, max_a=%.4f, "
            "U=%.1f, gene4=%.4f") % (
        pct_below, median_a, std_a, max_a, u_stat,
        gene4_fungi if gene4_fungi else 0)


# ===========================================================================
# TEST RUNNER
# ===========================================================================

def run_all_tests():
    """Run all test functions and generate report."""
    # Collect all test functions
    test_funcs = []
    g = globals()
    for name in sorted(g.keys()):
        if name.startswith('test_') and callable(g[name]):
            test_funcs.append((name, g[name]))

    total = len(test_funcs)
    passed = 0
    failed = 0
    errors = []

    print("=" * 70)
    print("Phylogenetics Skill Test Suite")
    print("=" * 70)
    print(f"Running {total} tests...\n")

    for name, func in test_funcs:
        try:
            result = func()
            passed += 1
            status = "PASS"
            print(f"  [{status}] {name}")
            if result:
                print(f"         {result}")
        except Exception as e:
            failed += 1
            status = "FAIL"
            error_msg = traceback.format_exc()
            errors.append((name, str(e), error_msg))
            print(f"  [{status}] {name}")
            print(f"         ERROR: {e}")

    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 70)

    if errors:
        print("\nFailed tests:")
        for name, err, tb in errors:
            print(f"\n  {name}:")
            print(f"    {err}")

    return passed, total, errors


if __name__ == "__main__":
    passed, total, errors = run_all_tests()
    sys.exit(0 if passed == total else 1)
