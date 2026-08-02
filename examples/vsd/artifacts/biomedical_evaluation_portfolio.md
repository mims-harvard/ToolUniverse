# Biomedical VSD Evaluation Portfolio

## Evaluation Summary

Five research workflows were evaluated through the same registry-first pipeline. The run published 5 narrowly scoped tools after 15 verification executions; all recorded assertions passed.

- Requested evidence mode: `network_backed`
- Live cases: `2`
- Checked-replay cases: `3`
- Portfolio SHA-256: `036e12725bee5e98e700b5f94514ee6b9375bcab66a73b38165044047ba321f3`

## 1. Rare-Disease Diagnostic Evidence Reconciliation

**Question.** Can a diagnostic review reconcile disease, phenotype, and gene identifiers before comparing rare-disease cohort and variant evidence?

**Decision context.** Normalize identifiers before combining phenotype, variant, natural-history, and trial evidence; the added annotations support evidence retrieval and do not establish a diagnosis.

**Evidence qualification.** This case completed in `replay` mode. The live attempt stopped at a governed boundary (`VSDPromotionError`), so the checked replay is reported and no live result is claimed.

### Existing ToolUniverse Coverage

- `Orphanet_get_natural_history`: Reuse curated rare-disease natural-history evidence.
- `HPO_get_diseases_by_phenotype`: Reuse phenotype-to-disease associations.
- `ClinVar_search_variants`: Reuse submitted variant interpretations.

### Gap And Source Qualification

The baseline planner classified the required operation as `missing`. SmartAPI query `rare disease phenotype ontology annotation` selected record `5a4c41bf2076b469a0e9cfcf2f2b8f29`, and inspection selected `get_/{curieid}` at `/{curieid}`.

Promotion mode was `strict`. The candidate, source document, operation, draft, verification, approval, and publication identities are retained in the JSON artifact.

### Comparison

**Without VSD.** ToolUniverse already covers phenotype, natural-history, and variant evidence, but this exact registered annotation operation is absent, so the workflow must reconcile identifier namespaces outside the governed tool path.

**With VSD.** The workflow gains one verified CURIE annotation operation that returns cross-ontology labels and identifiers with runtime provenance, allowing existing evidence tools to receive consistent identifiers.

The final planner classified the exact operation as `existing_exact` after `3` verification calls and explicit loading of `VSDTranslatorAnnotationLookup`.

### Observed Result

- Normalized disease label: `"amyotrophic lateral sclerosis"`
- Disease Ontology identifier: `"DOID:332"`
- GARD cross-reference: `"5786"`

### Limitations

- Annotation mappings are retrieval evidence, not a diagnostic conclusion.
- Replay values are provider-shaped test evidence; live mode is required to assess current upstream content.
- Conflicting or missing mappings still require domain review.

### References

