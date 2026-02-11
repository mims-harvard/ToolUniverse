Gemini CLI
=============================

**Building AI Scientists with Gemini CLI and ToolUniverse**

Overview
--------

Gemini CLI Integration enables powerful command-line-based scientific research through the Model Context Protocol (MCP). This approach provides a terminal-based interface for scientific research while leveraging Gemini's advanced reasoning capabilities and ToolUniverse's comprehensive scientific tools ecosystem.

.. code-block:: text

   ┌─────────────────┐
   │   Gemini CLI    │ ← Command Line Interface & Reasoning
   │                 │
   └─────────┬───────┘
             │ MCP Protocol
             │
   ┌─────────▼───────┐
   │ ToolUniverse     │ ← MCP Server
   │   MCP Server     │
   └─────────┬───────┘
             │
   ┌─────────▼───────┐
   │ 1000+ Scientific │ ← Scientific Tools Ecosystem
   │     Tools       │
   └─────────────────┘

**Benefits of Gemini CLI Integration**:

- **Command-Line Efficiency**: Fast, scriptable scientific research workflows
- **Advanced Reasoning**: Gemini's sophisticated reasoning for complex scientific problems
- **Comprehensive Tools**: Access to 1000+ scientific tools across multiple domains
- **Automated Execution**: Direct tool execution through natural language commands
- **Batch Processing**: Handle multiple research tasks efficiently

Prerequisites
-------------

Before setting up Gemini CLI integration, ensure you have:

- **Gemini CLI**: Installed and running on your system
- **Python 3.10+**: Required for ToolUniverse
- **UV Package Manager**: For dependency management
- **System Requirements**: macOS, Windows, or Linux
- **API Keys**: Valid API keys for external services (if required by specific tools)

Installation and Setup
----------------------

Step 1: Install Gemini CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install Gemini CLI following the official installation Tutorial:

.. code-block:: bash

   # Follow the installation Tutorial at:
   # https://github.com/google-gemini/gemini-cli

Verify installation:

.. code-block:: bash

   gemini --version

Step 2: Install UV and ToolUniverse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Create working directory for ToolUniverse
   # uv will automatically create and manage a virtual environment (.venv) inside this directory
   mkdir -p /path/to/tooluniverse-env
   uv --directory /path/to/tooluniverse-env pip install tooluniverse

   # Verify installation
   uv --directory /path/to/tooluniverse-env run python -c "import tooluniverse; print('ToolUniverse installed successfully')"

Step 3: Locate Gemini CLI Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Gemini CLI uses configuration files to manage MCP servers. You can configure them:

- **Globally**: In the `~/.gemini/settings.json` file
- **Per project**: In your project's `.gemini/settings.json` file

Create or open your `settings.json` file:

.. code-block:: bash

   # Global configuration
   mkdir -p ~/.gemini
   touch ~/.gemini/settings.json

   # Or project-specific configuration
   mkdir -p .gemini
   touch .gemini/settings.json

Step 4: Configure ToolUniverse MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the ToolUniverse MCP server configuration to your `settings.json`:

**Basic Configuration:**

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ]
       }
     }
   }

**Optimized Configuration for Research Users (Recommended):**

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio",
           "--exclude-tool-types",
           "PackageTool",
           "--hook-type",
           "SummarizationHook"
         ],
         "env": {
           "AZURE_OPENAI_API_KEY": "your-azure-openai-api-key",
           "AZURE_OPENAI_ENDPOINT": "https://your-resource.openai.azure.com"
         }
       }
     }
   }

**Configuration Benefits:**

- ``--exclude-tool-types PackageTool``: Removes package management tools to save context window space if you don't have coding needs
- ``--hook-type SummarizationHook``: Provides summary of the output that is too long to fit in the context window
- ``AZURE_OPENAI_API_KEY`` and ``AZURE_OPENAI_ENDPOINT``: Required for SummarizationHook functionality

.. _gemini-500-tool-limit:

**Important: Gemini CLI 500 Tool Limit**

Gemini CLI has a **500 tool limit** per MCP server. ToolUniverse provides 1000+ tools by default, which exceeds this limit. **You must use one of the following solutions** to work within this limit:

**Solution 1: Space Configuration (Recommended for Gemini CLI)**

Use the pre-configured ``gemini-essential.yaml`` Space to access ~400-450 essential scientific tools.

**Download the configuration file:**

