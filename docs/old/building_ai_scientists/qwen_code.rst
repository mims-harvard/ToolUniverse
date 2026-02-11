Qwen Code
=============================

**Building AI Scientists with Qwen Code and ToolUniverse**

.. image:: /_static/qwen_code.jpg
   :alt: Qwen Code integrates with ToolUniverse via MCP
   :align: center
   :width: 720px

Overview
--------

Qwen Code is a coding agent CLI that can query and edit large codebases and automate workflows. Integrated with the Model Context Protocol (MCP), it can connect to ToolUniverse to power evidence-based scientific research from your terminal.

.. code-block:: text

   ┌──────────────┐
   │  Qwen Code   │ ← Command Line Interface & Reasoning
   │              │
   └──────┬───────┘
          │ MCP Protocol
          │
   ┌──────▼───────┐
   │ ToolUniverse │ ← MCP Server
   │   MCP Server │
   └──────┬───────┘
          │
   ┌──────▼───────┐
   │ 1000+ Scientific Tools │
   └───────────────────────┘

**Benefits of Qwen Code Integration**:

- **Command-Line Efficiency**: Scriptable, terminal-first scientific workflows
- **Advanced Reasoning**: Qwen Coder models optimized for code and tooling
- **Comprehensive Tools**: Access 1000+ scientific tools via ToolUniverse
- **Automated Execution**: Natural language to tool execution
- **Batch Processing**: Efficient multi-task research

Prerequisites
-------------

Before setting up Qwen Code integration, ensure you have:

- **Qwen Code**: Installed and runnable (`qwen --version`)
- **ToolUniverse**: Installed
- **UV Package Manager**: For running the MCP server
- **System Requirements**: macOS, Windows, or Linux with Python 3.10+
- **API Keys**: For tools and optional summarization hooks

Installation and Setup
----------------------

Command Legend
~~~~~~~~~~~~~~

- System terminal (your shell: zsh/bash): run installation and file editing commands
- Qwen Code prompt (inside `qwen`): run slash commands like ``/mcp``, ``/stats``, ``/memory show``

Step 1: Install Qwen Code
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can install Qwen Code via npm or Homebrew.

.. code-block:: bash

   # From npm (requires Node.js >= 20)
   npm install -g @qwen-code/qwen-code@latest
   qwen --version

   # Or install from source
   git clone https://github.com/QwenLM/qwen-code.git
   cd qwen-code
   npm install
   npm install -g .

   # Or install with Homebrew (macOS/Linux)
   brew install qwen-code

For details, see the official repository `Qwen Code on GitHub <https://github.com/QwenLM/qwen-code>`_.

Step 2: Install ToolUniverse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install tooluniverse

Verify installation:

.. code-block:: bash

   python -c "import tooluniverse; print('ToolUniverse installed successfully')"

Step 3: Locate Qwen Code Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qwen Code reads settings from a home directory config at ``~/.qwen/settings.json`` or from a project-local ``.qwen/settings.json``.

Create or open your settings file:

.. code-block:: bash

   # Global configuration
   mkdir -p ~/.qwen
   vim ~/.qwen/settings.json

   # Or project-specific configuration
   mkdir -p .qwen
   vim .qwen/settings.json

Note: These commands are run in your system terminal.

Step 4: Configure ToolUniverse MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the ToolUniverse MCP server configuration to your Qwen settings ``settings.json``.

Note: Edit the JSON in your system terminal/editor.

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

- ``--exclude-tool-types PackageTool``: Saves context if you don't need coding package tools
- ``--hook-type SummarizationHook``: Summarizes long outputs to fit context
- ``AZURE_OPENAI_*``: Required for SummarizationHook

**Important Notes**:

- Replace `/path/to/tooluniverse-env` with your actual ToolUniverse working directory
- The working directory is where uv will create and manage the virtual environment (`.venv`)
- Prefer absolute paths for reliability

Step 5: Configure Context File (QWEN.md)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can provide project-specific research instructions to Qwen Code using a context file.

1. **Create QWEN.md** in your project root:

   .. code-block:: bash

      vim QWEN.md

