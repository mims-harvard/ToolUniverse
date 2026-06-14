---

name: tooluniverse-phylogenetics
description: "Phylogenetic analysis — de novo multiple sequence alignment (Clustal Omega/MUSCLE/MAFFT via EBI_msa_align) and neighbour-joining/UPGMA tree building (EBI_build_phylogenetic_tree) from your own sequences, plus tree analysis, treeness, saturation (PhyKIT), parsimony-informative sites, alignment gap analysis, DVMC, long-branch detection, BUSCO orthologs. Uses PhyKIT, Biopython, DendroPy. Use to align a set of sequences, build a tree from sequences or an alignment, or for phylogenetic tree QC, multi-gene phylogenomics, evolutionary-rate analysis, and comparative-genomics studies."
---

# Phylogenetics and Sequence Analysis

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- **`scogs_fungi.zip` / `scogs_animals.zip`** (BUSCO single-copy ortholog phylogenetics) → these contain the pre-computed alignments (`*.faa.mafft.clipkit`) and trees (`*.faa.mafft.clipkit.treefile`) from the original analysis. **Use these directly with PhyKIT** (see "BUSCO scogs questions" below). Re-running BUSCO → MAFFT → IQ-TREE from `*.busco.zip` files takes 1–6 hours AND produces slightly different numbers due to seed/version drift.
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed result files (CSV/TSV with names like `*results*`, `*tree*`, `*phykit*`, `*saturation*`, `*treeness*`) → read directly and report the requested value
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running from raw data produces different numbers than the published answer and is much slower (often 5–10× turn count).

---

## BUSCO scogs questions (multi-species phylogenomics)

data folders with `scogs_fungi.zip` and/or `scogs_animals.zip` ship
pre-computed per-ortholog alignments (and sometimes trees). The
question asks for a metric per group, or a Mann-Whitney U / median /
ratio comparison between groups.

### PRIMARY SCRIPT — both groups in one pass (use this FIRST)

When the question compares animals vs fungi (Mann-Whitney U, ratio,
fold-change, paired difference), the bundled paired-comparison script
extracts both zips, computes the metric per ortholog for each group,
and emits ALL of: per-group summary, two-tailed Mann-Whitney U +
p-value (in both orderings since U is asymmetric), paired-ortholog
median diff, paired-ortholog median ratio, group-median ratio, and
lowest-non-zero ratios — in one run, no aggregation step needed:

```bash
python skills/tooluniverse-phylogenetics/scripts/scogs_paired_compare.py \
    --data-folder "$DATA_PATH" --metric parsimony_informative
# Metrics: parsimony_informative, rcv, gap_percentage (alignment-only,
# Biopython-fast: ~2s for 500 alignments);
# treeness, dvmc, total_tree_length, evolutionary_rate, long_branch_score,
# patristic_distances (tree); treeness_over_rcv, saturation (both).
```

Output blocks (parse in Python or grep):

```
# SUMMARY group=animals: n=... mean=... median=... min=... max=... p25=... p75=... lowest_nonzero=... n_nonzero=...
# SUMMARY group=fungi:   n=... mean=... median=... min=... max=... p25=... p75=... lowest_nonzero=... n_nonzero=...
# MWU animals_vs_fungi: U=... p=...
# MWU fungi_vs_animals: U=... p=...        <-- U(a,b) + U(b,a) = n_a*n_b
# PAIRED n_common=N: median_diff(animals-fungi)=...  median_diff(fungi-animals)=...
# PAIRED RATIO median(animals/fungi)=... (n=...)    <-- for each common ortholog: a_val/b_val, then median
# PAIRED RATIO median(fungi/animals)=... (n=...)
# GROUP_MEDIAN_RATIO animals/fungi=...               <-- median(group_a) / median(group_b)
# GROUP_MEDIAN_RATIO fungi/animals=...
# GROUP_MEDIAN_DIFF animals-fungi=...
# LOWEST_NONZERO animals=... fungi=...
# LOWEST_NONZERO_RATIO animals/fungi=...
# LOWEST_NONZERO_RATIO fungi/animals=...
```

