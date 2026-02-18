# RNA-seq DESeq2 Differential Expression Analysis

Production-ready skill for RNA-seq differential expression analysis using PyDESeq2, with integrated enrichment analysis (gseapy) and gene annotation via ToolUniverse.

## Coverage

- **53 BixBench questions** across 15 projects
- **25+ core DE analysis patterns** (basic DEG counting, specific gene lookup, multi-condition comparisons, dispersion diagnostics, enrichment integration)
- **Any organism** (human, mouse, yeast, bacteria, etc.)

## Capabilities

| Capability | Status | Details |
|-----------|--------|---------|
| DESeq2 normalization | Supported | Size factor estimation, median-of-ratios |
| Wald test | Supported | Per-gene significance testing |
| LFC shrinkage | Supported | Adaptive shrinkage (apeglm-like) |
| Multi-factor designs | Supported | ~strain + media, ~condition + batch |
| Dispersion estimation | Supported | Genewise, fitted, MAP, final |
| GO enrichment | Supported | via gseapy (GO BP, MF, CC) |
| KEGG enrichment | Supported | KEGG_2021_Human, KEGG_2019_Mouse |
| Reactome enrichment | Supported | Reactome_2022 |
| WikiPathways enrichment | Supported | 2019 Human/Mouse |
| Multiple testing | Supported | BH, BY, Bonferroni, Holm |
| miRNA DE | Supported | t-test with multiple corrections |
| Proteomics DE | Supported | t-test on normalized intensities |
| Gene annotation | Supported | UniProt, Ensembl, MyGene via ToolUniverse |
| Batch effect handling | Supported | Multi-factor design or sample exclusion |
| GO term simplification | Supported | Jaccard similarity-based (approximates R simplify()) |

## Installation

```bash
# Required packages
pip install pydeseq2 gseapy pandas numpy scipy anndata statsmodels

# For ToolUniverse gene annotation
pip install tooluniverse
```

## Quick Start

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Load data
counts = pd.read_csv("counts.csv", index_col=0)
metadata = pd.read_csv("metadata.csv", index_col=0)

# Set reference level
metadata['condition'] = pd.Categorical(
    metadata['condition'], categories=['control', 'treatment']
)

# Run DESeq2
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~condition", quiet=True)
dds.deseq2()

# Get results
stat_res = DeseqStats(dds, contrast=['condition', 'treatment', 'control'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()

# Filter DEGs
results = stat_res.results_df
sig = results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)]
print(f"Significant DEGs: {len(sig)}")
```

## Test Results

```
84/84 tests passed (100.0%)
```

Test categories:
- Package imports (5 tests)
- Data loading (4 tests)
- Data validation (4 tests)
- Basic DESeq2 (4 tests)
- LFC shrinkage (2 tests)
- Multi-factor design (4 tests)
- Dispersion analysis (5 tests)
- Result filtering (4 tests)
- DEG set operations (4 tests)
- Multiple testing (4 tests)
- Enrichment ORA (5 tests)
- Gene extraction (4 tests)
- Statistical tests (4 tests)
- miRNA DE (4 tests)
- Enrichment term search (4 tests)
- GO simplification (2 tests)
- Output formatting (6 tests)
- Edge cases (5 tests)
- Distribution analysis (2 tests)
- Batch effect (3 tests)
- Enrichment overlap (2 tests)
- ToolUniverse integration (3 tests)

## File Structure

```
tooluniverse-rnaseq-deseq2/
  SKILL.md          # Full skill documentation (main reference)
  QUICK_START.md    # Quick start guide with recipes
  README.md         # This file
  test_skill.py     # Comprehensive test suite (84 tests)
```

## Key Implementation Notes

### PyDESeq2 v0.5.4 Specifics

1. **Reference level**: Use `pd.Categorical` with reference as first category (NOT `ref_level` parameter, which is deprecated)
2. **Dispersions**: Stored in `dds.var` (NOT `dds.varm`). Keys: `genewise_dispersions`, `fitted_dispersions`, `MAP_dispersions`, `dispersions`
3. **LFC shrinkage coefficient**: Format is `factor[T.level]` (e.g., `condition[T.treatment]`)
4. **Results access**: Call `stat_res.summary()` before accessing `stat_res.results_df`

### gseapy v1.1.11 Specifics

1. **No `organism` parameter**: Organism specificity is in the gene_sets library name
2. **Key libraries**: `GO_Biological_Process_2021`, `KEGG_2021_Human`, `KEGG_2019_Mouse`, `Reactome_2022`
3. **Result columns**: `Term`, `Overlap`, `P-value`, `Adjusted P-value`, `Odds Ratio`, `Combined Score`, `Genes`
