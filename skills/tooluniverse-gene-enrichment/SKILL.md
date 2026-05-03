---
name: tooluniverse-gene-enrichment
description: Perform comprehensive gene enrichment and pathway analysis using gseapy (ORA and GSEA), PANTHER, STRING, Reactome, and 40+ ToolUniverse tools. Supports GO enrichment (BP, MF, CC), KEGG, Reactome, WikiPathways, MSigDB Hallmark, and 220+ Enrichr libraries. Handles multiple ID types (gene symbols, Ensembl, Entrez, UniProt), multiple organisms (human, mouse, rat, fly, worm, yeast), customizable backgrounds, and multiple testing correction (BH, Bonferroni). Use when users ask about gene enrichment, pathway analysis, GO term enrichment, KEGG pathway analysis, GSEA, over-representation analysis, functional annotation, or gene set analysis.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Gene Enrichment and Pathway Analysis

Perform comprehensive gene enrichment analysis including Gene Ontology (GO), KEGG, Reactome, WikiPathways, and MSigDB enrichment using both Over-Representation Analysis (ORA) and Gene Set Enrichment Analysis (GSEA). Integrates local computation via gseapy with ToolUniverse pathway databases for cross-validated, publication-ready results.

**IMPORTANT**: Always use English terms in tool calls (gene names, pathway names, organism names), even if the user writes in another language. Only try original-language terms as a fallback if English returns no results. Respond in the user's language.

## Domain Reasoning: Background Selection

Enrichment results are only as good as your background. The default background (all annotated genes in the genome) inflates enrichment for tissue-specific or context-specific gene lists. Always consider: what is the appropriate background for this experiment? For brain RNA-seq, use brain-expressed genes as background; for a proteomics experiment, use detected proteins. A gene that is never expressed in your system cannot be a true negative control.

LOOK UP DON'T GUESS: adjusted p-values, gene set overlap counts, and which genes from your input list drive each enriched term. Always retrieve the `inputGenes` field from enrichment results — do not assume which genes caused a term to be significant. When a term looks surprising, verify by checking which genes overlap.

---

## When to Use This Skill

Apply when users:
- Ask about gene enrichment analysis (GO, KEGG, Reactome, etc.)
- Have a gene list from differential expression, clustering, or any experiment
- Want to know which biological processes, molecular functions, or cellular components are enriched
- Need KEGG or Reactome pathway enrichment analysis
- Ask about GSEA (Gene Set Enrichment Analysis) with ranked gene lists
- Want over-representation analysis (ORA) with Fisher's exact test
- Need multiple testing correction (Benjamini-Hochberg, Bonferroni)
- Ask about enrichGO, gseapy, clusterProfiler-style analyses

**NOT for** (use other skills instead):
- Network pharmacology / drug repurposing → Use `tooluniverse-network-pharmacology`
- Disease characterization → Use `tooluniverse-multiomic-disease-characterization`
- Single gene function lookup → Use `tooluniverse-disease-research`
- Spatial omics analysis → Use `tooluniverse-spatial-omics-analysis`
- Protein-protein interaction analysis only → Use `tooluniverse-protein-interactions`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **gene_list** | Yes | List of gene symbols, Ensembl IDs, or Entrez IDs | `["TP53", "BRCA1", "EGFR"]` |
| **organism** | No | Organism (default: human). Supported: human, mouse, rat, fly, worm, yeast, zebrafish | `human` |
| **analysis_type** | No | `ORA` (default) or `GSEA` | `ORA` |
| **enrichment_databases** | No | Which databases to query. Default: all applicable | `["GO_BP", "GO_MF", "GO_CC", "KEGG", "Reactome"]` |
| **gene_id_type** | No | Input ID type: `symbol`, `ensembl`, `entrez`, `uniprot` (auto-detected if omitted) | `symbol` |
| **p_value_cutoff** | No | Significance threshold (default: 0.05) | `0.05` |
| **correction_method** | No | Multiple testing: `BH` (Benjamini-Hochberg, default), `bonferroni`, `fdr` | `BH` |
| **background_genes** | No | Custom background gene set (default: genome-wide) | `["GENE1", "GENE2", ...]` |
| **ranked_gene_list** | No | For GSEA: gene-to-score mapping (e.g., log2FC) | `{"TP53": 2.5, "BRCA1": -1.3, ...}` |

---

## Core Principles

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **ID disambiguation FIRST** - Detect and convert gene IDs before ANY enrichment
3. **Multi-source validation** - Run enrichment on at least 2 independent tools, cross-validate
4. **Exact p-values** - Report raw p-values AND adjusted p-values with correction method
5. **Multiple testing correction** - ALWAYS apply Benjamini-Hochberg unless user specifies otherwise
6. **Gene set size filtering** - Filter by min/max gene set size to avoid trivial/overly broad terms
7. **Evidence grading** - Grade enrichment sources T1-T4
8. **Negative results documented** - "No significant enrichment" is a valid finding
9. **Source references** - Every enrichment result must cite the tool/database/library used
10. **Completeness checklist** - Mandatory section at end showing analysis coverage