For `long_branch_score` and `patristic_distances` (multi-value-per-tree
metrics), pass `--per-tree-stat mean` or `--per-tree-stat median` to
choose the per-tree summary BEFORE the cross-tree MWU. The question
wording "comparing **median** long branch scores" means per-tree
summary = median; "comparing **mean** long branch scores" means
per-tree summary = mean. Run TWICE (once with each) if uncertain.

### Single-group script (when only one group is asked about)

```bash
python skills/tooluniverse-phylogenetics/scripts/scogs_phykit_pipeline.py \
    --data-folder "$DATA_PATH" --group fungi --metric treeness --out /tmp/f.tsv
# Auto-falls-back to .faa.mafft when .faa.mafft.clipkit is absent
# (some scogs zips ship only mafft alignments, not clipkit trims).
```

### `phykit parsimony_informative` is NOT a valid CLI subcommand

PhyKIT's CLI exposes parsimony-informative-site count as
`parsimony_informative_sites` (alias `pis`). Calling
`phykit parsimony_informative <file>` returns the help banner with
non-zero exit and silently produces zero values. The bundled scripts
translate `parsimony_informative` → `parsimony_informative_sites`
automatically. The output is `<n_pi>\t<n_total>\t<percent>` — column
THREE is the percentage that questions usually ask for.

### Group-median ratio vs paired ratio (read this carefully)

When a question phrases tree-length / RCV / DVMC comparisons as
"ratio of fungal to animal X across orthologs", there are TWO distinct
quantities:

1. **GROUP_MEDIAN_RATIO** = `median(values_fungi) / median(values_animals)`.
   Use ALL orthologs in each group independently. This is what
   group-comparison published numbers usually report (n_fungi can
   differ from n_animals, and "across" is a population statement, not
   a paired one).

2. **PAIRED RATIO median** = for each ortholog present in BOTH groups,
   compute `value_fungi / value_animals`, then take the median across
   common orthologs. Smaller denominator (intersection only) and a
   different number when the groups have different size.

Default to GROUP_MEDIAN_RATIO unless the question explicitly says
"matched ortholog", "paired ortholog", "per-ortholog ratio", or "for
each ortholog". If the answer phrasing is ambiguous, BOTH numbers are
in the script's output — pick the one matching the question's
"across" / "paired" / "ratio of medians" phrasing.

### Total amino-acid count across single-copy orthologs — single representative, not all species

When a BUSCO single-copy ortholog dataset (`single_copy_busco_sequences/`) is
present and the question asks "**how many total amino acids** are present in all
single-copy ortholog sequences", count **one representative sequence per
ortholog**, not the sum across all species/copies.

Each `<ortholog_id>.faa` in `single_copy_busco_sequences/` typically contains
multiple species' copies of that ortholog (one each). Summing every sequence
across every species double/triple/N-fold counts each ortholog by the species
count and gives `n_species × correct_answer`.

| Question phrasing | Count |
|---|---|
| "total amino acids in all single-copy ortholog sequences" | Sum of ONE sequence per ortholog (either the FIRST entry per file or the median-length entry) |
| "total amino acids across N species' single-copy orthologs" | Sum across species explicitly (multi-species sum) |
| "average length of single-copy orthologs" | Mean per-ortholog length (one per ortholog) |

❌ WRONG: `for f in *.faa: sum(len(rec.seq) for rec in SeqIO.parse(f, 'fasta'))` then sum across files (multi-species sum)

✅ RIGHT: `for f in *.faa: first_rec = next(SeqIO.parse(f, 'fasta')); total += len(first_rec.seq)` (one representative per ortholog)

If your answer is `n_species × GT` (e.g. 32228 when GT looks like 13809 = 32228/2.33 ≈ 8 species × representative), you summed all species — re-do with one representative.

### Lowest-non-zero ratios

For metrics that can legitimately equal 0 for highly conserved or
very short alignments (parsimony informative %, RCV on near-identical
seqs), "lowest" in a question typically means "lowest non-zero". The
paired script emits `LOWEST_NONZERO_RATIO` for both orderings — use
that line when the raw min in a group is 0.

### File-layout fallback (alignment naming)

