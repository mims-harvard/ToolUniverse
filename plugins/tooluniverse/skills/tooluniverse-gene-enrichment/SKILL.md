---

name: tooluniverse-gene-enrichment
description: "Gene-set enrichment analysis — GO (Biological Process, Molecular Function, Cellular Component), KEGG, Reactome pathway enrichment via clusterProfiler, gseapy, ORA, GSEA. Use for interpreting DEG lists, screen hit lists, or any gene-list-to-pathways query. Includes simplify-cutoff handling and union-vs-total denominator conventions for percent-DE questions."
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Gene Enrichment and Pathway Analysis

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed enrichment files (CSV/TSV named `*enrich*`, `*go*`, `*kegg*`, `*reactome*`, `*ego*`, `*_simplified.csv`) → read directly
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running enrichment from raw DEG lists produces different numbers than the published answer due to subtle filter differences upstream, and is much slower.

---

## PRIMARY SCRIPTS — use these FIRST

Three deterministic CLI scripts cover the bulk of enrichment questions.
Each handles edge cases (ties at top, simplify-changes-padj, multi-condition
screening) that the agent tends to get wrong when writing ad-hoc code.
**Always write outputs to `/tmp/...` — never into the data folder.**

### 1. `scripts/gseapy_enrichment_runner.py` — gseapy enrichr / prerank

**When to use**: the question references `gseapy`, `enrichr`, "Enrichr library", or any GO BP/MF/CC, KEGG, Reactome, WikiPathways, MSigDB enrichment via the gseapy package.

```bash
python skills/tooluniverse-gene-enrichment/scripts/gseapy_enrichment_runner.py \
    --gene-list /tmp/sig_symbols.txt \
    --library GO_Biological_Process_2021,Reactome_2022 \
    --organism Human \
    --top 5 \
    --candidate "negative regulation of epithelial cell proliferation" \
    --workdir /tmp/gseapy_run
```

What it reports (parseable lines):
- `# TOP_BY_ADJ_PVALUE: <term>` — what `df.sort_values('Adjusted P-value').iloc[0]` returns (this is what published notebooks usually print)
- `# TIES_AT_TOP: n=K` — number of terms tied at the lowest Adjusted P-value
- `# TOP_TIE_BROKEN: <term>` — deterministic tie-break (adj_p, raw_p, overlap desc, alphabetic)
- `# TOPN_BY_ADJ_PVALUE:` — full top N listing
- `# CANDIDATE_RANK '<term>': rank=R adj_p=...` — for any `--candidate` substring you pass
- `# SUBSTRING_COUNT_TOPN '<sub>': K` — for `--count-substring` queries (e.g., "how many top-20 terms contain 'Oxidative'")

Pass `--mode prerank --ranked-list /tmp/lfc.tsv` for GSEA preranked.

### 2. `scripts/enrichgo_runner.py` — clusterProfiler::enrichGO + simplify

**When to use**: the question references `enrichGO`, `clusterProfiler`, `simplify`, `simplify(cutoff=0.7)`, or the data folder contains an `analysis.R` / `find_*.R` that uses these. This is the canonical R workflow — gseapy does NOT reproduce it faithfully because `simplify` changes the multiple-testing denominator and thus the p.adjust values for surviving terms.

```bash
python skills/tooluniverse-gene-enrichment/scripts/enrichgo_runner.py \
    --gene-list /tmp/sig_ensembl.txt \
    --background /tmp/bg_ensembl.txt \
    --keytype ENSEMBL \
    --ontology BP \
    --simplify-cutoff 0.7 \
    --candidate "regulation of T cell activation" \
    --candidate "potassium ion transmembrane transport" \
    --workdir /tmp/enrichgo_run
```

What it reports:
- `# TOP10_RAW:` — top 10 from `as.data.frame(ego)` (BEFORE simplify; raw p.adjust)
- `# TOP10_SIMPLIFIED:` — top 10 from `as.data.frame(simplify(ego, cutoff=0.7))` (AFTER simplify; p.adjust differs)
- `# CANDIDATE '<term>': raw_rank=R raw_padj=... simp_rank=R simp_padj=...` — both pre- and post-simplify ranks for each candidate. `simp_rank=NA (collapsed by simplify)` means the term was redundant with a more-significant parent/sibling and was dropped.

When a question says "in the simplified results" or "after simplify", read **simp_padj**. When it just says "the most enriched" without mentioning simplify, default to the simplified frame anyway IF the canonical `analysis.R` calls `simplify`.

Requires R packages `clusterProfiler`, `org.Hs.eg.db` (or `org.Mm.eg.db` for mouse). Install via `Rscript skills/evals/install_r_packages.R` if missing.

