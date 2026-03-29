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

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Rare Disease Genomics Research

## Rare Disease Investigation Strategy

The order of investigation matters: **phenotype -> disease -> gene -> variant**, not the reverse. When starting from a gene, reverse it: gene -> diseases -> expected phenotypes -> does the patient match?

Resist the urge to skip to ClinVar immediately. A "Pathogenic" ClinVar entry is only meaningful if the gene is actually causative for the disease in question with the right inheritance mode.

## Variant Prioritization Reasoning (CRITICAL)

**LOOK UP DON'T GUESS** -- when uncertain about any gene, variant, or disease association, search the database. Do not rely on memory.

### How to filter thousands of variants down to one causal variant

1. **Inheritance pattern first** -- Check Orphanet_get_natural_history for inheritance mode. This determines your filtering strategy:
   - Autosomal dominant: look for heterozygous variants in ONE copy; de novo if unaffected parents
   - Autosomal recessive: need TWO hits (homozygous or compound heterozygous); check carrier parents
   - X-linked recessive: hemizygous males affected; carrier females usually unaffected
   - Mitochondrial: maternal inheritance only; heteroplasmy complicates penetrance

2. **Allele frequency filter** -- Rare disease variants should be RARE in population:
   - Dominant diseases: allele frequency < 0.001 (1 in 1,000) in gnomAD
   - Recessive diseases: allele frequency < 0.01 (1 in 100) for carriers
   - Use gnomAD via Ensembl VEP annotation or OpenTargets variant info to check frequency
   - **LOOK UP** the actual frequency -- do not assume a variant is rare

3. **Consequence hierarchy** -- Prioritize by predicted impact:
   - Loss-of-function (frameshift, nonsense, splice-site): strongest candidates
   - Missense in conserved domain: strong if in known functional domain
   - Synonymous / intronic: usually benign unless at splice junction

4. **ClinVar vs OMIM vs gnomAD -- when to check each**:
   - **ClinVar**: "Is this specific variant known to be pathogenic?" Check review stars (>=2 stars = reliable)
   - **OMIM** (via Orphanet/GenCC): "Is this gene known to cause this disease?" Check BEFORE ClinVar
   - **gnomAD** (via VEP/OpenTargets): "Is this variant too common to cause a rare disease?" Check allele frequency

5. **Phenotype-genotype correlation** -- After identifying a candidate gene:
   - Get HPO phenotypes for the associated disease (Orphanet_get_phenotypes)
   - Check: do the patient's features match the "Very frequent" phenotypes?
   - Mismatches in core features argue AGAINST the gene being causative
   - GenCC validity level tells you how strong the gene-disease link is overall

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

Phase 0: Disambiguation (resolve to ORPHA code / HGNC symbol) -> Phase 1: Disease Characterization -> Phase 2: Phenotype Mapping (HPO) -> Phase 3: Causative Genes -> Phase 4: Gene-Disease Validity (GenCC) -> Phase 5: Pathogenic Variants (ClinVar) -> Phase 6: Epidemiology -> Phase 7: Clinical Trials -> Phase 8: Literature -> Phase 9: Report

---

## Phase 0: Disambiguation

Resolve user input to canonical Orphanet identifiers before doing anything else. Many disease names have subtypes or umbrella syndromes that will produce misleading results if you pick the wrong one.

**Orphanet_Orphanet_search_diseases**: `name` (string REQUIRED, e.g., "Marfan syndrome"), `exact` (bool, default False), `lang` (string, default "en"). Primary tool for name-to-ORPHA-code resolution. The parameter is `name` (NOT `query`). Returns multiple matches — select the exact disease, not subtypes or umbrella syndromes. "Marfan syndrome" should resolve to ORPHAcode 558, not 284993 ("Marfan syndrome and Marfan-related disorders").

**Orphanet_search_diseases**: `query` (string REQUIRED). Fallback if the primary tool returns no results.

**Orphanet_get_gene_diseases**: `gene_symbol` (string REQUIRED, e.g., "FBN1"). Use when starting from a gene. Returns all diseases associated with the gene, including association type.

