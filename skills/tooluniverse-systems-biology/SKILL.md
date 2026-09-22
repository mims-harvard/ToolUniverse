---
name: tooluniverse-systems-biology
description: Systems biology and pathway analysis integrating Reactome, KEGG, WikiPathways, BioCarta, NCI-Nature Pathway Interaction Database. Multi-database pathway enrichment, protein-pathway relationships, network reasoning. Use for pathway analysis on a gene list, multi-source pathway concordance, and systems-level interpretation across databases.
disable-model-invocation: true
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
| **BiGG Models** | Genome-scale metabolic reconstructions (85+ organisms), FBA-ready COBRA format |
| **Rhea** | Expert-curated biochemical reaction knowledgebase (ChEBI-based, EC-cross-referenced) |

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

LOOK UP DON'T GUESS: Km values, kcat values, cofactor requirements, and optimal pH/temperature for specific enzymes. Use `BindingDB_search_by_target`, `ChEMBL_get_molecule`, `BRENDA_get_enzyme_info` *(requires BRENDA_EMAIL + BRENDA_PASSWORD env vars; free academic registration at brenda-enzymes.org)* (if available), or `EuropePMC_search_articles` to retrieve published kinetic parameters. Do not estimate Km from first principles.

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
- **Flux Balance Analysis (FBA)**: When the system is underdetermined (more reactions than metabolites), FBA uses linear programming to optimize an objective function (e.g., maximize biomass production). Use `biomodels_search` to find a published SBML *paper's* model for the organism, or — for a model that is already curated, versioned, and ready to run FBA on without further cleanup — use BiGG (below).
- **13C-MFA**: Uses isotope labeling to experimentally constrain intracellular fluxes. The labeling pattern of metabolites reveals which pathways carried flux.
- **Control coefficients**: How much does a 1% change in enzyme activity change the pathway flux? Most enzymes have near-zero flux control coefficients — flux is usually controlled by a few rate-limiting steps plus substrate supply.

LOOK UP DON'T GUESS: stoichiometric coefficients, pathway topology, and published flux distributions. Use KEGG (`kegg_get_pathway_info`), Reactome (`Reactome_get_pathway_reactions`), and BioModels (`biomodels_search`) for these data.

### Genome-Scale Metabolic Models & FBA (BiGG)

