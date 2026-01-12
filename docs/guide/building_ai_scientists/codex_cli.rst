GPT Codex CLI
=============================

**Building AI Scientists with GPT Codex CLI and ToolUniverse**

Overview
--------

GPT Codex CLI integration enables powerful command-line-based scientific research through the Model Context Protocol (MCP). This approach provides a terminal-based interface for scientific research while leveraging Codex's advanced reasoning capabilities and ToolUniverse's comprehensive scientific tools ecosystem.

.. code-block:: text

   ┌─────────────────┐
   │   Codex CLI     │ ← Command Line Interface & Reasoning
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
   │ 600+ Scientific │ ← Scientific Tools Ecosystem
   │     Tools       │
   └─────────────────┘

**Benefits of Codex CLI Integration**:

- **Command-Line Efficiency**: Fast, scriptable scientific research workflows
- **Advanced Reasoning**: Codex's sophisticated reasoning for complex scientific problems
- **Comprehensive Tools**: Access to 600+ scientific tools across multiple domains
- **Automated Execution**: Direct tool execution through natural language commands
- **Batch Processing**: Handle multiple research tasks efficiently

Installation and Setup
----------------------


- **Codex CLI**: Install using npm or Homebrew
- **Python 3.10+**: Required for ToolUniverse
- **UV Package Manager**: For dependency management
- **ChatGPT Account**: For authentication (recommended)

Step 1: Install Codex CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: bash

   # Using npm (recommended):
   npm install -g @openai/codex

   # OR Using Homebrew (macOS/Linux):
   brew install codex

   #Verify installation:
   codex --version

Step 2: Install UV and ToolUniverse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Create working directory for ToolUniverse   
   mkdir -p /path/to/tooluniverse-env
   cd /path/to/tooluniverse-env
   # uv will create a virtual environment (.venv) inside this directory
   uv venv
   # uv will install tooluniverse and all its dependencies
   uv pip install tooluniverse

   # Verify installation
   cd ~
   uv --directory /path/to/tooluniverse-env run python -c "import tooluniverse; print('ToolUniverse installed successfully')"

Step 3: Configure Codex CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the configuration file:

.. code-block:: bash

   mkdir -p ~/.codex
   vim ~/.codex/config.toml

Add the ToolUniverse MCP server configuration:

.. code-block:: toml

   [mcp_servers.tooluniverse]
   command = "uv"
   args = [
     "--directory",
     "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
     "run",
     "tooluniverse-smcp-stdio"
   ]

.. dropdown:: Advanced Settings

   .. code-block:: toml

      [mcp_servers.tooluniverse]
      command = "uv"
      args = [
        "--directory",
        "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
        "run",
        "tooluniverse-smcp-stdio",
        "--exclude-tool-types",
        "PackageTool",
        "--hook-type",
        "SummarizationHook"
      ]

      [mcp_servers.tooluniverse.env]
      AZURE_OPENAI_API_KEY = "your-azure-openai-api-key"
      AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com"

   **Configuration Benefits:**

   - ``--exclude-tool-types PackageTool``: Removes package management tools to save context window space if you don't have coding needs
   - ``--hook-type SummarizationHook``: Provides summary of the output that is too long to fit in the context window
   - ``AZURE_OPENAI_API_KEY`` and ``AZURE_OPENAI_ENDPOINT``: Required for SummarizationHook functionality

Step 4: Authenticate and Start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Sign in with ChatGPT (recommended):**

.. code-block:: bash

   codex

Select **Sign in with ChatGPT** when prompted.

**Or use API key:**

.. code-block:: bash

   export OPENAI_API_KEY="your-api-key-here"
   codex

