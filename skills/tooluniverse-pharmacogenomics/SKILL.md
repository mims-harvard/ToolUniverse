---
name: tooluniverse-pharmacogenomics
description: Guide pharmacogenomics (PGx) research -- drug-gene interaction lookup, CPIC guideline retrieval, variant-drug annotation, allele function status, FDA biomarker labeling, and clinical dosing recommendations. Covers the full CPIC-to-PharmGKB-to-clinical-recommendation workflow. Use when users ask about pharmacogenomics, drug-gene interactions, CPIC guidelines, genotype-guided dosing, PGx biomarkers, CYP enzyme phenotypes, or star allele interpretation.
---

# Pharmacogenomics (PGx) Research Skill

Systematic PGx analysis: resolve gene-drug pairs, retrieve CPIC dosing guidelines, annotate alleles and variants with PharmGKB, check FDA PGx biomarker labeling, and generate evidence-graded clinical recommendations.

## When to Use

- "What CPIC guidelines exist for CYP2D6?"
- "Get dosing recommendations for codeine based on CYP2D6 poor metabolizer status"
- "Which drugs have FDA pharmacogenomic biomarkers for CYP2C19?"
- "Find PharmGKB clinical annotations for rs1799853"
- "Is this patient's CYP2D6 genotype relevant to tamoxifen dosing?"
- "What is the functional status of CYP2D6*4?"
- "List all CPIC level A gene-drug pairs for CYP2D6"

## Workflow Overview

```
Input (gene/drug/variant/phenotype)
  |
  v
Phase 0: Disambiguation (resolve gene symbols, drug names, rsIDs)
  |
  v
Phase 1: Gene-Drug Pair Identification (CPIC pairs + evidence levels)
  |
  v
Phase 2: Guideline & Dosing Retrieval (CPIC recommendations + PharmGKB)
  |
  v
Phase 3: Allele & Variant Annotation (star alleles, function, activity scores)
  |
  v
Phase 4: FDA Biomarker Labeling (regulatory PGx status)
  |
  v
Phase 5: Cross-Database Enrichment (EpiGraphDB, DGIdb, OpenTargets PGx)
  |
  v
Phase 6: Report (evidence-graded clinical summary)
```

---

## Phase 0: Disambiguation

Resolve user input to canonical identifiers before querying PGx databases.

**PharmGKB_search_genes**: `query` (string REQUIRED, e.g., "CYP2D6"). Returns `{status, data: [{id, symbol, name}]}`.
- Use to get PharmGKB gene accession ID (e.g., "PA128" for CYP2D6).

**PharmGKB_search_drugs**: `query` (string REQUIRED, e.g., "codeine"). Returns `{status, data: [{id, name, types}]}`.
- Use to get PharmGKB chemical ID (e.g., "PA449088" for codeine).

**PharmGKB_search_variants**: `query` (string REQUIRED, rsID e.g., "rs1799853"). Returns `{status, data: [{id, symbol, changeClassification, clinicalSignificance}]}`.
- Use to resolve rsIDs and find PharmGKB annotation IDs.

**CPIC_get_drug_info**: `name` (string REQUIRED, lowercase, e.g., "codeine"). Returns drug identifiers including `drugid`, `rxnormid`, `drugbankid`, `atcid`, `guidelineid`, and `flowchart` URL.
- Also resolves drug names: can be used to find the `guidelineid` directly from a drug name.

**CPIC_get_gene_info**: `symbol` (string REQUIRED, e.g., "CYP2D6"). Returns gene coordinates, PharmGKB/HGNC/Ensembl IDs, `lookupmethod` (ACTIVITY_SCORE or PHENOTYPE), and allele frequency methodology.

---

## Phase 1: Identify Gene-Drug Pairs

**CPIC_search_gene_drug_pairs**: `gene_symbol` (string), `cpiclevel` ("A"/"B"/"C"/"D"), `limit` (int, default 50). Returns `{status, data: [{genesymbol, drugid, cpiclevel, guidelineid, pgxtesting, clinpgxlevel, usedforrecommendation}]}`.
- Primary tool for filtering by evidence level. CPIC levels: A = strongest/actionable, B = moderate, C = informational, D = insufficient.
- **PostgREST auto-normalization**: Accepts plain gene symbols (e.g., "CYP2D6") -- the tool auto-prepends `eq.` prefix.
- Also accepts aliases: `gene` or `gene_symbol` both resolve to `genesymbol`.

