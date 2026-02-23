Python Guide
======================

**Complete guide for using ToolUniverse with Python**

Welcome to the Python developer path! This guide covers everything you need to build scientific workflows with ToolUniverse's Python API.

Installation
------------

Choose your preferred installation method:

.. tab-set::

   .. tab-item:: pip
      :sync: pip

      Standard installation with pip:

      .. code-block:: bash

         pip install tooluniverse

   .. tab-item:: uv (Recommended)
      :sync: uv

      Fast, modern package manager:

      .. code-block:: bash

         uv pip install tooluniverse

   .. tab-item:: Development
      :sync: dev

      For contributors and custom modifications:

      .. code-block:: bash

         git clone https://github.com/mims-harvard/ToolUniverse.git
         cd ToolUniverse
         uv sync  # or: pip install -e .[dev]

.. tip:: 🎯 **Pro Tip**
   
   Use ``uv`` for faster installations and better dependency management. Install it with: ``curl -LsSf https://astral.sh/uv/install.sh | sh``

Verify Installation
~~~~~~~~~~~~~~~~~~~

Check that ToolUniverse is installed correctly:

.. code-block:: python

   import tooluniverse
   print(f"ToolUniverse version: {tooluniverse.__version__}")
   print("✅ Installation successful!")

.. success:: ✅ **Installation Complete**
   
   You're ready to start using ToolUniverse!

Quick Start
-----------

Get your first scientific query running in 5 minutes:

.. card:: Step 1: Initialize ToolUniverse
   :class-card: step-card completed

   Create a ToolUniverse instance:

   .. code-block:: python

      from tooluniverse import ToolUniverse

      # Initialize ToolUniverse
      tu = ToolUniverse()

.. card:: Step 2: Load Tools
   :class-card: step-card completed

   Load the scientific tools ecosystem:

   .. code-block:: python

      # Load all 1000+ tools
      tu.load_tools()

      print(f"✅ Loaded {len(tu.all_tools)} scientific tools!")

   .. dropdown:: 💡 Advanced: Load Specific Tools
      :animate: fade-in-slide-down
      :color: info

      For faster loading, specify tool categories:

      .. code-block:: python

         # Load only specific tool categories
         tu.load_tools(tool_type=['uniprot', 'ChEMBL', 'opentarget'])

.. card:: Step 3: Execute Your First Tool
   :class-card: step-card current

   Query scientific databases:

   .. code-block:: python

      # Get protein function from UniProt
      result = tu.run({
          "name": "UniProt_get_function_by_accession",
          "arguments": {"accession": "P05067"}
      })

      print(result)

.. important:: ⚡ **Success!**
   
   You now have access to 1000+ scientific tools for drug discovery, protein analysis, literature search, and more!

Tool Execution
~~~~~~~~~~~~~~

All tools follow a **consistent structure**:

.. code-block:: python

   # Standardized query format
   query = {
       "name": "tool_name",           # Tool identifier
       "arguments": {                 # Tool parameters
           "parameter1": "value1",
           "parameter2": "value2"
       }
   }

   result = tu.run(query)

**Two execution methods:**

.. tab-set::

   .. tab-item:: Dictionary API
      
      Explicit and clear:

      .. code-block:: python

         # Method 1: Dictionary API
         result = tu.run({
             "name": "OpenTargets_get_associated_targets_by_disease_efoId",
             "arguments": {"efoId": "EFO_0000537"}
         })

   .. tab-item:: Direct Import

      Convenient shorthand:

      .. code-block:: python

         # Method 2: Direct Import
         from tooluniverse.opentarget_tool import OpenTargets_get_associated_targets_by_disease_efoId
         
         # Call directly
         result = OpenTargets_get_associated_targets_by_disease_efoId(
             efoId="EFO_0000537"
         )

Tool Finders
~~~~~~~~~~~~~~

