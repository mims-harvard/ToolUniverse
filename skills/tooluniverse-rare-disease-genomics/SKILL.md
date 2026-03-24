---
name: tooluniverse-rare-disease-genomics
description: >
  Rare disease genomics research -- disease identification via Orphanet, causative gene discovery,
  gene-disease validity assessment via GenCC, pathogenic variant lookup via ClinVar, HPO phenotype
  mapping, epidemiology and prevalence data, clinical trial search, and literature review.
  Use when users ask about rare diseases, orphan diseases, genetic causes of rare conditions,
  Orphanet codes, HPO phenotypes, gene-disease validity, rare disease prevalence, or treatment options
  for rare genetic disorders.
triggers:
  - keywords: [rare disease, orphan disease, Orphanet, ORPHA, HPO, phenotype, genetic disorder, inborn error, GenCC, gene-disease validity, rare genetic, congenital, inherited disorder]
  - patterns: ["rare disease", "orphan disease", "genetic cause of", "what genes cause", "prevalence of", "clinical features of", "HPO phenotypes for", "pathogenic variants in"]
---

# Rare Disease Genomics Research

Systematic rare disease investigation: identify diseases via Orphanet, map HPO phenotypes, discover
causative genes, assess gene-disease validity through GenCC, find pathogenic variants in ClinVar,
retrieve epidemiology data, search for active clinical trials, and gather relevant literature.

## When to Use

- "What is the genetic cause of Marfan syndrome?"
- "Find HPO phenotypes associated with cystic fibrosis"
- "What is the prevalence of Ehlers-Danlos syndrome?"
- "Which genes are linked to this rare disease?"
- "Is FBN1 definitively associated with Marfan syndrome?"
- "Find pathogenic variants in CFTR"
- "Are there clinical trials for Gaucher disease?"
- "What diseases are associated with gene FBN1?"

## NOT for (use other skills instead)

- Common disease genomics (type 2 diabetes, hypertension) -> Use `tooluniverse-disease-research`
- Cancer variant interpretation -> Use `tooluniverse-cancer-variant-interpretation`
- GWAS-based variant interpretation -> Use `tooluniverse-gwas-snp-interpretation`
- Pharmacogenomics / drug-gene interactions -> Use `tooluniverse-pharmacogenomics`
- Differential diagnosis from symptoms -> Use `tooluniverse-rare-disease-diagnosis`

---

## Workflow Overview

```
Input (disease name / gene symbol / ORPHA code)
  |
  v
Phase 0: Disambiguation (resolve disease name to ORPHA code, gene to HGNC)
  |
  v
Phase 1: Disease Characterization (definition, synonyms, classification, inheritance)
  |
  v
Phase 2: Phenotype Mapping (HPO terms with frequency and diagnostic criteria)
  |
  v
Phase 3: Causative Gene Discovery (genes, loci, association types)
  |
  v
Phase 4: Gene-Disease Validity (GenCC classifications, multiple submitter evidence)
  |
  v
Phase 5: Pathogenic Variant Lookup (ClinVar pathogenic/likely pathogenic variants)
  |
  v
Phase 6: Epidemiology (prevalence, incidence, age of onset, inheritance pattern)
  |
  v
Phase 7: Clinical Trials (active and recruiting trials for the condition)
  |
  v
Phase 8: Literature (recent publications on genetics of the disease)
  |
  v
Phase 9: Report (integrated evidence summary with confidence grading)
```

---

## Phase 0: Disambiguation

Resolve user input to canonical Orphanet identifiers.

**Orphanet_search_by_name**: `name` (string REQUIRED, e.g., "Marfan syndrome"), `exact` (bool, default False), `lang` (string, default "en"). Returns `{status, data: {results: [{ORPHAcode, "Preferred term", Date}]}}`.
- Primary tool for name-to-ORPHA-code resolution. Parameter is `name` (NOT `query`).
- Returns multiple matches; select the exact match (not subtypes or syndromes containing the name).
- Set `exact=True` for precise matching; leave False for fuzzy/keyword matching.
- Example: "Marfan syndrome" -> ORPHAcode 558 (not 284993 "Marfan syndrome and Marfan-related disorders").

