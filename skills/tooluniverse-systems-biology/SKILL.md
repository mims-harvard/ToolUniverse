---
name: tooluniverse-systems-biology
description: Comprehensive systems biology and pathway analysis using multiple pathway databases (Reactome, KEGG, WikiPathways, Pathway Commons, BioModels). Performs pathway enrichment, protein-pathway mapping, keyword searches, and systems-level analysis. Use when analyzing gene sets, exploring biological pathways, or investigating systems-level biology.
---

# Systems Biology & Pathway Analysis

Comprehensive pathway and systems biology analysis integrating multiple curated databases to provide multi-dimensional view of biological systems, pathway enrichment, and protein-pathway relationships.

## When to Use This Skill

**Triggers**:
- "Analyze pathways for this gene list"
- "What pathways is [protein] involved in?"
- "Find pathways related to [keyword/process]"
- "Perform pathway enrichment analysis"
- "Map proteins to biological pathways"
- "Find computational models for [process]"
- "Systems biology analysis of [genes/proteins]"

**Use Cases**:
1. **Gene Set Analysis**: Identify enriched pathways from RNA-seq, proteomics, or screen results
2. **Protein Function**: Discover pathways and processes a protein participates in
3. **Pathway Discovery**: Find pathways related to diseases, processes, or phenotypes
4. **Systems Integration**: Connect genes → pathways → processes → diseases
5. **Model Discovery**: Find computational systems biology models (SBML)
6. **Cross-Database Validation**: Compare pathway annotations across multiple sources

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Domain Reasoning: Enrichment vs Causation

Pathway analysis answers: which biological processes are enriched in my gene list? But enrichment is not causation. A pathway being enriched means your gene list overlaps it more than expected by chance. Ask: is the enrichment driven by a few hub genes, or by many genes distributed across the pathway? A pathway with 3 input genes but 200 annotated members is less informative than one where 15 of 40 members are in your list.

LOOK UP DON'T GUESS: pathway membership, gene-to-pathway assignments, and enrichment statistics. Do not assume a gene is in a pathway — use Reactome, KEGG, or Enrichr to verify. Pathway databases disagree on membership; cross-validate key findings across at least two sources.

## Core Databases Integrated

| Database | Strengths |
|----------|-----------|
| **Reactome** | Detailed mechanistic pathways with reactions; human-curated |
| **KEGG** | Metabolic maps, disease pathways, drug targets |
| **WikiPathways** | Emerging and community-curated pathways |
| **Pathway Commons** | Meta-database aggregating multiple sources |
| **BioModels** | Mathematical/computational SBML models |
| **Enrichr** | Statistical over-representation analysis |

## Workflow Overview

```
Input → Phase 1: Enrichment → Phase 2: Protein Mapping → Phase 3: Keyword Search → Phase 4: Top Pathways → Report
```

---

## Phase 1: Pathway Enrichment Analysis

**When**: Gene list provided (from experiments, screens, differentially expressed genes)

**Objective**: Identify biological pathways statistically over-represented in gene list

### Tools & Workflow

| Tool | Input | Use |
|------|-------|-----|
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (newline-separated symbols), `page_size` | FDR-corrected Reactome enrichment (recommended) |
| `enrichr_gene_enrichment_analysis` | `gene_list` (array), `libs` (array) | Over-representation with KEGG/Reactome/WikiPathways |
| `STRING_functional_enrichment` | `protein_ids` (array), `species`, `category` | Functional enrichment from PPI networks |
| `intact_get_interactions` | `identifier` (UniProt accession) | Binary protein interactions with evidence |

1. Submit gene list to Enrichr/Reactome. 2. Sort by adjusted p-value < 0.05. 3. Report top 10-20 pathways with IDs, p-values, and overlapping genes. If no enrichment, note explicitly.

---

## Phase 2: Protein-Pathway Mapping

**When**: Protein UniProt ID provided

**Objective**: Map protein to all known pathways it participates in

### Tools Used

**Reactome_map_uniprot_to_pathways**:
- **Input**:
  - `uniprot_id`: UniProt accession (e.g., "P53350")
- **Output**: Array of Reactome pathways containing this protein

**Reactome_get_pathway_reactions**:
- **Input**:
  - `stId`: Reactome pathway stable ID (e.g., "R-HSA-73817")
- **Output**: Array of reactions and subpathways
- **Use**: Get mechanistic details of pathways

### Workflow

1. Map UniProt ID to Reactome pathways
2. Get all pathways this protein appears in
3. For top pathway (or user-specified):
   - Retrieve detailed reactions and subpathways
   - Extract event names, types (Reaction vs Pathway)
   - Note disease associations if present

### Decision Logic

