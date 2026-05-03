---
name: tooluniverse-pharmacogenomics
description: Guide pharmacogenomics (PGx) research -- drug-gene interaction lookup, CPIC guideline retrieval, variant-drug annotation, allele function status, FDA biomarker labeling, and clinical dosing recommendations. Covers the full CPIC-to-PharmGKB-to-clinical-recommendation workflow. Use when users ask about pharmacogenomics, drug-gene interactions, CPIC guidelines, genotype-guided dosing, PGx biomarkers, CYP enzyme phenotypes, or star allele interpretation.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

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

### Finding Guideline IDs

Don't memorize guideline IDs. Use `CPIC_list_guidelines(gene="CYP2D6")` or `CPIC_list_guidelines(drug="codeine")` to discover them. Each result includes both the numeric `id` (for `CPIC_get_recommendations`) and the `clinpgxid` string (for `PharmGKB_get_dosing_guidelines`).

---

## Phase 2: Retrieve Dosing Guidelines

**CPIC_get_recommendations** (CPICGetRecommendationsTool): `guideline_id` (integer, OR `drug`/`drug_name` string for auto-resolution), `limit` (int, default 50), `offset` (int). Returns `{status, data: {guideline_id, recommendations: [{drugrecommendation, classification, phenotypes, implications, activityscore, lookupkey, population, drug: {name}}], count}}`.
- Preferred usage: `CPIC_get_recommendations(drug="codeine", limit=50)` — auto-resolves drug name to guideline_id via CPIC API, and filters within multi-drug guidelines (e.g., CYP2D6 opioid guideline covers codeine + tramadol) using RxNorm ID matching.
- `classification`: "Strong", "Moderate", or "Optional". `phenotypes`: maps gene → metabolizer phenotype. `activityscore`: maps gene → activity score.
- Fallback: `CPIC_get_drug_info(name="codeine")` to extract guidelineid, then `CPIC_get_recommendations(guideline_id=100416, limit=50)`.

**CPIC_get_drug_info**: `name` (string REQUIRED, lowercase, e.g., "codeine"). Returns `{status, data: [{drugid, guidelineid, flowchart, rxnormid, drugbankid}]}`.
- Key shortcut: returns `guidelineid` directly. Still useful for extracting DrugBank/ATC IDs.

**PharmGKB_get_dosing_guidelines**: `guideline_id` (string REQUIRED -- use `clinpgxid` from CPIC_list_guidelines, e.g., "PA166251445"). Returns `{status, data: {id, name, level, literature: [{title, crossReferences}], link}}`.
- Provides CPIC guideline metadata, literature citations, and link to full guideline.

**CPIC_list_guidelines**: `gene` (string, optional), `drug` (string, optional). Returns `{status, data: [{id, name, url, genes, clinpgxid}]}`. Returns all ~29 guidelines; supports built-in filtering by gene/drug.
- Use this to discover `clinpgxid` values for PharmGKB_get_dosing_guidelines.

> **Note**: `PharmGKB_get_clinical_annotations` requires an `annotation_id` (e.g., "1447954390"). To discover annotation IDs, use `PharmGKB_search_variants(query=rsID)` first, then extract annotation IDs from the results.

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

### Metabolizer Status Reasoning

A poor metabolizer has reduced or absent enzyme activity. What that means clinically depends entirely on whether the drug is active or a prodrug:

