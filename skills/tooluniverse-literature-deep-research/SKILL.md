---
name: tooluniverse-literature-deep-research
description: Deep literature review — PubMed, EuropePMC, bioRxiv preprints, citation networks, evidence synthesis. Disambiguates queries, runs collision-aware searches, grades evidence T1-T4, and produces structured reports. Use for systematic literature review, meta-analysis evidence collection, and detailed answer-with-citations workflows.
disable-model-invocation: true
---

# Literature Deep Research

Systematic literature research: disambiguate, search with collision-aware queries, grade evidence, produce structured reports.

**KEY PRINCIPLES**: (1) Disambiguate first (2) Right-size deliverable (3) Grade every claim T1-T4 (4) All sections mandatory even if "limited evidence" (5) Source attribution for every claim (6) English-first queries, respond in user's language (7) Report = deliverable, not search log

---

## LOOK UP, DON'T GUESS

Search PubMed/EuropePMC FIRST before reasoning. A published paper beats memory.

**Factoid search strategy:**
1. Extract KEY TERMS (most specific nouns/verbs)
2. `EuropePMC_search_articles(query="term1 term2 term3", limit=5)`
3. No results -> BROADEN (remove most restrictive term)
4. Too many -> NARROW (add specific terms)
5. Answer usually in abstract of top results
6. Failed query -> try DIFFERENT TERMS/synonyms, don't repeat

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Workflow

```
Phase 0: Clarify + Mode Select → Phase 1: Disambiguate + Profile → Phase 2: Literature Search → Phase 3: Report
```

---

## Phase 0: Mode Selection

| Mode | When | Deliverable |
|------|------|-------------|
| **Factoid** | Single concrete question | 1-page fact-check report + bibliography |
| **Mini-review** | Narrow topic | 1-3 page narrative |
| **Full Deep-Research** | Comprehensive overview | 15-section report + bibliography |

### Factoid Mode (Fast Path)
```markdown
# [TOPIC]: Fact-check Report
## Question / ## Answer (with evidence rating) / ## Source(s) / ## Verification Notes / ## Limitations
```

### Domain Detection

| Pattern | Domain | Action |
|---------|--------|--------|
| Gene/protein symbol | Biological target | Full bio disambiguation |
| Drug name | Drug | Drug disambiguation (1.5) |
| Disease name | Disease | Disease disambiguation (1.6) |
| CS/ML topic | General academic | Skip bio tools, literature-only |
| Cross-domain | Interdisciplinary | Resolve each entity in its domain |

### Cross-Skill Delegation
- Gene/protein deep-dive: `tooluniverse-target-research`
- Drug profile: `tooluniverse-drug-research`
- Disease profile: `tooluniverse-disease-research`

Use this skill for **literature synthesis**. Use specialized skills for **entity profiling**. For max depth, run both.

---

## Phase 1: Subject Disambiguation + Profile

### 1.1 Biological Target Resolution
```
UniProt_search → UniProt_get_entry_by_accession → UniProt_id_mapping
ensembl_lookup_gene → MyGene_get_gene_annotation
```

### 1.2 Naming Collision Detection
Check first 20 results. If >20% off-topic, build negative filter: `NOT [collision1] NOT [collision2]`.
Gene family: `"ADAR" NOT "ADAR2" NOT "ADARB1"`. Cross-domain: add context terms.

### 1.3 Baseline Profile (Bio Targets)
```
InterPro_get_protein_domains, UniProt_get_ptm_processing_by_accession, HPA_get_subcellular_location,
GTEx_get_median_gene_expression, GO_get_annotations_for_gene, Reactome_map_uniprot_to_pathways,
STRING_get_protein_interactions, intact_get_interactions, OpenTargets_get_target_tractability_by_ensemblID
```
GPCR targets: delegate to `tooluniverse-target-research`.