- **Multiple pathways**: Report all pathways, prioritize by hierarchical level
- **Top pathway details**: Get detailed reactions for 1-3 most relevant
- **Versioned IDs**: Reactome uses unversioned IDs - strip version if present
- **Empty results**: Check if protein ID valid; suggest alternative databases if Reactome empty

---

## Phase 3: Keyword-Based Pathway Search

**When**: User provides keyword or biological process name

**Objective**: Search multiple pathway databases to find relevant pathways

### Tools

| Tool | Key Params | Coverage |
|------|-----------|----------|
| `kegg_search_pathway` | `keyword` | Reference, metabolic, disease pathways |
| `kegg_get_pathway_info` | `pathway_id` (e.g., "hsa04930") | Detailed genes/compounds for a pathway |
| `WikiPathways_search` | `query`, `organism` | Community-curated, emerging pathways |
| `PathwayCommons_search` | `action`="search_pathways", `keyword` | Meta-database aggregating multiple sources |
| `biomodels_search` | `query`, `limit` | SBML computational models |

Search all databases in parallel. Group results by pathway concept. BioModels often returns empty — this is normal.

---

## Phase 4: Top-Level Pathway Catalog

**When**: Always included to provide context

**Objective**: Show major biological systems/pathways for organism

### Tools Used

**Reactome_list_top_pathways**:
- **Input**: `species` (e.g., "Homo sapiens")
- **Output**: Array of top-level pathway categories
- **Use**: Provides hierarchical pathway organization

### Workflow

1. Retrieve top-level pathways for specified organism
2. Display pathway categories (metabolism, signaling, disease, etc.)
3. Serve as reference for pathway hierarchy

### Decision Logic

- **Always show**: Provides context even if other phases empty
- **Organism-specific**: Filter by species of interest
- **Hierarchical view**: These are parent pathways with many subpathways

---

## Output Structure

Create a markdown report progressively: header → Phase 1 enrichment results → Phase 2 protein mapping → Phase 3 keyword search → Phase 4 top pathway catalog. Note empty results explicitly; never silently omit them. Include pathway IDs for follow-up.

## Tool Parameter Reference

**Critical Parameter Notes** (from testing):

| Tool | Correct Parameter | Common Mistake |
|------|-------------------|----------------|
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | `id` |
| `PathwayCommons_search` | `action` + `keyword` (both required) | omitting `action` |
| `enrichr_gene_enrichment_analysis` | `gene_list` (array) | string |

**Response Format Notes**:
- **Reactome**: Returns list directly (not wrapped in `{status, data}`)
- **Pathway Commons**: Returns dict with `total_hits` and `pathways`
- **Others**: Standard `{status: "success", data: [...]}` format

---

## Domain Reasoning: Enzyme Kinetics & Metabolic Analysis

LOOK UP DON'T GUESS: Km values, kcat values, cofactor requirements, and optimal pH/temperature for specific enzymes. Use `BindingDB_search_by_target`, `ChEMBL_get_molecule`, `BRENDA_search` (if available), or `EuropePMC_search_articles` to retrieve published kinetic parameters. Do not estimate Km from first principles.

### Michaelis-Menten Kinetics

The foundational model: v = Vmax * [S] / (Km + [S])
- **Km** = substrate concentration at half-maximal velocity. NOT binding affinity (Km = (koff + kcat) / kon).
- **Vmax** = maximum velocity = kcat * [E_total]. Proportional to enzyme concentration.
- **kcat** = turnover number = molecules of substrate converted per enzyme per second.
- **Catalytic efficiency** = kcat / Km. The "best" enzymes approach the diffusion limit (~10^8 M^-1 s^-1).

To determine Km and Vmax from data: use Lineweaver-Burk (1/v vs 1/[S]), Eadie-Hofstee (v vs v/[S]), or nonlinear regression (preferred — avoids distortion from reciprocal transforms). See `enzyme_kinetics.py` in `skills/tooluniverse-computational-biophysics/scripts/`.

### Allosteric Regulation & Cooperative Binding

Not all enzymes follow Michaelis-Menten. Sigmoidal v-vs-[S] curves indicate cooperativity.
- **Hill equation**: v = Vmax * [S]^nH / (K0.5^nH + [S]^nH)
- **Hill coefficient (nH)**: nH = 1 (no cooperativity), nH > 1 (positive, e.g., hemoglobin O2 binding nH ~ 2.8), nH < 1 (negative cooperativity).
- **K0.5**: substrate concentration at half-maximal velocity (analogous to Km but not identical for cooperative systems).
- Allosteric activators shift the curve LEFT (lower K0.5). Allosteric inhibitors shift it RIGHT (higher K0.5) or reduce Vmax.

