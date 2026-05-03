Available Tools Reference
==========================

**Complete reference of all ToolUniverse scientific tools and their capabilities.**

ToolUniverse provides 1000+ tools across eight major categories, each serving specific computational and analytical requirements in scientific research.

Tool Ecosystem Overview
-----------------------

ToolUniverse integrates tools across eight major categories:

.. code-block:: text

   ToolUniverse Ecosystem (1000+ Tools):

   ┌─────────────────┐
   │   ML Models     │ 15 tools  → Prediction, Classification, Generation
   │     (AI/ML)     │
   └─────────────────┘

   ┌─────────────────┐
   │   AI Agents     │ 33 tools  → Autonomous Planning, Tool Routing
   │   (Agentic)     │
   └─────────────────┘

   ┌─────────────────┐
   │   Software      │ 164 tools → Bioinformatics, Analysis Packages
   │   Packages      │
   └─────────────────┘

   ┌─────────────────┐
   │ Human Expert    │ 6 tools   → Consultation, Validation, Feedback
   │   Feedback      │
   └─────────────────┘

   ┌─────────────────┐
   │   Robotics      │ 1 tool    → ROS Communication, Lab Automation
   │  (Automation)   │
   └─────────────────┘

   ┌─────────────────┐
   │   Databases     │ 84 tools  → Structured Data, Knowledge Bases
   │   (Storage)     │
   └─────────────────┘

   ┌─────────────────┐
   │  Embedding      │ 4 tools   → Vector Search, Semantic Retrieval
   │   Stores        │
   └─────────────────┘

   ┌─────────────────┐
   │      APIs       │ 281 tools → External Services, Data Access
   │  (Integration)  │
   └─────────────────┘

Tool Categories Summary
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Tool Distribution by Category
 :header-rows: 1
 :widths: 25 15 15 45

 * - Category
 - Count
 - Percentage
 - Primary Use Cases
 * - APIs
 - 281
 - 48.4%
 - External data access, real-time information
 * - Software Packages
 - 164
 - 28.3%
 - Computational analysis, local processing
 * - Databases
 - 84
 - 14.5%
 - Structured data storage and retrieval
 * - AI Agents
 - 33
 - 5.7%
 - Autonomous reasoning and planning
 * - ML Models
 - 15
 - 2.6%
 - Prediction and classification tasks
 * - Expert Feedback
 - 6
 - 1.0%
 - Human validation and guidance
 * - Embedding Stores
 - 4
 - 0.7%
 - Semantic search and similarity
 * - Robotics
 - 1
 - 0.2%
 - Laboratory automation
 * - **Total**
 - **588**
 - **100%**
 - **Comprehensive scientific ecosystem**

 Molecular & Genetic Data
----------------------------

UniProt - Protein Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access comprehensive protein and gene information.

**Key Functions:**
* ``UniProt_get_function_by_accession`` - Get functional annotations by UniProt accession
* ``UniProt_search_proteins`` - Search proteins by keywords
* ``UniProt_get_protein_sequence`` - Retrieve protein sequences

**Example:**

.. code-block:: python

   query = {
       "name": "UniProt_get_function_by_accession",
       "arguments": {"accession": "P38398"}  # BRCA1 accession
   }
   result = tu.run(query)

Gene Ontology - Functional Annotation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gene Ontology annotations and functional analysis.

**Key Functions:**
* ``GeneOntology_get_annotations`` - Get GO annotations for genes
* ``GeneOntology_search_terms`` - Search GO terms
* ``GeneOntology_get_enrichment`` - Functional enrichment analysis

**Example:**

.. code-block:: python

   query = {
       "name": "GeneOntology_get_annotations",
       "arguments": {"gene_symbols": ["BRCA1", "BRCA2", "TP53"]}
   }

Enrichr - Gene Set Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive gene set enrichment analysis.

**Key Functions:**
* ``Enrichr_analyze_gene_list`` - Enrichment analysis for gene lists
* ``Enrichr_get_libraries`` - List available gene set libraries
* ``Enrichr_download_results`` - Download enrichment results

**Example:**

.. code-block:: python

   query = {
       "name": "Enrichr_analyze_gene_list",
       "arguments": {
           "genes": ["BRCA1", "BRCA2", "TP53", "ATM", "CHEK2"],
           "library": "KEGG_2021_Human"
       }
   }

 Disease & Target Data