**CPIC_get_gene_drug_pairs**: `genesymbol` (string REQUIRED). Returns ALL pairs for one gene including `drug: {name}`, `citations`, `guidelineid`.
- Returns drug names in response (unlike search which returns RxNorm IDs only).

**CPIC_list_drugs**: No params. Returns all drugs with guideline IDs. Use for browsing.

**CPIC_list_pgx_genes**: No params. Returns all PGx genes curated by CPIC with `symbol`, `lookupmethod`, `ensemblid`.

**EpiGraphDB_get_gene_drug_associations**: `gene_name` (string REQUIRED, e.g., "CYP2D6"). Returns `{status, data: {gene_drug_associations: [{gene, drug, source, pharmgkb_evidence, cpic_level, pgx_on_fda_label, guideline}]}}`.
- Aggregates CPIC + PharmGKB evidence with FDA label status in one call. Good for quick overview.

### Key Guideline IDs (verified)

| Guideline ID | Gene(s) | Drug(s) | clinpgxid |
|---|---|---|---|
| 100409 | CFTR | Ivacaftor | PA166251449 |
| 100411 | CYP2C19 | Clopidogrel | PA166251443 |
| 100412 | HLA-B, CYP2C9 | Phenytoin/Fosphenytoin | PA166251461 |
| 100414 | CYP2D6, CYP2C19 | Tricyclic Antidepressants | PA166251445 |
| 100415 | CYP2D6 | Tamoxifen | PA166251458 |
| 100416 | CYP2D6, OPRM1, COMT | Opioids (Codeine, Tramadol, Hydrocodone) | PA166251454 |
| 100421 | HLA-B | Abacavir | PA166251444 |
| 100422 | HLA-B | Allopurinol | PA166251446 |
| 100425 | CYP2C9, VKORC1, CYP4F2 | Warfarin | PA166251465 |
| 104243 | CYP2D6 | Atomoxetine | PA166251459 |

---

## Phase 2: Retrieve Dosing Guidelines

### Recommended Workflow: Drug-Name-First Approach (CPICGetRecommendationsTool)

The fastest path from a drug name to dosing recommendations uses the **auto-resolving** `CPIC_get_recommendations` tool:

```
# PREFERRED: Pass drug name directly -- auto-resolves to guideline_id
CPIC_get_recommendations(drug="codeine", limit=50)
  -> Auto-resolves codeine -> guideline_id=100416 via CPIC /drug endpoint
  -> Filters to codeine-specific recommendations within multi-drug guidelines
  -> Returns phenotype-specific dosing recommendations
```

The tool accepts EITHER:
- `guideline_id` (integer) -- direct guideline lookup
- `drug` or `drug_name` (string) -- auto-resolved to guideline_id via CPIC API

**This eliminates the need for a separate CPIC_get_drug_info call.** The tool also filters multi-drug guidelines (e.g., CYP2D6 opioid guideline covers codeine + tramadol) to the specific requested drug using RxNorm ID matching.

### Alternative: Two-Step Approach (still valid)

```
Step 1: CPIC_get_drug_info(name="codeine")
  -> Extract guidelineid (e.g., 100416)

Step 2: CPIC_get_recommendations(guideline_id=100416, limit=50)
  -> Filter by phenotype for patient-specific recommendation
```

### Tool Reference

**CPIC_get_recommendations** (CPICGetRecommendationsTool): `guideline_id` (integer, OR `drug`/`drug_name` string for auto-resolution), `limit` (int, default 50), `offset` (int). Returns `{status, data: {guideline_id, recommendations: [{drugrecommendation, classification, phenotypes, implications, activityscore, lookupkey, population, drug: {name}}], count}}`.
- `classification`: "Strong", "Moderate", or "Optional" (CPIC recommendation strength).
- `phenotypes`: Maps gene -> metabolizer phenotype (e.g., `{"CYP2D6": "Poor Metabolizer"}`).
- `activityscore`: Maps gene -> activity score (e.g., `{"CYP2D6": "0.0"}`).
- **Drug name auto-resolution**: Pass `drug="codeine"` and the tool calls CPIC `/drug` API with ilike matching to find the guideline_id automatically.
- **Multi-drug filtering**: When auto-resolving, also extracts RxNorm ID to filter within multi-drug guidelines.

