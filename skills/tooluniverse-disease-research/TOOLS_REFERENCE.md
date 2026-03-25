# Complete Tool Reference for Disease Information

Comprehensive reference of all ToolUniverse tools for disease information retrieval.

---

## 1. Disease Identification & Ontology

### OSL_get_efo_id_by_disease_name
**Purpose**: Map disease name to EFO ID (primary entry point)
```python
tu.tools.OSL_get_efo_id_by_disease_name(disease="diabetes mellitus")
# Returns: {"efo_id": "EFO:0000400", "name": "diabetes mellitus"}
```

### ols_search_efo_terms
**Purpose**: Search EFO ontology for disease terms
```python
tu.tools.ols_search_efo_terms(query="diabetes mellitus", rows=10)
# Returns: terms with iri, obo_id, label, description
```

### ols_get_efo_term
**Purpose**: Get detailed EFO term information
```python
tu.tools.ols_get_efo_term(obo_id="EFO:0000400")
# Returns: synonyms, description, has_children, is_obsolete
```

### ols_get_efo_term_children
**Purpose**: Get disease subtypes/children
```python
tu.tools.ols_get_efo_term_children(obo_id="EFO:0000400", size=20)
# Returns: child terms (disease subtypes)
```

### OpenTargets_get_disease_id_description_by_name
**Purpose**: Search OpenTargets for disease by name
```python
tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="Diabetes Mellitus")
# Returns: id, name, description
```

### umls_search_concepts
**Purpose**: Search UMLS for medical concepts
```python
tu.tools.umls_search_concepts(query="diabetes", sabs="SNOMEDCT_US", pageSize=25)
# Returns: CUI, name, source
# Note: Requires UMLS_API_KEY
```

### umls_get_concept_details
**Purpose**: Get UMLS concept details by CUI
```python
tu.tools.umls_get_concept_details(cui="C0011849")
# Returns: definitions, semantic types
```

### icd_search_codes
**Purpose**: Search ICD-10/ICD-11 codes
```python
tu.tools.icd_search_codes(query="diabetes", version="ICD10CM")
# Returns: ICD codes with descriptions
```

### snomed_search_concepts
**Purpose**: Search SNOMED CT concepts
```python
tu.tools.snomed_search_concepts(query="diabetes mellitus")
# Returns: SNOMED concepts with codes
```

---

## 2. Clinical Manifestations & Phenotypes

### OpenTargets_get_associated_phenotypes_by_disease_efoId
**Purpose**: Get HPO phenotypes for disease
```python
tu.tools.OpenTargets_get_associated_phenotypes_by_disease_efoId(efoId="EFO_0000384")
# Returns: phenotypeHPO (id, name, description), phenotypeEFO
```

### get_HPO_ID_by_phenotype (Monarch)
**Purpose**: Convert symptom name to HPO ID
```python
tu.tools.get_HPO_ID_by_phenotype(query="seizure", limit=5)
# Returns: HPO IDs matching the phenotype
```

### get_phenotype_by_HPO_ID (Monarch)
**Purpose**: Get phenotype details by HPO ID
```python
tu.tools.get_phenotype_by_HPO_ID(id="HP:0001250")
# Returns: phenotype details
```

### get_joint_associated_diseases_by_HPO_ID_list (Monarch)
**Purpose**: Find diseases from list of phenotypes (differential diagnosis)
```python
tu.tools.get_joint_associated_diseases_by_HPO_ID_list(
    HPO_ID_list=["HP:0001250", "HP:0001251"], limit=20
)
# Returns: diseases associated with these phenotypes
```

### MedlinePlus_search_topics_by_keyword
**Purpose**: Search consumer health information
```python
tu.tools.MedlinePlus_search_topics_by_keyword(
    term="diabetes", db="healthTopics", rettype="topic"
)
# Returns: topics with title, summary, url
```

### MedlinePlus_get_genetics_condition_by_name
**Purpose**: Get genetic condition information
```python
tu.tools.MedlinePlus_get_genetics_condition_by_name(condition="alzheimer-disease")
# Returns: description, genes, synonyms
```