------------------------

OpenTargets Platform
~~~~~~~~~~~~~~~~~~~~~

Comprehensive disease-target association data.

**Key Functions:**
* ``OpenTargets_get_associated_targets_by_disease_efoId`` - Disease-associated targets
* ``OpenTargets_get_associated_diseases_by_target`` - Target-associated diseases
* ``OpenTargets_get_disease_id_description_by_name`` - Disease lookup
* ``OpenTargets_get_evidence`` - Evidence for associations
* ``OpenTargets_get_drug_info`` - Drug information and mechanisms

**Example:**

.. code-block:: python

   # Get targets for Alzheimer's disease
   query = {
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000537"}  # hypertension
   }

EFO - Experimental Factor Ontology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Disease and experimental factor ontology.

**Key Functions:**
* ``EFO_search_diseases`` - Search diseases by name
* ``EFO_get_disease_hierarchy`` - Get disease relationships
* ``EFO_get_synonyms`` - Get disease synonyms

**Example:**

.. code-block:: python

   query = {
       "name": "EFO_search_diseases",
       "arguments": {"query": "diabetes"}
   }

 Drug & Chemical Data
-----------------------

PubChem - Chemical Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive chemical compound database.

**Key Functions:**
* ``PubChem_get_compound_info`` - Get compound information by name/ID
* ``PubChem_search_compounds`` - Search compounds by structure/properties
* ``PubChem_get_compound_properties`` - Molecular properties
* ``PubChem_similarity_search`` - Chemical similarity search

**Example:**

.. code-block:: python

   query = {
       "name": "PubChem_get_compound_info",
       "arguments": {"compound_name": "aspirin"}
   }

ChEMBL - Bioactivity Data
~~~~~~~~~~~~~~~~~~~~~~~~~

Chemical bioactivity and drug discovery data.

**Key Functions:**
* ``ChEMBL_get_compound_targets`` - Get targets for compounds
* ``ChEMBL_get_compounds_by_target`` - Get compounds targeting proteins
* ``ChEMBL_get_bioactivity_data`` - Bioactivity measurements
* ``ChEMBL_search_similar_compounds`` - Chemical similarity search

**Example:**

.. code-block:: python

   query = {
       "name": "ChEMBL_get_compounds_by_target",
       "arguments": {"target_symbol": "EGFR"}
   }

️ Drug Safety & Regulatory
----------------------------

OpenFDA - FDA Data
~~~~~~~~~~~~~~~~~~~

FDA drug labeling and adverse event data.

**Key Functions:**
* ``FAERS_count_reactions_by_drug_event`` - Count adverse reactions by drug
* ``openfda_get_warnings_by_drug_name`` - Get FDA warnings
* ``OpenFDA_get_drug_labels`` - Drug labeling information
* ``OpenFDA_search_recalls`` - Drug recall information

**Example:**

.. code-block:: python

   # Search adverse events
   query = {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "warfarin"}
   }

   # Get FDA warnings
   query = {
       "name": "openfda_get_warnings_by_drug_name",
       "arguments": {"medicinalproduct": "warfarin"}
   }

DailyMed - Drug Labeling
~~~~~~~~~~~~~~~~~~~~~~~~

Official FDA drug labeling information.

**Key Functions:**
* ``DailyMed_get_drug_label`` - Get official drug labels
* ``DailyMed_search_drugs`` - Search drugs by name
* ``DailyMed_get_NDC_info`` - NDC (drug code) information

**Example:**

.. code-block:: python

   query = {
       "name": "DailyMed_get_drug_label",
       "arguments": {"medicinalproduct": "metformin"}
   }

 Clinical Research
--------------------

ClinicalTrials.gov
~~~~~~~~~~~~~~~~~~

Clinical trial registry and results database.

**Key Functions:**
* ``ClinicalTrials_search_studies`` - Search clinical trials
* ``ClinicalTrials_get_study_details`` - Get detailed study information
* ``ClinicalTrials_get_trial_results`` - Get trial results
* ``ClinicalTrials_search_by_condition`` - Find trials by medical condition

**Example:**