**CPIC_get_drug_info**: `name` (string REQUIRED, lowercase, e.g., "codeine"). Returns `{status, data: [{drugid, guidelineid, flowchart, rxnormid, drugbankid}]}`.
- Key shortcut: returns `guidelineid` directly. Still useful for extracting DrugBank/ATC IDs.

**PharmGKB_get_dosing_guidelines**: `guideline_id` (string REQUIRED -- use `clinpgxid` from CPIC_list_guidelines, e.g., "PA166251445"). Returns `{status, data: {id, name, level, literature: [{title, crossReferences}], link}}`.
- Provides CPIC guideline metadata, literature citations, and link to full guideline.

**CPIC_list_guidelines**: `gene` (string, optional), `drug` (string, optional). Returns `{status, data: [{id, name, url, genes, clinpgxid}]}`. Returns all ~29 guidelines; supports built-in filtering by gene/drug.
- Use this to discover `clinpgxid` values for PharmGKB_get_dosing_guidelines.

> **Note**: `PharmGKB_search_clinical_annotations` is **not available** in this ToolUniverse instance. To discover PharmGKB annotation IDs, use `PharmGKB_search_variants(query=rsID)` to get the variant's PharmGKB page, or use `PharmGKB_get_clinical_annotations(annotation_id=...)` with a known ID from the PharmGKB website.

### Gotchas

- **Warfarin** (guideline 100425): Algorithm-based dosing; `CPIC_get_recommendations` returns 0 rows. Direct users to CPIC website or PharmGKB.
- **PharmGKB guideline linking**: Use `clinpgxid` (e.g., "PA166251445"), NOT `pharmgkbid` (old format returns 404).
- **Multi-gene guidelines**: TCA guideline (100414) covers both CYP2D6 and CYP2C19; recommendations have phenotype combinations.
- **Drug name case**: `CPIC_get_drug_info` requires lowercase. `CPIC_get_recommendations` with `drug=` uses ilike matching (case-insensitive).
- **CPIC_get_recommendations returns wrapped data**: Response is `{status, data: {guideline_id, recommendations: [...], count}}` -- recommendations are nested under `data.recommendations`.

---

## Phase 3: Allele & Variant Annotation

**CPIC_get_alleles**: `genesymbol` (string REQUIRED), `limit` (int, default 50). Returns `{status, data: [{name, clinicalfunctionalstatus, activityvalue, functionalstatus}]}`.
- Use `clinicalfunctionalstatus` (not `functionalstatus` which may be null). Values: "Normal function", "Decreased function", "No function", "Increased function", "Uncertain function", "Unknown function".
- `activityvalue`: numeric string (e.g., "1.0", "0.5", "0.0") or "n/a".

**PharmGKB_search_variants**: `query` (string REQUIRED, rsID). Returns variant classification and clinical significance.

**PharmGKB_get_clinical_annotations**: `annotation_id` (string REQUIRED, e.g., "1447954390"). Returns `{status, data: {accessionId, allelePhenotypes: [{allele, phenotype, limitedEvidence}], levelOfEvidence: {term}}}`.
- REQUIRES annotation_id -- cannot query by gene/drug directly. Discover IDs via `PharmGKB_search_variants(query=rsID)` or from the PharmGKB website.
- `levelOfEvidence.term`: "1A", "1B", "2A", "2B", "3", "4" (PharmGKB evidence levels).

**PharmGKB_get_gene_details**: `gene_id` (string REQUIRED, PharmGKB accession e.g., "PA128"). Returns detailed gene info including allele definition files, VIP citations.

**PharmGKB_get_drug_details**: `drug_id` (string REQUIRED, PharmGKB chemical ID e.g., "PA449088"). Returns drug metadata including SMILES, InChI, type (Drug/Prodrug).

