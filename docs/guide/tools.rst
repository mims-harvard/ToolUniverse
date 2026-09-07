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
------------------------

UniProt - Protein Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access comprehensive protein and gene information.

**Key Functions:**
* ``UniProt_get_function_by_accession`` - Get functional annotations by UniProt accession
* ``UniProt_search`` - Search UniProtKB with field queries
* ``UniProt_get_sequence_by_accession`` - Retrieve protein sequences

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
* ``GO_get_annotations_for_gene`` - Get GO annotations for a gene
* ``GO_search_terms`` - Search GO terms
* ``GO_get_genes_for_term`` - Get genes annotated to a GO term

**Example:**

.. code-block:: python

   query = {
       "name": "GO_get_annotations_for_gene",
       "arguments": {"gene_id": "TP53"}
   }

Enrichr - Gene Set Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive gene set enrichment analysis.

**Key Functions:**
* ``Enrichr_enrich`` - Enrichment analysis for a gene list against one library
* ``Enrichr_list_libraries`` - List available gene set libraries
* ``Enrichr_get_top_enriched`` - Top enriched terms across several libraries

**Example:**

.. code-block:: python

   query = {
       "name": "Enrichr_enrich",
       "arguments": {
           "gene_list": ["BRCA1", "BRCA2", "TP53", "ATM", "CHEK2"],
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
* ``OpenTargets_get_associated_diseases_by_drug_chemblId`` - Drug-associated diseases
* ``OpenTargets_get_disease_id_description_by_name`` - Disease lookup
* ``OpenTargets_get_evidence_by_datasource`` - Evidence for associations
* ``OpenTargets_get_drug_mechanisms_of_action_by_chemblId`` - Drug mechanisms of action

**Example:**

.. code-block:: python

   # Get targets for Alzheimer's disease
   query = {
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "MONDO_0004975"}  # Alzheimer disease
   }

EFO - Experimental Factor Ontology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Disease and experimental factor ontology.

**Key Functions:**
* ``ols_search_efo_terms`` - Search EFO terms by name
* ``OSL_get_efo_id_by_disease_name`` - Resolve a disease name to an EFO ID
* ``ols_get_efo_term_children`` - Get child terms of an EFO term

**Example:**

.. code-block:: python

   query = {
       "name": "ols_search_efo_terms",
       "arguments": {"query": "diabetes mellitus", "rows": 5}
   }

Drug & Chemical Data
-----------------------

PubChem - Chemical Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive chemical compound database.

**Key Functions:**
* ``PubChem_get_CID_by_compound_name`` - Look up compound IDs by name
* ``PubChem_search_compounds_by_substructure`` - Search compounds by substructure
* ``PubChem_get_compound_properties_by_CID`` - Molecular properties
* ``PubChem_search_compounds_by_similarity`` - Chemical similarity search

**Example:**

.. code-block:: python

   query = {
       "name": "PubChem_get_CID_by_compound_name",
       "arguments": {"name": "aspirin"}
   }

ChEMBL - Bioactivity Data
~~~~~~~~~~~~~~~~~~~~~~~~~

Chemical bioactivity and drug discovery data.

**Key Functions:**
* ``ChEMBL_get_molecule_targets`` - Get targets for a molecule
* ``ChEMBL_search_targets`` - Find target ChEMBL IDs by name or gene symbol
* ``ChEMBL_get_target_activities`` - Bioactivity measurements for a target
* ``ChEMBL_search_similar_molecules`` - Chemical similarity search

**Example:**

.. code-block:: python

   # EGFR is CHEMBL203; use ChEMBL_search_targets to look an ID up by name
   query = {
       "name": "ChEMBL_get_target_activities",
       "arguments": {"target_chembl_id": "CHEMBL203", "limit": 20}
   }

️ Drug Safety & Regulatory
----------------------------

OpenFDA - FDA Data
~~~~~~~~~~~~~~~~~~~

FDA drug labeling and adverse event data.

**Key Functions:**
* ``FAERS_count_reactions_by_drug_event`` - Count adverse reactions by drug
* ``FDA_get_warnings_by_drug_name`` - Get FDA warnings
* ``OpenFDA_search_drug_labels`` - Drug labeling information
* ``OpenFDA_search_drug_enforcement`` - Drug recall and enforcement information

**Example:**

.. code-block:: python

   # Search adverse events
   query = {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "warfarin"}
   }

   # Get FDA warnings
   query = {
       "name": "FDA_get_warnings_by_drug_name",
       "arguments": {"drug_name": "warfarin"}
   }