### 1.5 Drug Disambiguation
**Identity**: `OpenTargets_get_drug_chembId_by_generic_name`, `ChEMBL_get_drug`, `PubChem_get_CID_by_compound_name`, `drugbank_get_drug_basic_info_by_drug_name_or_id`
**Targets**: `ChEMBL_get_drug_mechanisms`, `OpenTargets_get_associated_targets_by_drug_chemblId`, `DGIdb_get_drug_gene_interactions`
**Safety**: `OpenTargets_get_drug_adverse_events_by_chemblId`, `OpenTargets_get_drug_indications_by_chemblId`, `search_clinical_trials`

### 1.6 Disease Disambiguation
```
OpenTargets disease search → EFO/MONDO IDs
DisGeNET_get_disease_genes, DisGeNET_search_disease
CTD_get_disease_chemicals
```

### 1.7 Compound Queries (e.g., "metformin in breast cancer")
Resolve both entities, then cross-reference via CTD_get_chemical_gene_interactions, CTD_get_chemical_diseases, OpenTargets drug-target/drug-disease tools. Intersect shared targets/pathways.

### 1.8 General Academic / 1.9 Interdisciplinary
Non-bio: skip bio tools, use ArXiv/DBLP/OSF. Cross-domain: resolve bio entities with 1.1-1.3, search CS/general in parallel, merge and cross-reference.

---

## Phase 2: Literature Search

**Methodology stays internal. Report shows findings, not process.**

### 2.1 Query Strategy
**Step 1: Seeds** (15-30 core papers): domain-specific title searches with date/sort filters.
**Step 2: Citation expansion**: `PubMed_get_cited_by`, `EuropePMC_get_citations/references`, `PubMed_get_related`, `SemanticScholar_get_recommendations`, `OpenCitations_get_citations`. If the opt-in Noodle MCP is connected (`noodle_*`, needs `NOODLE_MCP_URL`), its bounded citation/semantic graph traversal is another angle on the same PubMed corpus -- a discovery signal, not evidence of causality or validity, same caveat as the others.
**Step 3: Collision-filtered broader queries**: `"[TERM]" AND ([context]) NOT [collision]`

### 2.2 Literature Tools — core set + adaptive by domain

Run the **core multi-field set on every review** (catches what any single index misses), then add the domain rows that match the subject. Don't fire every source blindly — 6–10 well-chosen indexes beat 20 noisy ones.

**ALWAYS run (core, all disciplines)**: `PubMed_search_articles`, `EuropePMC_search_articles`, `openalex_search_works` (query param `search`/`query`) **or** `openalex_literature_search` (query param `search_keywords`) — pick one and match its param; mixing them silently returns off-topic results — and `SemanticScholar_search_papers`

**Then add by domain:**

| Domain | Add these | Notes |
|--------|-----------|-------|
| Biomedical / clinical | `PMC_search_papers` (full text), `PubTator3_LiteratureSearch` (entity & `relations:` queries), `PubMed_Guidelines_Search` (clinical guidelines) | PubTator normalizes gene/drug/disease entities |
| Biology (ecology/evolution/plant) | **EuropePMC as PRIMARY** + OpenAlex | PubMed returns 0–1 for non-clinical biology |
| CS / ML / AI | `ArXiv_search_papers`, `DBLP_search_publications` | arXiv + CS bibliography |
| Physics / HEP / astro | `InspireHEP_search_papers` | 1.6M+ particle/astro records |
| Broad / hard-to-find / OA | `Crossref_search_works`, `CORE_search_papers`, `DOAJ_search_articles`, `Fatcat_search_scholar`, `Consensus_search_papers` | DOI registry + OA aggregators + Internet Archive Scholar; Consensus (220M+ papers) adds an AI takeaway + study-design metadata per paper -- useful for fast triage, not a substitute for reading the source |
| Regional / EU-funded | `OpenAIRE_search_publications`, `HAL_search_archive` | EU open science + French national archive |
| Datasets / software / outputs | `Figshare_search_articles`, `Zenodo_search_records` | Citable DOIs for data & code |
| Preprints (latest) | `EuropePMC_search_articles(source='PPR')`, `OSF_search_preprints`, `BioRxiv_get_preprint`/`MedRxiv_get_preprint` (DOI lookup) | bioRxiv/medRxiv/PsyArXiv etc. |