- [Phenotype-driven rare genetic disease diagnosis](https://www.nature.com/articles/s41746-025-01749-1)
- [NCATS Biomedical Data Translator](https://ncats.nih.gov/research/research-activities/translator)
- [Human Phenotype Ontology](https://hpo.jax.org/)
- [Orphanet](https://www.orpha.net/)

## 2. Pan-Cancer Immunotherapy Evidence Validation

**Question.** Can a pan-cancer response analysis add molecular interaction evidence for immune checkpoints after cohort and expression tools identify candidate markers?

**Decision context.** Use cohort, expression, immune-study, and interaction evidence to prioritize checkpoint hypotheses for retrospective validation rather than treatment selection.

**Evidence qualification.** This case completed in `live` mode.

### Existing ToolUniverse Coverage

- `GDC_search_cases`: Reuse pan-cancer cohort construction.
- `GDC_get_gene_expression`: Reuse tumor expression measurements.
- `ImmPort_search_studies`: Reuse immune-study discovery.

### Gap And Source Qualification

The baseline planner classified the required operation as `missing`. SmartAPI query `innate immune interaction` selected record `e9eb40ff7ad712e4e6f4f04b964b5966`, and inspection selected `get_/query` at `/query`.

Promotion mode was `reviewed_response`. The candidate, source document, operation, draft, verification, approval, and publication identities are retained in the JSON artifact.

### Comparison

**Without VSD.** The registry can assemble cancer cohorts and expression evidence, but it lacks the exact InnateDB query operation, leaving checkpoint interaction support outside the planned ToolUniverse workflow.

**With VSD.** The workflow adds a bounded, verified interaction query for PDCD1, CTLA4, and LAG3, so interaction provenance can be compared alongside cohort and expression evidence.

The final planner classified the exact operation as `existing_exact` after `3` verification calls and explicit loading of `VSDInnateDBInteractionQuery`.

### Observed Result

- Matching interaction records: `8`
- Queried checkpoint: `"PDCD1"`
- First interacting marker: `"SOCS1"`

### Limitations

- Molecular interactions do not establish response causality or clinical benefit.
- The reviewed response schema is intentionally bounded to the stable BioThings envelope because the registry document omits that schema.
- Cancer-type, treatment, and assay-specific validation remains necessary.

### References

- [Pan-cancer longitudinal immunotherapy analysis](https://www.nature.com/articles/s41467-021-25432-7)
- [NCI Genomic Data Commons](https://gdc.cancer.gov/)
- [InnateDB](https://www.innatedb.com/)
- [ImmPort](https://www.immport.org/)

## 3. Context-Specific Oncology Combination Review

**Question.** Can an oncology combination workflow add curated interaction severity before advancing experimentally promising drug pairs?

**Decision context.** Combine target, dependency, synergy, and adverse-event evidence with curated interaction records to prioritize laboratory follow-up and safety review.

**Evidence qualification.** This case completed in `live` mode.

### Existing ToolUniverse Coverage

- `ChEMBL_get_target_activities`: Reuse target activity evidence.
- `DepMap_get_gene_dependencies`: Reuse cancer-context dependency evidence.
- `DrugSynergy_calculate_bliss`: Reuse measured combination-effect scoring.
- `FAERS_compare_drugs`: Reuse post-market safety signal comparison.

### Gap And Source Qualification

The baseline planner classified the required operation as `missing`. SmartAPI query `drug combination interaction oncology` selected record `00fb85fc776279163199e6c50f6ddfc6`, and inspection selected `get_/query` at `/query`.

Promotion mode was `reviewed_response`. The candidate, source document, operation, draft, verification, approval, and publication identities are retained in the JSON artifact.

### Comparison

**Without VSD.** ToolUniverse can score observed synergy and retrieve target, dependency, and safety evidence, but it lacks this exact curated interaction query, so a promising pair can reach review without a DDInter severity check in the same workflow.

**With VSD.** The workflow gains a bounded DDInter query that can flag curated interaction severity before experimental prioritization; it complements rather than replaces efficacy and safety analysis.

The final planner classified the exact operation as `existing_exact` after `3` verification calls and explicit loading of `VSDDDInterCombinationQuery`.

### Observed Result

- Matching curated records: `1`
- First combination: `"Idarubicin"`
- Interaction severity: `"Major"`

### Limitations

- Interaction severity is not an efficacy estimate and does not replace pharmacology review.
- The example query verifies retrieval and governance, not a treatment recommendation.
- The upstream specification omits the response schema, so publication depends on explicit reviewed-schema evidence.

### References

- [Context-specific drug combinations in lung cancer](https://www.nature.com/articles/s41467-023-39528-9)
- [DDInter drug-drug interaction database](https://academic.oup.com/nar/article/50/D1/D1200/6389535)
- [DepMap](https://depmap.org/portal/)
- [ChEMBL](https://www.ebi.ac.uk/chembl/)

## 4. Virtual-Cell Perturbation Dataset Selection

**Question.** Can a virtual-cell preparation workflow resolve candidate perturbagens to dataset identifiers before retrieving signatures and single-cell context?

**Decision context.** Resolve perturbagen names before selecting expression signatures, cell contexts, and training data for perturbation-response modeling.

**Evidence qualification.** This case completed in `replay` mode. The live attempt stopped at a governed boundary (`VSDPromotionError`), so the checked replay is reported and no live result is claimed.

### Existing ToolUniverse Coverage

- `CELLxGENE_get_cell_metadata`: Reuse single-cell context and cohort metadata.
- `CELLxGENE_get_expression_data`: Reuse cell-level expression retrieval.
- `L1000FWD_sig_search`: Reuse the existing signature-search workflow after identifier resolution.

### Gap And Source Qualification

The baseline planner classified the required operation as `missing`. SmartAPI query `single cell gene expression perturbation` selected record `235e75417247f07e5fed6acf3f345bb7`, and inspection selected `synonyms` at `/synonyms/{query_string}`.

Promotion mode was `strict`. The candidate, source document, operation, draft, verification, approval, and publication identities are retained in the JSON artifact.

### Comparison

**Without VSD.** ToolUniverse already performs L1000 signature search and CELLxGENE retrieval, but it does not expose the provider's synonym operation, so free-text perturbagen names must be resolved outside the planned tool chain.

**With VSD.** The workflow adds only the missing synonym operation from the already known provider, turning drug names into stable perturbagen identifiers before existing signature and single-cell tools run.

The final planner classified the exact operation as `existing_exact` after `3` verification calls and explicit loading of `VSDL1000PerturbagenResolver`.

### Observed Result

- Resolved perturbagen name: `"TRAMETINIB"`
- Resolved L1000 perturbagen identifier: `"BRD-K12343256"`

### Limitations

- Identifier resolution does not determine whether a perturbation is biologically appropriate for a model.
- Signature quality, dose, duration, cell state, and batch effects require separate evaluation.
- The provider may return multiple identifiers for one name; downstream selection must retain that ambiguity.

### References

- [Benchmarking single-cell perturbation response prediction](https://www.nature.com/articles/s41592-025-02980-0)
- [L1000FWD](https://maayanlab.cloud/L1000FWD/)
- [CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/)
- [Virtual Cell Challenge](https://virtualcellchallenge.org/)

## 5. Tuberculosis Resistance Evidence Integration

**Question.** Can a tuberculosis resistance workflow verify that a discovered radiomics service is available before combining genomic, antimicrobial-resistance, and imaging evidence?

**Decision context.** Gate an imaging branch on service readiness while existing tools assemble genome, resistance, drug, and study evidence; readiness does not authorize controlled-data access.

**Evidence qualification.** This case completed in `replay` mode. The live attempt stopped at a governed boundary (`VSDPromotionError`), so the checked replay is reported and no live result is claimed.

### Existing ToolUniverse Coverage

- `BVBRC_search_amr`: Reuse antimicrobial-resistance phenotype evidence.
- `BVBRC_search_genomes`: Reuse pathogen genome metadata.
- `PharmGKB_search_drugs`: Reuse drug identifier and pharmacogenomic context.
- `search_clinical_trials`: Reuse tuberculosis study discovery.

### Gap And Source Qualification

The baseline planner classified the required operation as `missing`. SmartAPI query `TBPortals radiomics` selected record `fc18c6cce884c23866beed24dce30a2d`, and inspection selected `get_/health_check` at `/health_check`.

Promotion mode was `strict`. The candidate, source document, operation, draft, verification, approval, and publication identities are retained in the JSON artifact.

### Comparison

**Without VSD.** ToolUniverse can retrieve pathogen, resistance, drug, and trial evidence, but it has no exact operation for checking the cataloged radiomics service before the workflow enters its imaging branch.

**With VSD.** The workflow gains a narrow readiness check bound to the cataloged service and contract; this prevents treating an unavailable imaging dependency as usable and does not create access to controlled images.

The final planner classified the exact operation as `existing_exact` after `3` verification calls and explicit loading of `VSDTBPortalsRadiomicsReadiness`.

### Observed Result

- Radiomics service status: `"ok"`
- Service label: `"TBPortals radiomics"`

### Limitations

- A health check establishes service readiness only; it does not validate a radiomics model or scientific result.
- Controlled imaging data, consent, and authorization remain outside this tool.
- The checked replay validates the lifecycle when the service is unreachable from the evaluation environment; current availability requires live mode.

### References

- [NIAID TB Portals multi-domain data platform](https://tbportals.niaid.nih.gov/what-are-the-tb-portals)
- [TB Portals data access policy](https://tbportals.niaid.nih.gov/access-data)
- [BV-BRC antimicrobial resistance resources](https://www.bv-brc.org/)
- [WHO tuberculosis data](https://www.who.int/teams/global-tuberculosis-programme/data)
