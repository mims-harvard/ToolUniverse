# Tool Reference: Multi-Omics Disease Characterization

Detailed tool parameters, inputs/outputs, and per-phase workflows.

---

## Phase 0: Disease Disambiguation Tools

**OpenTargets_get_disease_id_description_by_name** (primary):
- **Input**: `diseaseName` (string)
- **Output**: `{data: {search: {hits: [{id, name, description}]}}}`
- **CRITICAL**: Disease IDs use underscore format (e.g., `MONDO_0004975`), NOT colon format

**OSL_get_efo_id_by_disease_name** (secondary):
- **Input**: `disease` (string)
- **Output**: `{efo_id, name}`

**OpenTargets_get_disease_description_by_efoId**:
- **Input**: `efoId` (string, e.g., `MONDO_0004975`)
- **Output**: `{data: {disease: {id, name, description, dbXRefs}}}`

**OpenTargets_get_disease_synonyms_by_efoId**:
- **Input**: `efoId` (string)
- **Output**: `{data: {disease: {id, name, synonyms: [{relation, terms}]}}}`

**OpenTargets_get_disease_therapeutic_areas_by_efoId**:
- **Input**: `efoId` (string)
- **Output**: `{data: {disease: {id, name, therapeuticAreas: [{id, name}]}}}`

**OpenTargets_get_disease_ancestors_parents_by_efoId**:
- **Input**: `efoId` (string)
- **Output**: `{data: {disease: {id, name, ancestors: [{id, name}]}}}`

**OpenTargets_get_disease_descendants_children_by_efoId**:
- **Input**: `efoId` (string)
- **Output**: `{data: {disease: {id, name, descendants: [{id, name}]}}}`

**OpenTargets_map_any_disease_id_to_all_other_ids**:
- **Input**: `inputId` (string, e.g., `OMIM:104300`, `UMLS:C0002395`)
- **Output**: `{data: {disease: {id, name, dbXRefs: [str], ...}}}`

### Phase 0 Workflow
1. Search by disease name to get primary ID (OpenTargets)
2. Get full description and cross-references
3. Get synonyms for search term expansion
4. Get therapeutic areas for context
5. Get disease hierarchy (parents/children)
6. If user provided OMIM/other ID, map to MONDO/EFO first

### Collision-Aware Search
- Check if user's input matches any hit exactly
- If ambiguous, present top 3-5 options and ask user to select
- Prefer the most specific disease (not parent categories)
- For cancer, prefer the specific tumor type over generic "cancer"

### Key Disease IDs to Track
After disambiguation, store for downstream queries:
- `efo_id` - Primary ID for OpenTargets (e.g., `MONDO_0004975`)
- `disease_name` - Canonical name
- `synonyms` - For literature search expansion
- `therapeutic_areas` - For context
- `dbXRefs` - Cross-references (OMIM, UMLS, DOID, etc.)

---

## Phase 1: Genomics Layer Tools

**OpenTargets_get_associated_targets_by_disease_efoId** (primary):
- **Input**: `efoId` (string)
- **Output**: `{data: {disease: {id, name, associatedTargets: {count, rows: [{target: {id, approvedSymbol}, score}]}}}}`
- **NOTE**: Returns top 25 by default. Note the total `count`

**OpenTargets_get_evidence_by_datasource**:
- **Input**: `efoId` (string), `ensemblId` (string), optional `datasourceIds` (array), `size` (int, default 50)
- **Output**: `{data: {disease: {evidences: {count, rows: [{...}]}}}}`
- Key datasourceIds for genomics:
  - `['ot_genetics_portal']` - GWAS/genetics
  - `['gene2phenotype', 'genomics_england', 'orphanet']` - Rare variants
  - `['eva']` - ClinVar variants

**gwas_search_associations** (GWAS Catalog):
- **Input**: `disease_trait` (string), `size` (int, default 20)
- **Output**: `{data: [{association_id, p_value, or_per_copy_num, or_value, beta, risk_frequency, efo_traits}], metadata: {pagination: {totalElements}}}`
- **NOTE**: Use disease name (e.g., "Alzheimer"), not ID

**gwas_get_studies_for_trait**:
- **Input**: `disease_trait` (string), `size` (int)
- **NOTE**: May return empty if trait name does not match exactly. Try synonyms

**gwas_get_variants_for_trait**:
- **Input**: `disease_trait` (string), `size` (int)

**GWAS_search_associations_by_gene**:
- **Input**: `gene_name` (string)