### MedlinePlus_connect_lookup_by_code
**Purpose**: Look up by clinical code (ICD-10, LOINC)
```python
tu.tools.MedlinePlus_connect_lookup_by_code(
    cs="2.16.840.1.113883.6.90",  # ICD-10 CM OID
    c="E11.9"  # Type 2 diabetes
)
# Returns: MedlinePlus health information
```

---

## 3. Genetic & Molecular Basis

### OpenTargets_get_associated_targets_by_disease_efoId
**Purpose**: Get disease-gene associations with scores
```python
tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId="EFO_0000384")
# Returns: target.id, target.approvedSymbol, score
```

### OpenTargets_get_diseases_phenotypes_by_target_ensembl
**Purpose**: Find diseases associated with a gene (reverse lookup)
```python
tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(ensemblId="ENSG00000141510")
# Returns: diseases associated with this gene
```

### OpenTargets_target_disease_evidence
**Purpose**: Get evidence for target-disease association
```python
tu.tools.OpenTargets_target_disease_evidence(
    efoId="EFO_0000384", ensemblId="ENSG00000141510"
)
# Returns: evidence details, mutation data
```

### clinvar_search_variants
**Purpose**: Search ClinVar for variants
```python
tu.tools.ClinVar_search_variants(condition="breast cancer", max_results=20)
# OR
tu.tools.ClinVar_search_variants(gene="BRCA1", max_results=20)
# Returns: variant IDs, count
```

### clinvar_get_variant_details
**Purpose**: Get variant details by ClinVar ID
```python
tu.tools.clinvar_get_variant_details(variant_id="12345")
# Returns: variant information
```

### clinvar_get_clinical_significance
**Purpose**: Get pathogenicity classification
```python
tu.tools.clinvar_get_clinical_significance(variant_id="12345")
# Returns: clinical significance data
```

### gwas_search_associations
**Purpose**: Search GWAS associations
```python
tu.tools.gwas_search_associations(disease_trait="diabetes", size=20)
# Returns: associations with p_value, snp_allele, mapped_genes
```

### gwas_get_variants_for_trait
**Purpose**: Get variants for specific trait
```python
tu.tools.gwas_get_variants_for_trait(disease_trait="breast cancer", size=50)
# Returns: variants with rs_id, locations, mapped_genes
```

### gwas_get_associations_for_trait
**Purpose**: Get associations sorted by significance
```python
tu.tools.gwas_get_associations_for_trait(disease_trait="type 2 diabetes", size=20)
# Returns: associations sorted by p-value
```

### gwas_get_studies_for_trait
**Purpose**: Get GWAS studies for trait
```python
tu.tools.gwas_get_studies_for_trait(disease_trait="diabetes", size=20)
# Returns: study details, sample sizes
```

### gwas_get_snp_by_id
**Purpose**: Get SNP details by rs ID
```python
tu.tools.gwas_get_snp_by_id(rs_id="rs1234")
# Returns: SNP details, locations, alleles
```

### gwas_get_associations_for_snp
**Purpose**: Get all associations for a SNP
```python
tu.tools.gwas_get_associations_for_snp(rs_id="rs12345", size=20)
# Returns: traits associated with this SNP
```

### gwas_get_snps_for_gene
**Purpose**: Get SNPs mapped to a gene
```python
tu.tools.gwas_get_snps_for_gene(mapped_gene="BRCA1", size=20)
# Returns: SNPs in/near this gene
```

### GWAS_search_associations_by_gene
**Purpose**: Search GWAS by gene name
```python
tu.tools.GWAS_search_associations_by_gene(gene_name="TP53", size=10)
# Returns: associations for gene
```

### gnomad_get_variant_frequency
**Purpose**: Get population variant frequencies
```python
tu.tools.gnomad_get_variant_frequency(variant="1-55505647-G-T")
# Returns: population frequencies (gnomAD data)
```

---

## 4. Treatment Landscape

### OpenTargets_get_associated_drugs_by_disease_efoId
**Purpose**: Get drugs for disease
```python
tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(efoId="EFO_0000384", size=100)
# Returns: drug info, phase, status, mechanism, target
```

### OpenTargets_get_drug_chembId_by_generic_name
**Purpose**: Get ChEMBL ID from drug name
```python
tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="Aspirin")
# Returns: chemblId, name, description
```

