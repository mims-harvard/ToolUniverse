# Literature Deep Research - Complete Tool Reference

**All tool names for literature search + annotation databases used in enhanced research strategy.**

---

## Literature Search Tools (23)

### Biomedical & Life Sciences
```python
'PubMed_search_articles'          # 35M+ papers - primary biomedical
'PMC_search_papers'               # Full-text biomedical archive (NIH)
'EuropePMC_search_articles'       # 42M+ European biomedical (use source='PPR' for preprints)
'BioRxiv_get_preprint'            # Get bioRxiv preprint by DOI (not keyword search)
'BioRxiv_list_recent_preprints'   # List recent preprints by subject area
'MedRxiv_get_preprint'            # Get medRxiv preprint by DOI (not keyword search)
# For preprint keyword search, use: EuropePMC_search_articles(source='PPR')
```

### Computer Science
```python
'DBLP_search_publications'        # 6M+ CS publications
'ArXiv_search_papers'             # Physics/CS/math preprints
'SemanticScholar_search_papers'   # 200M+ AI-ranked papers
```

### General Academic
```python
'openalex_literature_search'      # 250M+ works across fields
'Crossref_search_works'           # 140M+ DOI registry (use filter:"type:journal-article")
'Fatcat_search_scholar'           # Internet Archive
'DOAJ_search_articles'            # Open access journals
'CORE_search_papers'              # 200M+ aggregated open access papers
'openalex_search_works'           # OpenAlex with sort/filter support
```

### Multi-Source Deep Search
```python
'advanced_literature_search_agent' # Deep multi-source search agent (slower, thorough)
```

### Regional/Specialized
```python
'OpenAIRE_search_publications'    # EU-funded research
'HAL_search_archive'              # French national archive
'OSF_search_preprints'            # Social science preprints
'Zenodo_search_records'           # Datasets, software, publications
```

### Text Mining / NER
```python
'PubTator3_LiteratureSearch'      # PubTator literature search with entity annotations
'PubTator3_EntityAutocomplete'    # Entity name autocomplete (genes, diseases, chemicals)
'PubTator3_get_annotations'       # Get entity annotations for a PMID/PMCID
```

---

## Citation & Metadata Tools (19)

### PubMed Citation Tools
```python
'PubMed_get_article'              # Complete metadata for PMID
'PubMed_get_cited_by'             # Forward citations (papers citing this)
'PubMed_get_related'              # Computationally related papers
'PubMed_get_links'                # External links (full-text)
```

### Europe PMC Citation Tools (Fallbacks)
```python
'EuropePMC_get_citations'         # Forward citations (fallback for PubMed)
'EuropePMC_get_references'        # Backward citations (reference list)
'EuropePMC_get_fulltext'          # Full-text XML for open access articles
'EuropePMC_get_fulltext_snippets' # Full-text snippet search within articles
```

### Open Citation Tools
```python
'OpenCitations_get_citations'     # Open citation data by DOI
'OpenCitations_get_references'    # Reference list by DOI
'OpenCitations_get_citation_count' # Citation count by DOI
```

### Semantic Scholar
```python
'SemanticScholar_get_paper'       # Paper metadata by DOI/PMID/S2 ID
'SemanticScholar_get_recommendations' # AI-recommended similar papers
'SemanticScholar_get_pdf_snippets' # PDF text extraction by DOI/PMID
```

### Citation Impact & Metrics
```python
'iCite_search_publications'       # PubMed search + iCite citation metrics (RCR, APT, NIH percentile)
'iCite_get_publications'          # iCite metrics by PMID (citation_count, RCR, APT)
'scite_get_tallies'               # Smart citation tallies (supporting/contradicting/mentioning)
```

### Full-Text / PDF Tools
```python
'ArXiv_get_pdf_snippets'          # ArXiv PDF text extraction
```

### Open Access
```python
'Unpaywall_check_oa_status'       # OA status by DOI (requires email)
```

---

## Protein/Gene Annotation Tools

### UniProt Tools
```python
'UniProt_search'                  # Search UniProt by query
'UniProt_get_entry_by_accession'  # Full protein entry
'UniProt_id_mapping'              # Map between ID types
'UniProt_get_function_by_accession'  # Function description
'UniProt_get_sequence_by_accession'  # Protein sequence
'UniProt_get_recommended_name_by_accession'  # Official name
'UniProt_get_alternative_names_by_accession'  # Aliases
'UniProt_get_subcellular_location_by_accession'  # Localization
'UniProt_get_ptm_processing_by_accession'  # PTMs, active sites
'UniProt_get_disease_variants_by_accession'  # Disease variants
```