**Orphanet_search_diseases**: `query` (string REQUIRED). Returns similar results; use as fallback if `search_by_name` returns no results.

**Orphanet_get_gene_diseases**: `gene_symbol` (string REQUIRED, e.g., "FBN1"). Returns `{status, data: {gene_name, diseases: [{orpha_code, preferred_term, disorder_group, typology, genes: [{symbol, association_type, association_status}]}]}}`.
- Use when starting from a gene symbol instead of a disease name.
- Returns all diseases associated with the gene, including association type ("Disease-causing germline mutation(s) in", "Candidate gene tested in", etc.).

### Key Identifiers

| Data Type | Format | Example |
|-----------|--------|---------|
| Disease (Orphanet) | ORPHAcode (integer) | 558 (Marfan syndrome) |
| Disease (MONDO) | MONDO:XXXXXXX | MONDO:0007947 |
| Gene (HGNC) | Gene symbol | FBN1 |
| Gene (HGNC curie) | HGNC:XXXX | HGNC:3603 |
| Phenotype (HPO) | HP:XXXXXXX | HP:0001519 |
| ICD-10 code | X##.# | Q87.4 |

### Verified ORPHA Codes (common rare diseases)

| Disease | ORPHAcode |
|---------|-----------|
| Marfan syndrome | 558 |
| Cystic fibrosis | 586 |
| Huntington disease | 399 |
| Duchenne muscular dystrophy | 98896 |
| Phenylketonuria | 716 |
| Gaucher disease | 355 |
| Fabry disease | 324 |

---

## Phase 1: Disease Characterization

**Orphanet_get_disease**: `orpha_code` (string REQUIRED, e.g., "558"). Returns `{status, data: {ORPHAcode, "Preferred term", Definition, Synonyms: [...]}}`.
- Provides the official Orphanet definition and synonym list.

**Orphanet_get_classification**: `orpha_code` (string REQUIRED). Returns `{status, data: {orpha_code, classification: {ORPHAcode, "Preferred term", Classification: [{ID, Name}]}}}`.
- Shows which Orphanet classification hierarchies include this disease (e.g., "rare genetic diseases", "rare ophthalmic disorders").

**Orphanet_get_natural_history**: `orpha_code` (string REQUIRED). Returns `{status, data: {orpha_code, preferred_term, average_age_of_onset: [...], type_of_inheritance: [...], disorder_group, typology}}`.
- Key fields: `average_age_of_onset` (e.g., "All ages", "Neonatal", "Infancy"), `type_of_inheritance` (e.g., "Autosomal dominant", "X-linked recessive").

**Orphanet_get_icd_mapping**: `orpha_code` (string REQUIRED). Returns `{status, data: {orpha_code, mappings: {ICD10: [{Code, Relation, Status}], ICD11: [{Code, Relation, Status}]}}}`.
- Maps ORPHA codes to ICD-10/ICD-11 for clinical coding.

---

## Phase 2: Phenotype Mapping (HPO)

**Orphanet_get_phenotypes**: `orpha_code` (string REQUIRED). Returns `{status, data: {orpha_code, preferred_term, phenotypes: [{hpo_id, hpo_term, frequency, diagnostic_criteria}]}}`.
- `frequency` values: "Very frequent (99-80%)", "Frequent (79-30%)", "Occasional (29-5%)", "Very rare (<4-1%)", "Excluded (0%)".
- `diagnostic_criteria`: "Diagnostic criterion" if the phenotype is part of formal diagnostic criteria; null otherwise.
- Use to build a phenotype profile for the disease.

### Frequency Interpretation