### OpenTargets_get_drug_mechanisms_of_action_by_chemblId
**Purpose**: Get drug mechanism of action
```python
tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL25")
# Returns: mechanism, actionType, targets
```

### OpenTargets_get_drug_warnings_by_chemblId
**Purpose**: Get drug warnings
```python
tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId="CHEMBL25")
# Returns: warningType, description, toxicityClass
```

### OpenTargets_get_drug_blackbox_status_by_chembl_ID
**Purpose**: Check withdrawn/blackbox status
```python
tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId="CHEMBL25")
# Returns: hasBeenWithdrawn, blackBoxWarning
```

### search_clinical_trials
**Purpose**: Search ClinicalTrials.gov
```python
tu.tools.search_clinical_trials(
    condition="lung cancer",
    intervention="pembrolizumab",
    query_term="Phase III",
    pageSize=20
)
# Returns: NCT ID, brief_title, status, phase
```

### get_clinical_trial_descriptions
**Purpose**: Get trial descriptions
```python
tu.tools.get_clinical_trial_descriptions(
    nct_ids=["NCT04852770", "NCT01728545"],
    description_type="full"
)
# Returns: detailed trial descriptions
```

### get_clinical_trial_conditions_and_interventions
**Purpose**: Get conditions and interventions
```python
tu.tools.get_clinical_trial_conditions_and_interventions(
    nct_ids=["NCT01158625"],
    condition_and_intervention=""
)
# Returns: conditions, arm_groups, interventions
```

### get_clinical_trial_eligibility_criteria
**Purpose**: Get eligibility criteria
```python
tu.tools.get_clinical_trial_eligibility_criteria(
    nct_ids=["NCT01158625"],
    eligibility_criteria=""
)
# Returns: eligibility_criteria, sex, age range
```

### get_clinical_trial_outcome_measures
**Purpose**: Get outcome measures
```python
tu.tools.get_clinical_trial_outcome_measures(
    nct_ids=["NCT01158625"],
    outcome_measures="primary"
)
# Returns: primary/secondary outcomes
```

### extract_clinical_trial_outcomes
**Purpose**: Extract efficacy results
```python
tu.tools.extract_clinical_trial_outcomes(
    nct_ids=["NCT01158625"],
    outcome_measure="overall survival"
)
# Returns: detailed outcome results
```

### extract_clinical_trial_adverse_events
**Purpose**: Extract safety data
```python
tu.tools.extract_clinical_trial_adverse_events(
    nct_ids=["NCT01158625"],
    organ_systems=["Cardiac Disorders"],
    adverse_event_type="serious"
)
# Returns: adverse event data
```

---

## 5. Biological Pathways & Mechanisms

### Reactome_get_diseases
**Purpose**: Get all disease-associated pathways
```python
tu.tools.Reactome_get_diseases()
# Returns: disease pathways with DOID annotations
```

### Reactome_get_pathway
**Purpose**: Get pathway details
```python
tu.tools.Reactome_get_pathway(stId="R-HSA-73817")
# Returns: pathway metadata, events, references
```

### Reactome_get_pathway_reactions
**Purpose**: Get reactions in pathway
```python
tu.tools.Reactome_get_pathway_reactions(stId="R-HSA-73817")
# Returns: reactions and subpathways
```

### Reactome_map_uniprot_to_pathways
**Purpose**: Get pathways for protein
```python
tu.tools.Reactome_map_uniprot_to_pathways(id="P04637")
# Returns: pathways containing this protein
```

### Reactome_map_uniprot_to_reactions
**Purpose**: Get reactions for protein
```python
tu.tools.Reactome_map_uniprot_to_reactions(id="P04637")
# Returns: reactions involving this protein
```

### Reactome_list_top_pathways
**Purpose**: List top-level pathways
```python
tu.tools.Reactome_list_top_pathways(species="Homo sapiens")
# Returns: top-level pathway hierarchy
```

### humanbase_ppi_analysis
**Purpose**: Tissue-specific protein interactions
```python
tu.tools.humanbase_ppi_analysis(
    gene_list=["TP53", "MDM2"],
    tissue="brain",
    max_node=10,
    interaction="co-expression",
    string_mode=True
)
# Returns: PPI network, GO biological processes
```

