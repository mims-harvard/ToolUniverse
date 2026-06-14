# Drug Target Validation - Tool Reference

Verified tool parameters, known corrections, fallback chains, and modality-specific tool guidance.

---

## Known Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `ensembl_lookup_gene` | `id` | `gene_id` (+ `species="homo_sapiens"` REQUIRED) |
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | `id` |
| `ensembl_get_xrefs` | `gene_id` | `id` |
| `GTEx_get_median_gene_expression` | `gencode_id` only | `gencode_id` + `operation="median"` |
| `OpenTargets_*` | `ensemblID` (uppercase) | `ensemblId` (camelCase) |
| `OpenTargets_get_publications_*` | `ensemblId` | `entityId` |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId` only | `ensemblId` + `size` (REQUIRED) |
| `MyGene_query_genes` | `q` | `query` |
| `PubMed_search_articles` | returns `{articles: [...]}` | returns **plain list** of dicts |
| `UniProt_get_function_by_accession` | returns dict | returns **list of strings** |
| `HPA_get_rna_expression_by_source` | `ensembl_id` | `gene_name` + `source_type` + `source_name` (ALL required) |
| `alphafold_get_prediction` | `uniprot_accession` | `qualifier` |
| `drugbank_get_safety_*` | simple params | `query`, `case_sensitive`, `exact_match`, `limit` (ALL required) |

---

## Verified Tool Parameters (Quick Reference)

| Tool | Parameters | Notes |
|------|-----------|-------|
| `ensembl_lookup_gene` | `gene_id`, `species` | species="homo_sapiens" REQUIRED; response wrapped in `{status, data, url, content_type}` |
| `OpenTargets_get_*_by_ensemblID` | `ensemblId` | camelCase, NOT ensemblID |
| `OpenTargets_get_publications_by_target_ensemblID` | `entityId` | NOT ensemblId |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | size is REQUIRED |
| `OpenTargets_target_disease_evidence` | `efoId`, `ensemblId` | Both REQUIRED |
| `GTEx_get_median_gene_expression` | `operation`, `gencode_id` | operation="median" REQUIRED |
| `HPA_get_rna_expression_by_source` | `gene_name`, `source_type`, `source_name` | ALL 3 required |
| `PubMed_search_articles` | `query`, `limit` | Returns plain list, NOT {articles:[]} |
| `UniProt_get_function_by_accession` | `accession` | Returns list of strings |
| `alphafold_get_prediction` | `qualifier` | NOT uniprot_accession |
| `drugbank_get_safety_*` | `query`, `case_sensitive`, `exact_match`, `limit` | ALL required |
| `STRING_get_protein_interactions` | `protein_ids`, `species` | protein_ids is array; species=9606 |
| `Reactome_map_uniprot_to_pathways` | `id` | NOT uniprot_id |
| `ChEMBL_get_target_activities` | `target_chembl_id__exact` | Note double underscore |
| `search_clinical_trials` | `query_term` | REQUIRED parameter |
| `gnomad_get_gene_constraints` | `gene_symbol` | NOT gene_id |
| `DepMap_get_gene_dependencies` | `gene_symbol` | NOT gene_id |
| `BindingDB_get_ligands_by_uniprot` | `uniprot`, `affinity_cutoff` | affinity in nM |
| `Pharos_get_target` | `gene` or `uniprot` | Both optional but need one |

---

## Fallback Chains

When a primary tool fails, use these fallbacks in order:

| Primary Tool | Fallback 1 | Fallback 2 | If All Fail |
|--------------|------------|------------|-------------|
| `OpenTargets_get_diseases_phenotypes_*` | `CTD_get_gene_diseases` | PubMed search | Note in report |
| `GTEx_get_median_gene_expression` (versioned) | GTEx (unversioned) | `HPA_search_genes_by_query` | Document gap |
| `ChEMBL_get_target_activities` | `BindingDB_get_ligands_by_uniprot` | `DGIdb_get_gene_info` | Note in report |
| `gnomad_get_gene_constraints` | `OpenTargets_get_target_constraint_info_*` | - | Note as unavailable |
| `Reactome_map_uniprot_to_pathways` | `OpenTargets_get_target_gene_ontology_*` | - | Use GO only |
| `STRING_get_protein_interactions` | `intact_get_interactions` | `OpenTargets interactions` | Note in report |
| `ProteinsPlus_predict_binding_sites` | `alphafold_get_prediction` | Literature pockets | Note as limited |

---

## Modality-Specific Tool Focus

### Small Molecule
- Emphasize: binding pockets, ChEMBL compounds, Lipinski compliance
- Key tractability: OpenTargets SM tractability bucket
- Structure: co-crystal structures with small molecule ligands
- Chemical matter: IC50/Ki/Kd data from ChEMBL/BindingDB

### Antibody
- Emphasize: extracellular domains, cell surface expression, glycosylation
- Key tractability: OpenTargets AB tractability bucket
- Structure: ectodomain structures, epitope mapping
- Expression: surface expression in disease vs normal tissue

### PROTAC
- Emphasize: intracellular targets, surface lysines, E3 ligase proximity
- Key tractability: OpenTargets PROTAC tractability
- Structure: full-length structures for linker design
- Chemical matter: known binders + E3 ligase binders

---

## Phase-by-Phase Tool Lists

### Phase 0: Target Disambiguation
- `MyGene_query_genes` - initial ID resolution
- `UniProt_get_entry_by_accession` - protein details
- `ensembl_lookup_gene` - Ensembl ID + version
- `ensembl_get_xrefs` - cross-references
- `OpenTargets_get_target_id_description_by_name` - OT target info
- `ChEMBL_search_targets` - ChEMBL target ID
- `UniProt_get_function_by_accession` - function summary
- `UniProt_get_alternative_names_by_accession` - collision detection

### Phase 1: Disease Association
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` - disease associations
- `OpenTargets_get_disease_id_description_by_name` - disease ID lookup
- `OpenTargets_target_disease_evidence` - detailed evidence
- `OpenTargets_get_evidence_by_datasource` - evidence by source
- `gwas_get_snps_for_gene` - GWAS associations
- `gwas_search_studies` - GWAS studies
- `gnomad_get_gene_constraints` - genetic constraint (pLI, LOEUF)
- `PubMed_search_articles` - literature evidence
- `OpenTargets_get_publications_by_target_ensemblID` - OT publications