Key identifier formats: disease codes are ORPHAcode integers (e.g., 558 for Marfan syndrome); gene identifiers are HGNC symbols (e.g., FBN1); phenotypes use HPO CURIE format (e.g., HP:0001519).

---

## Phase 1: Disease Characterization

**Orphanet_get_disease**: `orpha_code` (string REQUIRED, e.g., "558"). Returns the official Orphanet definition and synonym list.

**Orphanet_get_classification**: `orpha_code` (string REQUIRED). Shows which disease hierarchies include this condition (e.g., "rare genetic diseases", "rare ophthalmic disorders"). Useful for understanding what kind of rare disease this is.

**Orphanet_get_natural_history**: `orpha_code` (string REQUIRED). Returns `average_age_of_onset` and `type_of_inheritance`. Inheritance mode (autosomal dominant, X-linked recessive, etc.) is critical context for interpreting variant pathogenicity and family risk.

**Orphanet_get_icd_mapping**: `orpha_code` (string REQUIRED). Maps to ICD-10/ICD-11 for clinical coding contexts.

---

## Phase 2: Phenotype Mapping (HPO)

**Orphanet_get_phenotypes**: `orpha_code` (string REQUIRED). Returns HPO phenotypes with frequency labels and whether each is a formal diagnostic criterion.

Frequency should guide your interpretation: phenotypes marked "Very frequent (99-80%)" are core features present in nearly all patients and should be weighted heavily in differential diagnosis. "Frequent (79-30%)" are supporting features. "Occasional (29-5%)" reflect variable presentations. "Excluded (0%)" are active rule-out criteria — their presence argues against the diagnosis.

When a phenotype is marked `diagnostic_criteria: "Diagnostic criterion"`, it belongs to the formal diagnostic framework for that disease, not just a statistical association.

### OLS for ontology lookups

When you need to look up an HPO term by description or resolve a CURIE to a label, use the OLS tools. Pass `ontology="hp"` to scope to HPO, `ontology="ordo"` for Orphanet terms, `ontology="mondo"` for MONDO disease terms.

**ols_search_terms**: `query` (string REQUIRED), `ontology` (string, optional), `rows` (int, alias `size`, default 10), `exact_match` (bool, default False).

**ols_get_term_info**: `term_id` (CURIE e.g., "HP:0001519") OR `term_iri`. Prefix-based ontology inference works automatically — "HP:" routes to hp, "MONDO:" to mondo, "ORDO:" to ordo.

**ols_get_term_children** / **ols_get_term_ancestors**: `term_id` or `term_iri`, `ontology` (optional). Useful for finding parent HPO categories or broadening/narrowing a phenotype search.

---

## Phase 3: Causative Gene Discovery

**Orphanet_get_genes**: `orpha_code` (string REQUIRED, alias: `disease_id`). Returns genes with their association types and loci.

The association type is crucial. "Disease-causing germline mutation(s) in" means the gene is a confirmed cause — this is the primary diagnostic target. "Major susceptibility factor in" means risk factor with incomplete penetrance. "Candidate gene tested in" means preliminary and unconfirmed — do not report this as a causative gene without additional validation from GenCC or literature. "Modifying germline mutation in" means the gene modifies severity but does not cause the disease alone.

Do not treat all Orphanet gene associations equally. Always note the association type when reporting.

---

## Phase 4: Gene-Disease Validity Assessment

GenCC aggregates independent assessments from multiple clinical labs and curation groups. The key insight is that consensus across submitters matters more than any single classification. A single submitter at "Definitive" is weaker than three independent submitters agreeing at "Strong."

**GenCC_search_gene**: `gene_symbol` (string REQUIRED, e.g., "FBN1"). Returns all disease associations with classifications and submitters.

**GenCC_search_disease**: `disease` (string REQUIRED, e.g., "Marfan syndrome"). Note: the parameter is `disease` (NOT `disease_title`). Returns all gene associations for the disease with validity levels.

Classification levels from strongest to weakest: Definitive > Strong > Moderate > Limited > No Known Disease Relationship > Disputed > Refuted > Animal Model Only. "Disputed" means conflicting evidence exists — do not report this as a valid association. "Refuted" means a previously claimed association was disproven.