---

## Decision Tree: ORA vs GSEA

```
Q: Do you have a ranked gene list (with scores/fold-changes)?
  YES → Use GSEA (gseapy.prerank)
        - Input: Gene-to-score mapping (e.g., log2FC)
        - Statistics: Running enrichment score, permutation test
        - Cutoff: FDR q-val < 0.25 (standard for GSEA)
        - Output: NES (Normalized Enrichment Score), lead genes
        See: references/gsea_workflow.md

  NO  → Use ORA (gseapy.enrichr)
        - Input: Gene list only
        - Statistics: Fisher's exact test, hypergeometric
        - Cutoff: Adjusted P-value < 0.05 (or user specified)
        - Output: P-value, adjusted P-value, overlap, odds ratio
        See: references/ora_workflow.md
```

---

## Decision Tree: gseapy vs ToolUniverse Tools

```
Q: Which enrichment method should I use?

Primary Analysis (ALWAYS):
  ├─ gseapy.enrichr (ORA) OR gseapy.prerank (GSEA)
  │  - Most comprehensive (225+ Enrichr libraries)
  │  - GO (BP, MF, CC), KEGG, Reactome, WikiPathways, MSigDB
  │  - All organisms supported
  │  - Returns: P-value, Adjusted P-value, Overlap, Genes
  │  See: references/enrichr_guide.md

Cross-Validation (REQUIRED for publication):
  ├─ PANTHER_enrichment [T1 - curated]
  │  - Curated GO enrichment
  │  - Multiple organisms (taxonomy ID)
  │  - GO BP, MF, CC, PANTHER pathways, Reactome
  │
  ├─ STRING_functional_enrichment [T2 - validated]
  │  - Returns ALL categories in one call
  │  - Filter by category: Process, Function, Component, KEGG, Reactome
  │  - Network-based enrichment
  │
  └─ ReactomeAnalysis_pathway_enrichment [T1 - curated]
     - Reactome curated pathways
     - Cross-species projection
     - Detailed pathway hierarchy

Additional Context (Optional):
  ├─ GO_get_term_by_id, QuickGO_get_term_detail (GO term details)
  ├─ Reactome_get_pathway, Reactome_get_pathway_hierarchy (pathway context)
  ├─ WikiPathways_search, WikiPathways_get_pathway (community pathways)
  └─ STRING_ppi_enrichment (network topology analysis)
```

---

## Quick Start Workflow

1. **Create report file** immediately; populate progressively.
2. **Convert IDs**: Use `MyGene_batch_query` (fields: `symbol,entrezgene,ensembl.gene`) then `STRING_map_identifiers` to get canonical symbols. Auto-detect: `ENSG*` = Ensembl, numeric = Entrez, else = Symbol.
3. **Primary enrichment**: `gseapy.enrichr()` for ORA (gene list), `gseapy.prerank()` for GSEA (ranked list with scores). Use `background=background_genes` — do not leave as genome-wide default if your experiment has a specific expressed gene set.
4. **Cross-validate**: Run `PANTHER_enrichment` (param: comma-sep `gene_list`, `annotation_dataset='GO:0008150'`) and `ReactomeAnalysis_pathway_enrichment` (param: space-sep `identifiers`). `STRING_functional_enrichment` returns all categories — filter by `category` field.
5. **Report**: Include raw p-value, adjusted p-value, overlap ratio, and `inputGenes` for each significant term. Note consensus terms (significant in 2+ sources).

**See**: references/ for complete code examples (ora_workflow.md, gsea_workflow.md, cross_validation.md)

---

## Evidence Grading

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Curated/experimental enrichment | PANTHER, Reactome Analysis Service |
| **T2** | [T2] | Computational enrichment, well-validated | gseapy ORA/GSEA, STRING functional enrichment |
| **T3** | [T3] | Text-mining/predicted enrichment | Enrichr non-curated libraries |
| **T4** | [T4] | Single-source annotation | Individual gene GO annotations from QuickGO |

---

## Supported Organisms

Core organisms: human (9606), mouse (10090), rat (10116), fly (7227), worm (6239), yeast (4932). gseapy has full human/mouse support; other organisms are limited — use PANTHER or STRING for non-human enrichment.

**See**: references/organism_support.md for organism-specific libraries

---

## Common Patterns