| Orphanet Frequency | Meaning | Clinical Utility |
|-------------------|---------|-----------------|
| Very frequent (99-80%) | Nearly all patients | Core diagnostic feature |
| Frequent (79-30%) | Majority of patients | Supporting feature |
| Occasional (29-5%) | Minority of patients | Variable presentation |
| Very rare (<4-1%) | Rare association | Not useful for diagnosis |
| Excluded (0%) | Not associated | Rule-out criterion |

---

## Phase 3: Causative Gene Discovery

**Orphanet_get_genes**: `orpha_code` (string REQUIRED, alias: `disease_id`). Returns `{status, data: {orpha_code, disease_name, genes: [{Symbol, Name, GeneType, Locus: [{GeneLocus}], AssociationType, AssociationStatus, SourceOfValidation}]}}`.
- `AssociationType` values: "Disease-causing germline mutation(s) in", "Major susceptibility factor in", "Candidate gene tested in", "Modifying germline mutation in", "Disease-causing somatic mutation(s) in", "Role in the phenotype of".
- `AssociationStatus`: "Assessed" or "Not yet assessed".
- `SourceOfValidation`: PMIDs supporting the association.

### Association Type Interpretation

| AssociationType | Evidence Strength | Clinical Relevance |
|----------------|-------------------|-------------------|
| Disease-causing germline mutation(s) in | Definitive | Primary diagnostic target |
| Major susceptibility factor in | Strong | Risk factor; incomplete penetrance |
| Modifying germline mutation in | Moderate | Modifies severity/phenotype |
| Candidate gene tested in | Preliminary | Not confirmed; research use only |
| Role in the phenotype of | Variable | Contributes to specific features |

---

## Phase 4: Gene-Disease Validity Assessment

**GenCC_search_gene**: `gene_symbol` (string REQUIRED, e.g., "FBN1"). Returns `{status, data: {gene_symbol, submissions: [{gene_symbol, gene_curie, disease_title, disease_curie, classification, mode_of_inheritance, submitter, submitted_date}]}}`.
- Multiple submitters (ClinGen, Ambry Genetics, Invitae, etc.) independently classify gene-disease relationships.
- Aggregate across submitters for confidence assessment.

**GenCC_search_disease**: `disease` (string REQUIRED, e.g., "Marfan syndrome"). Returns `{status, data: {disease, submissions: [{gene_symbol, disease_title, disease_curie, classification, mode_of_inheritance, submitter}]}}`.
- Use when starting from a disease name to find all gene associations with validity levels.
- IMPORTANT: Parameter is `disease` (NOT `disease_title`).

**GenCC_get_classifications**: No params. Returns `{status, data: {classifications: [{classification, count, rank}]}}`.
- Reference for understanding classification levels.

### GenCC Classification Levels (by rank)

| Classification | Rank | Meaning |
|---------------|------|---------|
| Definitive | 1 | Highest confidence; replicated evidence |
| Strong | 2 | Strong evidence from multiple sources |
| Moderate | 3 | Moderate evidence; fewer independent sources |
| Limited | 4 | Preliminary evidence; single or few reports |
| No Known Disease Relationship | 5 | Evidence reviewed; no association found |
| Disputed | 6 | Conflicting evidence |
| Refuted | 7 | Previously claimed association disproven |
| Animal Model Only | 8 | Evidence only from animal models |

### Cross-Submitter Consensus Assessment

When multiple submitters agree, confidence increases:
- 3+ submitters at "Definitive" -> Very high confidence
- 2+ submitters at "Strong" or above -> High confidence
- Mixed classifications -> Report range and note disagreement
- Single submitter only -> Note limited independent validation

---

## Phase 5: Pathogenic Variant Lookup