When reporting GenCC results, always note: (1) the highest classification, (2) how many submitters agree, and (3) whether any submitters disagree. Three or more submitters at "Definitive" is very high confidence. A single submitter should always be flagged as requiring independent validation.

---

## Phase 5: Pathogenic Variant Lookup

**ClinVar_search_variants**: `gene` (string, gene symbol), `condition` (string, disease name), `variant_id` (string), `clinical_significance` (string), `max_results` (int, default 20, alias `limit`). At least one of `gene`, `condition`, or `variant_id` is required. The primary parameter is `gene` (NOT `query`).

Combine `gene` + `condition` for disease-specific variant lookup. This narrows results to variants classified in the context of the specific disease, which matters for genes associated with multiple conditions.

Review status reflects confidence in the classification. "Practice guideline" (4 stars) and "reviewed by expert panel" (3 stars) represent the highest-confidence assertions. "Criteria provided, multiple submitters, no conflicts" (2 stars) is good. "Criteria provided, single submitter" (1 star) is moderate. "No assertion criteria provided" (0 stars) should be treated with caution.

Do not report VUS (Variant of Uncertain Significance) as disease-causing. VUS means the evidence is insufficient to classify — it is not "probably pathogenic." The default returns 20 variants; check `total_count` to understand the full scope of pathogenic variants in the gene.

**ClinVar_get_variant_details**: `variant_id` (REQUIRED). Retrieves full details for a specific ClinVar variant.

**ClinVar_get_clinical_significance**: `variant_id` (REQUIRED). Returns the clinical significance summary with submitter count.

---

## Phase 6: Epidemiology

**Orphanet_get_epidemiology**: `orpha_code` (string REQUIRED). Returns prevalence estimates by type (point prevalence, annual incidence, birth prevalence), geographic region, and source.

Prevalence below 1 in 2,000 is the EU/US regulatory threshold for "rare disease." Below 1 in 100,000 is uncommon. Below 1 in 1,000,000 is ultra-rare. These distinctions matter for clinical trial feasibility, natural history study design, and regulatory pathway discussions.

Prevalence data can vary significantly by geography (founder effects, consanguinity rates, ascertainment) and may be outdated. Always report the geographic scope and source year when citing prevalence figures.

**Orphanet_get_natural_history**: (also useful in Phase 1) Returns age of onset and inheritance pattern — essential context for patient counseling and family risk.

---

## Phase 6b: Metabolite-Disease Context (IEM)

For inborn errors of metabolism (IEM), link metabolite accumulation to disease using HMDB.

**HMDB_search**: `query` (string REQUIRED, compound name or formula). Find HMDB IDs for metabolites.

**HMDB_get_metabolite**: `hmdb_id` (string) OR `compound_name` (string). Returns cross-database IDs (KEGG, ChEBI, PubChem) for downstream pathway analysis.

**HMDB_get_diseases**: `hmdb_id` (string) OR `compound_name` (string). Returns disease associations backed by CTD. Use to confirm which diseases are linked to metabolite accumulation.

---

## Phase 7: Clinical Trials

**search_clinical_trials**: `query_term` (string REQUIRED), `condition` (string, optional), `intervention` (string, optional), `pageSize` (int, optional, default 10).

For rare diseases, even observational natural history studies are valuable — they characterize disease progression and identify biomarkers. Prioritize recruiting trials, then active-not-recruiting, then recently completed. Phase 2-3 trials are most clinically relevant. Check `len(studies) > 0` rather than `total_count` — the latter can be None even when studies exist.

---

## Phase 8: Literature

**EuropePMC_search_articles**: `query` (string REQUIRED, e.g., "Marfan syndrome genetics"), `limit` (int, optional, default 10).

Use disease name + "genetics" or "gene" for genetic literature. For variant-specific evidence, add the gene symbol and variant. For genotype-phenotype correlations, add "genotype phenotype." Returns most recent articles first. HTML entities may appear in titles — strip for display.

---

## Evidence Grading

When synthesizing across phases, grade your confidence:

