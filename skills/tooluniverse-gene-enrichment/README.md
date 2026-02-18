# tooluniverse-gene-enrichment

Comprehensive gene enrichment and pathway analysis skill for the ToolUniverse ecosystem.

## Overview

Perform publication-ready gene enrichment analysis using Over-Representation Analysis (ORA) and Gene Set Enrichment Analysis (GSEA). Integrates local computation via **gseapy** with ToolUniverse APIs (**PANTHER**, **STRING**, **Reactome**) for cross-validated results across 225+ gene set libraries.

## Capabilities

| Capability | Method | Tool |
|-----------|--------|------|
| GO Enrichment (BP, MF, CC) | ORA / GSEA | gseapy, PANTHER, STRING |
| KEGG Pathway Enrichment | ORA / GSEA | gseapy, STRING |
| Reactome Pathway Enrichment | ORA | gseapy, ReactomeAnalysis API |
| WikiPathways Enrichment | ORA | gseapy |
| MSigDB Hallmark Enrichment | ORA / GSEA | gseapy |
| Multiple Testing Correction | BH, Bonferroni, BY, Holm | statsmodels |
| Gene ID Conversion | Symbol/Ensembl/Entrez/UniProt | MyGene, STRING |
| Cross-Validation | Multi-source consensus | gseapy + PANTHER + STRING |
| Network Context | PPI enrichment | STRING |
| Multi-Organism | human, mouse, rat, fly, worm, yeast, zebrafish | All tools |

## Quick Start

```python
import gseapy

# Standard GO enrichment (ORA)
result = gseapy.enrichr(
    gene_list=["TP53", "BRCA1", "EGFR", "MYC", "AKT1", "PTEN"],
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
sig = result.results[result.results['Adjusted P-value'] < 0.05]
print(sig[['Term', 'Adjusted P-value', 'Overlap']].head(5))
```

## Enrichment Databases

- **225+ Enrichr libraries** via gseapy (GO, KEGG, Reactome, WikiPathways, MSigDB, DisGeNET, CellMarker, GTEx, ChEA, ENCODE, and more)
- **PANTHER** over-representation analysis (curated GO, PANTHER Pathways, Reactome)
- **STRING** functional enrichment (GO, KEGG, Reactome, WikiPathways, COMPARTMENTS, DISEASES, HPO)
- **Reactome Analysis Service** pathway overrepresentation

## Supported Organisms

Human (9606), Mouse (10090), Rat (10116), Drosophila (7227), C. elegans (6239), Yeast (4932), Zebrafish (7955)

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Complete skill specification with 8-phase workflow, tool reference, response formats |
| `QUICK_START.md` | 10 use case examples with copy-paste code |
| `test_gene_enrichment.py` | 50-test comprehensive test suite (100% pass rate) |
| `README.md` | This file |

## Test Results

```
Total: 50 | Passed: 50 | Failed: 0 | Time: 63.4s
Pass Rate: 50/50 (100.0%)
```

### Test Coverage

| Phase | Tests | Description |
|-------|-------|-------------|
| gseapy ORA | 9 | GO BP/MF/CC, KEGG, Reactome, Hallmark, WikiPathways, multi-library, structure |
| GSEA | 3 | Preranked GO/KEGG, NES direction |
| PANTHER | 4 | GO BP/MF/CC, PANTHER Pathways |
| STRING | 3 | Functional enrichment, KEGG, PPI enrichment |
| Reactome API | 2 | Pathway enrichment, cross-validation |
| ID Conversion | 3 | MyGene batch, STRING map, enrichment after conversion |
| Multiple Testing | 3 | BH, Bonferroni, method comparison |
| Cross-Validation | 2 | GO BP consensus, KEGG consensus |
| Gene Lists | 4 | Immune, signaling, small (3), large (43) |
| Term Lookup | 2 | Specific GO term, specific KEGG pathway |
| GO Details | 2 | Term details, gene annotations |
| Pathway Details | 3 | Reactome, KEGG, WikiPathways |
| Organisms | 2 | Mouse gseapy, PANTHER mouse |
| Library Discovery | 2 | List libraries, version verification |
| BixBench | 4 | Adjusted p-val, most enriched, GSEA metabolic, enrichGO equivalent |
| Integration | 2 | Full pipeline, comparative enrichment |

## BixBench Question Support

This skill is designed to answer BixBench-style enrichment questions:

1. **"What is the adjusted p-val for [GO term] from enrichGO enrichment analysis?"**
   - Use `gseapy.enrichr()` with GO library, search results for specific term

2. **"Using gseapy and [library], which pathway is most significantly enriched?"**
   - Use `gseapy.enrichr()` with specified library, sort by Adjusted P-value

3. **"In a KEGG pathway enrichment analysis, what is the p-value for the most enriched pathway?"**
   - Use `gseapy.enrichr()` with KEGG_2021_Human, report top result

4. **"What GO Biological Processes are enriched (BH adjusted p < 0.05)?"**
   - Use `gseapy.enrichr()`, filter by Adjusted P-value < 0.05

5. **"Compare enrichment using Bonferroni vs BH correction"**
   - Use `statsmodels.stats.multitest.multipletests()` with both methods

## Dependencies

- **Required**: gseapy, pandas, scipy, statsmodels
- **ToolUniverse**: PANTHER, STRING, Reactome, MyGene, GO, QuickGO, WikiPathways, KEGG tools
- **Optional**: numpy (for GSEA ranked lists)

## Installation

```bash
pip install gseapy pandas scipy statsmodels
```