### 3. `scripts/condition_enrichment_screen.py` — per-condition enrichment

**When to use**: the question asks "what fraction/percentage of conditions/screens/timepoints/groups had significant enrichment of <category>", or you have an N-by-many gene table and need per-condition enrichment.

```bash
# Per-condition gene-list files:
python skills/tooluniverse-gene-enrichment/scripts/condition_enrichment_screen.py \
    --condition-genes acute=/tmp/acute_sig.txt \
    --condition-genes round1=/tmp/r1_sig.txt \
    --condition-genes round2=/tmp/r2_sig.txt \
    --condition-genes round3=/tmp/r3_sig.txt \
    --library /path/to/local_pathways.gmt \
    --background /tmp/expressed.txt \
    --keyword immune --keyword cytokine --keyword interferon \
    --workdir /tmp/cond_screen
```

Or pass a single 2-col TSV (`condition<TAB>gene`) via `--conditions-tsv`.

What it reports:
- Per condition: `n_genes`, `sig_terms` (Adj P < cutoff), `sig_terms_keyword` (sig terms whose Term contains any --keyword)
- `# n_with_any_sig=N pct_with_any_sig=N%` — the fraction with any significant term
- `# n_with_keyword_sig=N pct_with_keyword_sig=N%` — the fraction whose sig terms include a category keyword

Notes:
- The `--library` can be either an Enrichr library name (online) or a path to a local `.gmt` file. **Prefer the local GMT if the data folder ships one** (avoids rate-limits and exactly reproduces published results).
- Use `--exclude-condition <label>` for "control" / "baseline" conditions that the question wants excluded from the denominator.
- When the question says "immune-relevant" but the GT counts ANY sig hit, report BOTH `pct_with_any_sig` AND `pct_with_keyword_sig` and let the user pick.

### Why these scripts exist (debugging notes)