.. code-block:: python

   query = {
       "name": "ClinicalTrials_search_studies",
       "arguments": {
           "condition": "breast cancer",
           "intervention": "immunotherapy"
       }
   }

 Literature & Publications
-----------------------------

PubTator - Biomedical Literature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PubMed literature with named entity recognition.

**Key Functions:**
* ``PubTator_search_publications`` - Search literature with entities
* ``PubTator_get_annotations`` - Get entity annotations
* ``PubTator_search_by_entity`` - Search by specific entities

**Example:**

.. code-block:: python

   query = {
       "name": "PubTator_search_publications",
       "arguments": {
           "query": "@GENE_BRCA1 @DISEASE_cancer"
       }
   }

Europe PMC
~~~~~~~~~~

European literature database with full-text access.

**Key Functions:**
* ``EuropePMC_search_articles`` - Search articles and abstracts
* ``EuropePMC_get_full_text`` - Get full-text when available
* ``EuropePMC_get_citations`` - Get citation data

**Example:**

.. code-block:: python

   query = {
       "name": "EuropePMC_search_articles",
       "arguments": {"query": "CRISPR gene therapy"}
   }

Semantic Scholar
~~~~~~~~~~~~~~~~

AI-powered academic search engine.

**Key Functions:**
* ``SemanticScholar_search_papers`` - Search academic papers
* ``SemanticScholar_get_paper_details`` - Get detailed paper information
* ``SemanticScholar_get_citations`` - Citation network analysis

**Example:**

.. code-block:: python

   query = {
       "name": "SemanticScholar_search_papers",
       "arguments": {"query": "machine learning drug discovery"}
   }

OpenAlex
~~~~~~~~

Open academic publication database.

**Key Functions:**
* ``OpenAlex_search_works`` - Search academic works
* ``OpenAlex_get_author_info`` - Author information and metrics
* ``OpenAlex_get_institution_data`` - Institution research data

 Specialized Databases
------------------------

Human Protein Atlas
~~~~~~~~~~~~~~~~~~~

Tissue and cell expression data.

**Key Functions:**
* ``HPA_get_tissue_expression`` - Tissue expression patterns
* ``HPA_get_cell_expression`` - Single-cell expression data
* ``HPA_get_protein_localization`` - Subcellular localization

**Example:**

.. code-block:: python

   query = {
       "name": "HPA_get_tissue_expression",
       "arguments": {"gene_symbol": "BRCA1"}
   }

Reactome Pathways
~~~~~~~~~~~~~~~~~

Biological pathway database.

**Key Functions:**
* ``Reactome_get_pathways_by_gene`` - Pathways for genes
* ``Reactome_search_pathways`` - Search pathway database
* ``Reactome_get_pathway_details`` - Detailed pathway information

**Example:**

.. code-block:: python

   query = {
       "name": "Reactome_get_pathways_by_gene",
       "arguments": {"gene_symbol": "TP53"}
   }

HumanBase
~~~~~~~~~

Tissue-specific gene networks.

**Key Functions:**
* ``HumanBase_get_gene_networks`` - Tissue-specific networks
* ``HumanBase_predict_gene_function`` - Gene function prediction
* ``HumanBase_get_tissue_expression`` - Tissue expression patterns

MedlinePlus
~~~~~~~~~~~

Consumer health information.

**Key Functions:**
* ``MedlinePlus_get_health_topics`` - Health topic information
* ``MedlinePlus_search_conditions`` - Search medical conditions
* ``MedlinePlus_get_drug_info`` - Consumer drug information

 AI-Powered Tools
--------------------

Machine Learning Models (15 tools)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Apply machine learning algorithms for prediction, classification, and generation tasks.

**Core ML Tools:**

**boltz2_docking** - Protein-ligand binding prediction

.. code-block:: python

   {
       "name": "boltz2_docking",
       "arguments": {
           "protein_structure": "1ABC",
           "ligand_smiles": "CCO"
       }
   }
   # Returns: binding_affinity, binding_probability, confidence_score

**ADMET_predict_CYP_interactions** - Drug metabolism prediction

.. code-block:: python

   {
       "name": "ADMET_predict_CYP_interactions",
       "arguments": {
           "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
           "cyp_enzymes": ["CYP3A4", "CYP2D6"]
       }
   }
   # Returns: interaction_probabilities, metabolic_stability

