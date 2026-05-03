API Keys and Authentication
===========================

.. note::
   **Looking for other environment variables?**
   
   This page covers API keys only. For cache, logging, LLM, and other configuration options, see :doc:`../reference/environment_variables`.

Overview
--------

ToolUniverse provides access to 1000+ scientific tools across various domains. Many tools work without API keys, but some require authentication for full functionality or enhanced rate limits.

API Key Categories
------------------

Required API Keys (Essential Features)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These API keys are required for specific tool categories to function:

**NVIDIA NIM Healthcare APIs**

:API Key: ``NVIDIA_API_KEY``
:Required For: Protein structure prediction (AlphaFold2, ESMFold, OpenFold2, Boltz2), molecular docking (DiffDock), protein design (ProteinMPNN, RFdiffusion), genomics tools (Evo2-40B, MSA-Search, ESM2-650M), medical imaging (MAISI, Vista3D)
:How to Get: Visit https://build.nvidia.com and sign up for a free account. Navigate to your API keys section to generate a key.
:Rate Limits: 40 requests per minute (free tier)
:Tool Categories: ``nvidia_nim``

Recommended API Keys (Enhanced Performance)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These API keys are optional but provide better performance, higher rate limits, or additional features:

**USPTO Patent API**

:API Key: ``USPTO_API_KEY``
:Required For: Patent search, patent document retrieval, patent data analysis
:How to Get: Visit https://developer.uspto.gov/ and register for API access
:Rate Limits: Varies by endpoint
:Tool Categories: ``uspto``

**Hugging Face**

:API Key: ``HF_TOKEN``
:Required For: Access to Hugging Face models and datasets, required for certain machine learning tools
:How to Get: Visit https://huggingface.co/settings/tokens and create a new access token
:Rate Limits: Varies by model/dataset
:Tool Categories: ``agentic_tools`` (some models), model hosting features

**NCBI E-utilities**

:API Key: ``NCBI_API_KEY`` (environment variable)
:Required For: PubMed, Nucleotide, Protein, and other NCBI database searches
:How to Get: Create a free NCBI account at https://www.ncbi.nlm.nih.gov/account/, then visit account settings to generate an API key
:Rate Limits: 10 requests/second with key vs 3 requests/second without key
:Benefits: 3x faster rate limit for literature and sequence searches
:Tool Categories: ``pubmed``, ``ncbi_nucleotide``, ``pmc``
:Configuration: Set ``NCBI_API_KEY=your_key`` - automatically used by all NCBI tools. Tools work without this key at reduced rate limits.

**Semantic Scholar**

:API Key: ``SEMANTIC_SCHOLAR_API_KEY`` (environment variable)
:Required For: Academic literature search with enhanced rate limits
:How to Get: Visit https://www.semanticscholar.org/product/api and request an API key
:Rate Limits: 100 requests/second with key vs 1 request/second without key
:Benefits: 100x faster rate limit for literature searches
:Tool Categories: ``semantic_scholar``
:Configuration: Set ``SEMANTIC_SCHOLAR_API_KEY=your_key`` - automatically used. Tools work without this key at reduced rate limits.

**FDA OpenFDA**

:API Key: ``FDA_API_KEY``
:Required For: Drug adverse events, drug labeling, device adverse events
:How to Get: Visit https://open.fda.gov/apis/authentication/ and sign up for a free API key
:Rate Limits: 240 requests/minute with key vs 40 requests/minute without key
:Benefits: 6x rate limit increase for drug safety and labeling queries
:Tool Categories: ``fda_drug_adverse_event``, ``fda_drug_label``, ``adverse_event``

**DisGeNET**

:API Key: ``DISGENET_API_KEY``
:Required For: Gene-disease associations, variant-disease associations
:How to Get: Register at https://www.disgenet.org/ for free academic access
:Rate Limits: Required for API access
:Tool Categories: ``disgenet``

**OMIM (Online Mendelian Inheritance in Man)**