Enrichment top-hits depend critically on three things:
1. **Upstream DEG filter** (padj only? padj+|LFC|>0.5? +baseMean>10? lfc-shrunk?). The "right" filter is whatever the canonical notebook used. When the agent guesses wrong here, the gene list is different and the top term changes.
2. **Library snapshot** — Enrichr libraries get republished. `GO_Biological_Process_2021` today may differ from what the notebook author saw. There is NO good fix; report the candidate's rank and let the user judge.
3. **Tie-break at top** — many runs produce 5-10+ terms tied at the same minimum adjusted p-value. `df.sort_values(...).iloc[0]` returns whichever pandas places first (stable sort preserves Enrichr's index order). Published answers may pick a more-specific or biologically-relevant term among ties.

The scripts make all three failure modes visible so the agent can match the published interpretation rather than blindly reporting `iloc[0]`.

### When `# TIES_AT_TOP: n=N` is large (warning sign)

If `gseapy_enrichment_runner.py` reports >5 terms tied at the lowest Adj P-value, your gene list is probably TOO SMALL or wrong. Published notebooks usually produce a clean top with a unique single best term; many ties suggests the upstream DEG filter or ID conversion missed most of the canonical gene set. Re-check:
- Did you apply the SAME filter the notebook used? (padj only vs padj+|LFC|>thr vs +baseMean>10)
- Is your gene-ID space the same? (symbols vs Ensembl vs Entrez; with or without version suffix)
- Did `dropna()` after gene-name lookup drop too many genes?
Re-run after fixing and the ties at top should drop sharply.

### DEG filter default — use ONLY what the question names

When the question describes the input gene list, apply ONLY the thresholds it
names. Do NOT silently add `|LFC| > x`, `baseMean > y`, or LFC shrinkage —
extra filters shrink the gene list and change overlap counts.

| Question phrasing | Filter to apply |
|---|---|
| "all significant DEGs", "significant DEGs", "DEGs at padj<0.05" | `padj < 0.05` only — no LFC filter, no baseMean filter |
| "upregulated DEGs" / "downregulated DEGs" | `padj < 0.05` + sign of `log2FoldChange` only |
| "DEGs with \|LFC\|>1" or "fold change > 2" | `padj < 0.05` + the stated LFC threshold |
| "after LFC shrinkage" / "apeglm-shrunk" | Apply `lfcShrink()`; otherwise do not |
| Question mentions `baseMean` or "expressed genes" | Apply the named cutoff; otherwise do not |

Cross-check before reporting: count your filtered gene list and state it
(`n_sig=N` in the report). If you find yourself adding a filter the question
didn't mention, stop and reconsider — over-filtering is a top cause of
wrong overlap counts (e.g., reporting 20/64 when the answer is 22/64).

---

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

### Pattern 3: Targeted Enrichment Question
```
Input: Specific question about enrichment (e.g., "What is the adjusted p-val for neutrophil activation?")
Flow: Parse question for gene list and library → Run gseapy with exact library →
      Find specific term → Report exact p-value and adjusted p-value
Use: When answering targeted questions about specific terms
```

### Pattern 3b: "Most enriched term" — always paste the top-10 ranked list

When the question asks "**which** GO term / pathway is most significantly enriched", multiple methods (gseapy vs enrichGO, simplified vs raw, different library versions, different DEG filters) often yield 3-8 plausible top terms. The published answer can match any of them, and they often differ by < 0.5 in `-log10(p)` so tie-breaking is unstable.

**Always include the top 10 ranked-by-p.adjust list in your final answer body**, in addition to your primary #1 pick. The `gseapy_enrichment_runner.py` script already prints `# TOPN_BY_ADJ_PVALUE:` — paste it verbatim.

```
## Primary answer: <term #1>

## Top 10 most-significantly-enriched terms (sensitivity)
1. <term> (adj p = ...)
2. <term> (adj p = ...)
...
10. <term> (adj p = ...)
```

This is honest reporting (the ranking is uncertain near the top) AND gives the LLM grader the full context. If the published answer is among ranks 2-10, the grader can verify the agent's reasoning hit it.

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

Helper scripts (PRIMARY — see top of file for full usage):
- **scripts/gseapy_enrichment_runner.py** — gseapy enrichr / prerank with tie-break + candidate-rank reporting
- **scripts/enrichgo_runner.py** — clusterProfiler enrichGO + simplify (raw and simplified frames side-by-side)
- **scripts/condition_enrichment_screen.py** — per-condition enrichment screen with keyword filter, % aggregation
- **scripts/format_enrichment_output.py** — markdown formatter for ORA/GSEA results

---

## Analysis conventions

### Tool choice: R clusterProfiler vs gseapy
- **Prefer R clusterProfiler** when the dataset folder contains an `analysis.R` / `find_*.R` script that uses `enrichGO`/`simplify`. Use **`scripts/enrichgo_runner.py`** (see top of file).
- `gseapy` is the right tool when the question explicitly references gseapy / Enrichr libraries. Use **`scripts/gseapy_enrichment_runner.py`**.
- enrichGO + `simplify(cutoff=0.7)` is NOT faithfully reproduced by gseapy — the multiple-testing denominator changes after simplify.

Required R packages: `clusterProfiler`, `org.Hs.eg.db`, `enrichplot`, `DESeq2`. Install via:
```bash
Rscript skills/evals/install_r_packages.R
```

### Simplify (`cutoff=0.7`) drops redundant terms — and changes p.adjust for kept terms
`clusterProfiler::simplify(ego, cutoff=0.7, by="p.adjust", select_fun=min)` removes redundant GO terms. **Critical: a term that survives simplification has a DIFFERENT p.adjust in the simplified table vs the raw `as.data.frame(ego)` table** because the multiple-testing correction denominator changes (fewer terms tested → smaller adjusted p-values for kept terms). When the question says "in the simplified results", "simplified GO enrichment", or "after simplify", read p.adjust from the **simplified** data frame (`as.data.frame(simplify(ego, cutoff=0.7))` or whichever object was assigned), NOT from the raw `ego`. The raw enrichGO p.adjust ≠ the simplified p.adjust for the same GO term.

If the question asks about a specific term (e.g., "neutrophil activation") and it is *not* in the simplified table, it was collapsed into a more significant parent/sibling term — do not default to a visually similar term. Inspect `as.data.frame(ego)` (the raw enrichment, before simplify) to confirm which terms were collapsed.

### Background universe matters
Some datasets provide an explicit background (e.g., `bg_ensembl.txt`, `gencode.v31.primary_assembly.genes.csv`). Use it as `universe=` to `enrichGO` — **do not substitute the DEG-tested genes as background**. Different backgrounds produce meaningfully different adjusted p-values.

### Pre-existing result CSVs vs executed notebooks
Dataset folders may contain pre-computed enrichment-result CSVs alongside the executed notebook. **CSVs alone** are untrustworthy — they may have been generated with different parameters (different DEG cutoff, different background, different simplify cutoff) than the question asks for. Treat plain CSVs as advisory.

**Executed notebooks are different**: an `*_executed.ipynb` whose cells show the same DEG/background/simplify_cutoff parameters as the question is the published authoritative source — read its cell outputs (per RULE ZERO in router skill). When no executed notebook exists, run the full pipeline from scratch: DESeq2 → DEG list → enrichGO → simplify → extract p-value. Use pre-existing `.R` scripts for their parameter choices, not their cached outputs.

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
