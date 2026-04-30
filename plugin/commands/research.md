---
name: research
description: Run a full research workflow on a scientific question — categorize, plan, gather data with cross-validation, synthesize with evidence grading, and report. Use for any question that needs more than a single fact lookup. Includes uncertainty handling and stop conditions to prevent over-searching.
argument-hint: "[your research question]"
---

Research this question with a real workflow, not a single tool call: $ARGUMENTS

A direct tool call answers a factoid; research needs categorization, planning,
multi-source evidence, and synthesis. Run the steps below — but stop early
when a step's output makes a later step unnecessary.

## Step 0: Decide whether ToolUniverse tools/skills are even needed

Not every question is a research question. Before any planning, decide:

**USE tools/skills when the question needs:**
- Specific data lookups (variant pathogenicity, drug approvals, GWAS hits,
  mutation frequency, gene-disease association, clinical trials, etc.) —
  training knowledge is stale or missing entity-level facts
- Multi-source cross-validation (compound tools `gather_*`, `annotate_*`
  return concordance across databases — much faster than calling each)
- Local data analysis (RNA-seq, phylogenetics, statistics, imaging) — the
  matching skill encodes dataset-specific conventions (filter rules,
  library choice, aggregation level) that ad-hoc scripts get wrong
- Domain-specific computation (DESeq2, PhyKIT, clusterProfiler, MAGeCK) —
  wrapped tools match published-pipeline conventions, reimplementing gives
  different numbers