**OpenTargets_drug_pharmacogenomics_data**: `chemblId` (string REQUIRED, e.g., "CHEMBL1201560"), `size` (int). Returns PGx variant data from OpenTargets including variant consequences and drug associations.
- Queries by drug (ChEMBL ID), not by gene. Use when you have a ChEMBL ID and want PGx variant annotations from OpenTargets.

### Activity Score Interpretation (CYP2D6)

| Activity Score | Phenotype | Clinical Impact |
|---|---|---|
| >=3.0 | Ultrarapid Metabolizer | Increased metabolism; risk of toxicity (prodrugs) or treatment failure |
| 1.25-2.25 | Normal Metabolizer | Standard dosing |
| 0.25-1.0 | Intermediate Metabolizer | Reduced metabolism; consider dose reduction |
| 0.0 | Poor Metabolizer | Absent/minimal metabolism; avoid prodrugs, reduce active drug dose |

---

## Phase 4: FDA Biomarker Labeling

**fda_pharmacogenomic_biomarkers**: `drug_name` (string, optional), `biomarker` (string, optional, e.g., "CYP2D6"), `limit` (integer, default 10). Returns `{status, count, shown, results: [{Drug, TherapeuticArea, Biomarker, LabelingSection}]}`.
- ALWAYS pass `limit=1000` for complete results (default is 10).
- `LabelingSection` values: "Dosage and Administration", "Clinical Pharmacology", "Precautions", "Use in Specific Populations", "Boxed Warning", "Contraindications".
- Can query by drug, biomarker, or both.
- Not all drugs have entries (e.g., simvastatin absent for SLCO1B1; use rosuvastatin for SLCO1B1 PGx testing).

**FDA_get_pharmacogenomics_info_by_drug_name**: `drug_name` (string REQUIRED). Returns FDA label PGx sections with brand/generic names. Good for finding PGx labeling text in actual FDA labels.

### FDA PGx Classification

| Label Section | Clinical Actionability |
|---|---|
| Boxed Warning / Contraindications | Highest -- testing may be required |
| Dosage and Administration | Direct dosing guidance based on genotype |
| Use in Specific Populations | Population-specific PGx considerations |
| Clinical Pharmacology | Informational -- PK/PD impact described |
| Precautions | General awareness of PGx relevance |

---

## Phase 5: Cross-Database Enrichment

**DGIdb_get_drug_gene_interactions**: `genes` (array of strings REQUIRED, e.g., `["CYP2D6"]`), `interaction_types` (array, optional), `interaction_sources` (array, optional). Returns drug-gene interactions with sources.
- Broader coverage than CPIC; includes non-PGx interactions.
- Client-side filtering applied for `interaction_types` and `sources` parameters.

**DGIdb_get_gene_druggability**: `genes` (array of strings REQUIRED). Returns `{status, data: {data: {genes: {nodes: [{name, geneCategories}]}}}}`.
- Returns gene categories (e.g., "CLINICALLY ACTIONABLE", "DRUGGABLE GENOME").

**PharmGKB_get_dosing_guidelines**: (also in Phase 2) Provides DPWG (Dutch Pharmacogenetics Working Group) guidelines alongside CPIC.

**OpenTargets_drug_pharmacogenomics_data**: `chemblId` (string REQUIRED), `size` (int). Returns PGx variant annotations from the OpenTargets platform.
- Complements CPIC data with additional variant-level PGx evidence.

### Adverse Event Signal Detection for PGx-Relevant Drugs

**FAERS_filter_serious_events**: `drug_name` (string REQUIRED), `seriousness_type` (string: "all"/"death"/"hospitalization"/"disability"/"life_threatening"), `adverse_event` (string, optional -- filters to reports containing this specific reaction term). Returns `{status, data: {drug_name, seriousness_type, total_serious_events, top_serious_reactions: [{reaction, count}]}}`.
- Use to identify serious adverse events associated with PGx-relevant drugs (e.g., codeine respiratory depression in CYP2D6 ultrarapid metabolizers).
- The `adverse_event` parameter restricts results to reports containing that reaction, enabling targeted signal detection.

```python
# Example: Serious respiratory depression events for codeine
result = tu.tools.FAERS_filter_serious_events(
    drug_name="codeine", seriousness_type="all", adverse_event="respiratory depression"
)
# result["data"]["total_serious_events"] -> 68
```

### Optional Tools (require API keys or may be unavailable)