**Multi-source**: `advanced_literature_search_agent` (12+ DBs; needs Azure key -- fallback: query the core set individually).
**Citation impact**: `iCite_search_publications` (RCR/APT), `iCite_get_publications` (by PMID), `scite_get_tallies` (support/contradict). PubMed-only; for CS use SemanticScholar.

A domain-specific index returning 0 (e.g. ArXiv on a pure-clinical topic) is normal — only worry if the whole core set is empty.

### 2.3-2.4 Full-Text & PubMed Zero-Result Fallback

Full-text: see `FULLTEXT_STRATEGY.md` for three-tier strategy.

**CRITICAL**: PubMed returns 0 for ~30% of valid queries. **Always retry with EuropePMC** when PubMed returns empty. This is not optional.

### 2.5 Tool Failure / OA Handling
Retry once -> fallback tool. Key fallbacks: PubMed_get_cited_by -> EuropePMC_get_citations -> OpenCitations. OA: Unpaywall if configured, else Europe PMC/PMC/OpenAlex flags.

Last resort when every structured index above is empty (a brand-new preprint, a dataset page, a project site with no DOI): the opt-in `exa_*` tools (general neural web search, no key needed for casual use) can still find it, but it's general internet retrieval, not a scientific database -- verify anything it surfaces against a real source before citing, don't grade it T1-T4 as if it were literature.

### 2.6 Controlled Vocabulary, Text-Mined Annotations, Citation Cross-References, and Variant Literature

Four small tool families beyond core search/citation coverage — verified live, not schema-assumed:

**MeSH (controlled vocabulary)**: `MeSH_search_descriptors`/`MeSH_search_terms` resolve a free-text term to NLM's standardized MeSH descriptor/entry-term IDs; `MeSH_get_descriptor` returns the descriptor's official label, type, and annotation. Use to broaden or standardize a query before searching (e.g. a user says "sugar disease" -> `MeSH_search_terms` finds the descriptor is actually filed under "Diabetes Mellitus") or to confirm two different-sounding search hits are actually indexed under the same concept.

**EuroPMCAnnot (text-mined entity annotations)**: `EuroPMCAnnot_get_article_annotations` (all entity mentions in one article: genes, diseases, chemicals, organisms, etc.), `EuroPMCAnnot_get_chemicals_from_article` (chemical/compound mentions only, a filtered convenience view), `EuroPMCAnnot_get_annotations_by_type` (one annotation type across multiple articles at once). These extract what a paper mentions without you reading the full text — useful for a fast relevance check across many candidate papers, or for confirming a specific gene/chemical is actually discussed (not just present in an abstract keyword match). Live-verified example: `EuroPMCAnnot_get_chemicals_from_article` on PMC4353746 returned 19 real chemical mentions including "Resistin".

**Citation cross-references — naming collision, read carefully**: `src/tooluniverse/data/europepmc_citations_tools.json` defines `EPMC_get_citations`, `EPMC_get_references`, and `EuropePMC_get_article_datalinks` — do NOT confuse these with the already-documented `EuropePMC_get_citations`/`EuropePMC_get_references` (core `europe_pmc_tools.json`, used above in Phase 2.1/TOOL_NAMES_REFERENCE.md). They are separate implementations with near-identical names hitting the same underlying Europe PMC REST endpoints. **Live-verified as of this writing: the `/references` endpoint is down on BOTH implementations** (`EPMC_get_references` and `EuropePMC_get_references` both return a real `503 "This API is temporarily unavailable due to maintenance"` from `www.ebi.ac.uk`), and `EuropePMC_get_article_datalinks` independently confirmed broken via direct curl (33s response, HTTP 500). `EPMC_get_citations`/`EuropePMC_get_citations` (the forward-citation direction) both work normally. **Practical guidance**: prefer the already-documented `EuropePMC_get_citations`/`EuropePMC_get_references` names for citation work; if references-fetching fails with a 503, it is very likely this live outage, not a query problem — say so rather than reporting "no references found." `EuropePMC_get_article_datalinks` (when working) additionally surfaces what data/database records a paper deposited (GenBank accessions, PDB entries, clinical trial registrations) — complementary to, not a replacement for, citations/references.