:API Key: ``OMIM_API_KEY``
:Required For: Genetic disorder information, clinical synopses, gene-phenotype relationships
:How to Get: Request access at https://www.omim.org/api (academic license required)
:Rate Limits: Specified in license agreement
:Tool Categories: ``omim``

**BioGRID**

:API Key: ``BIOGRID_API_KEY``
:Required For: Protein-protein interaction data
:How to Get: Register at https://thebiogrid.org/ and request API access
:Rate Limits: Varies by license
:Tool Categories: ``ppi``

**UMLS (Unified Medical Language System)**

:API Key: ``UMLS_API_KEY``
:Required For: Medical terminology, concept mapping, semantic relationships
:How to Get: Register at https://uts.nlm.nih.gov/uts/signup-login (requires UMLS license)
:Rate Limits: Specified in license agreement
:Tool Categories: ``umls``

LLM Provider API Keys (For Agentic Tools)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These API keys enable AI-powered tools that use large language models for reasoning and analysis:

**OpenAI (ChatGPT, GPT-4)**

:API Key: ``OPENAI_API_KEY``
:Base URL: ``OPENAI_BASE_URL`` (optional, default: ``https://api.openai.com/v1``)
:Required For: Agentic tools, summarization, complex reasoning tasks
:How to Get: Visit https://platform.openai.com/api-keys and create a new API key
:Cost: Pay-per-use (varies by model)
:Tool Categories: ``agents``, ``output_summarization``, ``tool_discovery_agents``

**Azure OpenAI**

:API Key: ``AZURE_OPENAI_API_KEY``
:Endpoint: ``AZURE_OPENAI_ENDPOINT`` (required, e.g., ``https://your-endpoint.openai.azure.com``)
:API Version: ``AZURE_OPENAI_API_VERSION`` (required, e.g., ``2024-02-15-preview``)
:Required For: Alternative to OpenAI for enterprise deployments
:How to Get: Azure subscription required. Set up Azure OpenAI service in Azure Portal.
:Cost: Based on Azure pricing
:Tool Categories: Same as OpenAI

**Google Gemini**

:API Key: ``GEMINI_API_KEY``
:Model ID: ``GEMINI_MODEL_ID`` (optional, default: ``gemini-2.0-flash``)
:Required For: Agentic tools using Google's Gemini models
:How to Get: Visit https://ai.google.dev/ and get an API key (free tier available)
:Rate Limits: 60 requests/minute (free tier), higher with paid tiers
:Tool Categories: ``agents``, ``output_summarization``

**VLLM (Self-Hosted LLMs)**

:Server URL: ``VLLM_SERVER_URL``
:Required For: Self-hosted open-source LLMs
:How to Setup: Deploy your own VLLM server (see https://docs.vllm.ai/)
:Cost: Self-hosted (free, but requires GPU infrastructure)
:Tool Categories: ``agents`` (when configured)

MCP Server Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~

These settings configure connections to external Model Context Protocol (MCP) servers:

**Expert Feedback System**

:URL: ``EXPERT_FEEDBACK_MCP_SERVER_URL``
:Default: ``http://localhost:9877``
:Required For: Human-in-the-loop consultation and expert feedback workflows
:How to Setup: Run the expert feedback server locally or deploy to a remote server
:Tool Categories: ``mcp_auto_loader_expert_feedback``

**TxAgent MCP Server**

:Host: ``TXAGENT_MCP_SERVER_HOST``
:Required For: Transcriptomics analysis and gene expression workflows
:How to Setup: Deploy the TxAgent MCP server (see TxAgent documentation)
:Tool Categories: ``mcp_auto_loader_txagent``

**Boltz Structure Prediction**

:Host: ``BOLTZ_MCP_SERVER_HOST``
:Required For: Boltz protein structure prediction via MCP
:How to Setup: Deploy the Boltz MCP server
:Tool Categories: ``mcp_auto_loader_boltz``

**USPTO Patent Downloader**

:Host: ``USPTO_MCP_SERVER_HOST``
:Required For: Bulk patent document downloads
:How to Setup: Deploy the USPTO MCP server
:Tool Categories: ``mcp_auto_loader_uspto_downloader``

Data Path Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~

These environment variables specify paths to local data stores for specific tools:

**COMPASS Model**

:Path: ``COMPASS_MODEL_PATH``
:Required For: Immune cell type annotation and COMPASS model inference
:How to Setup: Download COMPASS model files and set path to model directory

**Pinnacle Embeddings**

:Path: ``PINNACLE_DATA_PATH``
:Required For: Protein-protein interaction embeddings
:How to Setup: Download Pinnacle embedding data and set path to data directory

**Transcriptformer Data**

:Path: ``TRANSCRIPTFORMER_DATA_PATH``
:Default: ``/root/PrismDB``
:Required For: Transcriptomics embeddings and predictions
:How to Setup: Download Transcriptformer data and set path

**DepMap Data**

:Path: ``DEPMAP_DATA_PATH``
:Required For: Cancer dependency data analysis
:How to Setup: Download DepMap 24Q2 data release and set path

Configuration Methods
---------------------

Choose the method that best fits your use case:

.. tab-set::

   .. tab-item:: MCP Configuration

      **For AI agents using Model Context Protocol (Claude, Cursor, etc.)**

      Add API keys to your MCP configuration file's ``env`` section:

      .. code-block:: json

         {
           "mcpServers": {
             "tooluniverse": {
               "command": "uvx",
               "args": ["tooluniverse"],
               "env": {
                 "PYTHONIOENCODING": "utf-8",
                 "NVIDIA_API_KEY": "your_nvidia_api_key",
                 "NCBI_API_KEY": "your_ncbi_api_key",
                 "SEMANTIC_SCHOLAR_API_KEY": "your_semantic_scholar_key",
                 "FDA_API_KEY": "your_fda_key",
                 "OPENTARGETS_API_KEY": "your_opentargets_key"
               }
             }
           }
         }

      **MCP config file locations:**

      - **Claude Desktop**: ``~/Library/Application Support/Claude/claude_desktop_config.json`` (macOS) or ``%APPDATA%\Claude\claude_desktop_config.json`` (Windows)
      - **Cursor**: ``.cursor/mcp_config.json`` in your project
      - **Other agents**: Check your agent's documentation

   .. tab-item:: Environment Variables

      **For Python scripts and command-line usage**

      Set environment variables in your shell:

      .. code-block:: bash

         # On Linux/macOS
         export NVIDIA_API_KEY="your_nvidia_api_key"
         export NCBI_API_KEY="your_ncbi_api_key"
         export OPENTARGETS_API_KEY="your_opentargets_key"

         # On Windows (Command Prompt)
         set NVIDIA_API_KEY=your_nvidia_api_key
         set NCBI_API_KEY=your_ncbi_api_key

         # On Windows (PowerShell)
         $env:NVIDIA_API_KEY="your_nvidia_api_key"
         $env:NCBI_API_KEY="your_ncbi_api_key"

   .. tab-item:: .env File

      **For Python projects with persistent configuration**

      Create a ``.env`` file in your project root:

      .. tip::
         **Use the template**: Copy ``.env.template`` from the project root as a starting point. It includes all available environment variables with documentation.
         
         .. code-block:: bash
         
            cp .env.template .env
            # Then edit .env and add your API keys

      Create a ``.env`` file manually:

      .. code-block:: bash

         # Required API Keys
         NVIDIA_API_KEY=your_nvidia_api_key_here
         USPTO_API_KEY=your_uspto_key_here
         HF_TOKEN=your_huggingface_token_here

         # Recommended API Keys (Optional but improves performance)
         NCBI_API_KEY=your_ncbi_key_here              # 3x faster PubMed queries
         SEMANTIC_SCHOLAR_API_KEY=your_key_here       # 100x faster literature search
         FDA_API_KEY=your_fda_key_here                # 6x faster drug safety queries
         DISGENET_API_KEY=your_disgenet_key_here      # Required for gene-disease data
         OMIM_API_KEY=your_omim_key_here              # Required for genetic disorders
         BIOGRID_API_KEY=your_biogrid_key_here        # Required for PPI data
         UMLS_API_KEY=your_umls_key_here              # Required for medical terminology

         # LLM Provider API Keys (for agentic tools)
         OPENAI_API_KEY=your_openai_key_here
         OPENAI_BASE_URL=https://api.openai.com/v1
         AZURE_OPENAI_API_KEY=your_azure_key_here
         AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
         AZURE_OPENAI_API_VERSION=2024-02-15-preview
         GEMINI_API_KEY=your_gemini_key_here
         GEMINI_MODEL_ID=gemini-2.0-flash
         VLLM_SERVER_URL=http://localhost:8000

         # MCP Server Configurations
         EXPERT_FEEDBACK_MCP_SERVER_URL=http://localhost:9877
         TXAGENT_MCP_SERVER_HOST=http://localhost:8001
         BOLTZ_MCP_SERVER_HOST=http://localhost:8002
         USPTO_MCP_SERVER_HOST=http://localhost:8003

         # Data Path Configurations
         COMPASS_MODEL_PATH=/path/to/compass/models
         PINNACLE_DATA_PATH=/path/to/pinnacle/data
         TRANSCRIPTFORMER_DATA_PATH=/path/to/prismdb
         DEPMAP_DATA_PATH=/path/to/depmap/data

      Load the ``.env`` file in your Python code:

      .. code-block:: python

         from dotenv import load_dotenv
         load_dotenv()  # Load from .env file

         from tooluniverse import ToolUniverse
         tu = ToolUniverse()
         tu.load_tools()

   .. tab-item:: Python Code

      **For setting API keys programmatically in Python**

      Set environment variables in your Python code:

      .. code-block:: python

         import os

         # Set API keys
         os.environ["NVIDIA_API_KEY"] = "your_nvidia_api_key"
         os.environ["NCBI_API_KEY"] = "your_ncbi_api_key"

         # Now initialize ToolUniverse
         from tooluniverse import ToolUniverse
         tu = ToolUniverse()
         tu.load_tools()

   .. tab-item:: Docker

      **For containerized deployments**

      Pass environment variables to Docker:

      .. code-block:: bash

         docker run -e NVIDIA_API_KEY=your_key \
                    -e NCBI_API_KEY=your_key \
                    -e SEMANTIC_SCHOLAR_API_KEY=your_key \
                    your-tooluniverse-image

      Or use a ``.env`` file with Docker Compose:

      .. code-block:: yaml

         version: '3.8'
         services:
           tooluniverse:
             build: .
             env_file:
               - .env
             ports:
               - "7000:7000"

Agentic Tool Configuration
---------------------------

For tools that use LLMs, additional configuration options are available:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Default LLM provider (OPENAI, AZURE_OPENAI, GEMINI, VLLM)
   TOOLUNIVERSE_LLM_DEFAULT_PROVIDER=OPENAI

   # Model configuration per task
   TOOLUNIVERSE_LLM_MODEL_DEFAULT=gpt-4-turbo-preview
   TOOLUNIVERSE_LLM_MODEL_SUMMARIZATION=gpt-3.5-turbo
   TOOLUNIVERSE_LLM_MODEL_REASONING=gpt-4

   # Temperature setting
   TOOLUNIVERSE_LLM_TEMPERATURE=0.7

   # Configuration mode (default or env_override or fallback)
   TOOLUNIVERSE_LLM_CONFIG_MODE=default

   # Custom fallback chain (JSON array of {api_type, model_id} objects)
   AGENTIC_TOOL_FALLBACK_CHAIN='[{"api_type":"OPENAI","model_id":"gpt-4"},{"api_type":"GEMINI","model_id":"gemini-pro"}]'

Configuration Modes
~~~~~~~~~~~~~~~~~~~

1. **default**: Use tool-specific configuration from JSON files
2. **env_override**: Environment variables override tool configuration
3. **fallback**: Try multiple providers in sequence if one fails

Verifying API Keys
------------------

Test your API key configuration:

.. code-block:: python

   from tooluniverse import ToolUniverse

   # Initialize and load tools
   tu = ToolUniverse()
   tu.load_tools()

   # Test NVIDIA NIM (requires NVIDIA_API_KEY)
   result = tu.run({
       "name": "NVIDIA_ESMFold_predict",
       "arguments": {
           "sequence": "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK"
       }
   })
   print("ESMFold test:", "success" if "pdb_content" in result else "failed")

   # Test NCBI (uses NCBI_API_KEY env var if set)
   result = tu.run({
       "name": "PubMed_search_articles",
       "arguments": {
           "query": "CRISPR",
           "limit": 5
       }
   })
   print("PubMed test:", "success" if len(result) > 0 else "failed")

   # Test OpenTargets (no API key needed - public API)
   result = tu.run({
       "name": "OpenTargets_get_associated_targets_by_disease_efoId",
       "arguments": {"efoId": "EFO_0000685"}
   })
   print("OpenTargets test:", "success" if len(result) > 0 else "failed")

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**"API key required" error**

- Verify the environment variable is set: ``echo $NVIDIA_API_KEY``
- Check for typos in variable names
- Ensure the ``.env`` file is in the correct location
- Reload environment: ``source .env`` or restart your shell

**"Invalid API key" error**

- Verify the key is correct and not expired
- Check if the key has necessary permissions
- Some APIs require activation after registration

**"Rate limit exceeded" error**

- Wait before retrying (most APIs have time-based limits)
- Consider getting an API key for higher limits
- Use batch operations when available

**Tools not loading**

- Check tool category is included in load_tools()
- Verify tool configuration files exist
- Check logs for specific error messages

Rate Limits Summary
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Service
     - Without API Key
     - With API Key
     - Notes
   * - NVIDIA NIM
     - Not available
     - 40 req/min
     - Required
   * - NCBI E-utilities
     - 3 req/sec
     - 10 req/sec
     - Optional (env var only)
   * - Semantic Scholar
     - 1 req/sec
     - 100 req/sec
     - Optional (env var only)
   * - OpenFDA
     - 40 req/min
     - 240 req/min
     - Recommended (env var)
   * - DisGeNET
     - Not available
     - As per license
     - Required

Best Practices
--------------

1. **Store API Keys Securely**
   
   - Never commit API keys to version control
   - Add ``.env`` to ``.gitignore``
   - Use environment variables in production
   - Rotate keys periodically

2. **Use .env Files for Development**
   
   - Use the provided ``.env.template`` at project root as a starting point
   - Each developer maintains their own ``.env``
   - Never commit ``.env`` to version control (add to ``.gitignore``)
   - Document which keys are required vs optional in the template

3. **Implement Rate Limiting**
   
   - ToolUniverse handles rate limiting internally for most APIs
   - Be mindful of daily/monthly quotas
   - Use batch operations when available

4. **Monitor Usage**
   
   - Track API usage in provider dashboards
   - Set up billing alerts for paid APIs
   - Cache responses when appropriate

5. **Prioritize Key Types**
   
   - Start with required keys for core functionality
   - Add recommended keys based on usage patterns
   - Only configure LLM providers if using agentic tools

Getting Help
------------

If you encounter issues with API keys or authentication:

1. Check the `Troubleshooting Guide <https://tooluniverse.readthedocs.io/help/troubleshooting>`_
2. Review the `FAQ <https://tooluniverse.readthedocs.io/faq>`_
3. Search `GitHub Issues <https://github.com/mims-harvard/ToolUniverse/issues>`_
4. Open a new issue with:
   
   - Tool category and specific tool name
   - Error messages (redact actual API keys!)
   - Your configuration method
   - Python and ToolUniverse versions

See Also
--------

- :doc:`building_ai_scientists/index` - AI agent platform setup
- :doc:`hooks/hook_configuration` - Advanced hook configuration
