---
name: tooluniverse-cancer-variant-interpretation
description: Provide comprehensive clinical interpretation of somatic mutations in cancer. Given a gene symbol + variant (e.g., EGFR L858R, BRAF V600E) and optional cancer type, performs multi-database analysis covering clinical evidence (CIViC), mutation prevalence (cBioPortal), therapeutic associations (OpenTargets, ChEMBL, FDA), resistance mechanisms, clinical trials, prognostic impact, and pathway context. Generates an evidence-graded markdown report with actionable recommendations for precision oncology. Use when oncologists, molecular tumor boards, or researchers ask about treatment options for specific cancer mutations, resistance mechanisms, or clinical trial matching.
---

# Cancer Variant Interpretation for Precision Oncology

Comprehensive clinical interpretation of somatic mutations in cancer. Transforms a gene + variant input into an actionable precision oncology report covering clinical evidence, therapeutic options, resistance mechanisms, clinical trials, and prognostic implications.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Evidence-graded** - Every recommendation has an evidence tier (T1-T4)
3. **Actionable output** - Prioritized treatment options, not data dumps
4. **Clinical focus** - Answer "what should we treat with?" not "what databases exist?"
5. **Resistance-aware** - Always check for known resistance mechanisms
6. **Cancer-type specific** - Tailor all recommendations to the patient's cancer type when provided
7. **Source-referenced** - Every statement must cite the tool/database source
8. **English-first queries** - Always use English terms in tool calls (gene names, drug names, cancer types), even if the user writes in another language. Respond in the user's language

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks:
- "What treatments exist for EGFR L858R in lung cancer?"
- "Patient has BRAF V600E melanoma - what are the options?"
- "Is KRAS G12C targetable?"
- "Patient progressed on osimertinib - what's next?"
- "What clinical trials are available for PIK3CA E545K?"
- "Interpret this somatic mutation: TP53 R273H"

---

## Input Parsing

**Required**: Gene symbol + variant notation (e.g., "EGFR L858R", "BRAF p.V600E", "EML4-ALK fusion", "HER2 amplification")
**Optional**: Cancer type (improves specificity)

Parse the gene symbol and variant separately. For fusions, use the kinase partner as the primary gene. For amplifications/deletions, use the gene name directly. Normalize common aliases: HER2 -> ERBB2, PD-L1 -> CD274, VEGF -> VEGFA.

---

## Phase 0: Tool Parameter Verification (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters.

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | `ensemblId` (camelCase) |
| `OpenTargets_get_drug_chembId_by_generic_name` | `genericName` | `drugName` |
| `OpenTargets_target_disease_evidence` | `ensemblID` | `ensemblId` + `efoId` |
| `MyGene_query_genes` | `q` | `query` |
| `search_clinical_trials` | `disease`, `biomarker` | `condition`, `query_term` (required) |
| `civic_get_variants_by_gene` | `gene_symbol` | `gene_id` (CIViC numeric ID) |
| `drugbank_*` | any 3 params | ALL 4 required: `query`, `case_sensitive`, `exact_match`, `limit` |
| `ChEMBL_get_drug_mechanisms` | `chembl_id` | `drug_chembl_id__exact` |
| `ensembl_lookup_gene` | no species | `species='homo_sapiens'` is REQUIRED |

---

## Workflow Overview

```
Input: Gene symbol + Variant notation + Optional cancer type

Phase 1: Gene Disambiguation & ID Resolution
  - Resolve gene to Ensembl ID, UniProt accession, Entrez ID
  - Get gene function, pathways, protein domains
  - Identify cancer type EFO ID (if cancer type provided)

Phase 2: Clinical Variant Evidence (CIViC)
  - Find gene in CIViC (via Entrez ID matching)
  - Get all variants for the gene, match specific variant
  - Retrieve evidence items (predictive, prognostic, diagnostic)

Phase 3: Mutation Prevalence (cBioPortal)
  - Frequency across cancer studies
  - Co-occurring mutations, cancer type distribution

Phase 4: Therapeutic Associations (OpenTargets + ChEMBL + FDA + DrugBank)
  - FDA-approved targeted therapies
  - Clinical trial drugs (phase 2-3), drug mechanisms
  - Combination therapies

Phase 5: Resistance Mechanisms
  - Known resistance variants (CIViC, literature)
  - Bypass pathway analysis (Reactome)

Phase 6: Clinical Trials
  - Active trials recruiting for this mutation
  - Trial phase, status, eligibility

Phase 7: Prognostic Impact & Pathway Context
  - Survival associations (literature)
  - Pathway context (Reactome), Expression data (GTEx)

Phase 8: Report Synthesis
  - Executive summary, clinical actionability score
  - Treatment recommendations (prioritized), completeness checklist
```

For detailed code snippets and API call patterns for each phase, see `ANALYSIS_DETAILS.md`.

---

## Clinical Reasoning Strategies

### Driver vs Passenger Reasoning

Not every mutation in a tumor is driving the cancer. Before querying databases, form a hypothesis:

