# Literature Deep Research - Workflow Cheat-Sheet

---

## Workflow Summary

```
1. CLARIFY → Subject type? Scope? Aliases? Domain?
2. DISAMBIGUATE → Resolve IDs, find collisions, gather baseline profile
3. SEARCH → High-precision seeds → Citation expansion → Collision-filtered broad
4. GRADE → Apply evidence tiers (T1-T4) to all claims
5. REPORT → 15-section template, integrated model, testable hypotheses
```

---

## Phase 1: Subject Disambiguation

### Biological Target Tools

| Data Type | Primary Tool | Fallback |
|-----------|--------------|----------|
| UniProt ID | `UniProt_search` | `proteins_api_get_protein` |
| Ensembl ID | `UniProt_id_mapping` | `ensembl_lookup_gene` |
| Domains | `InterPro_get_protein_domains` | UniProt features |
| Expression | `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` |
| GO Terms | `GO_get_annotations_for_gene` | `OpenTargets_get_target_gene_ontology_by_ensemblID` |
| Pathways | `Reactome_map_uniprot_to_pathways` | `kegg_get_gene_info` |
| Location | `HPA_get_subcellular_location` | UniProt localization |
| Interactions | `STRING_get_protein_interactions` | `intact_get_interactions` |
| Drug/Disease | `DGIdb_get_drug_gene_interactions` | `OpenTargets_get_associated_drugs_by_target_ensemblID` |

### Drug-Centric Tools

| Data Type | Primary Tool | Fallback |
|-----------|--------------|----------|
| Drug ID | `OpenTargets_get_drug_chembId_by_generic_name` | `ChEMBL_search_drugs` |
| Drug Info | `ChEMBL_get_drug` | `drugbank_get_drug_basic_info_by_drug_name_or_id` |
| Mechanisms | `ChEMBL_get_drug_mechanisms` | `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` |
| Targets | `OpenTargets_get_associated_targets_by_drug_chemblId` | `drugbank_get_targets_by_drug_name_or_drugbank_id` |
| Safety | `OpenTargets_get_drug_adverse_events_by_chemblId` | `OpenTargets_get_drug_warnings_by_chemblId` |
| Indications | `OpenTargets_get_drug_indications_by_chemblId` | `drugbank_get_indications_by_drug_name_or_drugbank_id` |
| Trials | `search_clinical_trials` | --- |

### General Academic (No Bio Tools)

Skip bio annotation tools. Use domain-appropriate literature databases directly:
- CS/ML: `ArXiv_search_papers`, `DBLP_search_publications`, `SemanticScholar_search_papers`
- Social Science: `OSF_search_preprints`, `openalex_literature_search`
- General: `openalex_literature_search`, `Crossref_search_works`, `CORE_search_papers`

### Interdisciplinary / Cross-Domain

For topics spanning multiple domains (e.g., "GNNs for drug discovery"):
1. Identify each domain component separately
2. Resolve bio entities using Phase 1 bio tools
3. Search CS/general literature using ArXiv, DBLP, SemanticScholar
4. Merge results from both bio and general tools in Phase 2
5. Cross-reference to find bridging papers

### Collision Detection

| Domain | Collision Check Syntax |
|--------|----------------------|
| Biomedical | PubMed: `"[TERM]"[Title]` |
| CS/ML | ArXiv: `ti:"[TERM]"` or SemanticScholar with `fieldsOfStudy` filter |
| General | OpenAlex or Crossref title search |

```
1. Search primary database (first 20 results)
2. If >20% off-topic → identify collision terms
3. Build filter: NOT [collision1] NOT [collision2]
```

**Gene family**: `"ADAR" NOT "ADAR2" NOT "ADARB1"` for ADAR1-specific.
**Cross-domain**: `"RAG" AND "language model" NOT "recombination activating"`.

---

## Phase 2: Query Strategy

### Step 1: High-Precision Seeds
```
Biomedical: "[TERM]"[Title] AND (mechanism OR function OR structure OR review)
CS/ML:      ti:"[TERM]" AND (architecture OR benchmark OR evaluation OR survey)
General:    "[TERM]" in title via OpenAlex/Crossref
```