**Document conversion (any format to markdown)**: `convert_to_markdown {"uri": "..."}` accepts an `http:`/`https:`/`file:`/`data:` URI and converts it to markdown — verified live on an HTML page. Reach for this when a source is a PDF, DOCX, PPTX, XLSX, or HTML page rather than something the literature tools above already return as structured JSON (e.g. a supplementary-materials file, an institutional report, a non-indexed working paper someone hands you a link to) and you need its actual text content, not just metadata. This is a generic conversion utility, not a literature-search tool — use PubMed/EuropePMC/OpenAlex above whenever the source is already indexed there.

**BGPT (structured critical-appraisal search)**: `BGPT_search_paper_evidence` is a literature search tool, not a generative model despite the name — live-verified, it returns real papers (`doi`, `title`, plus full-text-derived fields). Unlike PubMed/EuropePMC/OpenAlex (title+abstract only), each result also includes methods/techniques used, sample size and population, results, paper limitations and biases, conflicts of interest, data/code availability, and a `how_to_falsify` statement — reach for it when a claim needs quality-weighing (is this an RCT with n=12 or n=12,000? does the paper disclose a conflict of interest?) rather than just a citation. **Caveat**: these structured fields are model-generated summaries of the paper, not curated ground truth — treat them as an appraisal aid and still verify against the actual paper before citing a specific number from them. First 50 results/session are free; `BGPT_API_KEY` unlocks the paid tier after that.

**LitVar (literature-derived variant mentions)**: `LitVar_search_variants` (find variants by rsID/gene/HGVS as discussed in the literature), `LitVar_get_variant_publications` (PMIDs mentioning a specific variant), `LitVar_get_variant_details` (structured record: gene, HGVS, ClinGen IDs). This answers "what does the literature say has been written about variant X" — distinct from clinical variant-classification databases (ClinVar, gnomAD, already in Phase 1.1/TOOL_NAMES_REFERENCE.md), which answer "what is variant X's clinical significance." Use LitVar to find the papers, then a clinical database to grade the variant itself. Live-verified: `LitVar_search_variants(gene="BRCA1")` and rsID-based lookups (rs328, rs7903146) all returned real hits; `LitVar_get_variant_publications` returned real PMID lists per variant.

---

## Phase 3: Evidence Grading

| Tier | Label | Bio Example | CS/ML Example |
|------|-------|-------------|---------------|
| **T1** | Mechanistic | CRISPR KO + rescue, RCT | Formal proof, controlled ablation |
| **T2** | Functional | siRNA knockdown phenotype | Benchmark with baselines |
| **T3** | Association | GWAS, screen hit | Observational, case study |
| **T4** | Mention | Review article | Survey, workshop abstract |

Inline: `Target X regulates Y [T1: PMID:12345678]`. Per theme: summarize evidence distribution.

Triaging a large candidate set before reading in full: `Consensus_search_papers` returns study type and sample size per paper, a fast first pass for provisional tiering -- confirm against the actual paper before citing, its metadata is a starting point, not the grade itself.

---

## Report Output

| File | Mode |
|------|------|
| `[topic]_report.md` | Full |
| `[topic]_factcheck_report.md` | Factoid |
| `[topic]_bibliography.json` + `.csv` | All |

**Progressive update**: create report with all section headers immediately. Fill after each phase. Write Executive Summary LAST.

Use 15-section template from `REPORT_TEMPLATE.md`. Domain adaptations: bio (architecture/expression/GO/disease), drug (properties/MOA/PK/safety), disease (epi/patho/genes/treatments), general (history/theories/evidence/applications).

---

## Communication

Brief progress updates only: "Resolving identifiers...", "Building paper set...", "Grading evidence..."
Do NOT expose: raw tool outputs, dedup counts, search round details.

---

## References

- `TOOL_NAMES_REFERENCE.md` -- 130+ tools with parameters
- `REPORT_TEMPLATE.md` -- template, domain adaptations, bibliography, completeness checklist
- `FULLTEXT_STRATEGY.md` -- three-tier full-text verification
- `WORKFLOW.md` -- compact cheat-sheet
- `EXAMPLES.md` -- worked examples