Download `gemini-essential.yaml <https://github.com/mims-harvard/ToolUniverse/blob/main/examples/spaces/gemini-essential.yaml>`_ from the ToolUniverse repository and save it to your project directory (e.g., ``./examples/spaces/gemini-essential.yaml``).

Alternatively, if you have cloned the ToolUniverse repository, the file is already available at ``examples/spaces/gemini-essential.yaml``.

**Configuration:**

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",
           "run",
           "tooluniverse-smcp-stdio",
           "--load",
           "./examples/spaces/gemini-essential.yaml"
         ]
       }
     }
   }

**Benefits of gemini-essential.yaml:**

- **Under 500 tools**: Carefully selected ~400-450 essential tools, well within Gemini CLI's limit
- **Ready to use**: No need to manually configure tool selection
- **Direct access**: All selected tools are directly available without additional discovery steps

**What's Included:**

- Core scientific databases (FDA, OpenTargets, UniProt, PubChem)
- Literature search tools (PubMed, Europe PMC, OpenAlex, Semantic Scholar)
- Clinical data tools (ClinicalTrials.gov, FAERS)
- Structural biology tools
- Genomics and molecular biology tools

**Solution 2: Compact Mode (Alternative for Minimal Context Usage)**

For maximum context window efficiency, use compact mode which exposes only 4-5 core tools:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",
           "run",
           "tooluniverse-smcp-stdio",
           "--compact-mode"
         ]
       }
     }
   }

**Compact Mode Benefits:**

- **99% reduction**: Only 4-5 tools exposed instead of 1000+
- **Full functionality**: All 1000+ tools still accessible via ``execute_tool``
- **Minimal context usage**: Ideal for AI agents with limited context windows
- **Progressive disclosure**: Use ``list_tools``, ``grep_tools``, and ``get_tool_info`` to discover tools on demand
- **Well within limit**: 4-5 tools is far below the 500 tool limit

**Compact Mode Tools:**

- ``list_tools``: List all available tools
- ``grep_tools``: Search for tools by name or pattern
- ``get_tool_info``: Get detailed information about specific tools
- ``execute_tool``: Execute any ToolUniverse tool

.. seealso::
   For detailed information about compact mode, see :doc:`../compact_mode`

**Which Solution Should You Choose?**

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Feature
     - Space Configuration
     - Compact Mode
   * - Tools Exposed
     - ~400-450 tools
     - 4-5 tools
   * - Direct Access
     - Yes, all selected tools
     - Via execute_tool
   * - Context Usage
     - Medium
     - Minimal (99% reduction)
   * - Tool Discovery
     - Not needed
     - Required (list_tools, grep_tools)
   * - Best For
     - Users who want direct access to common tools
     - Users who want minimal context usage

**Recommendation:**

- **Use Space Configuration** if you want direct access to commonly used scientific tools
- **Use Compact Mode** if you want minimal context usage and don't mind using tool discovery commands

**Important Configuration Notes**:

- Replace `/path/to/tooluniverse-env` with your actual ToolUniverse working directory
- The working directory is where uv will create and manage the virtual environment (`.venv`)
- The path should point to the directory where your Gemini CLI environment is set up
- Use absolute paths for better reliability

**Example Configuration**:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory
           "run",
           "tooluniverse-smcp-stdio"
         ]
       }
     }
   }

Step 5: Configure Context File (GEMINI.md)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a context file to provide project-specific instructions for scientific research:

1. **Create GEMINI.md file** in your project root:
   .. code-block:: bash

      vim GEMINI.md

2. **Add ToolUniverse-specific context**:
   .. code-block:: markdown

  # ToolUniverse Scientific Research Project

  ## General Instructions

  - Leverage ToolUniverse's scientific tools ecosystem for evidence-based research
  - Use tools from tooluniverse mcp server first
  - Cross-validate findings across multiple tools and databases
  - Use appropriate scientific terminology

3. **Verify context loading**:
   .. code-block:: bash

      /memory show

This will display the loaded context files and their content.

Step 6: Start Gemini CLI
~~~~~~~~~~~~~~~~~~~~~~~~

After saving the configuration:

1. **Start Gemini CLI**:
   .. code-block:: bash

      gemini

2. **Verify MCP Server Connection**:
   .. code-block:: bash

      /mcp