ToolUniverse has **three ways** to find tools. Don't browse 1000+ tools manually—use Tool Finder!

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: 🔍 Keyword Search
      :class-card: hover-lift
      :shadow: md

      **Fast text matching**
      
      Best for: Exact terms you know

      .. code-block:: python

         tools = tu.run({
             "name": "Tool_Finder_Keyword",
             "arguments": {
                 "description": "protein structure",
                 "limit": 5
             }
         })

   .. grid-item-card:: 🤖 LLM Search
      :class-card: hover-lift
      :shadow: md

      **Natural language (LLM API required)**
      
      Best for: Descriptive queries

      .. code-block:: python

         tools = tu.run({
             "name": "Tool_Finder_LLM",
             "arguments": {
                 "description": "find tools for analyzing gene expression",
                 "limit": 5
             }
         })

   .. grid-item-card:: 🧠 Semantic Search
      :class-card: hover-lift
      :shadow: md

      **Embedding-based (GPU required)**
      
      Best for: Conceptual matches

      .. code-block:: python

         tools = tu.run({
             "name": "Tool_Finder",
             "arguments": {
                 "description": "drug safety analysis",
                 "limit": 5
             }
         })

   .. grid-item-card:: 📋 Browse by Category
      :class-card: hover-lift
      :shadow: md

      **Organized view**
      
      Best for: Exploring tool types

      .. code-block:: python

         # List by configuration file
         stats = tu.list_built_in_tools(mode='config')
         
         # List by tool type
         stats = tu.list_built_in_tools(mode='type')

.. seealso::
   For detailed guide on finding tools, see :doc:`finding_tools`


Common Examples
~~~~~~~~~~~~~~~

**Protein & Gene Information**

.. code-block:: python

   # Get protein function
   result = tu.run({
       "name": "UniProt_get_function_by_accession",
       "arguments": {"accession": "P05067"}
   })

**Drug Safety Analysis**

.. code-block:: python

   # Check adverse events
   result = tu.run({
       "name": "FAERS_count_reactions_by_drug_event",
       "arguments": {"medicinalproduct": "aspirin"}
   })

**Disease-Target Relationships**

.. code-block:: python

   # Find therapeutic targets
   result = tu.run({
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000685"}  # Rheumatoid arthritis
   })

**Literature Search**

.. code-block:: python

   # Search scientific papers
   result = tu.run({
       "name": "PubTator_search_publications",
       "arguments": {
           "query": "CRISPR cancer therapy",
           "limit": 10
       }
   })

Tool Specifications
~~~~~~~~~~~~~~~~~~~

Inspect tool details before execution:

.. code-block:: python

   # Get single tool specification
   spec = tu.tool_specification("UniProt_get_function_by_accession", format="openai")
   
   print(f"Name: {spec['name']}")
   print(f"Description: {spec['description']}")
   print("Parameters:")
   for param_name, param_info in spec['parameters']['properties'].items():
       print(f"  - {param_name}: {param_info['type']} - {param_info['description']}")

   # Get multiple specifications
   specs = tu.get_tool_specification_by_names([
       "FAERS_count_reactions_by_drug_event",
       "OpenTargets_get_associated_targets_by_disease_efoId"
   ])

.. seealso::
   For AI-Tool Interaction Protocol details, see :doc:`interaction_protocol`

Building Workflows
------------------

Chain tools for complex research tasks:

Multi-Step Pipeline
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from tooluniverse import ToolUniverse

   tu = ToolUniverse()
   tu.load_tools()

   # Step 1: Find tools for drug discovery
   tools = tu.run({
       "name": "Tool_Finder_Keyword",
       "arguments": {"description": "drug target", "limit": 3}
   })

   # Step 2: Get disease targets
   targets = tu.run({
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000685"}
   })

   # Step 3: For each target, get protein info
   rows = targets['data']['disease']['associatedTargets']['rows']
   for row in rows[:3]:  # First 3 targets
       target = row['target']
       protein_info = tu.run({
           "name": "UniProt_get_entry_by_accession",
           "arguments": {"accession": target.get("id")}
       })
       print(f"Target: {target.get('approvedSymbol')}")
       print(f"Protein: {protein_info}")

Batch Execution
~~~~~~~~~~~~~~~