### Domain/Structure Tools
```python
'InterPro_get_protein_domains'    # Domain architecture
'alphafold_get_prediction'        # AlphaFold structure
'get_protein_metadata_by_pdb_id'  # PDB structure metadata
'proteins_api_get_protein'        # Alternative protein data
```

### Gene Annotation
```python
'MyGene_get_gene_annotation'      # NCBI gene info, aliases
'ensembl_lookup_gene'             # Ensembl gene details
'ensembl_get_xrefs'               # Cross-references
```

---

## Expression Tools
### GTEx (Tissue Expression)
```python
'GTEx_get_gene_expression'        # Expression data
'GTEx_get_median_gene_expression' # Median TPM by tissue
```

### Human Protein Atlas
```python
'HPA_get_comprehensive_gene_details_by_ensembl_id'  # Full HPA data
'HPA_get_rna_expression_by_source'  # RNA expression
'HPA_get_subcellular_location'    # Subcellular localization
'HPA_get_protein_interactions_by_gene'  # DEPRECATED: returns error, use STRING/BioGRID instead
'HPA_get_cancer_prognostics_by_gene'  # Cancer prognosis
```

### Single-Cell (if available)
```python
'CELLxGENE_get_expression_data'   # Single-cell expression
```

---

## Pathway & Function Tools
### Gene Ontology
```python
'GO_get_annotations_for_gene'     # GO terms (BP, MF, CC)
'GO_get_term_details'             # GO term details
```

### Pathways
```python
'Reactome_map_uniprot_to_pathways'  # Reactome pathways
'kegg_get_gene_info'              # KEGG gene/pathways
'WikiPathways_search'             # WikiPathways
```

### Open Targets (Target-centric)
```python
'OpenTargets_get_target_gene_ontology_by_ensemblID'  # GO via OT
'OpenTargets_get_target_tractability_by_ensemblID'   # Druggability
'OpenTargets_get_associated_drugs_by_target_ensemblID'  # Known drugs
'OpenTargets_get_target_safety_profile_by_ensemblID'   # Safety
'OpenTargets_get_diseases_phenotypes_by_target_ensembl'  # Disease links
'OpenTargets_get_publications_by_target_ensemblID'   # Publications
```

---

## Interaction Tools (6)

```python
'STRING_get_protein_interactions'  # STRING PPI network
'intact_get_interactions'         # IntAct experimental PPIs
'intact_get_complex_details'      # Complex membership
'OpenTargets_get_target_interactions_by_ensemblID'  # OT interactions
'BioGRID_get_interactions'        # BioGRID protein-protein interactions
'BioGRID_get_chemical_interactions'  # BioGRID chemical-protein interactions
```

---

## Variant & Disease Tools

### gnomAD
```python
'gnomad_get_gene'                 # Population variants
'gnomad_get_gene_constraints'     # Constraint scores (pLI, LOEUF)
```

### ClinVar
```python
'clinvar_search_variants'         # Clinical variants
'clinvar_get_variant_details'     # Variant details
```

### Disease
```python
'OpenTargets_get_diseases_phenotypes_by_target_ensembl'  # Disease associations
'OpenTargets_get_target_constraint_info_by_ensemblID'  # Gene constraint info
'OpenTargets_get_biological_mouse_models_by_ensemblID'  # Mouse model phenotypes
'DGIdb_get_drug_gene_interactions'  # Drug-gene
'DGIdb_get_gene_druggability'     # Druggability categories
'CTD_get_chemical_gene_interactions'  # CTD chemical-gene interactions
'CTD_get_gene_diseases'           # CTD gene-disease associations
'CTD_get_disease_chemicals'       # Chemicals linked to a disease (CTD)
'CTD_get_chemical_diseases'       # Diseases linked to a chemical (CTD)
'DisGeNET_get_disease_genes'      # Gene-disease associations (DisGeNET score)
'DisGeNET_search_disease'         # Search diseases by name
```

---

## Drug/Chemical Tools (24)

