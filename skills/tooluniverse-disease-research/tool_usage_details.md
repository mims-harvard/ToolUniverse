# Disease Research: Complete Tool Usage by Section

Detailed tool calls for each of the 10 research dimensions.

---

## Section 1: Identity (use ALL)

```python
tu.tools.OSL_get_efo_id_by_disease_name(disease=disease_name)
tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName=disease_name)
tu.tools.ols_search_efo_terms(query=disease_name)
tu.tools.ols_get_efo_term(obo_id=efo_id)
tu.tools.ols_get_efo_term_children(obo_id=efo_id, size=30)
tu.tools.umls_search_concepts(query=disease_name)
tu.tools.umls_get_concept_details(cui=cui)
tu.tools.icd_search_codes(query=disease_name, version="ICD10CM")
tu.tools.snomed_search_concepts(query=disease_name)
```

---

## Section 2: Clinical Presentation (use ALL)

```python
tu.tools.OpenTargets_get_associated_phenotypes_by_disease_efoId(efoId=efo_id)
tu.tools.get_HPO_ID_by_phenotype(query=symptom)  # for each key symptom
tu.tools.get_phenotype_by_HPO_ID(id=hpo_id)  # for top phenotypes
tu.tools.MedlinePlus_search_topics_by_keyword(term=disease_name, db="healthTopics")
tu.tools.MedlinePlus_get_genetics_condition_by_name(condition=disease_slug)
tu.tools.MedlinePlus_connect_lookup_by_code(cs=icd_oid, c=icd_code)
```

---

## Section 3: Genetics (use ALL)

```python
tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=efo_id)
tu.tools.OpenTargets_target_disease_evidence(efoId=efo_id, ensemblId=gene_id)  # top genes
tu.tools.ClinVar_search_variants(condition=disease_name, max_results=50)
tu.tools.clinvar_get_variant_details(variant_id=vid)  # top variants
tu.tools.clinvar_get_clinical_significance(variant_id=vid)
tu.tools.gwas_search_associations(disease_trait=disease_name, size=50)
tu.tools.gwas_get_variants_for_trait(disease_trait=disease_name, size=50)
tu.tools.gwas_get_associations_for_trait(disease_trait=disease_name, size=50)
tu.tools.gwas_get_studies_for_trait(disease_trait=disease_name, size=30)
tu.tools.GWAS_search_associations_by_gene(gene_name=gene)  # top genes
tu.tools.gnomad_get_variant_frequency(variant=variant)  # key variants
```

---

## Section 4: Treatment (use ALL)

```python
tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(efoId=efo_id, size=100)
tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName=drug)
tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
tu.tools.search_clinical_trials(condition=disease_name, pageSize=50)
tu.tools.get_clinical_trial_descriptions(nct_ids=nct_list)
tu.tools.get_clinical_trial_conditions_and_interventions(nct_ids=nct_list)
tu.tools.get_clinical_trial_eligibility_criteria(nct_ids=nct_list)
tu.tools.get_clinical_trial_outcome_measures(nct_ids=nct_list)
tu.tools.extract_clinical_trial_outcomes(nct_ids=nct_list)
tu.tools.GtoPdb_list_diseases(name=disease_name)
tu.tools.GtoPdb_get_disease(disease_id=gtopdb_id)
```

---

## Section 5: Pathways (use ALL)

```python
tu.tools.Reactome_get_diseases()
tu.tools.Reactome_map_uniprot_to_pathways(uniprot_id=uniprot_id)  # top genes
tu.tools.Reactome_get_pathway(stId=pathway_id)
tu.tools.Reactome_get_pathway_reactions(stId=pathway_id)
tu.tools.humanbase_ppi_analysis(gene_list=top_genes, tissue=relevant_tissue)
tu.tools.GTEx_get_expression_summary(gene_symbol=gene)  # top genes
tu.tools.HPA_get_rna_expression_by_source(gene_name=gene)
tu.tools.geo_search_datasets(query=disease_name)
```

---

## Section 6: Literature (use ALL)

```python
tu.tools.PubMed_search_articles(query=f'"{disease_name}"', limit=100)
tu.tools.PubMed_search_articles(query=f'"{disease_name}" AND epidemiology', limit=50)
tu.tools.PubMed_search_articles(query=f'"{disease_name}" AND mechanism', limit=50)
tu.tools.PubMed_search_articles(query=f'"{disease_name}" AND treatment', limit=50)
tu.tools.PubMed_get_article(pmid=pmid)  # top 10 articles
tu.tools.PubMed_get_related(pmid=key_pmid)
tu.tools.PubMed_get_cited_by(pmid=key_pmid)
tu.tools.OpenTargets_get_publications_by_disease_efoId(efoId=efo_id)
tu.tools.openalex_search_works(query=disease_name, limit=50)
tu.tools.EuropePMC_search_articles(query=disease_name, limit=50)
tu.tools.SemanticScholar_search_papers(query=disease_name, limit=50)
```

---

## Section 7: Similar Diseases

```python
tu.tools.OpenTargets_get_similar_entities_by_disease_efoId(efoId=efo_id, threshold=0.3, size=30)
```

---

## Section 8: Cancer-Specific (if cancer)

```python
tu.tools.civic_search_diseases(limit=100)
tu.tools.civic_search_genes(query=gene, limit=20)
tu.tools.civic_get_variants_by_gene(gene_id=civic_gene_id, limit=50)
tu.tools.civic_get_variant(variant_id=vid)
tu.tools.civic_get_evidence_item(evidence_id=eid)
tu.tools.civic_search_therapies(limit=100)
tu.tools.civic_search_molecular_profiles(limit=50)
```

---

## Section 9: Pharmacology

```python
tu.tools.GtoPdb_get_targets(target_type=type, limit=50)  # GPCR, ion channel, etc
tu.tools.GtoPdb_get_target(target_id=tid)
tu.tools.GtoPdb_get_target_interactions(target_id=tid)
tu.tools.GtoPdb_search_interactions(approved_only=True)
tu.tools.GtoPdb_list_ligands(ligand_type="Approved")
```

---

## Section 10: Safety (use ALL)

```python
tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId=cid)
tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId=cid)
tu.tools.extract_clinical_trial_adverse_events(nct_ids=nct_list)
tu.tools.FAERS_count_reactions_by_drug_event(drug=drug_name, event=event)
tu.tools.AdverseEventPredictionQuestionGenerator(disease_name=disease, drug_name=drug)
```

---

## Research Protocol

### Step 1: Initialize Report

```python
from datetime import datetime

filename = f"{disease_name.lower().replace(' ', '_')}_research_report.md"
# Write template with placeholders for each section
```

### Step 2: Research Each Dimension

For EACH piece of information, track:
- **Tool name** that provided the data
- **Parameters** used in the query
- **Timestamp** of the query

### Step 3: Update Report After Each Dimension

```python
# Read current file
# Replace placeholder with formatted content
# Write back immediately
# Continue to next dimension
```