This will display:
- Server connection status (`CONNECTED` or `DISCONNECTED`)
- Available ToolUniverse tools
- Configuration details
- Any connection errors

Step 7: Verify Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test the integration by asking Gemini to:

1. **List available tools**:
   .. code-block::

      What scientific tools are available?

2. **Execute a simple tool**:
   .. code-block::

      Search for information about Alzheimer's disease

3. **Perform complex research**:
   .. code-block::

      Find recent papers about CRISPR gene editing in cancer therapy

Settings and Configuration
---------------------------

Tool Selection Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~

Optimize tool usage for better performance:

**Selective Tool Loading**:
- Load only relevant tools for specific research domains
- Reduce context window usage
- Improve response times

**Gemini CLI 500 Tool Limit**:
- See the :ref:`gemini-500-tool-limit` section in Step 4 above for detailed solutions
- Use ``gemini-essential.yaml`` Space configuration or compact mode to stay within limits

**Example Tool Selection**:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ],
         "includeTools": [
           "EuropePMC_search_articles",
           "ChEMBL_search_similar_molecules",
           "openalex_literature_search",
           "search_clinical_trials"
         ]
       }
     }
   }

**Custom Tool Sets**

Create custom tool sets for specific research domains:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse-literature": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ],
         "includeTools": [
           "EuropePMC_search_articles",
           "openalex_literature_search",
           "PubTator3_LiteratureSearch"
         ]
       },
       "tooluniverse-compounds": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ],
         "includeTools": [
           "ChEMBL_search_similar_molecules",
           "FDA_get_drug_names_by_indication",
           "drugbank_search"
         ]
       }
     }
   }

Multiple MCP Servers
~~~~~~~~~~~~~~~~~~~~

Run multiple ToolUniverse instances for different purposes:

.. code-block:: json

   {
     "mcpServers": {
       "tooluniverse-research": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ],
         "timeout": 30000
       },
       "tooluniverse-analysis": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
           "run",
           "tooluniverse-smcp-stdio"
         ],
         "timeout": 45000
       }
     }
   }

Troubleshooting
---------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**MCP Server Not Loading**:
- Verify ToolUniverse installation path
- Check UV package manager installation
- Ensure proper JSON syntax in configuration
- Check Gemini CLI logs for errors

**No Tools Discovered**:
- Verify the ToolUniverse MCP server is working
- Check if your `includeTools` or `excludeTools` filter is too restrictive
- Ensure all ToolUniverse dependencies are installed
- Review your ToolUniverse installation and configuration

**Tools Not Executing**:
- Check your `env` configuration for API keys
- Verify network connectivity to the required scientific APIs
- Increase the `timeout` value in your configuration
- Review parameter validation errors in the CLI output

**Performance Issues**:
- Increase the `timeout` value in the configuration
- Use `includeTools` to load only the necessary tools
- Check network connectivity and latency to external APIs
- Be mindful of potential rate limits for external services

Debug Mode
~~~~~~~~~~

Run the Gemini CLI with the `--debug` flag for detailed information:

.. code-block:: bash

   gemini --debug

This provides verbose output about:
- MCP server connection attempts
- The tool discovery process
- Tool execution details and errors


Tips
----------------

**Tool Selection**: Use `includeTools` to load only the tools you need for a specific task.

**Status Check**: Use `/mcp` to monitor server status and available tools.

**Debug Mode**: Use the `--debug` flag for verbose troubleshooting information.

.. tip::
   **Start with simple queries**: Begin with basic tool discovery and simple research questions to understand the integration, then progress to complex multi-step workflows as you become more familiar with the capabilities.

.. note::
   **Command-Line Efficiency**: Gemini CLI provides a powerful command-line interface for scientific research, enabling both interactive exploration and automated batch processing of research tasks.

Scientific Research Capabilities
=================================

Drug Discovery and Development
-------------------------------

Gemini CLI with ToolUniverse enables comprehensive drug discovery workflows:

**Target Identification**:
- Disease analysis and EFO ID lookup
- Target discovery and validation
- Literature-based target assessment

**Drug Analysis**:
- Drug information retrieval from multiple databases
- Safety profile analysis
- Drug interaction checking
- Clinical trial data access

**Example Workflow**:

.. code-block:: text

   User: Find FDA-approved drugs that target the EGFR protein and show me their chemical structures

   [Gemini uses ToolUniverse tools to:]
   1. Search FDA database for EGFR-targeting drugs
   2. Retrieve drug information and structures
   3. Analyze chemical properties
   4. Provide comprehensive drug profiles