- **DisGeNET_get_vda**: Variant-disease associations (requires DISGENET_API_KEY).

---

## Evidence Grading

### CPIC Evidence Levels

| Level | Description | Action |
|---|---|---|
| A | Strong evidence, clinical guidelines exist | Prescribing action recommended |
| B | Moderate evidence | Consider PGx-guided changes |
| C | Limited evidence | Informational only |
| D | Insufficient evidence | No clinical action |

### PharmGKB Levels of Evidence

| Level | Description |
|---|---|
| 1A | Annotation in a CPIC or DPWG guideline, or implemented in a major health system |
| 1B | Well-replicated clinical evidence |
| 2A | Moderate clinical evidence |
| 2B | Limited clinical evidence |
| 3 | Low-level, annotation-based evidence |
| 4 | Case report or preclinical only |

### CPIC Recommendation Strength

| Classification | Meaning |
|---|---|
| Strong | High confidence; benefits clearly outweigh risks |
| Moderate | Moderate confidence; benefits likely outweigh risks |
| Optional | Weak evidence; clinical judgment should guide |

---

## Tool Parameter Quick Reference

| Tool | Key Params | Return Format |
|---|---|---|
| CPIC_list_guidelines | (none) | `{status, data: [{id, name, genes, clinpgxid}]}` |
| CPIC_get_recommendations | `guideline_id` (int) OR `drug`/`drug_name` (string) | `{status, data: {guideline_id, recommendations: [...], count}}` |
| CPIC_search_gene_drug_pairs | `gene_symbol`/`gene`, `cpiclevel`, `limit` | `{status, data: [{genesymbol, cpiclevel, guidelineid}]}` |
| CPIC_get_gene_drug_pairs | `genesymbol` | `{status, data: [{cpiclevel, drug:{name}, guidelineid}]}` |
| CPIC_get_alleles | `genesymbol`, `limit` | `{status, data: [{name, clinicalfunctionalstatus, activityvalue}]}` |
| CPIC_get_gene_info | `symbol` | `{status, data: [{symbol, ensemblid, lookupmethod}]}` |
| CPIC_get_drug_info | `name` (lowercase) | `{status, data: [{drugid, guidelineid, flowchart}]}` |
| CPIC_list_drugs | (none) | `{status, data: [{name, guidelineid}]}` |
| CPIC_list_pgx_genes | (none) | `{status, data: [{symbol, lookupmethod}]}` |
| PharmGKB_search_genes | `query` | `{status, data: [{id, symbol, name}]}` |
| PharmGKB_search_drugs | `query` | `{status, data: [{id, name, types}]}` |
| PharmGKB_search_variants | `query` (rsID) | `{status, data: [{id, symbol, clinicalSignificance}]}` |
| ~~PharmGKB_search_clinical_annotations~~ | NOT AVAILABLE | Use PharmGKB_search_variants(query=rsID) instead |
| PharmGKB_get_clinical_annotations | `annotation_id` | `{status, data: {allelePhenotypes, levelOfEvidence}}` |
| PharmGKB_get_dosing_guidelines | `guideline_id` (clinpgxid string) | `{status, data: {name, level, literature}}` |
| PharmGKB_get_gene_details | `gene_id` (accession) | `{status, data: {symbol, name, alleleType}}` |
| PharmGKB_get_drug_details | `drug_id` (chemical ID) | `{status, data: {name, smiles, types}}` |
| fda_pharmacogenomic_biomarkers | `drug_name`, `biomarker`, `limit` | `{status, count, results: [{Drug, Biomarker, LabelingSection}]}` |
| FDA_get_pharmacogenomics_info_by_drug_name | `drug_name` | FDA label PGx sections |
| EpiGraphDB_get_gene_drug_associations | `gene_name` | `{status, data: {gene_drug_associations: [...]}}` |
| DGIdb_get_drug_gene_interactions | `genes` (array) | Drug-gene interactions with sources |
| DGIdb_get_gene_druggability | `genes` (array) | Gene categories |
| OpenTargets_drug_pharmacogenomics_data | `chemblId`, `size` | PGx variant data by drug |
| FAERS_filter_serious_events | `drug_name`, `seriousness_type`, `adverse_event` (optional) | `{status, data: {total_serious_events, top_serious_reactions}}` |

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---|---|
| Using wrong params with `CPIC_list_guidelines` | Supports `gene`, `gene_symbol`, `drug`, `drug_name` filters; use them to filter server-side |
| Using `CPIC_search_gene_drug_pairs` | Tool does not exist; use `CPIC_search_gene_drug_pairs` |
| Passing string to `guideline_id` in CPIC_get_recommendations | Must be integer (e.g., 100416 not "100416") -- OR use `drug="codeine"` for auto-resolution |
| Using `pharmgkbid` in PharmGKB_get_dosing_guidelines | Use `clinpgxid` (e.g., "PA166251445") |
| Passing gene/drug to PharmGKB_get_clinical_annotations | Requires `annotation_id`; discover IDs via `PharmGKB_search_variants(query=rsID)` |
| Omitting `limit` for fda_pharmacogenomic_biomarkers | Default is 10; always pass `limit=1000` |
| Using `gene_name` for DGIdb | Param is `genes` (array), e.g., `["CYP2D6"]` |
| Using uppercase drug name in CPIC_get_drug_info | Must be lowercase (e.g., "codeine" not "Codeine") |
| Calling CPIC_get_drug_info then CPIC_get_recommendations separately | Use `CPIC_get_recommendations(drug="codeine")` for one-step resolution |
| Not using CPIC_list_guidelines to discover clinpgxid | Call it first, then pass `clinpgxid` to PharmGKB_get_dosing_guidelines |
| Accessing recommendations as `data[0].drugrecommendation` | Auto-resolve response nests under `data.recommendations` list |