### gtex_get_expression_by_gene
**Purpose**: Get tissue-specific gene expression (GTEx)
```python
tu.tools.gtex_get_expression_by_gene(gene="BRCA1")
# Returns: expression levels across tissues
```

### HPA_get_protein_expression
**Purpose**: Get protein expression from Human Protein Atlas
```python
tu.tools.HPA_get_protein_expression(gene="TP53")
# Returns: protein expression by tissue, subcellular localization
```

### geo_search_datasets
**Purpose**: Search GEO for gene expression datasets
```python
tu.tools.geo_search_datasets(query="Alzheimer disease", max_results=20)
# Returns: GEO dataset accessions, descriptions
```

---

## 6. Literature & Research

### PubMed_search_articles
**Purpose**: Search biomedical literature
```python
tu.tools.PubMed_search_articles(
    query='"Alzheimer disease" AND biomarker',
    limit=50
)
# Returns: PMIDs
```

### PubMed_get_article
**Purpose**: Get article metadata
```python
tu.tools.PubMed_get_article(pmid="12345678")
# Returns: title, abstract, authors, journal
```

### PubMed_get_related
**Purpose**: Get related articles
```python
tu.tools.PubMed_get_related(pmid="20210808", limit=20)
# Returns: related PMIDs
```

### PubMed_get_cited_by
**Purpose**: Get citing articles
```python
tu.tools.PubMed_get_cited_by(pmid="20210808", limit=20)
# Returns: PMIDs of citing articles
```

### OpenTargets_get_publications_by_disease_efoId
**Purpose**: Get publications for disease
```python
tu.tools.OpenTargets_get_publications_by_disease_efoId(efoId="EFO_0000384")
# Returns: disease-related publications
```

### OpenTargets_get_publications_by_target_ensemblID
**Purpose**: Get publications for target
```python
tu.tools.OpenTargets_get_publications_by_target_ensemblID(ensemblId="ENSG00000141510")
# Returns: target-related publications
```

### openalex_search_works
**Purpose**: Search OpenAlex for works with institutional data
```python
tu.tools.openalex_search_works(query="Alzheimer disease biomarker", limit=50)
# Returns: works with authors, institutions, citations, topics
```

### europe_pmc_search_abstracts
**Purpose**: Search Europe PMC literature
```python
tu.tools.EuropePMC_search_articles(query="Parkinson disease mechanism", limit=50)
# Returns: abstracts from Europe PMC
```

### semantic_scholar_search_papers
**Purpose**: Search Semantic Scholar with citation networks
```python
tu.tools.SemanticScholar_search_papers(query="cancer immunotherapy", limit=50)
# Returns: papers with citation counts, influential citations
```

---

## 7. Similar Diseases

### OpenTargets_get_similar_entities_by_disease_efoId
**Purpose**: Find similar diseases, targets, drugs
```python
tu.tools.OpenTargets_get_similar_entities_by_disease_efoId(
    efoId="EFO_0000249",
    threshold=0.5,
    size=20
)
# Returns: similar entities with scores
```

---

## 8. Cancer-Specific (CIViC)

### civic_search_diseases
**Purpose**: Search cancer diseases
```python
tu.tools.civic_search_diseases(limit=50)
# Returns: cancer diseases in CIViC
```

### civic_search_genes
**Purpose**: Search cancer genes
```python
tu.tools.civic_search_genes(query="BRAF", limit=10)
# Returns: gene id, name, description
```

### civic_get_variants_by_gene
**Purpose**: Get variants for gene
```python
tu.tools.civic_get_variants_by_gene(gene_id=5, limit=50)
# Returns: variants for gene
```

### civic_get_variant
**Purpose**: Get variant details
```python
tu.tools.civic_get_variant(variant_id=4170)
# Returns: variant details
```

### civic_get_evidence_item
**Purpose**: Get clinical evidence
```python
tu.tools.civic_get_evidence_item(evidence_id=116)
# Returns: evidence description, level, type
```

### civic_search_therapies
**Purpose**: Search cancer therapies
```python
tu.tools.civic_search_therapies(limit=50)
# Returns: therapy list
```