**run_TxAgent_biomedical_reasoning** - Therapeutic reasoning

.. code-block:: python

   {
       "name": "run_TxAgent_biomedical_reasoning",
       "arguments": {
           "query": "What are the therapeutic targets for Alzheimer's disease?",
           "context": "precision_medicine"
       }
   }
   # Returns: therapeutic_insights, target_recommendations

AI Agents (33 tools)
~~~~~~~~~~~~~~~~~~~~

Autonomous tools that perceive environments, make decisions, and take actions toward research goals.

**Literature & Analysis Agents:**

**HypothesisGenerator** - Generate research hypotheses

.. code-block:: python

   {
       "name": "HypothesisGenerator",
       "arguments": {
           "research_area": "cancer immunotherapy",
           "constraints": ["FDA-approved targets", "known biomarkers"],
           "num_hypotheses": 5
       }
   }
   # Returns: ranked_hypotheses, supporting_evidence, testable_predictions

**ExperimentalDesignScorer** - Evaluate experimental designs

.. code-block:: python

   {
       "name": "ExperimentalDesignScorer",
       "arguments": {
           "experiment_description": "Phase II trial for EGFR inhibitor",
           "evaluation_criteria": ["feasibility", "statistical_power", "ethics"]
       }
   }
   # Returns: design_score, improvement_suggestions, risk_assessment

**MedicalLiteratureReviewer** - Comprehensive literature analysis

.. code-block:: python

   {
       "name": "MedicalLiteratureReviewer",
       "arguments": {
           "topic": "CAR-T cell therapy safety profile",
           "databases": ["PubMed", "ClinicalTrials.gov"],
           "time_range": "2020-2024"
       }
   }
   # Returns: comprehensive_review, key_findings, research_gaps

Tool Discovery & Composition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AI tools for discovering and combining other tools.

**Key Functions:**
* ``discover_tools_by_description`` - Find tools by natural language
* ``compose_tools_for_workflow`` - Create tool workflows
* ``optimize_tool_descriptions`` - Improve tool descriptions

**Example:**

.. code-block:: python

   query = {
       "name": "discover_tools_by_description",
       "arguments": {
           "description": "I need to find genes associated with heart disease"
       }
   }

 Search & Integration Tools
-----------------------------

Tool Finder
~~~~~~~~~~~

Find appropriate tools for your research needs.

**Key Functions:**
* ``find_tools_by_keyword`` - Keyword-based tool search
* ``find_tools_by_category`` - Browse tools by category
* ``get_tool_recommendations`` - Get tool recommendations

**Example:**

.. code-block:: python

   query = {
       "name": "find_tools_by_keyword",
       "arguments": {"keywords": ["drug", "safety", "adverse"]}
   }

Embedding Stores (4 tools)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Store and retrieve vectorized representations of scientific data for semantic search.

**Core Embedding Tools:**

**embedding_tool_finder** - Semantic tool discovery

.. code-block:: python

   {
       "name": "embedding_tool_finder",
       "arguments": {
           "query": "predict protein folding dynamics",
           "top_k": 10,
           "similarity_threshold": 0.7
       }
   }
   # Returns: relevant_tools, similarity_scores, tool_descriptions

**embedding_database_search** - Vector similarity search

.. code-block:: python

   {
       "name": "embedding_database_search",
       "arguments": {
           "query_vector": embedding_vector,
           "database": "pubmed_abstracts",
           "top_k": 50
       }
   }
   # Returns: similar_documents, relevance_scores, metadata

Data Integration
~~~~~~~~~~~~~~~~

Tools for combining data from multiple sources.

**Key Functions:**
* ``integrate_gene_data`` - Combine gene data from multiple sources
* ``cross_reference_identifiers`` - Map between different ID systems
* ``validate_data_consistency`` - Check data consistency

️ Tool Usage Patterns
-----------------------

Single Tool Queries
~~~~~~~~~~~~~~~~~~~~

Simple, focused queries for specific information:

.. code-block:: python

   # Get protein function by accession (EGFR → P00533)
   protein_query = {
       "name": "UniProt_get_function_by_accession",
       "arguments": {"accession": "P00533"}
   }

   # Search adverse events
   safety_query = {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "metformin"}
   }

