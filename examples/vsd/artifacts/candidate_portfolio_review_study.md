# VSD Candidate Portfolio Review

## Scope

Apply a documented review policy to every unique draft-ready scanner configuration and measure the smaller set that merits live verification.

Static review is a portfolio triage decision, not source approval. Catalog membership does not establish provider trust, anonymous accessibility, scientific validity, or permission to publish a tool.

## Review Funnel

| Stage | Count |
| --- | ---: |
| Exhaustive operation candidates | 37,570 |
| Mechanically draft-ready configurations | 3,097 |
| Unique endpoint identities | 3,041 |
| Initially eligible after metadata review | 1,847 |
| Draft-producing contracts refreshed | 290 / 290 |
| Eligible after current-contract review | 1,325 |
| Eligible research-facing scientific candidates | 139 |
| Lower-value service utility candidates | 81 |
| Held or superseded after portfolio review | 1,772 |
| Bounded live-review shortlist | 7 |
| Passed live verification and remained unapproved | 5 |

## Final Contract-Aware Dispositions

| Decision | Candidates |
| --- | ---: |
| `eligible_general_no_input_live_verification_on_demand` | 48 |
| `eligible_general_parameterized_verification_on_demand` | 1,057 |
| `eligible_scientific_no_input_live_verification` | 22 |
| `eligible_scientific_parameterized_verification` | 117 |
| `eligible_service_utility_verification_on_demand` | 81 |
| `hold_nonproduction_endpoint` | 205 |
| `hold_potential_side_effect` | 65 |
| `hold_stale_catalog_record` | 546 |
| `hold_undeclared_access_control` | 384 |
| `hold_weak_response_contract` | 522 |
| `superseded_endpoint_variant` | 50 |

## Principal Review Signals

| Signal | Candidates |
| --- | ---: |
| `contract_warnings_present` | 748 |
| `nonproduction_endpoint` | 211 |
| `possible_undeclared_access_control` | 387 |
| `potential_side_effect_semantics` | 65 |
| `public_authority_host` | 129 |
| `required_contract_parameters` | 1,174 |
| `response_shape_cannot_support_verification_assertions` | 522 |
| `scenario_inputs_required` | 1,807 |
| `scientific_vocabulary_match` | 235 |
| `service_utility_operation` | 145 |
| `stale_catalog_metadata` | 664 |
| `superseded_endpoint_variant` | 56 |

## Scientific Capability Families

| Provider | Candidate operations | No-input | Parameterized | Examples |
| --- | ---: | ---: | ---: | --- |
| Columbia Open Health Data (COHD) API (`cohd-api.transltr.io`) | 23 | 6 | 17 | `associatedConceptDomainFreq`, `associatedConceptFreq`, `chiSquare`, `conceptAgeCounts` |
| HuBMAP/SenNet Ontology API (hs-ontology-api) (`ontology.api.hubmapconsortium.org`) | 23 | 0 | 23 | `relationships_for_gene_target_symbol_get`, `annotations_get`, `assayclass_get`, `datasettypes_get` |
| FlyMine Web Services API (`www.flymine.org`) | 22 | 9 | 13 | `enrichmentWidget`, `getFacets`, `getLists`, `getListTags` |
| Columbia Open Health Data (COHD) for COVID-19 Research API (`covid.cohd.io`) | 19 | 6 | 13 | `associatedConceptDomainFreq`, `associatedConceptFreq`, `chiSquare`, `conceptAncestors` |
| UniProt Taxonomy Service (`www.ebi.ac.uk`) | 17 | 0 | 17 | `checkRelationshipBetweenTaxonomies`, `getTaxonomyPath`, `getTaxonomyPathNodes`, `getTaxonomiesDetailsByName` |
| CFDE Gene Regulation Linked Data Hub (`genboree.org`) | 10 | 1 | 9 | `getLDHSrvc`, `getDocUsingId`, `getEntTyBatch`, `getEntType` |
| PharmGKB REST API (`api.pharmgkb.org`) | 8 | 0 | 8 | `get_/data/gene/{id}/ontologyTerms`, `get_/data/ontologyTerm`, `get_/data/chemical/{id}`, `get_/data/clinicalAnnotation/{id}` |
| Automat-drug-central(Trapi v1.5.0), Automat-ehr-clinical-connections-kp(Trapi v1.5.0), Automat-genome-alliance(Trapi v1.5.0) (`automat.renci.org`) | 6 | 0 | 6 | `node__node_type___curie__get`, `one_hop__source_type___target_type___curie__get` |
| MetGENE REST API, REST API for Gene ID Conversion (`bdcw.org`) | 4 | 0 | 4 | `get_/metabolites/species/{species_id}/GeneIDType/{geneID_type}/GeneInfoStr/{gene_ID}/anatomy/{anatomy_name}/disease/{disease_name}/phenotype/{phenotype_name}/viewType/{vtf}`, `get_/reactions/species/{species_id}/GeneIDType/{geneID_type}/GeneInfoStr/{gene_ID}/anatomy/NA/disease/NA/phenotype/NA/viewType/{vtf}`, `get_/studies/species/{species_id}/GeneIDType/{geneID_type}/GeneInfoStr/{gene_ID}/anatomy/{anatomy_name}/disease/{disease_name}/phenotype/{phenotype_name}/viewType/{vtf}`, `get_/species/{species_id}/GeneIDType/{geneid_type}/GeneListStr/{gene_id}/View/{json_or_txt}` |
| BioThings Explorer (BTE) TRAPI (`bte.transltr.io`) | 3 | 0 | 3 | `asyncquery_response`, `get_/smartapi/{smartapi_id}/meta_knowledge_graph`, `get_/team/{team_name}/meta_knowledge_graph` |
| Translator Annotation Service (`biothings.transltr.io`) | 1 | 0 | 1 | `get_/{curieid}` |
| SenNet Ingest API (`ingest.api.sennetconsortium.org`) | 1 | 0 | 1 | `getAssayType` |
| Enrichr (`maayanlab.cloud`) | 1 | 0 | 1 | `geneSetLibrary` |
| NamSor API v2 (`v2.namsor.com`) | 1 | 0 | 1 | `taxonomyClasses` |