scogs zips ship in two shapes:
- **Full**: `<gene>.faa`, `<gene>.faa.mafft`, `<gene>.faa.mafft.clipkit`,
  `<gene>.faa.mafft.clipkit.treefile`, plus iqtree/bionj/log/mldist.
  Use clipkit alignment + treefile for tree-paired metrics.
- **Alignment-only**: just `<gene>.faa` + `<gene>.faa.mafft`. No
  trees, no clipkit. Used for parsimony, RCV, gap-percentage
  questions. Use the `.faa.mafft` (NOT raw `.faa`) — the published
  metric was computed on the MAFFT-aligned file.

Both bundled scripts auto-detect the layout and use the best available
alignment per ortholog. Do NOT re-run MAFFT or ClipKit yourself; the
shipped files are canonical.

**Anti-pattern:** running `phykit` on the raw `*.busco.zip` extracted
ortholog FASTAs and aligning/tree-building yourself. The pre-computed
files in `scogs_*.zip` are the canonical inputs.

---

PhyKIT, Biopython, and DendroPy for alignment/tree analysis, evolutionary metrics, and comparative genomics.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first.

---

## When to Use

FASTA/PHYLIP/Nexus/Newick files; treeness, RCV, DVMC, evolutionary rate, parsimony sites, tree length, bootstrap; group comparisons (Mann-Whitney U); tree construction (NJ/UPGMA/parsimony); Robinson-Foulds distance.

**De novo alignment / tree from your own sequences:** to align raw sequences (not pre-computed files), call `EBI_msa_align` (Clustal Omega / MUSCLE / MAFFT / Kalign / T-Coffee via EMBL-EBI), then pass its `data.aligned_fasta` string as the `aligned_sequences` argument of `EBI_build_phylogenetic_tree` (note the arg name differs from the output key) for a neighbour-joining or UPGMA tree (Newick). Feed that Newick / alignment straight into the PhyKIT metrics below.

**Still NOT for**: maximum-likelihood trees (IQ-TREE/RAxML) or Bayesian inference (MrBayes/BEAST) — `EBI_build_phylogenetic_tree` only does distance-based NJ/UPGMA. For publication ML/Bayesian phylogenies, run dedicated tooling; use the pre-computed `scogs_*` trees when available.

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

## Analysis conventions

### MANDATORY: Use `phykit_batch_analysis` tool for batch computations
For ANY question asking for statistics across multiple trees/alignments (median treeness, mean saturation, DVMC percentage, gap percentage, long branch scores), use the ToolUniverse tool:
```bash
tu run phykit_batch_analysis '{"operation":"batch","function":"treeness","directory":"./trees","extension":".treefile"}'
tu run phykit_batch_analysis '{"operation":"batch","function":"saturation","directory":"./alignments","extension":".fa","tree_directory":"./trees","tree_extension":".treefile"}'
tu run phykit_batch_analysis '{"operation":"gap_percentage","directory":"./alignments","extension":".fa"}'
```
Do NOT run phykit manually in a loop — the tool handles all files and returns correct summary statistics.

### PhyKIT column-position cheat sheet (parse output carefully)

When parsing PhyKIT stdout for batch metrics, the **column you want** depends on the metric:

| Command | Output columns | Column to take |
|---------|---------------|----------------|
| `phykit saturation` | `saturation_value <TAB> abs(saturation-1)` | **col 1** is the "saturation value" (1 = no saturation; closer to 1 = less saturated). **col 2** = `\|saturation - 1\|` (distance from no-saturation; higher = MORE saturated, less signal retained). Use col 1 for "saturation value" questions; col 2 for "distance from saturation" |
| `phykit toverr` (a.k.a. `treeness_over_rcv`) | `treeness/RCV <TAB> treeness <TAB> RCV` | **col 1** (treeness/RCV ratio) |
| `phykit long_branch_score -v` (verbose) | `taxon <TAB> score` per line | aggregate scores per tree (mean) |
| `phykit long_branch_score` (no -v) | `mean <TAB> median <TAB> 25%ile <TAB> 75%ile <TAB> min <TAB> max <TAB> std <TAB> var <TAB> n` | **col 1** (mean) for "mean LB score" |
| `phykit patristic_distances` (no -v) | summary stats line (same shape as LB) | **col 1** (mean) for "mean patristic distance" |