Genomics and Molecular Biology
-------------------------------

Access comprehensive genomics tools for molecular research:

**Gene Analysis**:
- Gene information from UniProt
- Protein structure analysis
- Expression pattern analysis
- Pathway involvement

**Molecular Interactions**:
- Protein-protein interactions
- Drug-target interactions
- Pathway analysis
- Functional annotation

**Example Workflow**:

.. code-block:: text

   User: Analyze the BRCA1 gene and its role in cancer development

   [Gemini uses ToolUniverse tools to:]
   1. Get BRCA1 gene information from UniProt
   2. Analyze protein structure and function
   3. Find protein interactions
   4. Identify cancer-related pathways
   5. Search for therapeutic targets

Literature Research and Analysis
---------------------------------

Comprehensive literature search and analysis capabilities:

**Literature Search**:
- PubMed searches
- Semantic Scholar integration
- Europe PMC access
- Citation analysis

**Content Analysis**:
- Abstract summarization
- Key finding extraction
- Trend analysis
- Gap identification

**Example Workflow**:

.. code-block:: text

   User: Find recent papers about CRISPR gene editing in cancer therapy published in the last 2 years

   [Gemini uses ToolUniverse tools to:]
   1. Search PubMed for recent papers
   2. Filter by publication date
   3. Analyze abstracts and key findings
   4. Identify research trends
   5. Provide comprehensive review

Clinical Research and Trials
-----------------------------

Access clinical trial data and regulatory information:

**Clinical Trials**:
- ClinicalTrials.gov searches
- Trial status and results
- Patient population analysis
- Outcome assessment

**Regulatory Information**:
- FDA drug approvals
- Safety warnings
- Labeling information
- Adverse event reports

**Example Workflow**:

.. code-block:: text

   User: Find ongoing clinical trials for Alzheimer's disease treatments in the United States

   [Gemini uses ToolUniverse tools to:]
   1. Search ClinicalTrials.gov
   2. Filter by Alzheimer's disease and US location
   3. Analyze trial designs and outcomes
   4. Check FDA approvals
   5. Assess safety profiles

Multi-Step Research Workflows
-------------------------------

Gemini CLI excels at complex, multi-step research workflows:

**Hypothesis-Driven Research**:
1. Formulate research hypothesis
2. Design experimental approach
3. Gather supporting evidence
4. Validate findings
5. Generate conclusions

**Comparative Analysis**:
1. Identify comparison targets
2. Gather data for each target
3. Perform comparative analysis
4. Identify differences and similarities
5. Draw conclusions

**Example Multi-Step Workflow**:

.. code-block:: text

   User: I'm researching potential drug targets for Parkinson's disease. Can you:
   1. Find recent papers on Parkinson's disease drug targets
   2. Search for compounds that interact with those targets
   3. Check if there are any ongoing clinical trials for those compounds

   [Gemini executes multi-step workflow:]
   1. Search literature for Parkinson's disease drug targets
   2. Identify key targets and mechanisms
   3. Search for compounds interacting with targets
   4. Check clinical trial status
   5. Provide comprehensive analysis

Iterative Research and Refinement
-----------------------------------

Gemini can iteratively refine research based on intermediate results:

**Adaptive Research**:
- Start with broad search
- Refine based on initial results
- Focus on promising directions
- Validate findings with additional tools

**Example Iterative Workflow**:

.. code-block:: text

   User: Investigate potential treatments for rare genetic diseases

   [Gemini performs iterative research:]
   1. Initial broad search for rare disease treatments
   2. Analyze results and identify patterns
   3. Focus on gene therapy approaches
   4. Investigate specific gene therapy trials
   5. Analyze safety and efficacy data

Batch Processing and Automation
--------------------------------

Gemini CLI enables batch processing of multiple research tasks:

**Automated Workflows**:
- Process multiple queries simultaneously
- Generate comprehensive reports
- Export results in various formats
- Schedule recurring research tasks

**Example Batch Processing**:

.. code-block:: text

   User: Analyze the following genes for cancer association: BRCA1, BRCA2, TP53, EGFR, KRAS

   [Gemini processes batch analysis:]
   1. Analyze each gene individually
   2. Compare cancer associations
   3. Identify common pathways
   4. Generate comparative report