**ClinVar_search_variants**: `gene` (string, gene symbol e.g., "FBN1"), `condition` (string, disease name e.g., "Marfan syndrome"), `variant_id` (string, ClinVar ID), `clinical_significance` (string, e.g., "Pathogenic"), `max_results` (int, default 20; alias `limit`). At least one of `gene`, `condition`, or `variant_id` required. Returns `{status, data: {total_count, variant_ids: [...], variants: [{variant_id, title, genes: [...], clinical_significance, review_status}]}}`.
- NOTE: Primary param is `gene` (NOT `query`). Combine `gene` + `condition` for disease-specific lookup.
- Returns pathogenic/likely pathogenic/VUS/benign variants.
- `clinical_significance` values: "Pathogenic", "Likely pathogenic", "Uncertain significance", "Benign", "Likely benign", "Conflicting classifications of pathogenicity".
- `review_status`: "criteria provided, single submitter", "reviewed by expert panel", "practice guideline", etc.
- Default returns up to 20 variants. For comprehensive search, note `total_count` indicates full count.

### ClinVar Review Status Hierarchy

| Review Status | Stars | Confidence |
|--------------|-------|------------|
| practice guideline | 4 | Highest |
| reviewed by expert panel | 3 | High |
| criteria provided, multiple submitters, no conflicts | 2 | Good |
| criteria provided, single submitter | 1 | Moderate |
| no assertion criteria provided | 0 | Low |

---

## Phase 6: Epidemiology

**Orphanet_get_epidemiology**: `orpha_code` (string REQUIRED). Returns `{status, data: {orpha_code, preferred_term, prevalences: [{type, class, geographic, qualification, mean_value, source, validation_status}]}}`.
- `type` values: "Point prevalence", "Annual incidence", "Lifetime prevalence", "Prevalence at birth".
- `class` values: "1-9 / 100 000", "1-5 / 10 000", "<1 / 1 000 000", etc.
- `geographic`: "Worldwide", "Europe", "United States", specific countries.
- `mean_value`: per 100,000 (numeric string).

**Orphanet_get_natural_history**: (also in Phase 1) Returns `average_age_of_onset` and `type_of_inheritance`.

### Prevalence Class Interpretation

| Orphanet Class | Approximate Prevalence | Category |
|---------------|----------------------|----------|
| >1 / 1000 | Common variant | Not truly rare |
| 1-5 / 10 000 | 1-5 per 10,000 | Rare |
| 6-9 / 100 000 | 6-9 per 100,000 | Rare |
| 1-9 / 100 000 | 1-9 per 100,000 | Rare |
| 1-9 / 1 000 000 | 1-9 per million | Ultra-rare |
| <1 / 1 000 000 | < 1 per million | Ultra-rare |

---

## Phase 6b: Ontology Lookup (OLS)

Use OLS to look up HPO, MONDO, ORDO, or other ontology terms by ID or free-text description.

**ols_search_terms**: `query` (string REQUIRED), `ontology` (string, optional, e.g., "hp", "ordo", "mondo"), `rows` (int, alias `size`, default 10), `exact_match` (bool, default False).
Returns `{status, data: [{id, label, description, ontology_name, obo_id, iri}]}`.
- Use when you have an HPO term description and need the HP:XXXXXXX ID.
- Infers ontology from CURIE prefix automatically (e.g., pass `ontology="hp"` to scope to HPO).

**ols_get_term_info**: `term_id` (string, CURIE e.g., "HP:0001519") OR `id` (alias) OR `term_iri` (full IRI URL).
Returns `{status, data: {label, description, synonyms, obo_id, ontology_name, iri}}`.
- Prefix-based ontology inference: "HP:" -> hp, "MONDO:" -> mondo, "ORDO:" -> ordo.

**ols_get_term_children**: `term_id` (string CURIE) OR `term_iri`, `ontology` (string, optional).
Returns child terms of the given ontology node.

**ols_get_term_ancestors**: `term_id` (string CURIE) OR `term_iri`, `ontology` (string, optional).
Returns ancestor terms -- useful for finding parent HPO categories.