**Tier 1 (Definitive)**: GenCC Definitive from multiple submitters + ClinVar expert-reviewed pathogenic variants + Orphanet "Disease-causing germline mutation(s) in" assessed association. Example: FBN1 causing Marfan syndrome.

**Tier 2 (Strong)**: GenCC Strong + ClinVar single-submitter pathogenic variants + Orphanet disease-causing. Strong but less replicated evidence.

**Tier 3 (Moderate)**: GenCC Limited or Moderate + ClinVar VUS + Orphanet candidate gene. Emerging associations requiring further validation.

**Tier 4 (Preliminary)**: Literature only, animal models, or no GenCC/ClinVar data. Genes from case studies without independent replication.

---

## Fallback Strategies

When a primary tool fails or returns no results:

- Disease lookup: try `Orphanet_search_diseases` if `Orphanet_Orphanet_search_diseases` fails
- Gene → diseases: `GenCC_search_gene` has broader coverage than `Orphanet_get_gene_diseases`
- Disease → genes: `GenCC_search_disease` as complement to `Orphanet_get_genes`
- Gene-disease validity: Orphanet AssociationType + SourceOfValidation PMIDs if GenCC has no submissions
- Pathogenic variants: EuropePMC literature search if ClinVar has no entries
- Epidemiology: literature search for prevalence studies if Orphanet data is absent

---

## Example Workflows

### Full Rare Disease Investigation (disease name input)

```
1. Orphanet_Orphanet_search_diseases(name="Marfan syndrome") -> ORPHAcode 558
2. Orphanet_get_disease(orpha_code="558") -> definition, synonyms
3. Orphanet_get_phenotypes(orpha_code="558") -> HPO phenotypes with frequencies
4. Orphanet_get_genes(orpha_code="558") -> FBN1 (disease-causing), TGFBR1, TGFBR2
5. GenCC_search_gene(gene_symbol="FBN1") -> Definitive from ClinGen, Ambry, Invitae
6. ClinVar_search_variants(gene="FBN1", clinical_significance="Pathogenic", max_results=50)
7. Orphanet_get_epidemiology(orpha_code="558") -> 1-5/10,000 worldwide
8. search_clinical_trials(query_term="Marfan syndrome", pageSize=10)
9. EuropePMC_search_articles(query="Marfan syndrome genetics", limit=5)
```

### Gene-First Investigation (starting from a gene)

```
1. Orphanet_get_gene_diseases(gene_symbol="FBN1") -> all associated diseases
2. GenCC_search_gene(gene_symbol="FBN1") -> validity classifications per disease
3. For top disease: Orphanet_get_phenotypes + Orphanet_get_epidemiology
4. ClinVar_search_variants(gene="FBN1", clinical_significance="Pathogenic")
```

---

## Common Mistakes to Avoid

- Using `disease_title` in GenCC_search_disease: use `disease` instead
- Using `query` in Orphanet_Orphanet_search_diseases: use `name`
- Using `query` in ClinVar_search_variants: use `gene`, `condition`, or `variant_id`
- Assuming the first Orphanet search result is the right disease: always check for subtypes
- Treating ClinVar VUS as pathogenic evidence
- Treating Orphanet "Candidate gene tested in" as a confirmed causative gene
- Ignoring GenCC submitter count: single-submitter Definitive is weaker than multi-submitter consensus

---

## Limitations

- Orphanet covers rare diseases only; common diseases may have minimal entries
- ClinVar returns up to 20 variants by default; paginated retrieval is limited
- GenCC submissions may lag behind the latest literature
- Some ultra-rare diseases have no GenCC submissions, no ClinVar variants, and no clinical trials

---

## Completeness Checklist

- [ ] Disease resolved to correct ORPHA code (not a subtype or umbrella)
- [ ] Causative genes identified with association types; GenCC validity assessed
- [ ] ClinVar variants checked with review status; VUS NOT reported as pathogenic
- [ ] Inheritance pattern checked BEFORE interpreting variants
- [ ] Epidemiology, clinical trials, and literature included
- [ ] Evidence graded by tier (T1-T4)