Step 5: Configure Context File (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a context file to provide project-specific instructions for scientific research:

1. **Create AGENTS.md file** in your project root:

   .. code-block:: bash

      vim AGENTS.md

2. **Add ToolUniverse-specific context**:

   .. code-block:: markdown

      # ToolUniverse Scientific Research Project

      ## General Instructions

      - Leverage ToolUniverse's scientific tools ecosystem for evidence-based research
      - Use tools from tooluniverse mcp server first
      - Cross-validate findings across multiple tools and databases
      - Use appropriate scientific terminology
      - Follow systematic research methodologies

Step 6: Verify Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Start Codex CLI: ``codex``
2. Check MCP status: ``/mcp``
3. Test with: ``What scientific tools are available?``

Scientific Research Capabilities
--------------------------------

Codex CLI with ToolUniverse provides comprehensive scientific research capabilities:

**Drug Discovery and Development**
- Target identification and validation
- Drug information retrieval and analysis
- Safety profile analysis and clinical trial data

**Genomics and Molecular Biology**
- Gene analysis from UniProt
- Protein structure and interaction analysis
- Pathway analysis and functional annotation

**Literature Research**
- PubMed and Semantic Scholar searches
- Abstract summarization and trend analysis
- Citation analysis and gap identification

**Clinical Research**
- ClinicalTrials.gov searches
- FDA approvals and safety information
- Regulatory information access

**Multi-Step Workflows**
- Hypothesis-driven research
- Comparative analysis
- Complex research task automation


Advanced Configuration
-----------------------

**Tool Selection**

Load only specific tools for better performance:

.. code-block:: toml

   [mcp_servers.tooluniverse]
   command = "uv"
   args = [
     "--directory",
     "/path/to/tooluniverse-env",  # Working directory: uv manages .venv here
     "run",
     "tooluniverse-smcp-stdio",
     "--include-tools",
     "EuropePMC_search_articles",
     "ChEMBL_search_similar_molecules",
     "search_clinical_trials"
   ]

**Multiple Servers**

Run different ToolUniverse instances for different purposes:

.. code-block:: toml

   [mcp_servers.tooluniverse-research]
   command = "uv"
   args = ["--directory", "/Users/username/tooluniverse-env", "run", "tooluniverse-smcp-stdio"]  # Working directory
   startup_timeout_sec = 60

   [mcp_servers.tooluniverse-analysis]
   command = "uv"
   args = ["--directory", "/Users/username/tooluniverse-env", "run", "tooluniverse-smcp-stdio"]  # Working directory
   startup_timeout_sec = 60

Troubleshooting
---------------

**Step-by-Step Debugging:**

1. **Check Codex CLI Version:**
   .. code-block:: bash

      codex --version

   Ensure you're using the latest version. Older versions may have MCP server issues.

2. **Verify Configuration File:**
   .. code-block:: bash

      cat ~/.codex/config.toml

   Ensure the file exists and has correct TOML syntax.

3. **Test MCP Server Manually:**
   .. code-block:: bash

      uv --directory /path/to/tooluniverse-env run tooluniverse-smcp-stdio

   This should start the MCP server directly to check if it works.

4. **Check Codex CLI Logs:**
   .. code-block:: bash

      DEBUG=true codex

   This enables detailed logging to see MCP server connection errors.

5. **Verify MCP Server Status:**
   Start Codex CLI and run:
   .. code-block::

      codex
      /mcp

   Check if ToolUniverse tools are listed.

6. **Check Available Commands:**
   .. code-block:: bash

      codex --help

   View all available Codex CLI options.

**Common Issues:**

- **MCP Server Not Loading**: Check ToolUniverse installation path and UV installation
- **No Tools Discovered**: Verify MCP server is working and tool filters aren't too restrictive
- **Tools Not Executing**: Check API keys and network connectivity
- **Authentication Issues**: Ensure ChatGPT sign-in or valid API key

**Debug Commands:**

- ``DEBUG=true codex``: Run with detailed logging
- ``codex --help``: Show all available options
- ``/mcp``: Show MCP server status (if available)

References
----------

- `Codex CLI GitHub Repository <https://github.com/openai/codex>`_
- `Codex CLI Documentation <https://github.com/openai/codex/tree/main/docs>`_
- `Model Context Protocol (MCP) <https://modelcontextprotocol.io/>`_
- `ToolUniverse Documentation <https://tooluniverse.readthedocs.io/>`_