**ols_find_similar_terms**: `ontology` (string REQUIRED, e.g., "hp"), `term_id` (string CURIE) OR `term_iri`, `size` (int, default 10).
Returns semantically similar terms within the specified ontology.

### Common Ontology Codes for Rare Disease

| Ontology | OLS code | Use Case |
|---|---|---|
| Human Phenotype Ontology | `hp` | Clinical phenotypes, signs, symptoms |
| Orphanet Rare Disease Ontology | `ordo` | Rare disease hierarchy |
| Monarch Disease Ontology | `mondo` | Cross-ontology disease terms |
| Disease Ontology | `doid` | Standard disease terms |
| Gene Ontology | `go` | Molecular function, biological process |

---

## Phase 6c: Metabolite-Disease Context (HMDB / Inborn Errors of Metabolism)

For metabolic rare diseases (IEM), use HMDB to link metabolites to diseases.

**HMDB_search**: `query` (string REQUIRED, compound name or formula).
Returns `{status, data: [{name, hmdb_id, formula, molecular_weight}]}`.
- Use to find HMDB IDs and cross-database IDs for metabolites.

**HMDB_get_metabolite**: `hmdb_id` (string, e.g., "HMDB0000159") OR `compound_name` (string, e.g., "phenylalanine").
Returns `{status, data: {name, formula, molecular_weight, iupac_name, smiles, inchikey, pubchem_cid, kegg_id, chebi_id, pathways}}`.
- Returns cross-database identifiers (KEGG, ChEBI, PubChem) for downstream pathway analysis.

**HMDB_get_diseases**: `hmdb_id` (string) OR `compound_name` (string).
Returns `{status, data: {diseases: [{disease_name, pmid, references}]}}`.
- Backed by CTD (Comparative Toxicogenomics Database); resolves via PubChem if name given.
- Use to confirm which rare diseases are linked to metabolite accumulation.

### IEM Example

```python
# Phenylketonuria: phenylalanine accumulation
meta = tu.tools.HMDB_search(query="phenylalanine")
hmdb_id = meta["data"][0]["hmdb_id"]  # HMDB0000159

# Get disease associations
diseases = tu.tools.HMDB_get_diseases(hmdb_id=hmdb_id)
# Cross-reference with Orphanet
orpha = tu.tools.Orphanet_search_diseases(query="phenylketonuria", limit=5)
orpha_code = orpha["data"][0]["orpha_code"]
genes = tu.tools.Orphanet_get_genes(orpha_code=orpha_code)  # PAH gene
```

---

## Phase 7: Clinical Trials

**search_clinical_trials**: `query_term` (string REQUIRED), `condition` (string, optional), `intervention` (string, optional), `pageSize` (int, optional, default 10). Returns `{status, data: {studies: [{NCT ID, brief_title, brief_summary, overall_status, condition: [...], phase: [...]}], nextPageToken, total_count}}`.
- Use disease name as `query_term`.
- `overall_status` values: "RECRUITING", "COMPLETED", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "TERMINATED", etc.
- `total_count` can be None even when studies exist; check `len(studies) > 0` instead.

### Filtering Strategy

For rare diseases, prioritize:
1. **Recruiting trials**: Active enrollment opportunities for patients
2. **Phase 2-3 trials**: Most clinically relevant
3. **Gene/enzyme replacement therapy**: Common for genetic rare diseases
4. **Natural history studies**: Even observational studies are valuable for rare diseases

---

## Phase 8: Literature

**EuropePMC_search_articles**: `query` (string REQUIRED, e.g., "Marfan syndrome genetics"), `limit` (int, optional, default 10). Returns `{status, data: [{title, abstract, authors: [...], journal, year, doi, url, pmid, pmcid, citations, open_access}]}`.
- Use disease name + "genetics" or "gene" for genetic literature.
- Note: HTML entities may appear in titles (e.g., `<i>FBN1</i>`); strip for display.
- Returns most recent articles first.