### ChEMBL
```python
'ChEMBL_search_drugs'            # Search drugs by name/synonym
'ChEMBL_get_drug'                # Get drug details by ChEMBL ID
'ChEMBL_get_drug_mechanisms'     # Drug mechanism of action
'ChEMBL_search_mechanisms'       # Search mechanisms by target/drug
'ChEMBL_search_targets'          # Search drug targets
'ChEMBL_get_target_activities'   # Bioactivity data for target
'ChEMBL_get_molecule_targets'    # Targets of a molecule by ChEMBL ID
```

### DrugBank
```python
'drugbank_get_drug_basic_info_by_drug_name_or_id'  # Basic drug info
'drugbank_get_indications_by_drug_name_or_drugbank_id'  # Drug indications
'drugbank_get_pharmacology_by_drug_name_or_drugbank_id'  # Pharmacology
'drugbank_get_drug_interactions_by_drug_name_or_id'  # Drug-drug interactions
'drugbank_get_targets_by_drug_name_or_drugbank_id'  # Drug targets
```

### PubChem
```python
'PubChem_get_CID_by_compound_name'  # Resolve compound name to CID
'PubChem_get_compound_properties_by_CID'  # Compound properties
'PubChem_get_compound_synonyms_by_CID'  # Compound synonyms
```

### Open Targets (Drug-centric)
```python
'OpenTargets_get_drug_chembId_by_generic_name'  # Resolve drug name to ChEMBL ID
'OpenTargets_get_drug_id_description_by_name'  # Drug description
'OpenTargets_get_drug_adverse_events_by_chemblId'  # Adverse events
'OpenTargets_get_drug_warnings_by_chemblId'  # Drug warnings
'OpenTargets_get_drug_mechanisms_of_action_by_chemblId'  # Mechanisms of action
'OpenTargets_get_associated_targets_by_drug_chemblId'  # Drug-target associations
'OpenTargets_get_associated_diseases_by_drug_chemblId'  # Drug-disease associations
'OpenTargets_get_drug_indications_by_chemblId'  # Approved indications
```

### Clinical Trials
```python
'search_clinical_trials'          # ClinicalTrials.gov search
```

---

## Utility Tools (1)

```python
'get_webpage_text_from_url'       # Fetch and extract text from a URL
```

---

## Tool Categories by Use Case

### Target Disambiguation (Phase 1)
```python
# Resolve IDs
'UniProt_search'
'UniProt_id_mapping'
'ensembl_lookup_gene'

# Get baseline profile
'InterPro_get_protein_domains'
'HPA_get_subcellular_location'
'GTEx_get_median_gene_expression'
'GO_get_annotations_for_gene'
'Reactome_map_uniprot_to_pathways'
```

### High-Precision Literature Seeds
```python
'PubMed_search_articles'          # "[GENE]"[Title] queries
'EuropePMC_search_articles'       # Alternative
```

### Citation Network Expansion
```python
'PubMed_get_cited_by'             # Forward citations (primary)
'EuropePMC_get_citations'         # Forward (fallback)
'OpenCitations_get_citations'     # Open citation data by DOI
'OpenCitations_get_references'    # Backward citations by DOI
'PubMed_get_related'              # Related papers
'SemanticScholar_get_recommendations' # AI-recommended similar papers
'EuropePMC_get_references'        # Backward citations
```

### Citation Impact Assessment
```python
'iCite_search_publications'       # Search + citation metrics (RCR, APT)
'iCite_get_publications'          # Metrics by PMID
'scite_get_tallies'               # Supporting/contradicting/mentioning counts
'OpenCitations_get_citation_count' # Open citation count by DOI
```

### Broad Search
```python
'openalex_literature_search'      # Comprehensive
'Crossref_search_works'           # DOI-based (filter:"type:journal-article")
'SemanticScholar_search_papers'   # AI-ranked
'CORE_search_papers'              # Aggregated open access
'advanced_literature_search_agent' # Deep multi-source (slower, thorough)
```

### OA Status Check
```python
'Unpaywall_check_oa_status'       # If email provided
# Otherwise use OA fields from:
# - EuropePMC (isOpenAccess)
# - OpenAlex (is_oa)
# - PMC papers (all OA)
```

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `PubMed_get_cited_by` | `EuropePMC_get_citations` | `OpenCitations_get_citations` |
| `PubMed_get_related` | `SemanticScholar_get_recommendations` | `SemanticScholar_search_papers` |
| `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` | Mark unavailable |
| `InterPro_get_protein_domains` | UniProt features | Mark unavailable |
| `Unpaywall_check_oa_status` | EuropePMC OA flag | OpenAlex is_oa |