DailyMed - Drug Labeling
~~~~~~~~~~~~~~~~~~~~~~~~

Official FDA drug labeling information.

**Key Functions:**
* ``DailyMed_search_spls`` - Search structured product labels by drug name, NDC or RxCUI
* ``DailyMed_get_spl_by_setid`` - Get a full label by its set ID
* ``DailyMed_parse_dosing`` - Extract the dosing section from a label

**Example:**

.. code-block:: python

   query = {
       "name": "DailyMed_search_spls",
       "arguments": {"drug_name": "metformin"}
   }

Clinical Research
--------------------

ClinicalTrials.gov
~~~~~~~~~~~~~~~~~~

Clinical trial registry and results database.

**Key Functions:**
* ``ClinicalTrials_search_studies`` - Search clinical trials
* ``ClinicalTrials_get_study`` - Get detailed study information by NCT ID
* ``ClinicalTrials_search_by_intervention`` - Find trials by intervention
* ``ClinicalTrials_search_by_sponsor`` - Find trials by lead sponsor

**Example:**

.. code-block:: python

   query = {
       "name": "ClinicalTrials_search_studies",
       "arguments": {
           "query_cond": "breast cancer",
           "query_intr": "immunotherapy"
       }
   }

Literature & Publications
-----------------------------

PubTator - Biomedical Literature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PubMed literature with named entity recognition.

**Key Functions:**
* ``PubTator3_LiteratureSearch`` - Search literature with entities
* ``PubTator3_get_annotations`` - Get entity annotations for PMIDs
* ``PubTator3_EntityAutocomplete`` - Resolve a free-text name to a PubTator entity ID

**Example:**

.. code-block:: python

   query = {
       "name": "PubTator3_LiteratureSearch",
       "arguments": {
           "query": "@GENE_BRCA1 AND @DISEASE_Neoplasms"
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
* ``SemanticScholar_get_paper`` - Get detailed paper information
* ``SemanticScholar_get_paper_citations`` - Citation network analysis

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
* ``openalex_search_works`` - Search academic works
* ``openalex_get_author`` - Author information and metrics
* ``openalex_get_institution`` - Institution research data

Specialized Databases
------------------------

Human Protein Atlas
~~~~~~~~~~~~~~~~~~~

Tissue and cell expression data.

**Key Functions:**
* ``HPA_get_rna_expression_in_specific_tissues`` - Tissue expression patterns
* ``HPA_get_comparative_expression_by_gene_and_cellline`` - Cell-line expression data
* ``HPA_get_subcellular_location`` - Subcellular localization

**Example:**

.. code-block:: python

   query = {
       "name": "HPA_get_rna_expression_in_specific_tissues",
       "arguments": {
           "ensembl_id": "ENSG00000012048",  # BRCA1
           "tissue_names": ["breast", "ovary"]
       }
   }

Reactome Pathways
~~~~~~~~~~~~~~~~~

Biological pathway database.

**Key Functions:**
* ``Reactome_map_uniprot_to_pathways`` - Pathways for a protein
* ``ReactomeContent_search`` - Search pathway database
* ``Reactome_get_pathway`` - Detailed pathway information

**Example:**

.. code-block:: python

   query = {
       "name": "Reactome_map_uniprot_to_pathways",
       "arguments": {"uniprot_id": "P04637"}  # TP53
   }

HumanBase
~~~~~~~~~

Tissue-specific gene networks.

**Key Functions:**
* ``humanbase_ppi_analysis`` - Tissue-specific protein-protein interaction networks

MedlinePlus
~~~~~~~~~~~

Consumer health information.

**Key Functions:**
* ``MedlinePlus_search_topics_by_keyword`` - Health topic information
* ``MedlinePlus_get_genetics_condition_by_name`` - Genetic condition information
* ``MedlinePlus_connect_lookup_by_code`` - Look up consumer information by drug or test code

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
           "sequence": "MVLSPADKTNVKAAW",
           "ligands": ["CCO"],
           "recycling_steps": 3,
           "sampling_steps": 200,
           "diffusion_samples": 1,
           "step_scale": 1.638,
           "use_potentials": False,
           "return_structure": True
       }
   }
   # Returns: binding affinity and probability, plus the predicted structure

**ADMETAI_predict_CYP_interactions** - Drug metabolism prediction