### Recommended Search Strategies

| Goal | Query Pattern |
|------|--------------|
| Genetic cause | "[disease] genetics" or "[disease] gene" |
| New variants | "[disease] novel variant" or "[disease] pathogenic" |
| Genotype-phenotype | "[disease] genotype phenotype correlation" |
| Treatment | "[disease] therapy" or "[disease] treatment" |
| Reviews | "[disease] review" |

---

## Evidence Grading

### Tier System

| Tier | Source | Example |
|------|--------|---------|
| T1 (Definitive) | GenCC Definitive + ClinVar expert-reviewed + Orphanet assessed | FBN1 causes Marfan (GenCC: Definitive from ClinGen + multiple submitters) |
| T2 (Strong) | GenCC Strong + ClinVar single-submitter + Orphanet disease-causing | Gene with strong but less replicated evidence |
| T3 (Moderate) | GenCC Limited/Moderate + ClinVar VUS + Orphanet candidate | Emerging gene-disease associations |
| T4 (Preliminary) | Literature only + animal models + no GenCC/ClinVar | Genes reported in case studies only |

---

## Tool Parameter Quick Reference

| Tool | Key Params | Return Format |
|------|-----------|---------------|
| Orphanet_search_by_name | `name` (REQUIRED), `exact`, `lang` | `{status, data: {results: [{ORPHAcode, "Preferred term"}]}}` |
| Orphanet_search_diseases | `query` | Same as search_by_name |
| Orphanet_get_disease | `orpha_code` (string) | `{status, data: {ORPHAcode, "Preferred term", Definition, Synonyms}}` |
| Orphanet_get_phenotypes | `orpha_code` (string) | `{status, data: {phenotypes: [{hpo_id, hpo_term, frequency, diagnostic_criteria}]}}` |
| Orphanet_get_genes | `orpha_code` (string, alias: `disease_id`) | `{status, data: {genes: [{Symbol, Name, AssociationType, Locus}]}}` |
| Orphanet_get_epidemiology | `orpha_code` (string) | `{status, data: {prevalences: [{type, class, geographic, mean_value}]}}` |
| Orphanet_get_natural_history | `orpha_code` (string) | `{status, data: {average_age_of_onset, type_of_inheritance}}` |
| Orphanet_get_classification | `orpha_code` (string) | `{status, data: {classification: {Classification: [{ID, Name}]}}}` |
| Orphanet_get_icd_mapping | `orpha_code` (string) | `{status, data: {mappings: {ICD10: [...], ICD11: [...]}}}` |
| Orphanet_get_gene_diseases | `gene_symbol` | `{status, data: {gene_name, diseases: [{orpha_code, preferred_term}]}}` |
| GenCC_search_gene | `gene_symbol` | `{status, data: {gene_symbol, submissions: [{classification, submitter}]}}` |
| GenCC_search_disease | `disease` (NOT disease_title) | `{status, data: {disease, submissions: [{gene_symbol, classification}]}}` |
| GenCC_get_classifications | (none) | `{status, data: {classifications: [{classification, count, rank}]}}` |
| ClinVar_search_variants | `gene`, `condition`, `clinical_significance`, `max_results` | `{status, data: {total_count, variants: [{variant_id, title, clinical_significance}]}}` |
| ClinVar_get_variant_details | `variant_id` (REQUIRED) | `{status, data: {accession, title, genes, clinical_significance, review_status}}` |
| ClinVar_get_clinical_significance | `variant_id` (REQUIRED) | `{status, data: {clinical_significance, review_status, submitter_count}}` |
| ols_search_terms | `query`, `ontology` (optional), `rows`/`size` | `{status, data: [{id, label, description, obo_id}]}` |
| ols_get_term_info | `term_id` or `term_iri` | `{status, data: {label, description, synonyms, obo_id}}` |
| ols_get_term_children | `term_id` or `term_iri`, `ontology` (optional) | Child terms list |
| ols_get_term_ancestors | `term_id` or `term_iri`, `ontology` (optional) | Ancestor terms list |
| ols_find_similar_terms | `ontology` (REQUIRED), `term_id` or `term_iri` | Similar terms list |
| HMDB_search | `query` (REQUIRED) | `{status, data: [{name, hmdb_id, formula}]}` |
| HMDB_get_metabolite | `hmdb_id` or `compound_name` | `{status, data: {name, formula, smiles, kegg_id, chebi_id}}` |
| HMDB_get_diseases | `hmdb_id` or `compound_name` | `{status, data: {diseases: [{disease_name, pmid}]}}` |
| search_clinical_trials | `query_term` + optional `condition`, `pageSize` | `{status, data: {studies: [{NCT ID, brief_title, overall_status}]}}` |
| EuropePMC_search_articles | `query`, `limit` | `{status, data: [{title, abstract, authors, journal, year, pmid}]}` |

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Using `disease_title` in GenCC_search_disease | Use `disease` (e.g., `disease="Marfan syndrome"`) |
| Using `query` in Orphanet_search_by_name | Primary param is `name` (e.g., `name="Marfan syndrome"`) |
| Using `query` in ClinVar_search_variants | Params are `gene`, `condition`, and/or `variant_id` (no `query` param) |
| Passing integer to Orphanet tools | `orpha_code` accepts string or int but use string (e.g., "558") |
| Assuming first Orphanet search result is correct | Filter for exact match; subtypes and related syndromes also appear |
| Not checking GenCC submitter consensus | Single submitter "Definitive" is weaker than 3+ submitters agreeing |
| Treating ClinVar VUS as pathogenic | VUS means uncertain; do not report as disease-causing |
| Using `total_count` from clinical trials as boolean | Can be None even with results; check `len(studies) > 0` |
| Ignoring Orphanet association type | "Candidate gene tested in" is NOT the same as "Disease-causing germline mutation(s) in" |