---

## Fallback Strategies

- **No CPIC guideline** -> Use `PharmGKB_search_variants(query=rsID)` for variant-level annotations; check EpiGraphDB for gene-drug evidence
- **CPIC_get_recommendations returns 0 rows** -> Check if algorithm-based (warfarin); use PharmGKB_get_dosing_guidelines
- **CPIC_get_recommendations drug auto-resolve fails** -> Fall back to CPIC_get_drug_info(name=drug) + manual guideline_id extraction
- **No FDA biomarker entry** -> Check DGIdb for known interactions; check EpiGraphDB `pgx_on_fda_label` field
- **Unknown variant** -> PharmGKB_search_variants by rsID; note as uncharacterized if absent
- **Need drug name from RxNorm ID** -> Use CPIC_get_gene_drug_pairs (returns `drug: {name}`) instead of CPIC_search_gene_drug_pairs (returns only RxNorm IDs)
- **PharmGKB annotation_id unknown** -> Get annotation IDs from PharmGKB website or via `PharmGKB_search_variants(query=rsID)`
- **Need additional PGx variant data** -> Use `OpenTargets_drug_pharmacogenomics_data(chemblId=...)` with ChEMBL ID

---

## Example Workflows

### Workflow 1: CYP2D6 Poor Metabolizer Prescribed Codeine (one-step)

```
Step 1: CPIC_get_recommendations(drug="codeine", limit=50)
  -> Auto-resolves codeine -> guideline_id=100416
  -> Filters to codeine-specific recommendations (excludes tramadol)
  -> Filter for phenotypes.CYP2D6="Poor Metabolizer"
  -> Result: "Avoid codeine use. If opioid use warranted, consider non-codeine opioid."
  -> classification: "Strong"

Step 2: CPIC_get_alleles(genesymbol="CYP2D6", limit=100)
  -> Verify patient's star alleles (e.g., *4/*4 = No function + No function = AS 0.0)

Step 3: fda_pharmacogenomic_biomarkers(drug_name="codeine", limit=1000)
  -> Confirm FDA label mentions CYP2D6

Step 4: Report with CPIC level A, Strong recommendation, FDA labeling status
```

**Alternative (gene-first)**: If starting from a gene, use `CPIC_get_gene_drug_pairs(genesymbol="CYP2D6")` to find all associated drugs and their guideline IDs.

### Workflow 2: Which Drugs Are Affected by CYP2C19 Genotype?

