AI-Tool Interaction Protocol
============================

**The foundation that makes ToolUniverse's 1000+ tools universally accessible to any AI system**

Overview
--------

Just as HTTP standardizes client-server communication across the web, ToolUniverse implements an **AI-Tool Interaction Protocol** that standardizes how AI models interact with scientific tools. This protocol abstracts away the complexity of 1000+ heterogeneous tools (machine learning models, databases, APIs, robotics systems) behind a unified interface.

.. code-block:: text

   ┌─────────────────┐
   │   AI Model      │ ← Your LLM, Agent, or Reasoning Model
   │ (GPT, Claude,   │
   │  Gemini, etc.)  │
   └─────────┬───────┘
             │ AI-Tool Interaction Protocol
             │
   ┌─────────▼───────┐
   │  ToolUniverse   │ ← Protocol Implementation
   │   Ecosystem     │
   └─────────┬───────┘
             │
   ┌─────────▼───────┐
   │  1000+ Tools     │ ← ML Models, APIs, Databases, etc.
   │ (Heterogeneous  │
   │   Backends)     │
   └─────────────────┘

Protocol Components
-------------------

The AI-Tool Interaction Protocol comprises three essential elements:

1. **Specification Schema** - How tools describe themselves
2. **Interaction Schema** - How to request tool execution
3. **Communication Methods** - Local Python and remote MCP

1. Tool Specification Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every tool in ToolUniverse exposes itself through a standardized specification:

.. code-block:: python

   {
       "name": "UniProt_get_entry_by_accession",
       "description": "Get complete JSON entry for a UniProtKB accession",
       "parameters": {
           "type": "object",
           "properties": {
               "accession": {
                   "type": "string",
                   "description": "UniProtKB accession (e.g., P05067)",
                   "required": true
               }
           }
       },
       "return_schema": {
           "type": "object",
           "description": "Complete UniProtKB entry with protein information"
       }
   }

**Schema Components:**

- **Name**: Unique tool identifier following `Database_action_description` format
- **Description**: Clear explanation of tool's purpose and functionality
- **Parameters**: Detailed argument specifications with types and requirements
- **Return Schema**: Structure of expected output data

2. Interaction Schema
~~~~~~~~~~~~~~~~~~~~~

All tool interactions follow a uniform request format:

.. code-block:: python

   {
       "name": "Tool_identifier",
       "arguments": {
           "parameter1": "value1",
           "parameter2": "value2"
       }
   }

**Example Requests:**

.. code-block:: python

   # Protein information request
   {
       "name": "UniProt_get_entry_by_accession",
       "arguments": {
           "accession": "P05067"
       }
   }

   # Drug safety analysis request
   {
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {
           "medicinalproduct": "aspirin"
       }
   }

   # ML model prediction request
   {
       "name": "boltz2_docking",
       "arguments": {
           "protein_id": "1ABC",
           "ligand_smiles": "CCO"
       }
   }

3. Communication Methods
~~~~~~~~~~~~~~~~~~~~~~~~

**Local Communication** (Python):

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()

   # Direct tool execution
   result = tu.run({
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000537"}  # hypertension
   })

**Remote Communication** (MCP):

.. code-block:: bash

   # Start MCP server
   tooluniverse-smcp --port 8000

   # AI assistants connect via MCP
   # Tools become available in Claude, ChatGPT, etc.

Core Operations
---------------

The protocol defines two fundamental operations that AI systems use to interact with ToolUniverse:

Find Tool Operation
~~~~~~~~~~~~~~~~~~~

**Purpose**: Discover relevant tools based on natural language descriptions

**Input**: Natural language query describing desired functionality

**Output**: List of relevant tool specifications

.. code-block:: python

   # How AI models discover tools
   query = "predict protein binding affinity"

   # Protocol returns relevant tools:
   tools_found = [
       "boltz2_docking",
       "ADMETAI_predict_properties",
       "ChEMBL_search_similar_molecules"
   ]

**Implementation Methods:**

1. **Keyword Search**: Fast TF-IDF matching with morphological processing
2. **LLM-based Search**: Contextual reasoning for complex queries
3. **Embedding Search**: Semantic similarity using fine-tuned models

Call Tool Operation
~~~~~~~~~~~~~~~~~~~

**Purpose**: Execute a selected tool with specified arguments

**Input**: Tool name and structured arguments

**Output**: Structured results from tool execution

.. code-block:: python

   # Standardized execution across all tool types
   request = {
       "name": "boltz2_docking",
       "arguments": {
           "protein_id": "P05067",
           "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
       }
   }

   result = tu.run(request)

   # Consistent result structure
   {
       "binding_affinity": -8.2,
       "binding_probability": 0.85,
       "confidence_score": 0.92,
       "metadata": {
           "model_version": "boltz-2",
           "execution_time": "2.3s"
       }
   }