### Phase 2: Druggability
- `OpenTargets_get_target_tractability_by_ensemblID` - tractability
- `OpenTargets_get_target_classes_by_ensemblID` - target classification
- `Pharos_get_target` - target development level (TDL)
- `DGIdb_get_gene_druggability` - druggability categories
- `alphafold_get_prediction` / `alphafold_get_summary` - structure prediction
- `ProteinsPlus_predict_binding_sites` - pocket detection
- `OpenTargets_get_chemical_probes_by_target_ensemblID` - chemical probes
- `OpenTargets_get_target_enabling_packages_by_ensemblID` - TEPs

### Phase 3: Chemical Matter
- `ChEMBL_search_targets` / `ChEMBL_get_target_activities` - bioactivity
- `BindingDB_get_ligands_by_uniprot` - binding data
- `PubChem_search_assays_by_target_gene` - HTS assays
- `PubChem_get_assay_summary` / `PubChem_get_assay_active_compounds` - assay details
- `OpenTargets_get_associated_drugs_by_target_ensemblID` - known drugs
- `ChEMBL_search_mechanisms` - drug mechanisms
- `DGIdb_get_gene_info` - drug-gene interactions

### Phase 4: Clinical Precedent
- `FDA_get_mechanism_of_action_by_drug_name` - FDA MoA
- `FDA_get_indications_by_drug_name` - FDA indications
- `drugbank_get_targets_by_drug_name_or_drugbank_id` - DrugBank targets
- `drugbank_get_safety_by_drug_name_or_drugbank_id` - DrugBank safety
- `search_clinical_trials` - active trials
- `OpenTargets_get_drug_warnings_by_chemblId` - drug warnings
- `OpenTargets_get_drug_adverse_events_by_chemblId` - adverse events

### Phase 5: Safety
- `OpenTargets_get_target_safety_profile_by_ensemblID` - safety profile
- `GTEx_get_median_gene_expression` - tissue expression
- `HPA_search_genes_by_query` / `HPA_get_comprehensive_gene_details_by_ensembl_id` - HPA expression
- `OpenTargets_get_biological_mouse_models_by_ensemblID` - KO phenotypes
- `gnomad_get_gene_constraints` - essentiality proxy
- `FDA_get_adverse_reactions_by_drug_name` - ADRs
- `FDA_get_warnings_and_cautions_by_drug_name` / `FDA_get_boxed_warning_info_by_drug_name` - warnings
- `OpenTargets_get_target_homologues_by_ensemblID` - paralogs

### Phase 6: Pathway Context
- `Reactome_map_uniprot_to_pathways` / `Reactome_get_pathway` - pathways
- `STRING_get_protein_interactions` - PPI network
- `intact_get_interactions` - experimental PPI
- `OpenTargets_get_target_interactions_by_ensemblID` - OT interactions
- `OpenTargets_get_target_gene_ontology_by_ensemblID` - GO terms
- `GO_get_annotations_for_gene` - GO annotations
- `STRING_functional_enrichment` - enrichment analysis

### Phase 7: Validation Evidence
- `DepMap_get_gene_dependencies` - essentiality screen
- `PubMed_search_articles` - functional studies literature
- `CTD_get_gene_diseases` - gene-disease associations

### Phase 8: Structural Insights
- `UniProt_get_entry_by_accession` - PDB cross-references
- `get_protein_metadata_by_pdb_id` / `pdbe_get_entry_summary` - PDB metadata
- `pdbe_get_entry_quality` / `pdbe_get_entry_experiment` - quality metrics
- `alphafold_get_prediction` / `alphafold_get_summary` - AlphaFold
- `ProteinsPlus_predict_binding_sites` - binding pockets
- `ProteinsPlus_generate_interaction_diagram` - interaction diagrams
- `InterPro_get_protein_domains` / `InterPro_get_domain_details` - domains

### Phase 9: Literature Deep Dive
- `PubMed_search_articles` - collision-aware searches
- `EuropePMC_search_articles` - broader coverage
- `openalex_search_works` - citation metrics