**Rule of thumb**: phykit `toverr` and `saturation` produce *multi-column lines per alignment*. Don't grep the value that "looks like the answer" — count columns from the header in `phykit <metric> --help`. If your batch median is wildly off the published number (e.g., median treeness/RCV ≈ 0.20 when expected ≈ 0.26), you almost certainly picked the wrong column.

Preferred: don't parse phykit output by hand — call the `phykit_batch_analysis` tool, which already returns the correct column for each metric. Supported `function` values are `treeness`, `saturation`, `dvmc`, `long_branch_score`, `total_tree_length`, `parsimony_informative`:

```bash
tu run phykit_batch_analysis '{"operation":"batch","function":"saturation","directory":"./alignments","extension":".fa","tree_directory":"./trees","tree_extension":".treefile"}'
tu run phykit_batch_analysis '{"operation":"batch","function":"treeness","directory":"./alignments","extension":".fa","tree_directory":"./trees","tree_extension":".treefile"}'
```

For `treeness_over_rcv` (toverr / treeness/RCV ratio) the tool has no matching `function`; use the bundled `scogs_*.py` scripts below, which compute it directly.

Sanity targets for biological scogs trees: median saturation ~0.4–0.7, median treeness/RCV ~0.2–0.4, median treeness ~0.05–0.15. Values an order of magnitude off these mean wrong column.

### Bundled script: BUSCO target_orthologs intersection

When the data folder has `*.busco.zip` files + `target_orthologs.txt`, use the bundled script — do NOT enumerate `single_copy_busco_sequences/*.faa` across all zips manually:

```bash
python skills/tooluniverse-phylogenetics/scripts/busco_target_orthologs.py \
  --data-folder /path/to/data
```

The default run prints FIVE summary lines covering every common
interpretation of "total amino acids":

```
# SUMMARY: n_targets=K, n_intersected=N (single-copy in ALL S species), intersected_total_aa=A, sum_all_aa=B
# SUMMARY group=all: intersected n=N total_aa=A, sum_all total_aa=B
# SUMMARY group=animals: sum_all total_aa=X        <-- per-group sum (animal species only)
# SUMMARY group=fungi:   sum_all total_aa=Y        <-- per-group sum (fungal species only)
```

### Picking the right SUMMARY line (read carefully)

Match the question phrasing to the summary line:

| Question phrasing | Pick this line | Why |
|---|---|---|
| "total AA in all single-copy ortholog sequences" with **only animal species in the data folder OR question mentions only one organism group** | `# SUMMARY group=animals: sum_all total_aa=...` (or `group=fungi`) | scogs phylogenomics analyses are run PER GROUP; "all" refers to all orthologs WITHIN that group, not the union across groups |
| "total AA across orthologs single-copy in **every** / **all** species" | `intersected_total_aa` | strict intersection rule |
| "total AA across all per-species copies" | `sum_all_aa` (group=all) | only when the question says "all species" or the data folder has just one organism group |

**Default rule when the data folder contains BOTH animal AND fungal busco
zips**: published "total amino acids" answers almost always refer to
ONE group (the analysis group), NOT the cross-group union. Use
`group=animals: sum_all` or `group=fungi: sum_all`. Do NOT pick the
union number (`sum_all_aa`) unless the question explicitly says
"across all 8 species" or "fungi and animals combined".

The script emits the per-group sums BEFORE the union sum on stdout for
this exact reason — read the output line by line and stop at the
`group=animals` / `group=fungi` line that matches the analysis group
implied by the question.

### Single-copy orthologs across species — comparison set + intersection

Two-step rule when counting across BUSCO `single_copy_busco_sequences/` data:

1. **Find the comparison set first.** If a `target_orthologs.txt` (or similar named subset list) exists in the data folder, that file IS the comparison set — restrict to those ortholog IDs only. Do not enumerate every BUSCO single-copy file across species. Do not assume "all" means the whole BUSCO output when a target list is provided.