**DO NOT use tools when:**
- The question is meta or general knowledge ("what is UniProt?", "should I
  use Skill X for Y?", "how does DESeq2 normalize counts?") — answer from
  knowledge, no tool calls
- The answer is a definition, taxonomy, or workflow choice (no data lookup)
- An API key error already returned once — don't retry, note the limit
- `find_tools` returned no matches across 2-3 keyword variants — stop and
  answer from knowledge with a low-confidence tag
- Local file computation (raw pandas/scipy work) — use pandas/scipy
  directly, MCP overhead is wasted

If Step 0 says "no tools needed", state the answer from knowledge in 1-3
paragraphs and stop. Don't run steps 1-6 just to look thorough.

## Step 1: Categorize and decide depth

Read the question and classify it before doing anything else:

| Category | Example | What this command should do |
|---|---|---|
| **Meta / general knowledge** | "Should I use Skill X?", "What is UniProt?" | Stop at Step 0; answer from knowledge. |
| **Factoid lookup** | "What's the UniProt ID for TP53 in human?" | Skip to step 4 with one tool call. |
| **Profile / overview** | "Tell me about BRCA1" | Steps 2-6, 3-5 sources. |
| **Hypothesis** | "Is X a good drug target for Y?" | Steps 2-6 with explicit cross-validation in step 5. |
| **Multi-step synthesis** | "Compare the safety profile of all GLP-1 agonists" | Steps 2-6 with a structured table in step 6. |
| **Local data analysis** | Question references a folder/file | Skip to "Local data" section below. |

Tell the user what category you picked in one line; this anchors expectations.

## Step 2: Plan the data sources

Decompose the question into 2-5 sub-questions. For each, name the data
source TYPE (gene-disease association, drug-target interaction, clinical
trial, literature, expression atlas, etc.) — not a specific tool yet.

If you don't know which tool maps to a source type, run `/find-tools` for
that sub-question. Otherwise, name the candidate tool inline.

Output the plan as a 3-5 line list before any tool call. This is the
anti-over-searching anchor: you'll only call tools the plan justifies.

## Step 3: Gather data per sub-question

For each sub-question:
- Use the Bash one-liners below if the tool is in the recipe set.
- Otherwise use `/run-tool <name> '<json>'` for input validation, retry, parsing.
- After 2 unsuccessful tool calls for a sub-question, STOP and answer that
  sub-question from your knowledge with a "low-confidence" tag.

Track what each call returned in a working scratchpad — you'll need it in
step 5 for cross-validation.

## Step 4: Cross-validate critical claims

If a fact answers the user's question directly (e.g., "BRCA1 is associated
with breast cancer"), it deserves at least 2 sources before you assert it.
Pick a second tool from a different database for that one critical fact.

For multi-fact questions, pick the 1-3 highest-impact claims and cross-check
those — not every fact. Cross-validation is expensive; use it where it
matters.

If two sources disagree, report both with their database names and the
direction of disagreement. Don't pick one silently.

## Step 5: Synthesize with evidence grading

Tag each claim in your final answer with an evidence tier:

- **T1** — primary database record (ClinVar pathogenic, FDA approval)
- **T2** — cross-validated across 2+ T1 sources
- **T3** — published literature finding (PubMed)
- **T4** — inferred from related data (e.g., pathway membership implies function)
- **K** — from your training knowledge, no database confirmation

Mark confidence inline so the user can audit. Don't bury T4/K facts mixed
with T1/T2.

## Step 6: Report — structured, with citations

Format depends on category from step 1:

- **Factoid**: one line answer + tool name + value.
- **Profile**: 5-8 bullet sections with evidence tier per fact.
- **Hypothesis**: explicit "yes/no/inconclusive" + 3-5 supporting/conflicting
  evidence bullets.
- **Multi-step**: a structured table (one row per item, columns for the
  facts compared).

Always include:
- Database names for each fact (so the user can verify).
- Date stamps if returned by the API.
- A "limitations" section if any sub-question hit step 3's stop condition.

## Stop conditions (preventing over-search)

- After 2 tool failures on the same sub-question → answer from knowledge.
- After step 3 if you have evidence for every sub-question → skip to step 5.
- Total tool calls > 15 → wrap up with what you have.
- API key error → never retry, note the missing key, suggest fallback or
  proceed without that source.

---

## Frequently-used tool one-liners

These are the tools most research questions reach for. Use them inline in
step 3 to save discovery time.

```bash
# Gene
tu run ensembl_lookup_gene '{"gene_id":"TP53","species":"homo_sapiens"}'
tu run UniProt_search '{"query":"BRCA1","organism":"human","limit":5}'

# Variant
tu run ClinVar_search_variants '{"query":"BRCA1","limit":10}'
tu run civic_get_variants_by_gene '{"gene_symbol":"BRAF"}'
tu run gnomad_get_gene '{"gene_symbol":"BRCA1"}'

# Drug
tu run DGIdb_get_drug_gene_interactions '{"genes":["TP53","PIK3CA"]}'
tu run OpenFDA_search_drug_approvals '{"operation":"search_approvals","drug_name":"alpelisib","limit":3}'
tu run ChEMBL_search_molecules '{"query":"metformin","limit":5}'

# Cancer
tu run IntOGen_get_drivers '{"cancer_type":"BRCA"}'
tu run GDC_get_mutation_frequency '{"gene_symbol":"TP53"}'
tu run OncoKB_annotate_variant '{"operation":"annotate_variant","gene":"PIK3CA","variant":"H1047R","tumor_type":"Breast Cancer"}'

# Literature
tu run PubMed_search_articles '{"query":"BRCA1 resistance therapy","max_results":10}'

# Pathway
tu run STRING_get_interaction_partners '{"identifiers":"TP53","species":9606,"limit":10}'
tu run ReactomeContent_search '{"query":"PI3K AKT"}'

# Compound (multi-source, returns concordance — prefer when 3+ sub-questions overlap)
tu run gather_gene_disease_associations '{"disease":"breast cancer"}'
tu run annotate_variant_multi_source '{"variant":"BRAF V600E","gene":"BRAF"}'
tu run gather_disease_profile '{"disease":"breast cancer"}'
```

Tool not listed → `/find-tools <topic>` to discover.
For 5+ tool calls in a tight loop → use the Python SDK (`from tooluniverse import ToolUniverse`).

---

## Local data analysis — invoke a Skill, don't write pandas

When the question references a local folder/file (CSV, TSV, Excel, VCF,
h5ad, FASTQ, treefile, etc.), do NOT write your own analysis script.
Invoke the matching skill via the Skill tool first — skills encode
dataset-specific conventions (encoding, aggregation level, library choice,
significance thresholds, set-operation semantics) that ad-hoc scripts get
wrong.

Routing table:

| If the question involves… | Skill |
|---|---|
| RNA-seq count matrix, DESeq2, DEG lists, dispersion, design formulas | `tooluniverse-rnaseq-deseq2` |
| GO / KEGG / Reactome enrichment, clusterProfiler::simplify, gseapy | `tooluniverse-gene-enrichment` |
| Regression, ANOVA, chi-square, ordinal/logistic, Cox, spline, clinical-trial AE/SDTM | `tooluniverse-statistical-modeling` |
| Microscopy / image segmentation / colony / fluorescence / dose-response / .tif | `tooluniverse-image-analysis` |
| DNA methylation, CpG, m6A, MeRIP-seq, bisulfite, ChIP-seq, chromatin | `tooluniverse-epigenomics` |
| FASTQ, Trimmomatic, BWA, samtools, alignment, coverage depth | `tooluniverse-sequence-analysis` |
| VCF parsing, VAF, SNP, variant classification, mutation counts | `tooluniverse-variant-analysis` |
| Phylogenetic trees, treeness, PhyKIT, parsimony, sequence alignment | `tooluniverse-phylogenetics` |
| scRNA-seq, h5ad, scanpy, UMAP, clustering, cell-type annotation | `tooluniverse-single-cell` |
| CRISPR screen, MAGeCK, sgRNA counts, screen QC | `tooluniverse-crispr-screen-analysis` |
| Mass spec, TMT, iTRAQ, label-free proteomics | `tooluniverse-proteomics-analysis` |

**Critical pre-step (RULE ZERO)**: before writing your own analysis, check if
the data folder contains a `*_executed.ipynb` notebook or canonical analysis
script (`analysis.R`, `run_*.py`). If one exists, read its outputs first via
`tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'`
or by executing the script — it IS the published analysis. Reimplementing
gives different numbers because of subtle filter, library-version, and
sample-exclusion choices you don't see by skimming.
