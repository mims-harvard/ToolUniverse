Claude Code Setup
=================

**Connect ToolUniverse to Claude Code**

Claude Code integration combines Anthropic's reasoning model with ToolUniverse's 1000+ scientific tools in a development-focused environment.

.. tip:: 🚀 **Fastest setup — no installation needed**

   Open Claude Code and paste this single message:

   .. code-block:: text

      Please read https://raw.githubusercontent.com/mims-harvard/ToolUniverse/main/skills/setup-tooluniverse/SKILL.md and follow it to help me set up ToolUniverse.

   Claude Code will fetch the setup guide from GitHub and walk you through everything interactively.

Prerequisites
-------------

.. important:: ✅ **What you need:**
   
   - **Claude Code CLI** - Install via: ``npm install -g @anthropic-ai/claude-code``
   - **uv/uvx** - `Install uv <https://docs.astral.sh/uv/>`_

.. seealso:: `Claude Code MCP official guide <https://docs.anthropic.com/en/docs/claude-code/mcp>`_

Setup Steps
-----------

.. card:: Step 1: Configure MCP Server
   :class-card: step-card current

   Add ToolUniverse MCP server to Claude Code:

   .. code-block:: bash

      claude mcp add --transport stdio tooluniverse -- uvx tooluniverse

   .. dropdown:: 💡 What does this do?
      :animate: fade-in-slide-down
      :color: info

      - ``--transport stdio``: Uses standard input/output for communication
      - ``tooluniverse``: Server name (the label stored in Claude Code)
      - ``uvx tooluniverse``: Runs the ToolUniverse MCP stdio server via uvx (no separate install needed)

.. card:: Step 2: Install Agent Skills (Optional)
   :class-card: step-card pending

   .. code-block:: bash

      npx skills add mims-harvard/ToolUniverse

.. card:: Step 3: Start Claude Code
   :class-card: step-card pending

   Launch Claude Code with ToolUniverse:

   .. code-block:: bash

      claude

.. card:: Step 4: Verify Integration
   :class-card: step-card pending

   Test in Claude Code:

   .. code-block:: text

      "List available ToolUniverse tools"
      "Find protein P05067 function"

   .. success:: ✅ **Working!**
      
      Claude Code can now access scientific tools!

Example Workflows
-----------------

.. tab-set::

   .. tab-item:: Drug Discovery

      .. code-block:: text

         "Search ChEMBL for compounds similar to aspirin,
         then analyze their ADMET properties"

   .. tab-item:: Code Generation

      .. code-block:: text

         "Write a Python script that:
         1. Searches PubMed for COVID-19 papers
         2. Extracts key findings
         3. Saves to CSV"

   .. tab-item:: Data Analysis

      .. code-block:: text

         "Get gene expression data for BRCA1 from GTEx,
         analyze tissue specificity, create visualization"

Advanced Configuration
----------------------

.. dropdown:: 🎛️ Load Specific Tool Categories
   :animate: fade-in-slide-down
   :color: primary

   .. code-block:: bash

      claude mcp add --transport stdio tooluniverse -- \
        uvx tooluniverse \
        --tool-categories uniprot,chembl,opentarget

.. dropdown:: 🔑 API Keys
   :animate: fade-in-slide-down
   :color: info

   Set environment variables:

   .. code-block:: bash

      export NCBI_API_KEY=your_key
      export SEMANTIC_SCHOLAR_API_KEY=your_key

Troubleshooting
---------------

.. dropdown:: ❌ MCP server not found
   :color: danger

   Ensure ``uvx`` is installed and working:

   .. code-block:: bash

      uvx --version
      uvx tooluniverse --help


Next Steps
----------

.. button-ref:: index
   :color: secondary
   :shadow:
   :expand:

   ← **Back to Platform Selector**

.. seealso::
   - :doc:`../finding_tools` - Tool discovery
   - :doc:`../scientific_workflows` - Workflow patterns
   - :doc:`../../help/troubleshooting` - Common issues
