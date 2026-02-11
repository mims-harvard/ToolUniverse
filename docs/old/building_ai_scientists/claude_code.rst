Claude Code
=============================

**Building AI Scientists with Claude Code and ToolUniverse**

Overview
--------

Claude Code integration enables powerful IDE- or terminal-based scientific research through the Model Context Protocol (MCP). This approach provides a developer-friendly interface for research while leveraging Claude's advanced reasoning and ToolUniverse's 1000+ scientific tools.

.. code-block:: text

   ┌─────────────────┐
   │   Claude Code   │ ← IDE/CLI Interface & Reasoning
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

**Benefits of Claude Code Integration**:

- **Developer Workflow**: Use Claude inside VS Code/JetBrains or terminal
- **Advanced Reasoning**: Claude's strong multi-step reasoning
- **Comprehensive Tools**: Access to 1000+ ToolUniverse tools
- **Automated Execution**: Natural-language to tools, directly in your editor
- **Batch & Iteration**: Run multi-step research loops effectively

Prerequisites
-------------

Before setting up Claude Code integration, ensure you have:

- **Claude Code**: Installed in your IDE or CLI
- **Python 3.10+**: macOS, Windows, or Linux
- **API Keys** (optional): For specific tools or hooks (e.g., Azure OpenAI for summarization)

Installation and Setup
----------------------

Step 0: Install Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install Claude Code in your terminal (any OS with Node.js 18+):

.. code-block:: bash

   # Standard (recommended)
   npm install -g @anthropic-ai/claude-code

Verify and diagnose your installation:

.. code-block:: bash

   claude doctor

Native installer (beta) alternatives:

.. code-block:: bash

   # macOS/Linux/WSL: stable
   curl -fsSL https://claude.ai/install.sh | bash
   # latest
   curl -fsSL https://claude.ai/install.sh | bash -s latest

On Windows PowerShell:

.. code-block:: powershell

   irm https://claude.ai/install.ps1 | iex

After installation, you can start Claude Code in a project:

.. code-block:: bash

   cd your-project
   claude

For details, see: `Anthropic — Set up Claude Code <https://docs.anthropic.com/en/docs/claude-code/setup>`_.

For Windows installation, see: `Anthropic — Windows setup <https://docs.anthropic.com/en/docs/claude-code/setup#windows-setup>`_.

Step 1: Install ToolUniverse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Using pip
   pip install tooluniverse

   # Or using uv (faster)
   uv pip install tooluniverse

Step 2: Add ToolUniverse to Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   claude mcp add --transport stdio tooluniverse -- tooluniverse-smcp-stdio --compact-mode

   # Verify it was added successfully
   claude mcp list

You should see ``tooluniverse`` in the list of MCP servers. The ``--compact-mode`` flag optimizes tool descriptions for better context efficiency.

Step 3: Verify in IDE/CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

After saving the configuration, verify connectivity:

- Terminal (Claude Code CLI)
  - Launch in your project:

    .. code-block:: bash

       cd /path/to/your-project
       claude

  - In the chat, ask: "What ToolUniverse tools are available?"
  - If issues occur, run diagnostics:

    .. code-block:: bash

       claude doctor

  - For terminal configuration, see: `Claude Code CLI reference <https://docs.anthropic.com/en/docs/claude-code/cli-reference>`_

- VS Code
  - Restart VS Code, then open Command Palette and run: "Claude: Open Chat"
  - Ask: "What ToolUniverse tools are available?"
  - If tools don't appear, check `.claude/settings.local.json` and reload window
  - For VS Code setup, see: `Add Claude Code to your IDE <https://docs.anthropic.com/en/docs/claude-code/add-claude-code-to-your-ide>`_

- JetBrains (IntelliJ/PyCharm/etc.)
  - Restart IDE → open the Claude tool window
  - Ask: "What ToolUniverse tools are available?"
  - If tools don't appear, review Tools → Claude Code → MCP Servers settings
  - For JetBrains setup, see: `Add Claude Code to your IDE <https://docs.anthropic.com/en/docs/claude-code/add-claude-code-to-your-ide>`_

Scientific Research Capabilities
--------------------------------

Drug Discovery and Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code with ToolUniverse enables comprehensive drug discovery workflows:

**Target Identification**:
- Disease analysis and EFO ID lookup
- Target discovery and validation
- Literature-based target assessment

**Drug Analysis**:
- Drug information retrieval from multiple databases
- Safety profile analysis
- Drug interaction checking
- Clinical trial data access

Genomics and Molecular Biology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Literature Research and Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive literature search and analysis capabilities:

**Literature Search**:
- PubMed, Europe PMC, and Semantic Scholar
- Citation analysis and trend detection

**Content Analysis**:
- Abstract summarization
- Key finding extraction
- Gap identification

Multi-Step Research Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code excels at complex, multi-step research workflows:

**Hypothesis-Driven Research**:
1. Formulate a hypothesis
2. Design an approach and select tools
3. Gather supporting evidence
4. Validate findings
5. Generate conclusions

Advanced Configuration
----------------------

Tool Selection
~~~~~~~~~~~~~~

Load only specific tools for focused research domains:

.. code-block:: bash

   # Add ToolUniverse with specific tools only
   claude mcp add --transport stdio tooluniverse -- tooluniverse-smcp-stdio --compact-mode --include-tools EuropePMC_search_articles,ChEMBL_search_similar_molecules,openalex_literature_search

Summarization Hook
~~~~~~~~~~~~~~~~~~

Enable automatic summarization for long outputs (requires Azure OpenAI):

.. code-block:: bash

   claude mcp add --transport stdio tooluniverse --env AZURE_OPENAI_API_KEY=your-key --env AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com -- tooluniverse-smcp-stdio --compact-mode --hook-type SummarizationHook

Multiple Instances
~~~~~~~~~~~~~~~~~~

Run separate instances for different purposes:

.. code-block:: bash

   # Literature research instance
   claude mcp add --transport stdio tooluniverse-literature -- tooluniverse-smcp-stdio --compact-mode --include-tools EuropePMC_search_articles,openalex_literature_search

   # Drug analysis instance
   claude mcp add --transport stdio tooluniverse-drugs -- tooluniverse-smcp-stdio --compact-mode --include-tools ChEMBL_search_similar_molecules,search_clinical_trials

   # List all servers
   claude mcp list

   # Remove a server
   claude mcp remove tooluniverse-literature

Troubleshooting
---------------

**MCP Server Not Loading**:

- Verify ToolUniverse is installed: ``python -c "import tooluniverse; print('OK')"``
- Check server status: ``claude mcp list``
- Run diagnostics: ``claude doctor``

**No Tools Discovered**:

- Check if tool filters are too restrictive
- Verify the command works: ``tooluniverse-smcp-stdio --help``

**Tools Not Executing**:

- Provide required API keys via ``--env`` flags
- Verify network connectivity

For more help, see: `Claude Code troubleshooting <https://docs.anthropic.com/en/docs/claude-code/troubleshooting>`_.