> **Note:** `HPA_get_protein_interactions_by_gene` is DEPRECATED. Use `STRING_get_protein_interactions` or `BioGRID_get_interactions` instead.

---

## Parameter Quick Reference

### Literature Search
```python
# PubMed
{'query': '"GENE"[Title]', 'limit': 100}

# ArXiv
{'query': 'ti:"transformer" AND abs:"attention mechanism"', 'limit': 50, 'sort_by': 'submittedDate'}

# DBLP
{'query': 'graph neural network', 'max_results': 50}

# SemanticScholar
{'query': 'retrieval augmented generation', 'limit': 50, 'year': '2023-2024', 'sort': 'citationCount:desc'}

# OpenAlex
{'search_keywords': 'term', 'max_results': 100, 'year_from': 2020}

# With collision filter
{'query': '"TRAG" AND immune NOT plasmid NOT conjugation', 'limit': 50}
```

### Citation Tools
```python
{'pmid': '12345678', 'limit': 100}  # PubMed citations
{'article_id': 'MED:12345678', 'source': 'MED'}  # EuropePMC
```

### Annotation Tools
```python
# UniProt
{'accession': 'P38606'}
{'ids': ['P38606'], 'from_db': 'UniProtKB_AC-ID', 'to_db': 'Ensembl'}

# GTEx (gencode_id is an Ensembl gene ID; dataset_id defaults to gtex_v8)
{'gencode_id': 'ENSG00000114573', 'dataset_id': 'gtex_v8'}

# InterPro
{'uniprot_accession': 'P38606'}
```

---

## Complete Alphabetical Tool List

### Literature & Text Mining (24)
1. `advanced_literature_search_agent` (deep multi-source)
2. `ArXiv_search_papers`
3. `ArXiv_get_pdf_snippets` (PDF text extraction)
4. `BioRxiv_get_preprint` (DOI retrieval)
5. `BioRxiv_list_recent_preprints` (recent by subject)
6. `CORE_search_papers` (aggregated open access)
7. `Crossref_search_works`
8. `DBLP_search_publications`
9. `DOAJ_search_articles`
10. `EuropePMC_search_articles`
11. `Fatcat_search_scholar`
12. `HAL_search_archive`
13. `MedRxiv_get_preprint` (DOI retrieval)
14. `OpenAIRE_search_publications`
15. `openalex_literature_search`
16. `openalex_search_works`
17. `OSF_search_preprints`
18. `PMC_search_papers`
19. `PubMed_search_articles`
20. `PubTator3_LiteratureSearch` (literature search with entity annotations)
21. `PubTator3_EntityAutocomplete` (entity name autocomplete)
22. `PubTator3_get_annotations` (entity annotations for PMID/PMCID)
23. `SemanticScholar_search_papers`
24. `Zenodo_search_records`

### Citation & Impact (19)
25. `EuropePMC_get_citations`
26. `EuropePMC_get_references`
27. `EuropePMC_get_fulltext` (full-text XML)
28. `EuropePMC_get_fulltext_snippets` (full-text snippet search)
29. `iCite_get_publications` (metrics by PMID)
30. `iCite_search_publications` (search + metrics)
31. `OpenCitations_get_citations`
32. `OpenCitations_get_references`
33. `OpenCitations_get_citation_count`
34. `PubMed_get_article`
35. `PubMed_get_cited_by`
36. `PubMed_get_links`
37. `PubMed_get_related`
38. `scite_get_tallies`
39. `SemanticScholar_get_paper` (paper metadata)
40. `SemanticScholar_get_pdf_snippets` (PDF text extraction)
41. `SemanticScholar_get_recommendations`
42. `Unpaywall_check_oa_status`

### Protein/Gene (17)
43. `alphafold_get_prediction`
44. `ensembl_get_xrefs`
45. `ensembl_lookup_gene`
46. `get_protein_metadata_by_pdb_id`
47. `InterPro_get_protein_domains`
48. `MyGene_get_gene_annotation`
49. `proteins_api_get_protein`
50. `UniProt_get_alternative_names_by_accession`
51. `UniProt_get_disease_variants_by_accession`
52. `UniProt_get_entry_by_accession`
53. `UniProt_get_function_by_accession`
54. `UniProt_get_ptm_processing_by_accession`
55. `UniProt_get_recommended_name_by_accession`
56. `UniProt_get_sequence_by_accession`
57. `UniProt_get_subcellular_location_by_accession`
58. `UniProt_id_mapping`
59. `UniProt_search`