- **Is this gene a known oncogene or tumor suppressor?** Genes like EGFR, BRAF, KRAS, TP53, PIK3CA are well-established cancer drivers. A mutation in one of these warrants deep investigation. A mutation in a gene with no known cancer role is likely a passenger.
- **Is this specific mutation recurrent across tumors (hotspot)?** Use cBioPortal to check. A mutation seen in hundreds of independent tumors (e.g., BRAF V600E) is almost certainly a driver. A unique, never-before-seen missense in the same gene is less certain.
- **What is the predicted functional impact?** Truncating mutations (nonsense, frameshift) in tumor suppressors are likely loss-of-function drivers. Missense mutations in oncogenes at known hotspot residues are likely gain-of-function drivers.
- **Conclusion pattern**: A recurrent mutation in a known driver gene is likely actionable. A unique mutation in a gene not associated with cancer is likely a passenger. State your assessment and the reasoning behind it.

### Actionability Reasoning

Actionable means a therapy exists that targets this alteration. Think in tiers based on evidence strength:

- **Tier 1**: FDA-approved drug for this mutation in this cancer type. The standard of care — recommend confidently. Example reasoning: "CIViC returns Level A evidence, FDA label confirms indication."
- **Tier 2**: FDA-approved for this mutation in a different cancer type, or strong clinical trial evidence (phase 2-3) in this cancer type. Reasonable to consider, especially under tumor-agnostic approvals or with molecular tumor board discussion.
- **Tier 3**: Preclinical evidence only — cell line data, animal models, or case reports. May justify clinical trial enrollment but not off-label use.
- **Tier 4**: Biological rationale but no direct evidence — the mutation is in a druggable pathway, or a structurally similar mutation responds to therapy. Hypothesis-generating only.

When synthesizing, state the tier and explain WHY you assigned it based on the evidence you found, not just which database returned a hit.

### Resistance Reasoning

If the patient has already been treated, ask: could this mutation be a resistance mechanism?

- **On-target resistance**: Mutations in the drug target gene itself that restore signaling despite drug binding. These typically emerge at the drug-binding site (e.g., EGFR T790M after erlotinib, EGFR C797S after osimertinib, ABL T315I after imatinib).
- **Bypass pathway activation**: Mutations in parallel signaling pathways that render the target irrelevant (e.g., MET amplification bypassing EGFR inhibition, BRAF activation bypassing MEK inhibition).
- **Phenotypic transformation**: Lineage changes (e.g., small cell transformation in EGFR-mutant lung cancer) that eliminate dependence on the original driver.
- **Timing matters**: If the mutation was detected AFTER treatment, it is more likely a resistance mechanism than if it was present at diagnosis.

### When to Use Which Tool

Form your clinical hypothesis FIRST based on gene function and mutation type, THEN use tools to validate:

- **CIViC** (`civic_search_genes`, `civic_get_variants_by_gene`): Your primary source for clinical evidence. Returns curated evidence items with evidence levels, clinical significance, and associated therapies. Start here for any variant with potential clinical relevance.
- **cBioPortal** (`cBioPortal_get_mutations`): Use to assess mutation prevalence — is this a hotspot? How common is it across cancer types? This informs your driver vs passenger assessment.
- **OpenTargets** (`OpenTargets_get_associated_drugs_by_target_ensemblID`): Use for actionability — what drugs target this gene? Cross-reference with CIViC evidence to assign tiers.
- **PubMed** (`PubMed_search_articles`): Use when CIViC lacks entries for your variant, or to find resistance mechanism reports and recent clinical trial results.
- **ClinicalTrials.gov** (`search_clinical_trials`): Use after establishing the variant is potentially actionable, to find enrollment opportunities.

---

## Tool Reference (Verified Parameters)

### Gene Resolution

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `MyGene_query_genes` | `query`, `species` | `hits[].ensembl.gene`, `.entrezgene`, `.symbol` |
| `UniProt_search` | `query`, `organism`, `limit` | `results[].accession` |
| `OpenTargets_get_target_id_description_by_name` | `targetName` | `data.search.hits[].id` |
| `ensembl_lookup_gene` | `gene_id`, `species` (REQUIRED) | `data.id`, `.version` |

### Clinical Evidence

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `civic_search_genes` | `query`, `limit` | `data.genes.nodes[].id`, `.entrezId` |
| `civic_get_variants_by_gene` | `gene_id` (CIViC numeric) | `data.gene.variants.nodes[]` |
| `civic_get_variant` | `variant_id` | `data.variant` |

### Drug Information

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | `data.target.drugAndClinicalCandidates.rows[]` |
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | `results[].indications_and_usage` |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL required) | `results[]` |

### Mutation Prevalence

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `cBioPortal_get_mutations` | `study_id`, `gene_list` | `data[].proteinChange` |
| `cBioPortal_get_cancer_studies` | `limit` | `[].studyId`, `.cancerTypeId` |

### Clinical Trials & Literature

| Tool | Key Parameters | Response Key Fields |
|------|---------------|-------------------|
| `search_clinical_trials` | `query_term` (required), `condition` | `studies[]` |
| `PubMed_search_articles` | `query`, `limit`, `include_abstract` | Returns **list** of dicts (NOT wrapped) |
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt accession) | Pathway mappings |
| `GTEx_get_median_gene_expression` | `gencode_id`, `operation="median"` | Expression by tissue |

---

## Fallback Strategy

When a primary tool returns no results, fall back rather than reporting "no data found":
- **CIViC empty** -> search PubMed for "[gene] [variant] clinical evidence"
- **OpenTargets no drugs** -> try ChEMBL drug search by target
- **cBioPortal specific study empty** -> try pan-cancer study (msk_impact_2017 or similar)
- **Reactome no pathways** -> use UniProt function annotation for pathway context