```
Step 1: CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A")
  -> List all Level A pairs (clopidogrel, voriconazole, PPIs, SSRIs, TCAs)

Step 2: EpiGraphDB_get_gene_drug_associations(gene_name="CYP2C19")
  -> Cross-reference with PharmGKB evidence and FDA label status

Step 3: fda_pharmacogenomic_biomarkers(biomarker="CYP2C19", limit=1000)
  -> Get full FDA labeling coverage

Step 4: Summarize by evidence tier and clinical actionability
```

### Workflow 3: Variant rs1799853 Clinical Significance

```
Step 1: PharmGKB_search_variants(query="rs1799853")
  -> Returns: CYP2C9 variant, Missense, drug-response significance

Step 2: CPIC_get_alleles(genesymbol="CYP2C9", limit=100)
  -> Map variant to star allele (*2 contains rs1799853)
  -> clinicalfunctionalstatus: "Decreased function"

Step 3: CPIC_get_gene_drug_pairs(genesymbol="CYP2C9")
  -> List affected drugs (warfarin, phenytoin, NSAIDs)

Step 4: For each drug with guideline, retrieve specific dosing recommendations:
  CPIC_get_recommendations(drug="phenytoin", limit=50)
  -> Auto-resolves and returns phenotype-specific dosing
```

### Workflow 4: Quick Drug PGx Lookup (new -- drug-name-only)

```
Step 1: CPIC_get_recommendations(drug="tamoxifen", limit=50)
  -> Auto-resolves tamoxifen -> guideline_id=100415
  -> Returns all CYP2D6 phenotype recommendations

Step 2: PharmGKB_search_variants(query="rs16947")  # Use known variant rsID for CYP2D6*2
  -> Discover PharmGKB clinical annotation IDs

Step 3: fda_pharmacogenomic_biomarkers(drug_name="tamoxifen", limit=1000)
  -> FDA labeling status

Step 4: Report with dosing table by phenotype
```

---

## Drug Class Context (RxClass)

When PGx analysis involves understanding which drug class a substrate belongs to, or finding all drugs in a class that share the same metabolizing enzyme, use:

| Tool | Key Params | Use Case |
|------|-----------|----------|
| `RxClass_get_drug_classes` | `drug_name` or `rxcui`, `rela_source` | Get all class memberships (ATC, MoA, EPC, VA) for a drug |
| `RxClass_find_classes` | `query` (keyword), `class_type` | Find class IDs without knowing RxNorm CUI |
| `RxClass_get_class_members` | `class_id`, `rela_source`, `ttys="IN"` | List all drugs within a therapeutic class |

Example: find all SSRIs (class members) to advise which require CYP2D6 testing as a class note.

## FDA Substance Identification (FDAGSRS)

For canonical FDA substance identification (UNII codes, cross-references to ATC/DrugBank/CAS), use:

| Tool | Key Params | Use Case |
|------|-----------|----------|
| `FDAGSRS_search_substances` | `query` (name/UNII/InChIKey), `substance_class`, `limit` | Find UNII code and substance class for any FDA-regulated substance |
| `FDAGSRS_get_substance` | `unii` (10-char code) | Full record: all names, cross-references, structure, approval status |
| `FDAGSRS_get_structure` | `unii` | SMILES, InChIKey, MW, stereochemistry (chemical substances only) |

Example: confirm regulatory identity of a PGx-relevant drug (e.g., verify that "warfarin sodium" and "warfarin" share the same UNII) before cross-referencing in CPIC or PharmGKB.

---

## Limitations

- CPIC covers ~29 guidelines (~130 genes); many drug-gene pairs lack formal guidelines.
- PharmGKB clinical annotation IDs must be discovered (not derivable from gene/drug names alone -- use PharmGKB website or PharmGKB_search_variants for rsID-based lookup).
- Warfarin dosing requires algorithmic calculation (CPIC website), not simple table lookup.
- FDA biomarker table may lag behind current labeling changes.
- DisGeNET requires API key (DISGENET_API_KEY).
- CPIC_search_gene_drug_pairs returns RxNorm drug IDs, not drug names; use CPIC_get_gene_drug_pairs for names.
- Activity score interpretation varies by gene (CYP2D6 uses numeric scores; others may use phenotype-based lookup).
- CPIC_get_recommendations drug auto-resolution uses ilike matching -- ambiguous drug names may match multiple entries.
