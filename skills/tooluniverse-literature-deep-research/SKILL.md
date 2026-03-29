---
name: tooluniverse-literature-deep-research
description: Comprehensive literature deep research across any academic domain using 120+ ToolUniverse tools. Conducts subject disambiguation, systematic literature search with citation network expansion, evidence grading (T1-T4), and structured theme extraction. Produces detailed reports with mandatory completeness checklists, integrated models, and testable hypotheses. Use when users need thorough literature reviews, target/drug/disease profiles, topic deep-dives, claim verification, or systematic evidence synthesis. Supports biomedical (genes, proteins, drugs, diseases), computer science, social science, and general academic topics. For single factoid questions, uses a fast verification mode with inline answer.
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
**Step 2: Citation expansion**: `PubMed_get_cited_by`, `EuropePMC_get_citations/references`, `PubMed_get_related`, `SemanticScholar_get_recommendations`, `OpenCitations_get_citations`
**Step 3: Collision-filtered broader queries**: `"[TERM]" AND ([context]) NOT [collision]`

### 2.2 Literature Tools

**Biomedical**: `PubMed_search_articles`, `PMC_search_papers`, `EuropePMC_search_articles`, `PubTator3_LiteratureSearch`
**Biology (ecology/evolution/plant)**: **EuropePMC as PRIMARY** (PubMed returns 0-1 for non-clinical biology). Also `openalex_literature_search`.
**CS/ML**: `ArXiv_search_papers`, `DBLP_search_publications`, `SemanticScholar_search_papers`
**General**: `openalex_literature_search`, `Crossref_search_works`, `CORE_search_papers`, `DOAJ_search_articles`
**Preprints**: `BioRxiv_get_preprint`, `MedRxiv_get_preprint`, `OSF_search_preprints`, `EuropePMC_search_articles(source='PPR')`
**Multi-source**: `advanced_literature_search_agent` (12+ DBs; needs Azure key -- fallback: query PubMed+ArXiv+SemanticScholar+OpenAlex individually)
**Citation impact**: `iCite_search_publications` (RCR/APT), `iCite_get_publications` (by PMID), `scite_get_tallies` (support/contradict). PubMed-only; for CS use SemanticScholar.

### 2.3-2.4 Full-Text & PubMed Zero-Result Fallback

Full-text: see `FULLTEXT_STRATEGY.md` for three-tier strategy.

**CRITICAL**: PubMed returns 0 for ~30% of valid queries. **Always retry with EuropePMC** when PubMed returns empty. This is not optional.

### 2.5 Tool Failure / OA Handling
Retry once -> fallback tool. Key fallbacks: PubMed_get_cited_by -> EuropePMC_get_citations -> OpenCitations. OA: Unpaywall if configured, else Europe PMC/PMC/OpenAlex flags.

---

## Phase 3: Evidence Grading

| Tier | Label | Bio Example | CS/ML Example |
|------|-------|-------------|---------------|
| **T1** | Mechanistic | CRISPR KO + rescue, RCT | Formal proof, controlled ablation |
| **T2** | Functional | siRNA knockdown phenotype | Benchmark with baselines |
| **T3** | Association | GWAS, screen hit | Observational, case study |
| **T4** | Mention | Review article | Survey, workshop abstract |

Inline: `Target X regulates Y [T1: PMID:12345678]`. Per theme: summarize evidence distribution.

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

- `TOOL_NAMES_REFERENCE.md` -- 123 tools with parameters
- `REPORT_TEMPLATE.md` -- template, domain adaptations, bibliography, completeness checklist
- `FULLTEXT_STRATEGY.md` -- three-tier full-text verification
- `WORKFLOW.md` -- compact cheat-sheet
- `EXAMPLES.md` -- worked examples