Execute multiple tools in parallel:

.. code-block:: python

   # Prepare multiple queries
   queries = [
       {"name": "UniProt_get_function_by_accession", "arguments": {"accession": "P05067"}},
       {"name": "UniProt_get_function_by_accession", "arguments": {"accession": "P04637"}},
       {"name": "UniProt_get_function_by_accession", "arguments": {"accession": "P01112"}},
   ]

   # Execute in batch
   results = [tu.run(query) for query in queries]

.. seealso::
   - :doc:`tool_composition` - Advanced tool chaining patterns
   - :doc:`scientific_workflows` - Real-world research scenarios
   - :doc:`tooluniverse_case_study` - End-to-end drug discovery example

Configuration
-------------

API Keys
~~~~~~~~

Some tools require API keys for enhanced performance:

.. dropdown:: 🔑 Setting Up API Keys
   :animate: fade-in-slide-down
   :color: primary

   **Environment Variables** (Recommended)

   .. code-block:: bash

      # Essential for specific features
      export NVIDIA_API_KEY=your_nvidia_key_here        # Structure prediction
      export HF_TOKEN=your_huggingface_token_here       # Model hosting

      # Recommended for better performance
      export NCBI_API_KEY=your_ncbi_key_here            # 3x faster queries
      export SEMANTIC_SCHOLAR_API_KEY=your_key_here     # 100x faster literature
      export FDA_API_KEY=your_fda_key_here              # 6x faster safety data

   **Using .env File**

   .. code-block:: bash

      # Copy template
      cp docs/.env.template .env

      # Edit with your keys
      nano .env

   **See detailed guide:** :doc:`api_keys`

Tool Loading Options
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load all tools (default)
   tu.load_tools()

   # Load specific categories
   tu.load_tools(tool_type=['uniprot', 'ChEMBL', 'opentarget'])

   # Load only specific tools by name
   tu.load_tools(include_tools=['UniProt_get_function_by_accession', 'PubMed_search_articles'])

Logging
~~~~~~~

Configure logging for debugging:

.. code-block:: python

   import logging

   # Enable detailed logging
   logging.basicConfig(level=logging.INFO)

   # ToolUniverse operations will now log details
   tu = ToolUniverse()
   tu.load_tools()

.. seealso::
   For comprehensive logging configuration, see :doc:`logging`

Advanced Features
-----------------

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: 🔗 Tool Composition
      :link: tool_composition
      :link-type: doc
      :class-card: hover-lift
      :shadow: md

      Chain multiple tools into scientific workflows

   .. grid-item-card:: 🎣 Hooks System
      :link: hooks/index
      :link-type: doc
      :class-card: hover-lift
      :shadow: md

      Intelligent output processing and summarization

   .. grid-item-card:: 💾 Cache System
      :link: cache_system
      :link-type: doc
      :class-card: hover-lift
      :shadow: md

      Optimize performance with smart caching

   .. grid-item-card:: 🌐 HTTP API
      :link: http_api
      :link-type: doc
      :class-card: hover-lift
      :shadow: md

      Deploy ToolUniverse as a remote service

.. button-ref:: tooluniverse_case_study
   :color: primary
   :shadow:
   :expand:

   📚 **Complete Case Study**: Drug discovery workflow with Gemini 2.5 Pro

.. button-ref:: ../api/modules
   :color: secondary
   :shadow:
   :expand:

   🔌 **API Reference**: Detailed Python API documentation

.. toctree::
   :maxdepth: 2
   :hidden:

   coding_api
   interaction_protocol
   loading_tools
   listing_tools
   finding_tools
   tool_caller
   tool_composition
   toolspace
   examples
   tooluniverse_case_study
   http_api

Need Help?
----------

- 📖 **Documentation**: :doc:`../index`
- 🐛 **Issues**: `GitHub Issues <https://github.com/mims-harvard/ToolUniverse/issues>`_
- 💬 **Community**: `Slack Channel <https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ>`_
- ❓ **FAQ**: :doc:`../help/faq`