## Live Review

The live phase selected at most one no-input scientific operation per host before considering another operation from the same host. Each candidate was rebound to the current catalog contract, checked for drift, and either deferred or executed three times through the normal isolated VSD verifier. No candidate was approved or published.

| Outcome | Candidates |
| --- | ---: |
| `rejected_or_deferred_at_live_review` | 2 |
| `verified_live_unapproved` | 5 |

### Live Results

| API | Operation | Host | Outcome | Evidence |
| --- | --- | --- | --- | --- |
| Columbia Open Health Data (COHD) API | `datasets` | `cohd-api.transltr.io` | `verified_live_unapproved` | 3 hash-bound calls passed |
| Columbia Open Health Data (COHD) for COVID-19 Research API | `datasets` | `covid.cohd.io` | `rejected_or_deferred_at_live_review` | Verification case 0 did not execute successfully: {'status': 'error', 'error': 'Validation error: Source request exceeded its total timeout', 'error_details': {'type': 'ToolValidat |
| CFDE Gene Regulation Linked Data Hub | `getLDHSrvc` | `genboree.org` | `verified_live_unapproved` | 3 hash-bound calls passed |
| FlyMine Web Services API | `getLists` | `www.flymine.org` | `verified_live_unapproved` | 3 hash-bound calls passed |
| Columbia Open Health Data (COHD) API | `domainCounts` | `cohd-api.transltr.io` | `verified_live_unapproved` | 3 hash-bound calls passed |
| Columbia Open Health Data (COHD) for COVID-19 Research API | `domainCounts` | `covid.cohd.io` | `rejected_or_deferred_at_live_review` | Verification case 0 did not execute successfully: {'status': 'error', 'error': 'Validation error: Source request exceeded its total timeout', 'error_details': {'type': 'ToolValidat |
| FlyMine Web Services API | `getListTags` | `www.flymine.org` | `verified_live_unapproved` | 3 hash-bound calls passed |

## Measured Contribution

The gross count measures discovery breadth, while the reviewed and live counts measure usable growth potential. Every draft-producing contract was refetched and all 3,097 configuration hashes were matched to the current documents. VSD contributes a repeatable path from a missing capability to an inspectable candidate, then removes duplicates, stale sources, suspected access-control gaps, weak response contracts, and low-value utility operations before execution. The checked cancer qualification independently shows the later stages: four scanner-derived operations passed verification, approval, publication, fresh ToolUniverse loading, and twenty workflow calls, while four plausible candidates failed closed on live schema drift.

The review does not establish provider endorsement or scientific truth. Candidates marked eligible still require a concrete demand, provider governance review, representative inputs when applicable, live verification, explicit approval, and lifecycle monitoring.

The machine-readable ledger contains the decision and evidence for every candidate plus the refresh result for every draft-producing contract.

Review SHA-256: `3f1a99d861d851ab43983251987f5664b4ed1262605de6d71ef8aced2d0f29a4`.