### Expression (6)
60. `CELLxGENE_get_expression_data`
61. `GTEx_get_gene_expression`
62. `GTEx_get_median_gene_expression`
63. `HPA_get_comprehensive_gene_details_by_ensembl_id`
64. `HPA_get_rna_expression_by_source`
65. `HPA_get_subcellular_location`

### Pathway/Function (9)
66. `GO_get_annotations_for_gene`
67. `GO_get_term_details`
68. `kegg_get_gene_info`
69. `OpenTargets_get_associated_drugs_by_target_ensemblID`
70. `OpenTargets_get_publications_by_target_ensemblID`
71. `OpenTargets_get_target_gene_ontology_by_ensemblID`
72. `OpenTargets_get_target_safety_profile_by_ensemblID`
73. `OpenTargets_get_target_tractability_by_ensemblID`
74. `Reactome_map_uniprot_to_pathways`
75. `WikiPathways_search`

### Interaction (6)
76. `BioGRID_get_interactions`
77. `BioGRID_get_chemical_interactions`
78. `intact_get_complex_details`
79. `intact_get_interactions`
80. `OpenTargets_get_target_interactions_by_ensemblID`
81. `STRING_get_protein_interactions`

### Variant/Disease (17, 1 deprecated)
82. `clinvar_get_variant_details`
83. `clinvar_search_variants`
84. `CTD_get_chemical_diseases`
85. `CTD_get_chemical_gene_interactions`
86. `CTD_get_disease_chemicals`
87. `CTD_get_gene_diseases`
88. `DGIdb_get_drug_gene_interactions`
89. `DGIdb_get_gene_druggability`
90. `DisGeNET_get_disease_genes`
91. `DisGeNET_search_disease`
92. `gnomad_get_gene`
93. `gnomad_get_gene_constraints`
94. `HPA_get_cancer_prognostics_by_gene`
95. `HPA_get_protein_interactions_by_gene` # DEPRECATED: use STRING/BioGRID
96. `OpenTargets_get_biological_mouse_models_by_ensemblID`
97. `OpenTargets_get_diseases_phenotypes_by_target_ensembl`
98. `OpenTargets_get_target_constraint_info_by_ensemblID`

### Drug/Chemical (24)
99. `ChEMBL_get_molecule_targets`
100. `ChEMBL_search_drugs`
101. `ChEMBL_get_drug`
102. `ChEMBL_get_drug_mechanisms`
103. `ChEMBL_search_mechanisms`
104. `ChEMBL_search_targets`
105. `ChEMBL_get_target_activities`
106. `drugbank_get_drug_basic_info_by_drug_name_or_id`
107. `drugbank_get_indications_by_drug_name_or_drugbank_id`
108. `drugbank_get_pharmacology_by_drug_name_or_drugbank_id`
109. `drugbank_get_drug_interactions_by_drug_name_or_id`
110. `drugbank_get_targets_by_drug_name_or_drugbank_id`
111. `OpenTargets_get_drug_chembId_by_generic_name`
112. `OpenTargets_get_drug_id_description_by_name`
113. `OpenTargets_get_drug_adverse_events_by_chemblId`
114. `OpenTargets_get_drug_warnings_by_chemblId`
115. `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`
116. `OpenTargets_get_associated_targets_by_drug_chemblId`
117. `OpenTargets_get_associated_diseases_by_drug_chemblId`
118. `OpenTargets_get_drug_indications_by_chemblId`
119. `PubChem_get_CID_by_compound_name`
120. `PubChem_get_compound_properties_by_CID`
121. `PubChem_get_compound_synonyms_by_CID`
122. `search_clinical_trials`

### Utility (1)
123. `get_webpage_text_from_url`

---

**Total Tools**: 123 (122 active, 1 deprecated: HPA_get_protein_interactions_by_gene)
- Literature & Text Mining: 24
- Citation & Impact: 19
- Protein/Gene Annotation: 17
- Expression: 6
- Pathway/Function: 9
- Interaction: 6
- Variant/Disease: 17 (1 deprecated)
- Drug/Chemical: 24 (incl. ChEMBL target tools, clinical trials)
- Utility: 1

*Last Updated: 2026-03-07*