- **Active drug + poor metabolizer**: drug accumulates → toxicity risk (e.g., codeine is a prodrug — this case doesn't apply; but nortriptyline is active — PM → high plasma levels → side effects).
- **Prodrug + poor metabolizer**: less conversion to active form → reduced efficacy (e.g., codeine → morphine; clopidogrel → active thienopyridine).
- **Prodrug + ultrarapid metabolizer**: excess activation → toxicity (classic case: codeine in CYP2D6 UM → morphine accumulation → respiratory depression).

This active-vs-prodrug distinction determines the direction of clinical concern. Get it right before interpreting any metabolizer phenotype.

**Star allele reasoning**: Don't memorize allele tables. The logic is always: allele function status (normal / decreased / no function) → diplotype → predicted enzyme activity → phenotype (UM/NM/IM/PM) → clinical recommendation. Use `CPIC_get_alleles(genesymbol=...)` to look up function status for any specific allele.

---

## Phase 4: FDA Biomarker Labeling

**fda_pharmacogenomic_biomarkers**: `drug_name` (string, optional), `biomarker` (string, optional, e.g., "CYP2D6"), `limit` (integer, default 10). Returns `{status, count, shown, results: [{Drug, TherapeuticArea, Biomarker, LabelingSection}]}`.
- ALWAYS pass `limit=1000` for complete results (default is 10).
- `LabelingSection` values: "Dosage and Administration", "Clinical Pharmacology", "Precautions", "Use in Specific Populations", "Boxed Warning", "Contraindications".
- Can query by drug, biomarker, or both.
- Not all drugs have entries (e.g., simvastatin absent for SLCO1B1; use rosuvastatin for SLCO1B1 PGx testing).

**FDA_get_pharmacogenomics_info_by_drug_name**: `drug_name` (string REQUIRED). Returns FDA label PGx sections with brand/generic names. Good for finding PGx labeling text in actual FDA labels.

### FDA PGx Label Reasoning

The `LabelingSection` field tells you how actionable the PGx information is. "Boxed Warning" or "Contraindications" means testing may be required or the drug contraindicated in certain genotypes — highest urgency. "Dosage and Administration" means genotype directly drives dose selection. "Clinical Pharmacology" is usually informational (PK/PD data), not a prescribing directive. When in doubt, retrieve the full label text with `FDA_get_pharmacogenomics_info_by_drug_name`.

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

**FAERS_filter_serious_events**: `drug_name` (string REQUIRED), `seriousness_type` ("all"/"death"/"hospitalization"/"disability"/"life_threatening"), `adverse_event` (string, optional). Use to detect serious adverse event signals for PGx-relevant drugs — e.g., respiratory depression reports for codeine in the context of CYP2D6 UM status. The `adverse_event` parameter filters to reports containing that specific reaction term.

**Optional**: `DisGeNET_get_vda` for variant-disease associations (requires DISGENET_API_KEY).

---

## When PGx Testing Changes Clinical Decisions

PGx testing changes clinical decisions ONLY for drugs with narrow therapeutic indices metabolized by polymorphic enzymes where genotype reliably predicts outcome. If the drug has a wide therapeutic index or is cleared by multiple redundant pathways, PGx status rarely alters the prescribing decision even when a variant is present.

**Evidence grading — reasoning approach**: CPIC levels A/B represent actionable evidence; C/D are informational. PharmGKB level 1A means the annotation is already embedded in a CPIC or DPWG guideline — the highest confidence tier. Levels 3/4 are hypothesis-generating, not prescribing-grade. CPIC recommendation strength (Strong/Moderate/Optional) within a guideline reflects how certain the genotype-to-outcome link is for that specific phenotype.

The key question is not "what level is this?" but "does this level justify changing the prescription?" For Level A CPIC with Strong classification, yes. For PharmGKB level 3, no — report it but don't act on it alone.

---

## Key Parameter Notes

Critical parameter behaviors to remember — these are the ones that actually cause failures:

- `CPIC_get_recommendations`: accepts `guideline_id` (integer) OR `drug`/`drug_name` (string). Never pass guideline_id as a string.
- `PharmGKB_get_dosing_guidelines`: requires `clinpgxid` (e.g., "PA166251445"), not the numeric `pharmgkbid`. Get clinpgxid from `CPIC_list_guidelines`.
- `PharmGKB_get_clinical_annotations`: requires `annotation_id`. Cannot query by gene or drug. Discover IDs via `PharmGKB_search_variants(query=rsID)`.
- `fda_pharmacogenomic_biomarkers`: default `limit=10` is almost always too small. Pass `limit=1000`.
- `CPIC_get_drug_info`: drug name must be lowercase.
- `DGIdb_get_drug_gene_interactions` and `DGIdb_get_gene_druggability`: `genes` is an array, not a string (e.g., `["CYP2D6"]`).
- `CPIC_search_gene_drug_pairs`: returns RxNorm IDs, not drug names. Use `CPIC_get_gene_drug_pairs` when you need drug names.

---

## CPIC Guideline Application Reasoning

CPIC guidelines give genotype → phenotype → recommendation mappings. The skill is knowing when to apply them, not memorizing the mappings themselves. Use tools to retrieve the specific recommendation for the specific phenotype. The reasoning chain is:

1. Does a CPIC guideline exist for this gene-drug pair? (Level A or B = actionable)
2. What is the patient's phenotype? (from diplotype + allele function statuses)
3. What does the guideline recommend for that phenotype? (retrieve with `CPIC_get_recommendations`)
4. Is there FDA label reinforcement? (check `fda_pharmacogenomic_biomarkers`)

If step 1 is no, fall back to PharmGKB variant annotations for evidence-graded but non-guideline information.

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

**Drug-first (codeine + CYP2D6 PM)**: `CPIC_get_recommendations(drug="codeine", limit=50)` → filter `phenotypes.CYP2D6="Poor Metabolizer"` → Strong recommendation: avoid codeine. Then `CPIC_get_alleles(genesymbol="CYP2D6", limit=100)` to confirm star allele function (e.g., *4/*4 → no function, AS 0.0). Then `fda_pharmacogenomic_biomarkers(drug_name="codeine", limit=1000)` to confirm FDA label status. Gene-first alternative: `CPIC_get_gene_drug_pairs(genesymbol="CYP2D6")` to list all associated drugs.

**Gene-first (all CYP2C19 drugs)**: `CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A")` for Level A pairs. `EpiGraphDB_get_gene_drug_associations(gene_name="CYP2C19")` for CPIC + PharmGKB + FDA label overview in one call. `fda_pharmacogenomic_biomarkers(biomarker="CYP2C19", limit=1000)` for complete FDA coverage.

**Variant-first (rs1799853)**: `PharmGKB_search_variants(query="rs1799853")` → CYP2C9 variant, drug-response significance. `CPIC_get_alleles(genesymbol="CYP2C9", limit=100)` → maps to *2, "Decreased function". `CPIC_get_gene_drug_pairs(genesymbol="CYP2C9")` → warfarin, phenytoin, NSAIDs. For each drug with a guideline: `CPIC_get_recommendations(drug="phenytoin", limit=50)`.

---

## Drug Class Context (RxClass)

When PGx analysis involves understanding which drug class a substrate belongs to, or finding all drugs in a class that share the same metabolizing enzyme: use `RxClass_get_drug_classes(drug_name=...)` to get all class memberships for a drug, `RxClass_find_classes(query=..., class_type=...)` to find class IDs from a keyword, and `RxClass_get_class_members(class_id=..., rela_source=..., ttys="IN")` to list all drugs in a class. Example: find all SSRIs to advise which require CYP2D6 testing as a class note.

## FDA Substance Identification (FDAGSRS)

For canonical FDA substance identification (UNII codes, cross-references to ATC/DrugBank/CAS): use `FDAGSRS_search_substances(query=...)` to find the UNII code, `FDAGSRS_get_substance(unii=...)` for the full record with all names and cross-references, and `FDAGSRS_get_structure(unii=...)` for SMILES/InChIKey. Useful to confirm that two drug name variants (e.g., "warfarin sodium" and "warfarin") share the same UNII before cross-referencing in CPIC or PharmGKB.

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