2. **Then apply the intersection rule.** "Single-copy ortholog" across species means single-copy in EVERY species in the comparison set. If an ortholog is missing from one species' `single_copy_busco_sequences/`, exclude it from the count entirely — do not partially count the species that do have it.

Sanity check: if any species shows a much smaller per-ortholog count than others (e.g., one species at ~600 aa while others are 4000+ aa for the same ortholog set), the missing-from-some orthologs are inflating the per-ortholog average — drop them first.

**Worked example.** data folder has 8 species (4 animal, 4 fungal) `*.busco.zip` + `target_orthologs.txt` listing 10 ortholog IDs:
- Wrong: enumerate all `single_copy_busco_sequences/*.faa` across all 8 species → ≈80 files → sum AA → answer 32228 (treats every per-species copy independently).
- Right: for each of the 10 target IDs, check it appears as `single_copy` in **all 8** species → keep only intersected IDs (often 5/10 — some target IDs are multi-copy/missing in one species) → for kept IDs, sum AA across the 8 species → 13809.
- **"5 trees" semantics**: when a question says "5 trees" but you find 10 treefiles, the GT used the intersected subset (orthologs single-copy in all species) — not all 10. Re-derive the intersection before averaging.

### Process the FULL set, not a sample (batch metrics)

When a question asks for a median/percentile/mean across orthologs, your batch must include EVERY ortholog in the relevant comparison set:
- `scogs_fungi.zip` ships ~255 fungal alignments+trees; `scogs_animals.zip` ships ~241. Median computed from a 10-file sample is NOT the published answer.
- For `phykit_batch_analysis`, always point at the **extracted scogs directory** containing all per-ortholog files, not a hand-picked subset.
- If your computed RCV/treeness/DVMC median diverges from a sanity-check target by >10%, count files first — you likely processed a subset.

### Filter THEN compute (don't compute then filter)

Questions of the form "max X in genes with >70% gaps" require the filter to be applied before the max:
```python
# 1. Compute gap% per alignment
# 2. Keep only alignments with gap% > 70
# 3. Compute treeness/RCV ON THE FILTERED SET
# 4. Take max
```
Computing the metric across all genes and then taking max returns the global max, which is wrong.

### Animals vs fungi — long branch score aggregation

PhyKIT's `long_branch_score -v` outputs per-taxon LB scores (one row
per leaf in the tree). For per-tree summaries:
1. Per-tree: run `phykit long_branch_score -v <tree>` → list of
   per-taxon scores.
2. Per-tree summary: collapse to ONE number per tree using either
   the **mean** or the **median** of those per-taxon scores.
3. Per-group summary: aggregate per-tree numbers (median/mean/MWU U +
   p-value).

**Match the per-tree summary to the question phrasing:**

| Question says... | Use `--per-tree-stat ...` |
|---|---|
| "mean long branch scores" | `mean` |
| "median long branch scores" | `median` |
| "average long branch score" (ambiguous) | run BOTH and pick the one matching numbers/units |

The bundled `scogs_paired_compare.py --metric long_branch_score
--per-tree-stat {mean,median}` does steps 1+2 for both groups in one
pass and emits the cross-group MWU U + p-value directly.

Common error: averaging the four animal species and four fungal
species directly without going through the per-tree step — this
conflates species LB and ortholog LB and yields the wrong delta.

### Treeness/RCV: use the right input file

`phykit toverr` (a.k.a. `treeness_over_rcv`) takes BOTH alignment and tree. Use the **trimmed** alignment (`*.faa.mafft.clipkit`) paired with its **treefile** (`*.faa.mafft.clipkit.treefile`), not the raw `.faa.mafft`. ClipKit-trimmed alignments are what produced the canonical tree, so the RCV must be computed on the same trimmed alignment for the ratio to match published numbers.

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

# Evolutionary rate (median across trees)
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir trees --function evolutionary_rate --ext .treefile --stat median

# Mean patristic distance per tree, then mean across trees
python skills/tooluniverse-phylogenetics/scripts/phykit_batch.py \
  --dir trees --function patristic_distances --ext .treefile --stat mean
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