### Enzyme Inhibition Types

| Type | Effect on Km | Effect on Vmax | Lineweaver-Burk pattern |
|------|-------------|----------------|------------------------|
| Competitive | Increases (Km_app = Km * (1 + [I]/Ki)) | Unchanged | Lines intersect on y-axis |
| Uncompetitive | Decreases | Decreases | Parallel lines |
| Noncompetitive (pure) | Unchanged | Decreases (Vmax_app = Vmax / (1 + [I]/Ki)) | Lines intersect on x-axis |
| Mixed | Changes | Decreases | Lines intersect in quadrant II or III |

To determine Ki: measure v at multiple [I] and [S], fit to the appropriate model. The `enzyme_kinetics.py` script handles competitive, uncompetitive, and noncompetitive inhibition calculations.

### Troubleshooting "No Activity" Results

When a purified enzyme shows no catalytic activity, systematically check:

1. **Oligomeric state**: Many enzymes are obligate dimers/tetramers. Dilute protein may dissociate. Check with SEC, native PAGE, or DLS. Concentrate sample or add stabilizing agents (glycerol, specific ions).
2. **Cofactors**: Metal ions (Zn2+, Mg2+, Mn2+), coenzymes (NAD+, FAD, PLP), or prosthetic groups may be lost during purification. LOOK UP the enzyme's cofactor requirements and supplement the assay buffer.
3. **pH**: Most enzymes have a sharp pH optimum. Even 1 pH unit off can reduce activity 10-fold. Buffer at the literature-reported optimal pH.
4. **Temperature**: Standard assays at 25C or 37C. Thermophilic enzymes need 50-80C. Psychrophilic enzymes denature above 30C.
5. **Reducing environment**: Many enzymes need DTT or beta-mercaptoethanol to maintain active-site cysteines in reduced form.
6. **Substrate**: Wrong isomer (D- vs L-), wrong oxidation state, or degraded substrate. Use fresh substrate and verify by a positive control enzyme.
7. **Inhibitors in buffer**: EDTA chelates essential metals. Phosphate competes at phospho-binding sites. Detergents can denature.
8. **Protein folding**: Inclusion body protein may be misfolded even after refolding. Check by CD spectroscopy or thermal shift assay.

### Metabolic Flux Analysis Reasoning

Metabolic flux analysis (MFA) quantifies the rates of metabolic reactions in vivo, not just enzyme activities in vitro.

Key concepts:
- **Steady-state assumption**: At metabolic steady state, the rate of production of each intermediate equals its rate of consumption. This gives a system of linear equations: S * v = 0, where S is the stoichiometric matrix and v is the flux vector.
- **Flux Balance Analysis (FBA)**: When the system is underdetermined (more reactions than metabolites), FBA uses linear programming to optimize an objective function (e.g., maximize biomass production). Use `biomodels_search` to find published SBML models for the organism.
- **13C-MFA**: Uses isotope labeling to experimentally constrain intracellular fluxes. The labeling pattern of metabolites reveals which pathways carried flux.
- **Control coefficients**: How much does a 1% change in enzyme activity change the pathway flux? Most enzymes have near-zero flux control coefficients — flux is usually controlled by a few rate-limiting steps plus substrate supply.

LOOK UP DON'T GUESS: stoichiometric coefficients, pathway topology, and published flux distributions. Use KEGG (`kegg_get_pathway_info`), Reactome (`Reactome_get_pathway_reactions`), and BioModels (`biomodels_search`) for these data.

---

## Fallback Strategies

### Enrichment Analysis
- **Primary**: Enrichr with KEGG library
- **Fallback**: Try alternative libraries (Reactome, GO Biological Process)
- **If all fail**: Note "enrichment analysis unavailable" and continue

### Protein Mapping
- **Primary**: Reactome protein-pathway mapping
- **Fallback**: Use keyword search with protein name
- **If empty**: Check if protein ID valid; suggest checking gene symbol

### Keyword Search
- **Primary**: Search all databases (KEGG, WikiPathways, Pathway Commons, BioModels)
- **Fallback**: If all empty, broaden keyword (e.g., "diabetes" → "glucose")
- **If still empty**: Note "no pathways found for [keyword]"

---

## Limitations & Known Issues

- **Reactome**: Strong human coverage; limited for non-model organisms
- **KEGG**: Requires keyword match; may miss synonyms
- **WikiPathways**: Variable curation quality; check pathway version dates
- **Pathway Commons**: Aggregation may have duplicates; check source attribution
- **BioModels**: Sparse for many processes; often returns no results
- **Enrichr**: Requires gene symbols (not IDs); case-sensitive

**Best for**: Gene set analysis, protein function investigation, pathway discovery, systems-level biology