**OpenTargets_search_gwas_studies_by_disease**:
- **Input**: `diseaseIds` (array of strings), `enableIndirect` (bool, default true), `size` (int, default 10)
- **Output**: `{data: {studies: {count, rows: [{id, studyType, traitFromSource, publicationFirstAuthor, publicationDate, pubmedId, nSamples, nCases, nControls}]}}}`

**clinvar_search_variants**:
- **Input**: `condition` (string) or `gene` (string), optional `max_results` (int)

### Phase 1 Workflow
1. Get associated genes from OpenTargets (overall scores)
2. For top 10-15 genes, get genetic evidence via `OpenTargets_get_evidence_by_datasource`
3. Search GWAS Catalog for associations
4. Search OpenTargets GWAS studies
5. Search ClinVar for rare variants
6. For top GWAS genes, check `GWAS_search_associations_by_gene`

### Gene Tracking
Maintain a dictionary of genes found in genomics layer:
```python
genomics_genes = {
    'PSEN1': {'score': 0.87, 'evidence': 'genetic', 'ensembl_id': 'ENSG00000080815', 'layer': 'genomics'},
    'APP': {'score': 0.82, 'evidence': 'genetic', 'ensembl_id': 'ENSG00000142192', 'layer': 'genomics'},
}
```

---

## Phase 2: Transcriptomics Layer Tools

**ExpressionAtlas_search_differential**:
- **Input**: optional `gene` (string), `condition` (string), `species` (string, default 'homo sapiens')

**ExpressionAtlas_search_experiments**:
- **Input**: optional `gene` (string), `condition` (string), `species` (string)

**expression_atlas_disease_target_score**:
- **Input**: `efoId` (string), `pageSize` (int, required)

**europepmc_disease_target_score**:
- **Input**: `efoId` (string), `pageSize` (int, required)

**HPA_get_rna_expression_by_source** (Human Protein Atlas):
- **Input**: `gene_name` (string), `source_type` (string: 'tissue', 'blood', 'brain'), `source_name` (string)
- **Output**: `{status, data: {gene_name, source_type, source_name, expression_value, expression_level, expression_unit}}`
- **NOTE**: ALL 3 params required. `source_type` options: 'tissue', 'blood', 'brain', 'cell_line', 'single_cell'

**HPA_get_rna_expression_in_specific_tissues**:
- **Input**: `gene_name` (string), `tissues` (array of strings)

**HPA_get_cancer_prognostics_by_gene**:
- **Input**: `gene_name` (string) - for cancer context

**HPA_get_subcellular_location**:
- **Input**: `gene_name` (string)

**HPA_search_genes_by_query**:
- **Input**: `query` (string)

### Phase 2 Workflow
1. Search Expression Atlas for differential expression studies
2. Get expression-based disease scores
3. Get literature-based disease scores (EuropePMC)
4. For top 10-15 genes from genomics layer, check tissue expression via HPA
5. Check disease-relevant tissue expression patterns
6. For cancer: check prognostic biomarkers

---

## Phase 3: Proteomics & Interaction Layer Tools

**STRING_get_interaction_partners** (primary PPI):
- **Input**: `protein_ids` (array of strings), `species` (int, default 9606), `confidence_score` (float, default 0.4), `limit` (int, default 20)
- **Output**: `{status: 'success', data: [{stringId_A, stringId_B, preferredName_A, preferredName_B, ncbiTaxonId, score, nscore, fscore, pscore, ascore, escore, dscore, tscore}]}`
- **NOTE**: `protein_ids` is an array, NOT string. Gene symbols like `['APOE']` work

**STRING_get_network**:
- **Input**: `protein_ids` (array), `species` (int), `confidence_score` (float)

**STRING_functional_enrichment**:
- **Input**: `protein_ids` (array), `species` (int)

**STRING_ppi_enrichment**:
- **Input**: `protein_ids` (array), `species` (int)

**intact_get_interactions**:
- **Input**: `identifier` (string - UniProt ID or gene name)

**intact_search_interactions**:
- **Input**: `query` (string), `first` (int, default 0), `max` (int, default 25)

**HPA_get_protein_interactions_by_gene**:
- **Input**: `gene_name` (string)
- **Output**: `{gene, interactions, interactor_count, interactors: [...]}`