Tool Types & Backend Abstraction
---------------------------------

The protocol successfully abstracts diverse tool backends:

Machine Learning Models
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Protein structure prediction
   {
       "name": "boltz2_docking",
       "arguments": {"protein_id": "1ABC", "ligand_smiles": "CCO"}
   }

   # ADMET property prediction
   {
       "name": "ADMETAI_predict_admet_properties",
       "arguments": {"smiles": "CCO", "properties": ["BBB_penetrance"]}
   }

Database APIs
~~~~~~~~~~~~~

.. code-block:: python

   # GraphQL database (OpenTargets)
   {
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000537"}  # hypertension
   }

   # REST API (UniProt)
   {
       "name": "UniProt_get_entry_by_accession",
       "arguments": {"accession": "P05067"}
   }

Scientific Software Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Bioinformatics tools
   {
       "name": "get_biopython_info",
       "arguments": {"package": "Bio.SeqIO"}
   }

   # Analysis packages
   {
       "name": "Enrichr_analyze_gene_list",
       "arguments": {"genes": ["BRCA1", "BRCA2"], "library": "KEGG_2021_Human"}
   }

AI Agents & Tools
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Literature review agent
   {
       "name": "conduct_literature_review_and_summarize",
       "arguments": {"topic": "HMG-CoA reductase inhibitors"}
   }

   # Hypothesis generation
   {
       "name": "HypothesisGenerator",
       "arguments": {"context": "Alzheimer's disease treatment"}
   }

Error Handling & Validation
----------------------------

The protocol includes robust error handling:

Input Validation
~~~~~~~~~~~~~~~~

.. code-block:: python

   # Automatic parameter validation
   request = {
       "name": "UniProt_get_entry_by_accession",
       "arguments": {
           "accession": "INVALID_ID"  # Invalid format
       }
   }

   # Protocol returns structured error
   {
       "status": "error",
       "error_type": "ValidationError",
       "message": "Invalid UniProt accession format",
       "details": {
           "parameter": "accession",
           "expected_format": "P12345 or Q9Y261",
           "received": "INVALID_ID"
       }
   }

Protocol Extensions
-------------------

Tool Composition
~~~~~~~~~~~~~~~~

The protocol supports chaining tools for complex workflows:

.. code-block:: python

   # Composed workflow example
   workflow = {
       "name": "drug_discovery_pipeline",
       "arguments": {
           "disease": "hypercholesterolemia",
           "steps": [
               "target_identification",
               "compound_screening",
               "ADMET_prediction",
               "patent_analysis"
           ]
       }
   }

Human-in-the-Loop
~~~~~~~~~~~~~~~~~

Expert feedback integration through the protocol:

.. code-block:: python

   # Request human expert consultation
   {
       "name": "consult_human_expert",
       "arguments": {
           "question": "Which HMG-CoA reductase inhibitor shows best safety profile?",
           "context": {"compounds": ["lovastatin", "pravastatin", "simvastatin"]},
           "expertise_required": "pharmacology"
       }
   }

Remote Tool Integration
~~~~~~~~~~~~~~~~~~~~~~~

MCP-based remote tool registration:

.. code-block:: python

   # Register external MCP server tools
   {
       "name": "register_mcp_tools",
       "arguments": {
           "server_url": "mcp://expert-system.company.com:8080",
           "tool_categories": ["proprietary_ml_models", "private_databases"]
       }
   }

Protocol Benefits
-----------------

**For AI Developers:**
- Single interface for 1000+ diverse tools
- No tool-specific integration work required
- Automatic error handling and validation
- Consistent response formats

**For Scientists:**
- Focus on research logic, not technical implementation
- Reproducible workflows across different tools
- Easy tool discovery and experimentation
- Human expertise integration when needed

**For Tool Creators:**
- Standardized way to expose functionality
- Automatic AI compatibility
- Built-in documentation and validation
- Community discoverability

Implementation Details
----------------------

The protocol is implemented through ToolUniverse's core components:

- **Tool Registry**: Maps tool names to implementation classes
- **Tool Caller**: Handles protocol parsing and execution
- **Tool Finder**: Implements the three discovery strategies
- **Tool Manager**: Manages local and remote tool registration
- **Validation Engine**: Ensures request/response compliance

.. tip::
   **The protocol makes ToolUniverse unique**: While other frameworks provide tool orchestration, ToolUniverse creates a universal language for AI-tool interaction, similar to how HTTP enabled the modern web.