Multi-Tool Workflows
~~~~~~~~~~~~~~~~~~~~

Combine multiple tools for comprehensive analysis:

.. code-block:: python

   # Step 1: Get disease info
   disease_query = {
       "name": "OpenTargets_get_disease_id_description_by_name",
       "arguments": {"diseaseName": "diabetes"}
   }

   # Step 2: Get associated targets
   targets_query = {
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": disease_id}
   }

   # Step 3: Analyze target pathways
   pathway_query = {
       "name": "Enrichr_analyze_gene_list",
       "arguments": {
           "genes": target_list,
           "library": "KEGG_2021_Human"
       }
   }

Batch Processing
~~~~~~~~~~~~~~~~

Process multiple related queries efficiently:

.. code-block:: python

   # Process multiple genes
   genes = ["BRCA1", "BRCA2", "TP53", "ATM"]

   results = {}
   for accession in ["P38398", "P51587", "P04637", "Q13315"]:  # BRCA1, BRCA2, TP53, ATM
       query = {
           "name": "UniProt_get_function_by_accession",
           "arguments": {"accession": accession}
       }
       results[accession] = tu.run(query)

Integration Patterns
~~~~~~~~~~~~~~~~~~~~

Multi-Tool Workflows
~~~~~~~~~~~~~~~~~~~~

Combine multiple tools for comprehensive analysis:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Drug discovery workflow
   def drug_discovery_pipeline(disease_name):
       tooluni = ToolUniverse()
       tooluni.load_tools()

       # 1. Find disease ID
       disease_query = {
           "name": "OpenTargets_get_disease_id_description_by_name",
           "arguments": {"disease_name": disease_name}
       }
       disease_info = tooluni.run(disease_query)

       # 2. Get associated targets
       targets_query = {
           "name": "OpenTargets_get_associated_targets_by_disease_efoId",
           "arguments": {"efoId": disease_info['id']}
       }
       targets_result = tooluni.run(targets_query)
       targets = targets_result['data']['disease']['associatedTargets']['rows']

       # 3. Find drugs for each target
       drugs = []
       for row in targets[:5]:  # Top 5 targets
           target = row['target']
           drugs_query = {
               "name": "OpenTargets_get_associated_drugs_by_target_ensemblID",
               "arguments": {
                   "target_ensembl_id": target['id'],
                   "size": 10,
                   "cursor": ""
               }
           }
           target_drugs = tooluni.run(drugs_query)
           drugs.extend(target_drugs)

       # 4. Check safety profiles
       for drug in drugs[:10]:  # Top 10 drugs
           safety_query = {
               "name": "openfda_get_warnings_by_drug_name",
               "arguments": {"drug_name": drug['name']}
           }
           safety = tooluni.run(safety_query)
           drug['safety_warnings'] = safety

       return drugs

Tool Composition Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~

**Sequential Workflows:**

.. code-block:: python

   # Disease → Targets → Compounds → Prediction
   workflow = [
       ("OpenTargets_get_associated_targets_by_disease_efoId", {"efoId": disease_id}),
       ("ChEMBL_search_compounds_by_target", {"target_id": target_result}),
       ("boltz2_docking", {"protein_id": target, "ligand_smiles": compound}),
       ("ADMETAI_predict_admet_properties", {"smiles": compound})
   ]

**Parallel Data Gathering:**

.. code-block:: python

   # Multi-database literature search
   parallel_searches = [
       ("PubTator_search_publications", {"query": research_topic}),
       ("EuropePMC_search_articles", {"query": research_topic}),
       ("SemanticScholar_search_papers", {"query": research_topic})
   ]

**Feedback Loops:**

.. code-block:: python

   # Iterative optimization
   while not satisfactory_result:
       prediction = ml_model_prediction(current_compound)
       if prediction.score < threshold:
           analogs = chemical_database_search(current_compound)
           current_compound = select_best_analog(analogs)
       else:
           break

 Tool Performance Tips
------------------------

Optimization Strategies
~~~~~~~~~~~~~~~~~~~~~~~

1. **Use specific queries**: More specific queries return faster
2. **Limit results**: Use ``limit`` parameter to control result size
3. **Cache results**: Enable caching for repeated queries
4. **Batch when possible**: Some tools support batch operations

Rate Limiting
~~~~~~~~~~~~~