BiGG Models (bigg.ucsd.edu) is a curated database of 108 genome-scale metabolic
reconstructions (bacteria, archaea, eukaryotes — E. coli, yeast, human Recon3D,
and more), each already in FBA-ready COBRA format: every reaction carries flux
`lower_bound`/`upper_bound` and a `gene_reaction_rule`, unlike a `biomodels_search`
hit (which is a paper's raw SBML file that may need cleanup before it will run).
Use BiGG when the goal is to actually *run* FBA, not just read about a pathway.

**Tools** (each has its own `operation` enum value defaulted in its schema — you don't need to set it manually, just call the tool named for what you want):

| Tool | Key Params | Use |
|------|-----------|-----|
| `BiGG_list_models` | none | Discover available organisms/models (108 total) |
| `BiGG_get_model` | `model_id` | Model metadata: reaction/metabolite/gene counts, publication DOI, genome accession |
| `BiGG_get_model_reactions` | `model_id` | Enumerate every reaction ID + name in a model |
| `BiGG_get_reaction` | `reaction_id`, `model_id` (or `"universal"`) | Full stoichiometry, participating metabolites, gene-reaction rule |
| `BiGG_get_metabolite` | `metabolite_id`, `model_id` (or `"universal"`) | Formula, compartment, cross-refs (KEGG/MetaCyc/HMDB/ChEBI) |
| `BiGG_search` | `query`, `search_type` (`models`/`reactions`/`metabolites`/`genes`) | Free-text discovery across any of the four entity types |
| `BiGG_get_database_version` | none | Data currency check |
| `BiGG_download_model` | `model_id`, `format` (`json`/`sbml`) | The full FBA-ready COBRA model — every reaction with bounds/objective coefficient, every metabolite, every gene |

**Workflow — find a model, inspect it, get it FBA-ready:**

1. `BiGG_list_models` → each entry has `bigg_id`, `organism`, `reaction_count`, `metabolite_count`, `gene_count`. For a quick/small worked example, `e_coli_core` (E. coli core metabolism: 95 reactions, 72 metabolites, 137 genes) is the standard teaching model; for genome-scale work pick a full reconstruction like `iJO1366` (E. coli) or `Recon3D` (human).
2. `BiGG_get_model(model_id="e_coli_core")` → publication DOI, genome accession (`ncbi_accession:NC_000913.3` for E. coli), file sizes, last-updated date — check currency before citing.
3. `BiGG_get_model_reactions(model_id="e_coli_core")` → list of `{bigg_id, name, organism}` per reaction (e.g. `ACKr` = "Acetate kinase"). Use this to find candidate reaction IDs before drilling in.
4. `BiGG_get_reaction(reaction_id="ACKr", model_id="e_coli_core")` → full stoichiometry as a `metabolites` array (each with `bigg_id`, `name`, signed `stoichiometry`), plus `gene_reaction_rule` (empty string/None for some reactions — a real absence, not a fetch failure) and `database_links` (RHEA, etc.).
5. `BiGG_get_metabolite(metabolite_id="g3p_c", model_id="e_coli_core")` → `name`, `formula`, `compartment_bigg_id`/`compartment_name`, and `database_links` for cross-referencing to KEGG/ChEBI. Note some fields (e.g. `formulae`) come back `None` for some entries — report what's actually present rather than assuming every field is populated.
6. `BiGG_search(query="glucose", search_type="metabolites")` → ranked hits across the **universal** namespace by default (`model_bigg_id: "Universal"`) as well as model-specific IDs; use `search_type="models"` to find organisms, `"genes"` to resolve a gene symbol to its BiGG gene ID.
7. `BiGG_download_model(model_id="e_coli_core", format="json")` → the complete COBRA model: top-level `metabolites`/`reactions`/`genes`/`compartments` arrays, each reaction with `lower_bound`, `upper_bound`, `gene_reaction_rule`, and a `metabolites` dict of `{metabolite_id: stoichiometry}` — this is the object to hand to a COBRApy `Model` for FBA, not `BiGG_get_model`'s metadata-only response. `format="sbml"` returns the same model as an SBML XML string instead, for tools that expect that format.

**Gotchas** (from live testing): `model_id` defaults to `"universal"` for `BiGG_get_reaction`/`BiGG_get_metabolite` — pass the specific model ID when you want model-scoped stoichiometry/bounds rather than the universal (model-agnostic) entry. `BiGG_search`'s default `search_type` is `"reactions"` — set it explicitly for metabolite/gene/model searches. `BiGG_get_model` returns only counts and metadata; `BiGG_download_model` is the one that returns an actually runnable model.

### Reaction-Level Biochemistry (Rhea)

Rhea (rhea-db.org, SIB) is an expert-curated knowledgebase of individual
biochemical reactions — each has a ChEBI-based equation, a curation status
(`approved`, `reviewed`, etc.), a mass/charge balance flag, and cross-referenced
EC number(s). Use it when the question is about ONE reaction's participants,
stoichiometry, and enzyme classification, rather than a whole model's fluxes
(BiGG, above) or a pathway diagram (Reactome/KEGG).

**Tools:**

| Tool | Key Params | Use |
|------|-----------|-----|
| `Rhea_search_reactions` | `query`, `limit`, `offset` | Free-text search by compound/keyword. **Use a single keyword, not a phrase** — `query="glucose"` returns real hits, `query="glucose oxidation"` returns zero (verified live) |
| `Rhea_search_by_ec` | `ec_number`, `limit`, `offset` | All reactions catalyzed by a given EC class |
| `Rhea_search_by_chebi` | `chebi_id`, `limit`, `offset` | All reactions where a specific ChEBI compound participates (substrate, product, or either) |
| `Rhea_get_reaction` | `rhea_id` | Full detail: equation, `status_curation`, `balanced`/`transport` flags, reactants/products with ChEBI IDs and stoichiometry |
| `Rhea_get_reaction_participants` | `rhea_id` | Just the reactants/products list (subset of `Rhea_get_reaction`, useful when you don't need curation metadata) |

**Workflow (real values from live testing):** `Rhea_search_reactions(query="glucose")` →
`RHEA:14293` ("D-glucose + NAD(+) = D-glucono-1,5-lactone + NADH + H(+)", EC 1.1.1.47/1.1.1.118/1.1.1.359 among others) →
`Rhea_get_reaction(rhea_id="RHEA:14293")` → `status_curation: "approved"`, `balanced: true`, reactants
`[{chebi_id: "CHEBI:4167", name: "D-glucose", stoichiometry: "1"}, {chebi_id: "CHEBI:57540", name: "NAD+", ...}]`.
Cross-reference a Rhea `chebi_id` against `tooluniverse-chemical-compound-retrieval`'s PubChem/ChEBI tools for
the compound's structure, and a Rhea `ec_numbers` value against BRENDA (see Domain Reasoning above) for kinetic
constants on that same reaction.

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
- **BiGG**: Curated reconstructions only exist for 108 organisms (mostly bacteria/model organisms; not every species of interest has one) — check `BiGG_search(search_type="models")` before assuming coverage; `BiGG_get_reaction`/`BiGG_get_metabolite` default to the `"universal"` (model-agnostic) namespace unless `model_id` is passed explicitly

---

## GO Term Lookup, KEGG BRITE Classification, and Causal-Statement Mining (GOAPI / KEGG BRITE / INDRA)

Four more small, previously-undocumented tool families, live-tested below. Two of them overlap in *purpose* with tools already used elsewhere in ToolUniverse — read the overlap notes before reaching for these as a first choice.

### GOAPI: direct GO term/gene-annotation lookup

`GOAPI_get_term`, `GOAPI_get_gene_functions`, `GOAPI_get_genes_by_function` (`go_api_tools.json`) hit the GO API directly. **Overlap note**: this is a *different* tool family from `GO_get_annotations_for_gene` / `GO_get_term_by_id` / `GO_get_term_details` (`gene_ontology_tools.json`), which several other skills — `tooluniverse-target-research`, `tooluniverse-gene-enrichment`, `tooluniverse-structural-variant-analysis` — already document for the same purpose. Prefer those existing tools if you're already using them elsewhere in a workflow; reach for GOAPI when its CURIE-based gene addressing (below) or its reverse "genes by function" lookup is specifically what you need.

- `GOAPI_get_term(go_id="GO:0006281")` → term label + full definition + PMID xrefs (verified live: "GO:0006281" = "DNA repair", correct definition returned).
- `GOAPI_get_gene_functions(gene_id=..., rows=, aspect=)` → **gotcha, verified live**: `gene_id` must be a CURIE (`"HGNC:11998"`, `"UniProtKB:P04637"`, `"MGI:MGI:98834"`), not a bare gene symbol — `gene_id="TP53"` fails with a 400, `gene_id="UniProtKB:P04637"` succeeds and returns real GO terms with `evidence_type`/`evidence_label`/`provided_by`/`references` per annotation (e.g. p53 → "negative regulation of cell population proliferation", IMP evidence from UniProt, PMID:10962037).
- `GOAPI_get_genes_by_function(go_id=...)` → the reverse direction: real gene list annotated with a GO term, each with `gene_id` (CURIE), `gene_label`, `taxon_id`.

### KEGG BRITE: hierarchical functional classification

`KEGG_list_brite_hierarchies` (no params) and `KEGG_get_brite_hierarchy(hierarchy_id=...)` (`kegg_brite_tools.json`) — genuinely new, no existing coverage. BRITE is KEGG's classification-tree layer (e.g. enzymes grouped by EC hierarchy, drugs by target class), distinct from `kegg_search_pathway`/`kegg_get_pathway_info` already in this skill's Phase 3, which return pathway *maps* rather than classification *trees*.

- `KEGG_list_brite_hierarchies()` → real response: 156 hierarchy files (e.g. `br08901` = "KEGG pathway maps").
- `KEGG_get_brite_hierarchy(hierarchy_id="ko01000")` → real nested `children` tree of enzyme classes (e.g. "1. Oxidoreductases" → "1.1 Acting on the CH-OH group of donors" → ...). Use when you need the classification structure itself (e.g. "what are all the kinase subclasses"), not a single pathway's gene/compound list.

### INDRA: automated literature-mined causal statements

`INDRA_get_statements`, `INDRA_get_evidence_count`, `INDRA_get_statement_by_hash` (`indra_tools.json`) — genuinely new. INDRA text-mines causal relationships (Activation/Inhibition/Phosphorylation/Complex/etc.) directly from PubMed abstracts and assembles them with evidence counts — this is **automated extraction with variable precision**, not manually curated causal edges like SIGNOR's (documented in `tooluniverse-protein-interactions`). Treat an INDRA statement as a literature-mining lead to verify, not a confirmed mechanism, especially when `evidence_shown` is low relative to `total_evidence`.

- `INDRA_get_evidence_count(agent="TP53")` → real count: 25,846 total evidence items across all TP53 statements (verified live; slow-ish, ~3-20s).
- `INDRA_get_statements(agent="EGFR", limit=3)` → **gotcha**: this call can take 30-90+ seconds — give it a generous timeout, don't assume a hang means failure. Real response: statements typed `Phosphorylation`/`Complex`/etc., each with `hash`, `evidence_shown`, and per-evidence `pmid`+source sentence (e.g. a real Phosphorylation statement backed by 2 shown evidence sentences from PMID 31635022 and 37443708, out of 74,891 total evidence for EGFR overall — most evidence is never shown per call, use `INDRA_get_evidence_count` first to gauge how well-studied a relationship is).
- `INDRA_get_statement_by_hash(hash=...)` → full single-statement detail once you have a hash from the above (real example: hash `-35357180905875939`, an EGFR Inhibition statement with 1,376 evidence items).

### Known-broken tool, verified live: ReactomeInteractors

`ReactomeInteractors_get_protein_interactors`, `ReactomeInteractors_get_entity_pathways`, `ReactomeInteractors_search_entity` (`reactome_interactors_tools.json`) — **all 3 tools currently return HTTP 521 on every call**, confirmed both via `tu test`/`tu run` and an independent direct `curl` to Reactome's own interactors endpoint (`reactome.org/ContentService/interactors/...`), which also returned 521. This is Reactome's interactors service being unreachable at the origin, not a ToolUniverse bug — it may be transient, so don't assume it's permanently gone, but **do not fabricate protein-interactor or entity-pathway results from this family** if you hit the same error; report it as "ReactomeInteractors service currently unreachable (HTTP 521)" and fall back to `STRING_functional_enrichment`, `intact_get_interactions`, or (for causal edges) SIGNOR/INDRA above instead. Note this is a *different* tool family from the already-documented `Reactome_map_uniprot_to_pathways`/`Reactome_get_pathway_reactions` (Phase 2, above) and from `Reactome_get_interactor` (singular, in `reactome_tools.json`, used by `tooluniverse-spatial-omics-analysis`) — three separate Reactome-branded tool families exist in the registry; this section covers only the `ReactomeInteractors_*` one.

**Best for**: Gene set analysis, protein function investigation, pathway discovery, systems-level biology