**humanbase_ppi_analysis**:
- **Input**: `gene_list` (array), `tissue` (string), `max_node` (int), `interaction` (string), `string_mode` (bool)
- **NOTE**: ALL params required. `interaction` options: 'coexpression', 'interaction', 'coexpression_and_interaction'

### Phase 3 Workflow
1. Take top 15-20 genes from genomics + transcriptomics layers
2. Query STRING for interaction partners of each gene
3. Build composite PPI network using STRING_get_network
4. Test PPI enrichment (are genes more connected than random?)
5. Get functional enrichment from STRING
6. For disease-relevant tissue, get tissue-specific network (HumanBase)
7. Identify hub genes (highest degree centrality)
8. Check IntAct for experimentally validated interactions

### Hub Gene Analysis
- **Degree**: Number of interaction partners
- **Betweenness**: Number of shortest paths through node
- **Hub score**: Genes with degree > mean + 1 SD are hubs

---

## Phase 4: Pathway & Network Layer Tools

**enrichr_gene_enrichment_analysis** (primary enrichment):
- **Input**: `gene_list` (array, min 2), `libs` (array of library names)
- **Output**: `{status: 'success', data: '{...JSON string...}'}`
- **Key libraries**: `['KEGG_2021_Human']`, `['Reactome_2022']`, `['WikiPathway_2023_Human']`, `['GO_Biological_Process_2023']`, `['GO_Molecular_Function_2023']`, `['GO_Cellular_Component_2023']`
- **NOTE**: `data` field is a JSON string, needs parsing. `libs` is REQUIRED as array

**ReactomeAnalysis_pathway_enrichment**:
- **Input**: `identifiers` (string - space-separated gene list), optional `page_size` (int, default 20), `include_disease` (bool), `projection` (bool)
- **Output**: `{data: {token, analysis_type, pathways_found, pathways: [{pathway_id, name, species, is_disease, is_lowest_level, entities_found, entities_total, entities_ratio, p_value, fdr, reactions_found, reactions_total}]}}`

**Reactome_map_uniprot_to_pathways**:
- **Input**: `id` (string - UniProt accession)

**Reactome_get_pathway** / **Reactome_get_pathway_reactions**:
- **Input**: `stId` (string, e.g., 'R-HSA-73817')

**kegg_search_pathway**:
- **Input**: `keyword` (string)

**kegg_get_pathway_info**:
- **Input**: `pathway_id` (string, e.g., 'hsa04930')

**WikiPathways_search**:
- **Input**: `query` (string), optional `organism` (string, e.g., 'Homo sapiens')

### Phase 4 Workflow
1. Collect all genes from genomics + transcriptomics layers (top 20-30)
2. Run Enrichr enrichment for KEGG, Reactome, WikiPathways
3. Run ReactomeAnalysis for detailed Reactome enrichment with p-values
4. Search KEGG for disease-specific pathways
5. Search WikiPathways for disease pathways
6. For top Reactome pathways, get detailed reactions
7. Identify cross-pathway connections (genes in multiple pathways)

---

## Phase 5: Gene Ontology & Functional Annotation Tools

**enrichr_gene_enrichment_analysis** (GO enrichment):
- Use with `libs=['GO_Biological_Process_2023']` for BP
- Use with `libs=['GO_Molecular_Function_2023']` for MF
- Use with `libs=['GO_Cellular_Component_2023']` for CC

**GO_get_annotations_for_gene**:
- **Input**: `gene_id` (string - gene symbol or UniProt ID)

**GO_search_terms**:
- **Input**: `query` (string)

**QuickGO_annotations_by_gene**:
- **Input**: `gene_product_id` (string, e.g., 'UniProtKB:P02649'), optional `aspect` ('biological_process', 'molecular_function', 'cellular_component'), `taxon_id` (int: 9606), `limit` (int: 25)

**OpenTargets_get_target_gene_ontology_by_ensemblID**:
- **Input**: `ensemblId` (string)

### Phase 5 Workflow
1. Run Enrichr GO enrichment for all 3 aspects using combined gene list
2. For top 5 genes, get detailed GO annotations from QuickGO
3. For top genes, get OpenTargets GO terms
4. Summarize key biological processes, molecular functions, cellular components

---

## Phase 6: Therapeutic Landscape Tools

**OpenTargets_get_associated_drugs_by_disease_efoId** (primary):
- **Input**: `efoId` (string), `size` (int, REQUIRED - use 100)
- **Output**: `{data: {disease: {knownDrugs: {count, rows: [{drug: {id, name, tradeNames, maximumClinicalTrialPhase, isApproved, hasBeenWithdrawn}, phase, mechanismOfAction, target: {id, approvedSymbol}, disease: {id, name}, urls: [{url, name}]}]}}}}`

