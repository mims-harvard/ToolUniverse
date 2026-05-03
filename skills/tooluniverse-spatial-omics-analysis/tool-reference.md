# Spatial Omics: Tool Parameter & Response Reference

Critical parameter names and response formats. Referenced from SKILL.md.

---

## Verified Parameter Names

| Tool | Parameter | CORRECT | Common MISTAKE | Notes |
|------|-----------|---------|----------------|-------|
| `MyGene_query_genes` | query | `query` | `q` | Filter results by `symbol` field |
| `STRING_functional_enrichment` | identifiers | `protein_ids` (array) | `identifiers` | Also needs `species=9606` |
| `STRING_get_interaction_partners` | identifiers | `protein_ids` (array) | `identifiers` | `limit`, `confidence_score` optional |
| `ReactomeAnalysis_pathway_enrichment` | genes | `identifiers` (string) | Array | SPACE-SEPARATED string, NOT array |
| `HPA_get_subcellular_location` | gene | `gene_name` | `ensembl_id` | Uses gene symbol |
| `HPA_get_cancer_prognostics_by_gene` | gene | `ensembl_id` | `gene_name` | Uses Ensembl ID, NOT symbol |
| `HPA_get_rna_expression_by_source` | params | `gene_name`, `source_type`, `source_name` | - | ALL 3 required |
| `HPA_get_rna_expression_in_specific_tissues` | gene | `ensembl_id` | `gene_name` | Uses Ensembl ID |
| `HPA_get_comprehensive_gene_details_by_ensembl_id` | all params | ALL 5 required | Missing booleans | Set booleans to False except expression |
| `OpenTargets_get_target_tractability_by_ensemblID` | target | `ensemblId` | `ensemblID` | camelCase |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | target | `ensemblId`, `size` | - | Both REQUIRED |
| `OpenTargets_get_associated_targets_by_disease_efoId` | disease | `efoId` | `diseaseId` | Returns nested response |
| `DGIdb_get_gene_druggability` | genes | `genes` (array) | `gene_name` | Array of strings |
| `DGIdb_get_drug_gene_interactions` | genes | `genes` (array) | `gene_name` | Array of strings |
| `clinical_trials_search` | action | `action='search_studies'` | Missing action | `action` is REQUIRED |
| `ensembl_lookup_gene` | species | `species='homo_sapiens'` | No species | REQUIRED parameter |
| GTEx tools | gencode | `gencode_id` (array) | `gene_id` | Requires versioned GENCODE ID |

---

## Response Format Reference

| Tool | Response Format | Key Fields |
|------|----------------|------------|
| `STRING_functional_enrichment` | `{status, data: [{category, term, description, p_value, fdr, inputGenes}]}` | Filter by FDR < 0.05 |
| `ReactomeAnalysis_pathway_enrichment` | `{data: {pathways: [{pathway_id, name, p_value, fdr, entities_found, entities_total}]}}` | Top 20 returned |
| `STRING_get_interaction_partners` | `{status, data: [{preferredName_A, preferredName_B, score}]}` | Score > 0.7 for high confidence |
| `MyGene_query_genes` | `{hits: [{_id, symbol, name, ensembl: {gene}, entrezgene}]}` | Filter by exact symbol match |
| `HPA_get_subcellular_location` | `{gene_name, main_locations: [], additional_locations: [], location_summary}` | Direct dict response |
| `OpenTargets_get_target_tractability_by_ensemblID` | `{data: {target: {id, tractability: [{label, modality, value}]}}}` | Check value=true |
| `DGIdb_get_gene_druggability` | `{data: {genes: {nodes: [{name, geneCategories: [{name}]}]}}}` | GraphQL response |
| `PubMed_search_articles` | Plain list of `[{pmid, title, authors, journal, pub_date}]` | No data wrapper |
| `clinical_trials_search` | `{total_count, studies: [{nctId, title, status, conditions}]}` | total_count can be None |

---

## Fallback Strategies

### Pathway Enrichment
- **Primary**: STRING_functional_enrichment (most comprehensive, one call)
- **Fallback**: ReactomeAnalysis_pathway_enrichment (Reactome-specific)
- **Default**: Individual gene GO annotations (GO_get_annotations_for_gene)

### Tissue Expression
- **Primary**: HPA_get_rna_expression_by_source
- **Fallback**: HPA_get_comprehensive_gene_details_by_ensembl_id
- **Default**: Note "tissue expression data unavailable"

### Disease Association
- **Primary**: OpenTargets_get_associated_targets_by_disease_efoId
- **Fallback**: OpenTargets_target_disease_evidence (per gene)
- **Default**: Skip disease section if no disease context

### Drug Information
- **Primary**: OpenTargets_get_associated_drugs_by_target_ensemblID
- **Fallback**: DGIdb_get_drug_gene_interactions
- **Default**: Note "no approved drugs identified"

### Literature
- **Primary**: PubMed_search_articles
- **Fallback**: openalex_literature_search
- **Default**: Note "no spatial-specific literature found"

---

## Limitations & Known Issues

### Database-Specific
- **Enrichment**: `enrichr_gene_enrichment_analysis` returns connectivity graph (107MB), NOT standard enrichment. Use `STRING_functional_enrichment` instead
- **GTEx**: SOAP-style tools requiring `operation` parameter; needs versioned GENCODE IDs (e.g., `ENSG00000141510.16`)
- **HPA**: Some tools use `gene_name`, others use `ensembl_id` - check parameter reference
- **OpenTargets**: Disease IDs use underscore format (`MONDO_0007254`), not colon
- **cBioPortal_get_cancer_studies**: BROKEN - has literal `{limit}` in URL causing 400 error

### Conceptual
- **No raw spatial data processing**: Analyzes gene LISTS, not raw spatial matrices
- **No spatial statistics**: Cannot perform Moran's I, spatial autocorrelation, or variogram analysis
- **No image analysis**: Cannot process H&E or fluorescence images
- **No deconvolution**: Use BayesSpace, cell2location, RCTD externally
- **Ligand-receptor inference**: Based on gene co-expression + known pairs, not spatial proximity statistics (use CellChat, NicheNet, COMMOT externally)

### Technical
- **Large gene lists**: >200 genes may slow STRING queries; batch or sample
- **Response format variability**: Always check both dict and list response types
- **Rate limits**: STRING and OpenTargets may throttle frequent requests