2. **Add ToolUniverse-specific context**:

   .. code-block:: markdown

      # ToolUniverse Scientific Research Project

      ## General Instructions

      - Use ToolUniverse's scientific tools ecosystem for evidence-based research
      - Prefer tools from the `tooluniverse` MCP server first
      - Cross-validate findings across multiple sources
      - Use appropriate scientific terminology

Step 6: Start Qwen Code and Verify MCP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Start Qwen Code**:

   .. code-block:: bash

      qwen

   Note: Run this in your system terminal.

2. **Verify MCP Server Connection**:

   In the Qwen Code prompt, run:

   .. code-block::

      /mcp

3. **Verify context loading**:

   Enter
   In the Qwen Code prompt, run:

   .. code-block::

      /memory show


For authentication methods (OAuth and API keys), see: `Authorization (Qwen Code README) <https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authorization>`_.


This will display connection status, available ToolUniverse tools, configuration details, and any errors.

Step 7: Verify Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Try these prompts inside Qwen Code:

**List available tools**:

   .. code-block::

      What scientific tools are available?

**Execute a simple tool**:

   .. code-block::

      Search for information about Alzheimer's disease

**Perform literature search**:

   .. code-block::

      Find recent papers about CRISPR gene editing in cancer therapy

Scientific Research Capabilities
--------------------------------

Drug Discovery and Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With ToolUniverse, Qwen Code supports comprehensive drug discovery workflows:

**Target Identification**:
- Disease analysis and EFO ID lookup
- Target discovery and validation
- Literature-based assessment

**Drug Analysis**:
- Drug information retrieval
- Safety profile analysis
- Drug interaction checking
- Clinical trial data access

Genomics and Molecular Biology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access genomics tools for molecular research:

**Gene Analysis**:
- Gene information from UniProt
- Protein structure analysis
- Expression patterns and pathways

**Molecular Interactions**:
- Protein-protein and drug-target interactions
- Pathway analysis and functional annotation

Literature Research and Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Perform literature search and analysis:

**Literature Search**:
- PubMed, Europe PMC, Semantic Scholar
- Citation analysis and filtering

**Content Analysis**:
- Abstract summarization and key finding extraction
- Trend analysis and gap identification

Settings and Configuration
---------------------------

Tool Selection Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~

Optimize tool usage:

**Selective Tool Loading**:

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
- Use ``/stats`` to confirm session info and limits

**No Tools Discovered**:
- Verify the ToolUniverse MCP server is working
- Check if your ``includeTools`` or ``excludeTools`` filter is too restrictive
- Ensure all ToolUniverse dependencies are installed

**Tools Not Executing**:
- Check your ``env`` configuration for needed API keys
- Verify network connectivity
- Increase the ``timeout`` value

Debug and Session Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qwen Code provides built-in session commands:

- ``/compress``: Compress conversation history to stay within token limits
- ``/clear``: Clear history and start fresh
- ``/stats``: Show current session token usage and limits

Authentication Options
----------------------

Qwen Code supports multiple authentication methods.

**1. Qwen OAuth (Recommended)**

Start Qwen Code and follow the browser-based login.

.. code-block:: bash

   qwen

Benefits include generous free-tier quotas and automatic credential management. See `Qwen Code on GitHub <https://github.com/QwenLM/qwen-code>`_.

**2. OpenAI-Compatible API**

Configure environment variables or a project ``.env`` file:

.. code-block:: bash

   export OPENAI_API_KEY="your_api_key_here"
   export OPENAI_BASE_URL="your_api_endpoint"
   export OPENAI_MODEL="your_model_choice"

For regional guidance and provider options (Bailian, ModelScope, ModelStudio, OpenRouter), refer to the repository docs: `Qwen Code on GitHub <https://github.com/QwenLM/qwen-code>`_.

Tips
----

**Tool Selection**: Use ``includeTools`` to load only necessary tools.

**Status Check**: Use ``/mcp`` to confirm server status and available tools.

**Session Control**: Use ``/compress`` and ``/stats`` to manage token usage.

References
----------

- Qwen Code repository: `https://github.com/QwenLM/qwen-code <https://github.com/QwenLM/qwen-code>`_