---

## Fallback Strategies

| Phase | Primary Tool | Fallback |
|-------|-------------|----------|
| Disease lookup | Orphanet_search_by_name | Orphanet_search_diseases |
| Gene -> diseases | Orphanet_get_gene_diseases | GenCC_search_gene (broader coverage) |
| Disease -> genes | Orphanet_get_genes | GenCC_search_disease |
| Gene-disease validity | GenCC_search_gene | Orphanet AssociationType + SourceOfValidation PMIDs |
| Pathogenic variants | ClinVar_search_variants | Literature search via EuropePMC |
| Epidemiology | Orphanet_get_epidemiology | Literature search for prevalence studies |
| Clinical trials | search_clinical_trials | EuropePMC search for "[disease] clinical trial" |

---

## Example Workflows

### Workflow 1: Full Rare Disease Investigation (disease name input)

```
Step 1: Orphanet_search_by_name(name="Marfan syndrome")
  -> ORPHAcode 558

Step 2: Orphanet_get_disease(orpha_code="558")
  -> Definition: connective tissue disorder with cardiovascular, musculoskeletal, ophthalmic manifestations

Step 3: Orphanet_get_phenotypes(orpha_code="558")
  -> HPO phenotypes with frequencies (aortic root aneurysm: Very frequent, ectopia lentis: Frequent)

Step 4: Orphanet_get_genes(orpha_code="558")
  -> FBN1 (disease-causing), TGFBR1, TGFBR2 (also disease-causing)

Step 5: GenCC_search_gene(gene_symbol="FBN1")
  -> Definitive classification from ClinGen, Ambry, Invitae (high consensus)

Step 6: ClinVar_search_variants(gene="FBN1", clinical_significance="Pathogenic", max_results=50)
  -> 207 total variants; filter for Pathogenic/Likely pathogenic

Step 7: Orphanet_get_epidemiology(orpha_code="558")
  -> Point prevalence 1-5/10,000 worldwide

Step 8: search_clinical_trials(query_term="Marfan syndrome", pageSize=10)
  -> Active trials (losartan, atenolol, aortic monitoring)

Step 9: EuropePMC_search_articles(query="Marfan syndrome genetics", limit=5)
  -> Recent publications on FBN1 variants, genotype-phenotype correlation
```