### civic_search_molecular_profiles
**Purpose**: Search biomarker profiles
```python
tu.tools.civic_search_molecular_profiles(limit=50)
# Returns: molecular profiles
```

---

## 9. Pharmacology (GtoPdb)

### GtoPdb_list_diseases
**Purpose**: Search diseases
```python
tu.tools.GtoPdb_list_diseases(name="diabetes", limit=20)
# Returns: diseases with IDs, OMIM, DOID
```

### GtoPdb_get_disease
**Purpose**: Get disease details
```python
tu.tools.GtoPdb_get_disease(disease_id=652)
# Returns: targets, ligands, description
```

### GtoPdb_get_targets
**Purpose**: Get pharmacological targets
```python
tu.tools.GtoPdb_get_targets(target_type="GPCR", limit=20)
# Returns: targets with drugs, ligands
```

### GtoPdb_get_target
**Purpose**: Get target details
```python
tu.tools.GtoPdb_get_target(target_id=290)
# Returns: detailed target info
```

### GtoPdb_get_target_interactions
**Purpose**: Get target-ligand interactions
```python
tu.tools.GtoPdb_get_target_interactions(
    target_id=290,
    action_type="Agonist"
)
# Returns: interactions with affinity
```

### GtoPdb_search_interactions
**Purpose**: Search drug-target interactions
```python
tu.tools.GtoPdb_search_interactions(
    approved_only=True,
    limit=100
)
# Returns: interaction data
```

### GtoPdb_list_ligands
**Purpose**: Search ligands/drugs
```python
tu.tools.GtoPdb_list_ligands(ligand_type="Approved", limit=20)
# Returns: ligands with properties
```

### GtoPdb_get_ligand
**Purpose**: Get ligand details
```python
tu.tools.GtoPdb_get_ligand(ligand_id=1016)
# Returns: SMILES, properties, targets
```

---

## 10. Protein Information (UniProt)

### UniProt_get_disease_variants_by_accession
**Purpose**: Get disease-associated variants
```python
tu.tools.UniProt_get_disease_variants_by_accession(accession="P05067")
# Returns: disease variants for protein
```

### UniProt_get_function_by_accession
**Purpose**: Get protein function
```python
tu.tools.UniProt_get_function_by_accession(accession="P05067")
# Returns: protein function description
```

### UniProt_get_subcellular_location_by_accession
**Purpose**: Get protein localization
```python
tu.tools.UniProt_get_subcellular_location_by_accession(accession="P05067")
# Returns: cellular location
```

---

## 11. Adverse Events

### AdverseEventPredictionQuestionGenerator
**Purpose**: Generate safety questions
```python
tu.tools.AdverseEventPredictionQuestionGenerator(
    disease_name="Alzheimer's disease",
    drug_name="Kisunla"
)
# Returns: safety prediction questions
```

### AdverseEventICDMapper
**Purpose**: Map adverse events to ICD codes
```python
tu.tools.AdverseEventICDMapper(
    source_text="Patient experienced headache and nausea"
)
# Returns: ICD-10 codes for adverse events
```

### FAERS_count_reactions_by_drug_event
**Purpose**: Get FDA adverse event reports count
```python
tu.tools.FAERS_count_reactions_by_drug_event(drug="metformin", event="nausea")
# Returns: count of adverse event reports from FAERS
```

---

## ID Mapping Summary

| From | To | Tool |
|------|-----|------|
| Disease name | EFO ID | `OSL_get_efo_id_by_disease_name` |
| Disease name | EFO ID | `OpenTargets_get_disease_id_description_by_name` |
| Drug name | ChEMBL ID | `OpenTargets_get_drug_chembId_by_generic_name` |
| Gene symbol | Ensembl ID | Use OpenTargets search |
| UniProt ID | Pathways | `Reactome_map_uniprot_to_pathways` |
| Symptom | HPO ID | `get_HPO_ID_by_phenotype` |
| HPO IDs | Diseases | `get_joint_associated_diseases_by_HPO_ID_list` |
| Gene | Diseases | `OpenTargets_get_diseases_phenotypes_by_target_ensembl` |
| SNP rs ID | Diseases | `gwas_get_associations_for_snp` |

---

## Query Construction Tips

### PubMed Queries