**OpenTargets_get_target_tractability_by_ensemblID**:
- **Input**: `ensemblId` (string)

**OpenTargets_get_associated_drugs_by_target_ensemblID**:
- **Input**: `ensemblId` (string), `size` (int, REQUIRED)

**search_clinical_trials**:
- **Input**: `query_term` (string, REQUIRED), optional `condition` (string), `intervention` (string), `pageSize` (int, default 10)
- **NOTE**: `query_term` is REQUIRED even if `condition` is provided

**OpenTargets_get_drug_mechanisms_of_action_by_chemblId**:
- **Input**: `chemblId` (string)

### Phase 6 Workflow
1. Get all drugs for disease from OpenTargets
2. For top disease-associated genes, check tractability
3. For top genes with no approved drugs, identify repurposing candidates
4. Search clinical trials for disease
5. For top approved drugs, get mechanism of action

### Drug Tracking
```python
drug_targets = {
    'PSEN1': {'drugs': ['Semagacestat'], 'tractability': 'small_molecule', 'clinical_phase': 3},
    'ACHE': {'drugs': ['Donepezil', 'Galantamine'], 'tractability': 'small_molecule', 'clinical_phase': 4},
}
```

---

## Tool Parameter Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` | Primary disambiguation |
| `OSL_get_efo_id_by_disease_name` | `disease` | Secondary disambiguation |
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId` | Returns top 25 genes |
| `OpenTargets_get_evidence_by_datasource` | `efoId`, `ensemblId`, `datasourceIds[]`, `size` | Per-gene evidence |
| `OpenTargets_search_gwas_studies_by_disease` | `diseaseIds[]`, `size` | GWAS studies |
| `gwas_search_associations` | `disease_trait`, `size` | GWAS Catalog |
| `clinvar_search_variants` | `condition` or `gene`, `max_results` | Rare variants |
| `ExpressionAtlas_search_differential` | `condition`, `species` | DEGs |
| `expression_atlas_disease_target_score` | `efoId`, `pageSize` (REQUIRED) | Expression scores |
| `europepmc_disease_target_score` | `efoId`, `pageSize` (REQUIRED) | Literature scores |
| `HPA_get_rna_expression_by_source` | `gene_name`, `source_type`, `source_name` (ALL REQUIRED) | Tissue expression |
| `STRING_get_interaction_partners` | `protein_ids[]`, `species` (9606), `limit` | PPI partners |
| `STRING_get_network` | `protein_ids[]`, `species` | PPI network |
| `STRING_functional_enrichment` | `protein_ids[]`, `species` | Functional enrichment |
| `STRING_ppi_enrichment` | `protein_ids[]`, `species` | Network significance |
| `intact_search_interactions` | `query`, `max` | Experimental PPIs |
| `humanbase_ppi_analysis` | `gene_list[]`, `tissue`, `max_node`, `interaction`, `string_mode` (ALL REQ) | Tissue PPI |
| `enrichr_gene_enrichment_analysis` | `gene_list[]`, `libs[]` (BOTH REQUIRED) | Pathway/GO enrichment |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (space-sep string) | Reactome enrichment |
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt accession) | Protein-pathway mapping |
| `kegg_search_pathway` | `keyword` | KEGG pathway search |
| `WikiPathways_search` | `query`, `organism` | WikiPathways search |
| `GO_get_annotations_for_gene` | `gene_id` | GO annotations |
| `QuickGO_annotations_by_gene` | `gene_product_id` (e.g., 'UniProtKB:P02649') | Detailed GO |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | `efoId`, `size` (REQUIRED) | Disease drugs |
| `OpenTargets_get_target_tractability_by_ensemblID` | `ensemblId` | Druggability |
| `search_clinical_trials` | `query_term` (REQUIRED), `condition`, `pageSize` | Clinical trials |
| `PubMed_search_articles` | `query`, `limit` | Literature |
| `ensembl_lookup_gene` | `gene_id`, `species` ('homo_sapiens' REQUIRED) | Gene lookup |
| `MyGene_query_genes` | `query`, `species`, `fields`, `size` | Gene info |
| `OpenTargets_get_similar_entities_by_disease_efoId` | `efoId`, `threshold`, `size` (ALL REQUIRED) | Similar diseases |