### Workflow 2: Gene-First Investigation (starting from a gene)

```
Step 1: Orphanet_get_gene_diseases(gene_symbol="FBN1")
  -> List all associated diseases (Marfan, stiff skin syndrome, etc.)

Step 2: GenCC_search_gene(gene_symbol="FBN1")
  -> Validity classifications for each disease association

Step 3: For top disease (ORPHAcode 558):
  Orphanet_get_phenotypes(orpha_code="558")
  Orphanet_get_epidemiology(orpha_code="558")

Step 4: ClinVar_search_variants(gene="FBN1", clinical_significance="Pathogenic")
  -> Pathogenic variants in this gene
```

### Workflow 3: Phenotype-Focused (clinical features query)

```
Step 1: Orphanet_search_by_name(name="disease name")
  -> Get ORPHAcode

Step 2: Orphanet_get_phenotypes(orpha_code="XXX")
  -> Full HPO phenotype list with frequencies

Step 3: Filter phenotypes:
  -> Diagnostic criteria (diagnostic_criteria != null)
  -> Very frequent features (core phenotype)
  -> Occasional features (variable presentation)

Step 4: Orphanet_get_natural_history(orpha_code="XXX")
  -> Age of onset, inheritance pattern
```

### Workflow 4: Treatment and Trial Search

```
Step 1: Orphanet_search_by_name(name="Gaucher disease")
  -> ORPHAcode 355

Step 2: search_clinical_trials(query_term="Gaucher disease", pageSize=20)
  -> Filter for RECRUITING status

Step 3: EuropePMC_search_articles(query="Gaucher disease treatment", limit=10)
  -> Recent therapy publications (enzyme replacement, substrate reduction)

Step 4: Orphanet_get_genes(orpha_code="355")
  -> GBA1 gene -> context for gene therapy trials
```

---

## Limitations

- Orphanet coverage focuses on rare diseases only; common diseases may have minimal entries.
- ClinVar returns up to 20 variants by default; total_count shows full count but paginated retrieval is limited.
- GenCC submissions may lag behind latest literature; check publication dates.
- Orphanet prevalence data relies on published studies and may be outdated for some conditions.
- Clinical trial search via ClinicalTrials.gov may miss trials registered in other registries (EU Clinical Trials Register, ISRCTN).
- EuropePMC may include HTML entities in titles that need stripping for clean display.
- Some very rare diseases may have no GenCC submissions, no ClinVar variants, or no clinical trials.
- Orphanet gene-disease associations include "Candidate gene tested in" which indicates preliminary/unconfirmed associations.

---

## Completeness Checklist

Before delivering a report, verify:
- [ ] Disease resolved to ORPHA code (not a subtype or related syndrome)
- [ ] Definition and synonyms retrieved
- [ ] HPO phenotypes listed with frequencies
- [ ] Diagnostic criteria phenotypes highlighted
- [ ] Causative genes identified with association types
- [ ] Gene-disease validity assessed via GenCC (with submitter consensus)
- [ ] Pathogenic variants retrieved from ClinVar (significance and review status noted)
- [ ] Epidemiology data included (prevalence, incidence, geographic scope)
- [ ] Inheritance pattern and age of onset documented
- [ ] Clinical trials searched (recruiting status highlighted)
- [ ] Recent literature cited
- [ ] Evidence graded by tier (T1-T4)
- [ ] Limitations noted for gaps in data