**Good query construction**:
```python
# Specific disease + topic
query = '"Alzheimer disease" AND mechanism'

# Multiple terms with OR
query = '"Parkinson disease" OR "Parkinson\'s disease" AND therapy'

# Exclude terms
query = '"diabetes" NOT "gestational diabetes" AND treatment'

# Recent papers only
query = '"cancer" AND immunotherapy'
arguments = {'query': query, 'years': 2}  # Last 2 years
```

**Field-specific searches**:
```python
# Title only
query = 'Alzheimer[Title] AND biomarker[Title]'

# MeSH terms
query = '"Alzheimer Disease"[MeSH] AND "Drug Therapy"[MeSH]'

# Publication types
query = '"diabetes" AND systematic review[Publication Type]'
```

### OpenTargets Queries

**Disease ID formats**:
- EFO IDs: `EFO_0000249` (Alzheimer's)
- Orphanet: `Orphanet_558` (rare diseases)
- MONDO: `MONDO_0008199`

**Finding disease IDs**:
```python
# Search by name
result = tu.tools.OSL_get_efo_id_by_disease_name(disease='Alzheimer disease')
efo_id = result.get('efo_id')  # Get EFO ID
```

### Clinical Trials Queries

**Effective search strategies**:
```python
# By condition
{'condition': 'Alzheimer Disease'}

# By intervention
{'condition': 'cancer', 'intervention': 'pembrolizumab'}

# By phase
{'condition': 'diabetes', 'query_term': 'Phase 3'}

# By status
{'condition': 'depression', 'status': 'Recruiting'}
```

---

## Common Issues & Solutions

### Issue: Disease name vs EFO ID mismatch

**Solution**: Always try to get both
```python
if disease_name and not disease_id:
    # Get EFO ID from name
    result = tu.tools.OSL_get_efo_id_by_disease_name(disease=disease_name)
    disease_id = result.get('efo_id')
elif disease_id and not disease_name:
    # Get name from EFO ID
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(efoId=disease_id)
    disease_name = result.get('name')
```

### Issue: Empty results from a tool

**Solution**: Try alternative tools or queries
```python
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id)
if not targets.get('data'):
    # Try PubMed text mining as fallback
    pmids = tu.tools.PubMed_search_articles(query=f'"{disease_name}" AND gene')
```

### Issue: Timeout on slow queries

**Solution**: Set appropriate timeouts and handle gracefully
```python
try:
    result = future.result(timeout=120)  # 2 minutes
except TimeoutError:
    result = {'status': 'timeout', 'message': 'Query too slow'}
```

### Issue: Rate limiting

**Solution**: Add delays or use caching
```python
import time
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(tool_name, args_json):
    # Cache results to avoid repeated queries
    import json
    return tu.run({'name': tool_name, 'arguments': json.loads(args_json)})
```

---

## Performance Optimization

### Parallel Execution Best Practices

```python
# Good: Independent paths in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        'path1': executor.submit(path1_func),
        'path2': executor.submit(path2_func),
        # All independent
    }

# Bad: Dependent queries in parallel
# Don't parallelize if path2 needs path1 results
```

### Result Limiting

```python
# Limit results to avoid overwhelming output
top_targets = targets['data'][:10]  # Top 10 only
top_pathways = pathways['data'][:5]  # Top 5 only
top_drugs = drugs['data'][:5]  # Top 5 only
```

### Caching Strategy

```python
# Cache expensive queries
cache = {}

def get_gene_info(gene_id):
    if gene_id in cache:
        return cache[gene_id]
    
    result = tu.tools.UniProt_get_entry_by_accession(accession=gene_id)
    cache[gene_id] = result
    return result
```

---

## Data Quality Indicators

Track data quality in your synthesis:

```python
quality_metrics = {
    'sources_queried': 15,  # How many tools used
    'sources_successful': 12,  # How many returned data
    'completeness_score': 0.80,  # 80% of paths succeeded
    'data_recency': {
        'publications': '2024',  # Most recent paper
        'trials': '2024',  # Most recent trial
        'approval': '2023'  # Most recent drug approval
    }
}
```

Include in report:
```
Data Quality: ⭐⭐⭐⭐ (80% complete, 12/15 sources)
Most recent data: 2024
```