.. code-block:: python

   {
       "name": "ADMETAI_predict_CYP_interactions",
       "arguments": {
           "smiles": ["CC(=O)OC1=CC=CC=C1C(=O)O"]  # Aspirin
       }
   }
   # Returns: per-CYP-isoform inhibition probabilities

AI Agents (33 tools)
~~~~~~~~~~~~~~~~~~~~

Autonomous tools that perceive environments, make decisions, and take actions toward research goals.

**Literature & Analysis Agents:**

**HypothesisGenerator** - Generate research hypotheses

.. code-block:: python

   {
       "name": "HypothesisGenerator",
       "arguments": {
           "context": "Checkpoint inhibitors work in only a subset of solid tumours.",
           "domain": "cancer immunotherapy",
           "number_of_hypotheses": 5
       }
   }
   # Returns: ranked hypotheses with supporting rationale

**ExperimentalDesignScorer** - Evaluate experimental designs

.. code-block:: python

   {
       "name": "ExperimentalDesignScorer",
       "arguments": {
           "hypothesis": "EGFR inhibition slows progression in EGFR-mutant NSCLC.",
           "design_description": "Phase II single-arm trial, 80 patients, 12-month PFS endpoint"
       }
   }
   # Returns: design score with improvement suggestions

**MedicalLiteratureReviewer** - Comprehensive literature analysis

.. code-block:: python

   {
       "name": "MedicalLiteratureReviewer",
       "arguments": {
           "research_topic": "CAR-T cell therapy safety profile",
           "literature_content": "<abstracts or full text to synthesise>",
           "focus_area": "safety profile",
           "study_types": "randomized controlled trials",
           "quality_level": "moderate and above",
           "review_scope": "rapid review"
       }
   }
   # Returns: synthesised review with key findings and research gaps

Search & Integration Tools
-----------------------------

Tool Finder
~~~~~~~~~~~

Find appropriate tools for your research needs.

**Key Functions:**
* ``Tool_Finder_Keyword`` - Keyword-based tool search
* ``Tool_Finder_LLM`` - LLM-reasoned tool search
* ``Tool_RAG`` - Embedding-based semantic tool search

**Example:**

.. code-block:: python

   query = {
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": "drug safety and adverse events", "limit": 10}
   }

Embedding Stores
~~~~~~~~~~~~~~~~

Store and retrieve vectorized representations of scientific data for semantic search.

**Core Embedding Tools:**

**embedding_database_create** - Create a collection to embed into

.. code-block:: python

   {
       "name": "embedding_database_create",
       "arguments": {"database_name": "pubmed_abstracts"}
   }

**embedding_database_search** - Vector similarity search

.. code-block:: python

   {
       "name": "embedding_database_search",
       "arguments": {
           "database_name": "pubmed_abstracts",
           "query": "protein folding dynamics",
           "top_k": 50
       }
   }
   # Returns: similar documents with relevance scores and metadata

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
       "name": "Enrichr_enrich",
       "arguments": {
           "gene_list": target_list,
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
           "arguments": {"diseaseName": disease_name}
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
               "arguments": {"ensemblId": target['id']}
           }
           target_drugs = tooluni.run(drugs_query)
           drugs.extend(target_drugs)

       # 4. Check safety profiles
       for drug in drugs[:10]:  # Top 10 drugs
           safety_query = {
               "name": "FDA_get_warnings_by_drug_name",
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
       ("ChEMBL_get_target_activities", {"target_chembl_id": target_chembl_id}),
       ("ADMETAI_predict_physicochemical_properties", {"smiles": [compound]}),
       ("ADMETAI_predict_toxicity", {"smiles": [compound]})
   ]

**Parallel Data Gathering:**

.. code-block:: python

   # Multi-database literature search
   parallel_searches = [
       ("PubTator3_LiteratureSearch", {"query": research_topic}),
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
   ml_tools = tu.filter_tools(include_tool_types=["admetai"])
   database_tools = tu.filter_tools(include_tool_types=["uniprot", "ChEMBL"])
   api_tools = tu.filter_tools(include_tool_types=["EuropePMC", "pubtator"])

**By Functionality:**

.. code-block:: python

   # Keyword search across all categories
   protein_tools = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": "protein structure prediction", "limit": 10}
   })
   drug_tools = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": "drug safety analysis", "limit": 10}
   })
   literature_tools = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": "literature review automation", "limit": 10}
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