ToolUniverse automatically handles API rate limits, but you can optimize:

.. code-block:: python

   import time

   # Add delays for large batch operations
   for query in large_query_list:
       result = tu.run(query)
       time.sleep(0.1)  # Small delay between requests

Error Handling
~~~~~~~~~~~~~~

Always include error handling for robust applications:

.. code-block:: python

   try:
       result = tu.run(query)
       if result and 'data' in result:
           # Process successful result
           process_data(result['data'])
       else:
           print("No data returned")
   except Exception as e:
       print(f"Query failed: {e}")

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

Category-Specific Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**ML Models**:
- Remote execution reduces local resource requirements
- Batch predictions when possible
- Cache results for expensive computations

**APIs**:
- Respect rate limits and implement backoff
- Use pagination for large datasets
- Cache frequent queries

**Databases**:
- Use specific field queries instead of full searches
- Implement result limits for exploration
- Index frequently accessed data

**Agents**:
- Configure appropriate timeout values
- Use streaming for long-running tasks
- Implement progress monitoring

Best Practices
--------------

1. **Tool Selection**: Choose the right tool for your specific use case
2. **Rate Limiting**: Respect API rate limits to avoid blocking
3. **Error Handling**: Always handle potential API errors gracefully
4. **Caching**: Use caching for frequently accessed data
5. **Batch Processing**: Use batch operations when available for efficiency
6. **Configuration**: Configure tools appropriately for your environment

Tool Discovery & Selection
---------------------------

Finding the Right Tools
~~~~~~~~~~~~~~~~~~~~~~~

**By Category:**

.. code-block:: python

   # List tools by type (use get_tool_types() to see available types)
   print(tu.get_tool_types())        # e.g. ['opentarget', 'ChEMBL', 'uniprot', ...]
   ml_tools = tu.filter_tools(include_tool_types=["ML_tools"])
   database_tools = tu.filter_tools(include_tool_types=["uniprot", "ChEMBL"])
   api_tools = tu.filter_tools(include_tool_types=["EuropePMC", "PubMed"])

**By Functionality:**

.. code-block:: python

   # Semantic search across all categories
   protein_tools = tu.run({
       "name": "find_tools",
       "arguments": {"query": "protein structure prediction", "limit": 10}
   })
   drug_tools = tu.run({
       "name": "find_tools",
       "arguments": {"query": "drug safety analysis", "limit": 10}
   })
   literature_tools = tu.run({
       "name": "find_tools",
       "arguments": {"query": "literature review automation", "limit": 10}
   })

**By Domain:**

.. code-block:: python

   # Load domain-specific tools
   tu.load_tools(tool_type=[
       "opentarget",    # Disease-target data
       "ChEMBL",        # Chemical data
       "uniprot",       # Protein data
       "pubtator"       # Literature with entities
   ])

API Authentication
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # API keys are managed via environment variables
   # Set them before importing ToolUniverse or use a .env file
   import os

   os.environ['NCBI_API_KEY'] = 'your_ncbi_key'
   os.environ['SEMANTIC_SCHOLAR_API_KEY'] = 'your_s2_key'

   # ToolUniverse automatically reads API keys from environment variables
   tu = ToolUniverse()
   tu.load_tools()

Future Extensions
-----------------

**Planned Categories**:
- **Visualization Tools**: Interactive plotting and dashboard generation
- **Workflow Engines**: Advanced orchestration and scheduling
- **Cloud Services**: Distributed computing and storage
- **Compliance Tools**: Regulatory and ethics validation

**Community Contributions**:
- Tool submission guidelines
- Quality assurance processes
- Community voting and validation
- Maintenance and updates

 Next Steps
-------------

Now that you know what tools are available:

* **Try Examples**: :doc:`examples` - See tools in action
* **Build Workflows**: :doc:`scientific_workflows` - Combine tools for research
* **Extend ToolUniverse**: :doc:`../expand_tooluniverse/index` - Create custom tools

.. tip::
   **Discovery tip**: Use the AI-powered tool discovery features to find the right tools for your specific research questions!

.. tip::
   **Tool ecosystem synergy**: The eight categories are designed to work together. APIs provide data access, ML models add intelligence, agents orchestrate complex workflows, while databases and embedding stores enable efficient information management.