### Step 2: Citation Expansion
```
PubMed_get_cited_by(pmid) → Forward citations
EuropePMC_get_citations(pmid) → Fallback for forward
OpenCitations_get_citations(doi) → Open citation data
PubMed_get_related(pmid) → Related papers
SemanticScholar_get_recommendations(pmid) → AI-recommended
EuropePMC_get_references(pmid) → Backward citations
```

### Step 2b: Citation Impact (optional)
```
iCite_search_publications(query) → Search + RCR/APT/NIH percentile (PubMed-only)
iCite_get_publications(pmids) → Metrics by PMID (PubMed-only)
scite_get_tallies(doi) → Supporting/contradicting/mentioning counts (PubMed-only)
SemanticScholar_get_paper(paper_id) → Citation counts for any paper (CS/ML included)
```

### Step 3: Collision-Filtered Broad
```
"[TERM]" AND ([context1] OR [context2]) NOT [collision_term]
```

---

## Evidence Grading

| Tier | Label | Bio Criteria | CS/ML Criteria |
|------|-------|-------------|----------------|
| **T1** | ★★★ Mechanistic | CRISPR KO + rescue, RCT | Formal proof, controlled ablation + significance |
| **T2** | ★★☆ Functional | Knockdown/functional study | Benchmark with standard dataset + baselines |
| **T3** | ★☆☆ Association | Screen hit, GWAS, correlation | Observational, case study, anecdotal |
| **T4** | ☆☆☆ Mention | Review, text-mining | Survey, blog post, workshop abstract |

```markdown
Target X regulates pathway Y [★★★: PMID:12345678] through direct
phosphorylation [★★☆: PMID:23456789].
```

---

## Report Sections (ALL Required)

| # | Section | Must Include |
|---|---------|--------------|
| 1 | Subject Identity & Scope | IDs, synonyms, collisions |
| 2 | Background & Context | Domain-specific background |
| 3 | Key Entities & Relationships | Partners, targets, actors |
| 4 | Spatial/Temporal Context | Location, timeline, distribution |
| 5 | Quantitative Profile | Expression, metrics, trends |
| 6 | Core Mechanisms / Arguments | Function with evidence grades |
| 7 | Experimental / Empirical Evidence | Direct studies or "none found" |
| 8 | Variation & Heterogeneity | Variants, subtypes, competing views |
| 9 | Applied / Translational Relevance | With evidence strength |
| 10 | External Factors | Or "none identified" |
| 11 | Methods & Assays | Standard + emerging approaches |
| 12 | Research Themes | ≥3 papers/theme or "limited" |
| 13 | Open Questions & Gaps | What's unknown |
| 14 | Integrated Model | + 3-5 testable hypotheses |
| 15 | Conclusions | Confidence assessment |

---

## Theme Extraction

| Papers | Status |
|--------|--------|
| ≥10 | Major theme (full section) |
| 3-9 | Minor theme (subsection) |
| <3 | Note as "limited evidence" |

---

## Output Files

1. **`[topic]_report.md`** - Main narrative (DEFAULT)
2. **`[topic]_bibliography.json`** - Full deduplicated papers (ALWAYS)
3. **`[topic]_bibliography.csv`** - Tabular bibliography (ALWAYS)
4. **`[topic]_factcheck_report.md`** - Factoid/verification mode output
5. **`methods_appendix.md`** - Methodology (ONLY if requested)

---

## Tool Failure Handling

```
Attempt 1 → fails → wait 2s → Attempt 2 → fails → wait 5s → Fallback tool
```

| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubMed_get_cited_by` | `EuropePMC_get_citations` | `OpenCitations_get_citations` |
| `PubMed_get_related` | `SemanticScholar_get_recommendations` | `SemanticScholar_search_papers` |
| `iCite_search_publications` | `iCite_get_publications` (if have PMIDs) | PubMed + manual metrics |
| `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` | --- |
| `Unpaywall_check_oa_status` | EuropePMC/OpenAlex OA flags | --- |

---

## DO vs DON'T

| DO | DON'T |
|----|-------|
| Disambiguate first | Jump straight to literature |
| Grade all evidence | Treat all papers equally |
| State "limited evidence" | Leave sections blank |
| Generate hypotheses | Stop at description |
| Keep methodology internal | Show search process |
| Use fallback tools | Give up on first failure |
| Check for collisions | Assume terms are unambiguous |
| Adapt template to domain | Force bio sections on non-bio topics |