### Pattern 1: Standard DEG Enrichment (ORA)
```
Input: List of differentially expressed gene symbols
Flow: ID validation → gseapy ORA (GO + KEGG + Reactome) →
      PANTHER + STRING cross-validation → Report top enriched terms
Use: When you have unranked gene list from DESeq2/edgeR
```

### Pattern 2: Ranked Gene List (GSEA)
```
Input: Gene-to-log2FC mapping from differential expression
Flow: Convert to ranked Series → gseapy GSEA (GO + KEGG + MSigDB) →
      Filter by FDR < 0.25 → Report NES and lead genes
Use: When you have fold-changes or other ranking metric
```

### Pattern 3: BixBench Enrichment Question
```
Input: Specific question about enrichment (e.g., "What is the adjusted p-val for neutrophil activation?")
Flow: Parse question for gene list and library → Run gseapy with exact library →
      Find specific term → Report exact p-value and adjusted p-value
Use: When answering targeted questions about specific terms
```

### Pattern 4: Multi-Organism Enrichment
```
Input: Gene list from mouse experiment
Flow: Use organism='mouse' for gseapy → organism=10090 for PANTHER/STRING →
      projection=True for Reactome human pathway mapping
Use: When working with non-human organisms
```

**See**: references/common_patterns.md for more examples

---

## Troubleshooting

**"No significant enrichment found"**:
- Verify gene symbols are valid (STRING_map_identifiers)
- Try different library versions (2021 vs 2023 vs 2025)
- Try relaxing significance cutoff or use GSEA instead

**"Gene not found" errors**:
- Check ID type and convert using MyGene_batch_query
- Remove version suffixes from Ensembl IDs (ENSG00000141510.16 → ENSG00000141510)

**"STRING returns all categories"**:
- This is expected; filter by `d['category'] == 'Process'` after receiving results

**See**: references/troubleshooting.md for complete guide

---

## Tool Reference

### Primary Enrichment Tools
| Tool | Input | Output | Use For |
|------|-------|--------|---------|
| `gseapy.enrichr()` | gene_list, gene_sets, organism | `.results` DataFrame | ORA with 225+ libraries |
| `gseapy.prerank()` | rnk (ranked Series), gene_sets | `.res2d` DataFrame | GSEA analysis |

### Cross-Validation Tools
| Tool | Key Parameters | Evidence Grade |
|------|---------------|----------------|
| `PANTHER_enrichment` | gene_list (comma-sep), organism, annotation_dataset | [T1] |
| `STRING_functional_enrichment` | protein_ids, species | [T2] |
| `ReactomeAnalysis_pathway_enrichment` | identifiers (space-sep), page_size | [T1] |

### ID Conversion Tools
| Tool | Input | Output |
|------|-------|--------|
| `MyGene_batch_query` | gene_ids, fields | Symbol, Entrez, Ensembl mappings |
| `STRING_map_identifiers` | protein_ids, species | Preferred names, STRING IDs |

**See**: references/tool_parameters.md for complete parameter documentation

---

## Detailed Documentation

All detailed examples, code blocks, and advanced topics have been moved to `references/`:

- **references/ora_workflow.md** - Complete ORA examples with all databases
- **references/gsea_workflow.md** - Complete GSEA workflow with ranked lists
- **references/enrichr_guide.md** - All 225+ Enrichr libraries and usage
- **references/cross_validation.md** - Multi-source validation strategies
- **references/id_conversion.md** - Gene ID disambiguation and conversion
- **references/tool_parameters.md** - Complete tool parameter reference
- **references/organism_support.md** - Organism-specific configurations
- **references/common_patterns.md** - Detailed use case examples
- **references/troubleshooting.md** - Complete troubleshooting guide
- **references/multiple_testing.md** - Correction methods (BH, Bonferroni, BY)
- **references/report_template.md** - Standard report format

Helper scripts:
- **scripts/format_enrichment_output.py** - Format results for reports
- **scripts/compare_enrichment_sources.py** - Cross-validation analysis
- **scripts/filter_by_gene_set_size.py** - Filter terms by size

---

## Resources

For network-level analysis: [tooluniverse-network-pharmacology](../tooluniverse-network-pharmacology/SKILL.md)
For disease characterization: [tooluniverse-multiomic-disease-characterization](../tooluniverse-multiomic-disease-characterization/SKILL.md)
For spatial omics: [tooluniverse-spatial-omics-analysis](../tooluniverse-spatial-omics-analysis/SKILL.md)
For protein interactions: [tooluniverse-protein-interactions](../tooluniverse-protein-interactions/SKILL.md)

gseapy documentation: https://gseapy.readthedocs.io/
PANTHER API: http://pantherdb.org/services/oai/pantherdb/
STRING API: https://string-db.org/cgi/help?sessionId=&subpage=api
Reactome Analysis: https://reactome.org/AnalysisService/
